import os
import re
import json
import time
from openai import OpenAI, RateLimitError

from models.schemas import ProjectPlan, GeneratedFile, DeveloperOutput, Task
from rag.knowledge_base import retrieve_patterns


SKIP_KEYWORDS = ["unit test", "integration test", "write test"]


def _slugify_module(project_name: str) -> str:
    """Turns 'Calculator App' into 'calculator_app' -- a valid Python package name."""
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

        entities_str = "\n".join(f"- {e.name}: {e.fields}" for e in plan.entities) or "(none)"
        endpoints_str = "\n".join(f"- {ep.method} {ep.path} - {ep.description}" for ep in plan.endpoints) or "(none -- not a web API)"
        existing_paths = "\n".join(f"- {f.path}" for f in existing_files) if existing_files else "(none yet)"

        retrieved = retrieve_patterns(task.title, task.description)
        if retrieved:
            reference_str = "\n\n".join(f"[{p['title']}]\n{p['snippet']}" for p in retrieved)
        else:
            reference_str = "(no specific pattern retrieved)"

        prompt = f"""
You are a Python Developer Agent. Write plain, idiomatic Python (standard library first).
Only use a third-party package (flask, requests, etc.) if plan.tech_notes explicitly calls
for it -- otherwise stick to stdlib (tkinter for GUIs, unittest/pytest for tests, argparse
for CLIs).

PROJECT CONTEXT:
Package/folder name: {package_name}
Modules: {plan.modules}
Tech notes: {plan.tech_notes}

ENTITIES:
{entities_str}

ENDPOINTS:
{endpoints_str}

FILES ALREADY GENERATED (for consistent naming/imports):
{existing_paths}

REFERENCE PATTERNS (retrieved for this task type):
{reference_str}

CURRENT TASK:
[{task.task_id}] {task.title}
{task.description}

Generate the Python file (or requirements.txt / config file) needed to complete this exact task.
Use the reference patterns above as a style/structure guide where relevant, adapted to this project.

Respond with ONLY a JSON object in this exact shape (no markdown, no explanation):
{{
  "path": "{package_name}/<module_or_file>.py",
  "content": "<full file content as a single string, with \\n for newlines>"
}}

IMPORTANT: return exactly ONE file object, for ONE module, even if the task title mentions
multiple things. If the task genuinely needs more than one file, generate only the
first/primary one -- a separate task will handle the rest.

Rules:
- Use relative imports within the '{package_name}' package (e.g. "from {package_name}.model import X").
- Keep module/class/function names consistent with what's implied by ENTITIES and already-generated files.
- Write complete, runnable code - no placeholders like "# TODO implement".
- Test files go at "tests/test_<name>.py" using pytest style (plain `assert`, no unittest.TestCase
  boilerplate needed).
- requirements.txt (only if third-party packages are actually needed) goes at the project root.
- The main entry point (the file you run with `python`) should be named "main.py" at the project root.
"""

        max_retries = 4
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert Python developer. Always respond with valid JSON only, no markdown fences."},
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

        return DeveloperOutput(files=files, notes=notes)