import os
import re
import json
import time
from openai import OpenAI, RateLimitError

from models.schemas import ProjectPlan, GeneratedFile, DeveloperOutput, Task
from rag.knowledge_base import retrieve_patterns


# Tasks that produce no source file. Test tasks are deliberately NOT listed here:
# the planner always emits a test task and the TesterAgent needs real tests to run, so
# matching "unit test" (which also matched "JUnit tests") silently discarded them and
# left `mvn test` with nothing to execute.
SKIP_KEYWORDS = ["documentation", "readme", "deploy", "ci/cd", "pipeline setup"]

BASE_PACKAGE = "com.example"


def _slugify_module(project_name: str) -> str:
    """Turns 'Calculator App' into 'calculator_app' -- used for the Maven artifactId
    and as the last segment of the Java package name."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", project_name).strip("_").lower()
    if not cleaned:
        cleaned = "app"
    if cleaned[0].isdigit():
        cleaned = "app_" + cleaned
    return cleaned


def _repair_double_escaping(content: str) -> str:
    if "\\n" in content or '\\"' in content or "\\t" in content:
        content = (
            content.replace('\\r\\n', '\n')
                   .replace('\\n', '\n')
                   .replace('\\t', '\t')
                   .replace('\\"', '"')
        )
    return content


class RateLimitStop(Exception):
    """Raised to halt the whole pipeline immediately when the daily token quota is hit
    (i.e. even after retrying with backoff, it's still failing)."""
    pass


class DeveloperAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "openai/gpt-oss-120b"

    def _is_code_task(self, task: Task) -> bool:
        title_lower = task.title.lower()
        return not any(keyword in title_lower for keyword in SKIP_KEYWORDS)

    def _salvage_multi_file_response(self, error: Exception) -> list["GeneratedFile"] | None:
        body = getattr(error, "body", None)
        if not isinstance(body, dict):
            return None

        failed_gen = body.get("error", {}).get("failed_generation")
        if not failed_gen:
            return None

        wrapped = failed_gen.strip()
        if not wrapped.startswith("["):
            wrapped = f"[{wrapped}]"

        try:
            file_dicts = json.loads(wrapped)
        except json.JSONDecodeError:
            return None

        results = []
        for fd in file_dicts:
            if "path" not in fd or "content" not in fd:
                continue
            content = _repair_double_escaping(fd["content"])
            results.append(GeneratedFile(path=fd["path"], content=content))

        return results or None

    def _generate_file_for_task(self, plan: ProjectPlan, task: Task, existing_files: list[GeneratedFile], package_name: str) -> list[GeneratedFile]:

        java_package = f"{BASE_PACKAGE}.{package_name}"
        src_root = f"src/main/java/{java_package.replace('.', '/')}"

        entities_str = "\n".join(f"- {e.name}: {e.fields}" for e in plan.entities) or "(none)"
        endpoints_str = "\n".join(f"- {ep.method} {ep.path} - {ep.description}" for ep in plan.endpoints) or "(none -- not a web API)"
        existing_paths = "\n".join(f"- {f.path}" for f in existing_files) if existing_files else "(none yet)"

        retrieved = retrieve_patterns(task.title, task.description)
        if retrieved:
            reference_str = "\n\n".join(f"[{p['title']}]\n{p['snippet']}" for p in retrieved)
        else:
            reference_str = "(no specific pattern retrieved)"

        prompt = f"""
You are a Java Spring Boot Developer Agent. Write idiomatic, complete, compilable Java
using Spring Boot 3.x conventions (Java 17+). The output is ALWAYS Java/Spring Boot --
never Python, Flask, or any other stack, regardless of anything in the task description.

PROJECT CONTEXT:
Java base package: {java_package}
Maven artifactId: {package_name}
Modules: {plan.modules}
Tech notes: {plan.tech_notes}

ENTITIES:
{entities_str}

ENDPOINTS:
{endpoints_str}

FILES ALREADY GENERATED (for consistent naming/imports/package declarations):
{existing_paths}

REFERENCE PATTERNS (retrieved for this task type -- follow this style/structure):
{reference_str}

CURRENT TASK:
[{task.task_id}] {task.title}
{task.description}

Generate the ONE file needed to complete this exact task. It will be one of:
- "pom.xml" (Maven build file, at the project root) -- include spring-boot-starter-web,
  spring-boot-starter-data-jpa, spring-boot-starter-validation, com.h2database:h2 (or the
  DB specified in tech_notes), spring-boot-starter-test, and the spring-boot-maven-plugin.
- "src/main/resources/application.properties"
- A Java class/interface under "{src_root}/<subpackage>/<ClassName>.java" -- use subpackages
  "entity", "repository", "service", "controller", "dto", "config", or "exception" as
  appropriate, matching the task.
- A JUnit 5 test class under "src/test/java/{java_package.replace('.', '/')}/<subpackage>/<ClassName>Test.java"

Respond with ONLY a JSON object in this exact shape (no markdown, no explanation):
{{
  "path": "<correct relative path per the rules above>",
  "content": "<full file content as a single string, with \\n for newlines>"
}}

IMPORTANT: return exactly ONE file object, for ONE class/file, even if the task title
mentions multiple things. If the task genuinely needs more than one file, generate only
the first/primary one -- a separate task will handle the rest.

Rules:
- Every Java file must start with the correct "package {java_package}.<subpackage>;" line
  and correct imports -- no placeholders like "// TODO implement".
- Keep class/field names consistent with what's implied by ENTITIES and already-generated
  files.
  - Every Maven dependency MUST include an explicit <version> tag - never omit it.
- Prefer the H2 in-memory database (already usable for this project) instead of adding external database drivers like MySQL/PostgreSQL, unless the requirement explicitly demands production persistence. H2 avoids setup complexity and is ideal for a demo.
- Controllers use @RestController + @RequestMapping; Services use @Service; Repositories
  extend JpaRepository<Entity, Long>; Entities use @Entity/@Id/@GeneratedValue.
- Test files use JUnit 5 (@Test, org.junit.jupiter.api) and Mockito where relevant.
- pom.xml must be complete and valid XML, buildable with `mvn compile`.
"""

        max_retries = 4
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert Java Spring Boot developer. Always respond with valid JSON only, no markdown fences. You never generate Python, Flask, or non-Java output."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                raw = response.choices[0].message.content
                data = json.loads(raw)
                content = _repair_double_escaping(data["content"])
                return [GeneratedFile(path=data["path"], content=content)]
            except RateLimitError as e:
                if attempt == max_retries:
                    raise RateLimitStop(
                        f"Daily/rate token limit hit while generating [{task.task_id}] {task.title}, "
                        f"even after {max_retries} retries with backoff. Stopping the run now. "
                        f"Original error: {e}"
                    )
                wait = 2 ** attempt
                print(f"     Rate-limited, waiting {wait}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait)
                last_error = e
            except Exception as e:
                salvaged = self._salvage_multi_file_response(e)
                if salvaged:
                    print(f"     Recovered {len(salvaged)} file(s) from a multi-file response")
                    return salvaged
                last_error = e

        raise RuntimeError(f"Failed after {max_retries} attempts: {last_error}")

    def develop(self, plan: ProjectPlan, project_name: str) -> DeveloperOutput:

        package_name = _slugify_module(project_name)

        files: list[GeneratedFile] = []
        notes: list[str] = []
        seen_paths: dict[str, str] = {}

        code_tasks = [t for t in plan.tasks if self._is_code_task(t)]

        for task in code_tasks:
            print(f"  -> Generating file for [{task.task_id}] {task.title} ...")
            try:
                generated_files = self._generate_file_for_task(plan, task, files, package_name)

                for generated in generated_files:
                    if generated.path in seen_paths:
                        note = f"[{task.task_id}] overwrote file at '{generated.path}' originally created by [{seen_paths[generated.path]}] - merging not yet supported, keeping latest version."
                        notes.append(note)
                        print(f"     Note: {note}")
                        files = [f for f in files if f.path != generated.path]

                    seen_paths[generated.path] = task.task_id
                    files.append(generated)

            except RateLimitStop as e:
                notes.append(str(e))
                print(f"     STOPPING RUN: {e}")
                break
            except Exception as e:
                notes.append(f"Failed to generate file for {task.task_id} ({task.title}): {e}")
                print(f"     Failed: {e}")

        # Guard: catch stack drift before it silently reports "success".
        has_java = any(f.path.endswith(".java") for f in files)
        has_pom = any(f.path.endswith("pom.xml") for f in files)
        has_python = any(f.path.endswith(".py") for f in files)

        if has_python:
            notes.append("WARNING: Python file(s) were generated for a Java/Spring Boot project. This indicates prompt/stack drift and should be investigated.")
        if not has_pom:
            notes.append("WARNING: No pom.xml was generated -- this project will not build with Maven.")
        if not has_java:
            notes.append("WARNING: No .java files were generated -- this is not a valid Spring Boot output.")

        return DeveloperOutput(files=files, notes=notes)