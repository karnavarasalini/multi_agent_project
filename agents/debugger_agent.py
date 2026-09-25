import json
import os
import re
import time

from models.schemas import CodeFix, DebugResult, ProjectState
from openai import OpenAI, RateLimitError
from rag.knowledge_base import retrieve_known_fix, add_fix_as_pattern
from pathlib import Path
from datetime import datetime

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-120b"

# FIXED: matches BOTH Maven-wrapped ([ERROR] /path/File.java:[12,4] message) and
# plain javac (/path/File.java:9: message) output.
MAVEN_COMPILE_ERROR_RE = re.compile(
    r"(?:\[ERROR\]\s*)?([^\s:]+\.java):\[?(\d+)(?:,(\d+))?\]?"
)
FAILED_TEST_RE = re.compile(r"(\S+Test)[.#](\S+)")

# FIXED: same format-agnostic fix -- matches "cannot find symbol / symbol: class X /
# location: package Y" whether or not preceded by "[ERROR]"/"[line,col]" brackets.
MISSING_CLASS_RE = re.compile(
    r"(?:\[ERROR\]\s*)?\S+\.java:\[?\d+(?:,\d+)?\]?:?\s+cannot find symbol\s+"
    r"symbol:\s+class\s+(?P<symbol>\w+)\s+"
    r"location:\s+package\s+(?P<package>[\w.]+)",
    re.MULTILINE,
)

# Matches a missing *member* (method/variable), e.g.
#   cannot find symbol
#     symbol:   method getRead()
#     location: variable bookDetails of type com.example.app.entity.Book
# javac reports these against the CALLING file, but the defect is in the DECLARING
# type -- so we use the "location" type to route the fix to the right file.
MISSING_MEMBER_RE = re.compile(
    r"cannot find symbol\s*\n\s*symbol:\s+(?:method|variable)\s+(?P<member>\w+)[^\n]*\n"
    r"\s*location:\s+(?:variable\s+\w+\s+of\s+type\s+|class\s+|interface\s+)(?P<type>[\w.$]+)",
)

# Matches a Java package declaration at the top of a file, e.g. "package com.example.app.entity;"
PACKAGE_DECL_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)

# NEW: detects the "file is empty" marker TesterAgent emits when a .java file is
# 0 bytes / whitespace-only on disk. An empty file is syntactically legal Java and
# never appears as a javac diagnostic, so this needs its own line format and its
# own repair path -- see fix_empty_file() below.
EMPTY_FILE_RE = re.compile(r"\[ERROR\]\s+(\S+\.java):\s+file is empty")

# NEW: detects the known Lombok/javac internal-compiler crash that happens when an
# old Lombok release's patched javac hooks don't match a newer JDK's internals.
# This is a pom.xml dependency-version problem, not a bug in any generated .java
# file -- no per-file LLM edit can ever fix it, so it gets a deterministic fast path.
LOMBOK_JAVAC_CRASH_RE = re.compile(
    r"ExceptionInInitializerError.*?TypeTag\s*::\s*UNKNOWN|"
    r"com\.sun\.tools\.javac\.code\.TypeTag\s*::\s*UNKNOWN",
    re.DOTALL,
)
MIN_SAFE_LOMBOK_VERSION = "1.18.32"

# Common layer-name suffixes generated projects use -- stripping the last one off a
# file's package gives a good guess at the project's base package.
_LAYER_NAMES = {"entity", "repository", "service", "controller", "model", "dto", "config", "exception"}

RATE_LIMIT_FLAG = "__RATE_LIMIT_HIT__"


class RateLimitStop(Exception):
    pass


def call_llm(prompt: str, max_retries: int = 4) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.choices[0].message.content
            print(f"\n>>> LLM SUCCESS: {result[:200]}")
            return result
        except RateLimitError as e:
            if attempt == max_retries:
                print(f"\n>>> RATE LIMIT HIT (final): {e}")
                return f"{RATE_LIMIT_FLAG}: {e}"
            wait = 2 ** attempt
            print(f"\n>>> RATE LIMITED, waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
        except Exception as e:
            print(f"\n>>> LLM CALL FAILED: {type(e).__name__}: {e}")
            return f"__LLM_CALL_FAILED__: {e}"


def _resolve_path(file_path: str, project_root: str) -> str:
    if re.match(r"^/[A-Za-z]:", file_path):
        file_path = file_path[1:]
    return file_path if os.path.isabs(file_path) else os.path.join(project_root, file_path)


def _strip_code_fence(text: str) -> str:
    return text.strip().removeprefix("```java").removeprefix("```").removesuffix("```").strip()


def _read_generated(path: str, project_state: ProjectState, project_root: str) -> str:
    """Current content of a generated file, preferring what's actually on disk."""
    resolved = _resolve_path(path, project_root)
    if os.path.exists(resolved):
        try:
            return open(resolved, encoding="utf-8").read()
        except OSError:
            pass
    for gf in project_state.developer_output.files:
        if gf.path == path:
            return gf.content or ""
    return ""


def _class_name_from_path(path: str) -> str:
    return os.path.basename(path).removesuffix(".java")


def _plan_context(project_state: ProjectState) -> str:
    """The authoritative schema for this project. Without this the LLM re-invents
    entity fields on every debug pass (e.g. replacing 'read' with 'isbn')."""
    plan = project_state.plan
    if plan is None:
        return "(no plan available)"

    entities = "\n".join(f"- {e.name}: {e.fields}" for e in plan.entities) or "(none)"
    endpoints = "\n".join(f"- {ep.method} {ep.path}" for ep in plan.endpoints) or "(none)"
    notes = "\n".join(f"- {n}" for n in plan.tech_notes) or "(none)"
    return (
        f"ENTITIES (authoritative -- these exact fields and types MUST exist, "
        f"do not rename, drop, or invent fields):\n{entities}\n\n"
        f"ENDPOINTS:\n{endpoints}\n\n"
        f"TECH NOTES:\n{notes}"
    )


def _find_generated_path_for_class(class_name: str, project_state: ProjectState) -> str | None:
    target = f"{class_name}.java"
    for gf in project_state.developer_output.files:
        if os.path.basename(gf.path) == target:
            return gf.path
    return None


def _gather_related_files(target_path: str, project_state: ProjectState, project_root: str, max_files: int = 6) -> str:
    """Full contents of the other generated files that either use the target class or
    are used by it. A compile error is frequently reported in one file but caused by a
    collaborator, so the LLM needs to see both to produce a consistent fix."""
    target_cls = _class_name_from_path(target_path)
    target_content = _read_generated(target_path, project_state, project_root)

    related = []
    for gf in project_state.developer_output.files:
        if gf.path == target_path or not gf.path.endswith(".java"):
            continue
        other_cls = _class_name_from_path(gf.path)
        content = _read_generated(gf.path, project_state, project_root)

        uses_target = target_cls in content
        used_by_target = other_cls in target_content
        if not (uses_target or used_by_target):
            continue

        why = []
        if uses_target:
            why.append(f"calls into {target_cls}")
        if used_by_target:
            why.append(f"used by {target_cls}")
        related.append(f"--- {gf.path} ({', '.join(why)}) ---\n{content}")

        if len(related) >= max_files:
            break

    return "\n\n".join(related) if related else "(no related files found)"


def parse_missing_members(output: str) -> list[dict]:
    """Missing method/field errors, mapped to the type that should declare them."""
    found = []
    seen = set()
    for m in MISSING_MEMBER_RE.finditer(output):
        member = m.group("member")
        fq_type = m.group("type")
        simple_type = fq_type.rsplit(".", 1)[-1]
        key = (member, simple_type)
        if key not in seen:
            seen.add(key)
            found.append({"member": member, "type": simple_type, "fq_type": fq_type})
    return found


def call_llm_json(prompt: str, max_retries: int = 4) -> str:
    """Same retry/rate-limit contract as call_llm, but constrained to a JSON object."""
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert Java Spring Boot developer performing whole-project compile-error repair. Always respond with a single valid JSON object only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            if attempt == max_retries:
                print(f"\n>>> RATE LIMIT HIT (final): {e}")
                return f"{RATE_LIMIT_FLAG}: {e}"
            wait = 2 ** attempt
            print(f"\n>>> RATE LIMITED, waiting {wait}s before retry {attempt + 1}/{max_retries}...")
            time.sleep(wait)
        except Exception as e:
            print(f"\n>>> LLM JSON CALL FAILED: {type(e).__name__}: {e}")
            return f"__LLM_CALL_FAILED__: {e}"


def parse_maven_errors(output: str) -> list[dict]:
    """Parses javac-style compile errors in either Maven-wrapped
    '[ERROR] /path/File.java:[12,4] message' form or plain javac
    '/path/File.java:9: message' form (column group is optional and unused)."""
    errors = []
    for match in MAVEN_COMPILE_ERROR_RE.finditer(output):
        file_path, line, _col = match.groups()
        errors.append({"file": file_path, "line": int(line)})
    return errors


def group_by_file(errors: list[dict]) -> dict[str, list[dict]]:
    grouped = {}
    for e in errors:
        grouped.setdefault(e["file"], []).append(e)
    return grouped


# ---------- missing-class detection & creation ----------

def parse_missing_classes(output: str) -> list[dict]:
    """Finds 'cannot find symbol: class X / location: package Y' blocks -- these mean
    a whole file is missing, not that an existing file needs patching."""
    found = []
    seen = set()
    for m in MISSING_CLASS_RE.finditer(output):
        symbol = m.group("symbol")
        package = m.group("package")
        key = (symbol, package)
        if key not in seen:
            seen.add(key)
            found.append({"symbol": symbol, "package": package})
    return found


def _class_to_relative_path(symbol: str, package: str) -> str:
    pkg_path = package.replace(".", os.sep)
    return os.path.join("src", "main", "java", pkg_path, f"{symbol}.java")


def _file_already_exists(symbol: str, project_state: ProjectState) -> bool:
    target_name = f"{symbol}.java"
    return any(os.path.basename(gf.path) == target_name for gf in project_state.developer_output.files)


def _gather_reference_context(symbol: str, project_state: ProjectState, project_root: str, max_files: int = 3) -> str:
    """Pulls in the content of any generated file that references the missing/empty
    class, so the LLM knows what fields/methods it needs to have."""
    snippets = []
    for gf in project_state.developer_output.files:
        if symbol in (gf.content or ""):
            resolved = _resolve_path(gf.path, project_root)
            if os.path.exists(resolved):
                content = open(resolved, encoding="utf-8").read()
            else:
                content = gf.content or ""
            snippets.append(f"--- {gf.path} (references {symbol}) ---\n{content}")
        if len(snippets) >= max_files:
            break
    return "\n\n".join(snippets)


def create_missing_file(symbol: str, package: str, project_root: str, project_state: ProjectState) -> CodeFix | None:
    relative_path = _class_to_relative_path(symbol, package)
    resolved_path = _resolve_path(relative_path, project_root)

    context = _gather_reference_context(symbol, project_state, project_root)

    prompt = f"""You are generating a MISSING Java class for a Spring Boot project. This class
does not exist yet -- it is referenced by other files but was never created.

CLASS NAME: {symbol}
PACKAGE: {package}

The following existing files reference this class -- infer the required fields, types,
getters/setters, and any needed annotations (Lombok @Data, @Builder if a .builder() call
is used elsewhere, validation annotations, etc.) from how it's used:

{context if context else "(no referencing files found -- infer a reasonable minimal DTO/entity)"}

Return the COMPLETE Java file content only, no explanation, no markdown fences.
Start with 'package {package};' and include all necessary imports."""

    generated = call_llm(prompt)

    if generated.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(
            f"Daily/rate token limit hit while creating missing class '{symbol}', even after retrying. "
            f"Details: {generated}"
        )
    if generated.startswith("__LLM_CALL_FAILED__"):
        return None

    generated = _strip_code_fence(generated)

    os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(generated)

    existing_file_cls = type(project_state.developer_output.files[0]) if project_state.developer_output.files else None
    if existing_file_cls:
        new_file = existing_file_cls(path=relative_path, content=generated)
        project_state.developer_output.files.append(new_file)

    return CodeFix(
        file_path=relative_path,
        updated_content=generated,
        explanation=f"Created missing class {symbol} in package {package} (was referenced but never generated)",
        confidence="high",
    )


# ---------- NEW: empty-file repair ----------

def parse_empty_files(output: str) -> list[str]:
    """Finds the '[ERROR] path.java: file is empty' lines TesterAgent emits."""
    seen = []
    for m in EMPTY_FILE_RE.finditer(output):
        path = m.group(1)
        if path not in seen:
            seen.append(path)
    return seen


def _package_from_path(java_path: str) -> str | None:
    normalized = java_path.replace("\\", "/")
    m = re.search(r"src/(?:main|test)/java/(.+)/[^/]+\.java$", normalized)
    return m.group(1).replace("/", ".") if m else None


def _find_project_entries_by_basename(basename: str, project_state: ProjectState) -> list:
    return [gf for gf in project_state.developer_output.files if os.path.basename(gf.path) == basename]


def fix_empty_file(rel_path: str, project_root: str, project_state: ProjectState) -> CodeFix | None:
    """Repairs a source file that's empty on disk. Root cause is almost always a
    duplicate GeneratedFile entry for the same class (e.g. one relative path, one
    absolute path resolving to the same file) where the empty entry got written
    last and clobbered the real content -- so first check for a non-empty in-memory
    duplicate and restore from it directly. Only fall back to LLM regeneration if no
    such duplicate exists."""
    basename = os.path.basename(rel_path)
    entries = _find_project_entries_by_basename(basename, project_state)
    project_path = next(
        (e.path for e in entries if e.path.replace("\\", "/") == rel_path), rel_path
    )

    for gf in entries:
        if (gf.content or "").strip():
            _write_and_register(project_path, gf.content, project_root, project_state)
            print(f"  Restored {project_path} from a non-empty duplicate GeneratedFile entry")
            return CodeFix(
                file_path=project_path,
                updated_content=gf.content,
                explanation=(
                    f"Restored {project_path}, which was empty on disk -- a duplicate "
                    f"GeneratedFile entry for the same class had overwritten it. "
                    f"Recovered the real content from that duplicate."
                ),
                confidence="high",
            )

    # No usable in-memory duplicate -- regenerate from scratch via LLM.
    class_name = basename.removesuffix(".java")
    package = _package_from_path(project_path)
    if not package:
        print(f"  Could not determine package for empty file {rel_path} -- skipping regeneration.")
        return None

    context = _gather_reference_context(class_name, project_state, project_root)
    prompt = f"""A Java file in a Spring Boot project is EMPTY (0 bytes) on disk and needs to be
regenerated from scratch. Other files in the project reference this class.

{_plan_context(project_state)}

CLASS NAME: {class_name}
PACKAGE: {package}

Files that reference this class (infer required fields/methods/annotations from usage):

{context if context else "(no referencing files found -- infer a reasonable implementation from the class name and ENDPOINTS/ENTITIES above)"}

Return the COMPLETE Java file content only, no explanation, no markdown fences.
Start with 'package {package};' and include all necessary imports."""

    generated = call_llm(prompt)
    if generated.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(f"Daily/rate token limit hit while regenerating empty file '{rel_path}'. Details: {generated}")
    if generated.startswith("__LLM_CALL_FAILED__"):
        return None

    generated = _strip_code_fence(generated)
    _write_and_register(project_path, generated, project_root, project_state)
    print(f"  Regenerated empty file {project_path} from context")

    return CodeFix(
        file_path=project_path,
        updated_content=generated,
        explanation=f"Regenerated {project_path}, which was empty on disk, from other files that reference {class_name}.",
        confidence="medium",
    )


# ---------- NEW: Lombok/javac internal-compiler crash repair ----------

def fix_lombok_javac_crash(project_state: ProjectState, project_root: str) -> CodeFix | None:
    """Deterministically bumps <lombok.version> in pom.xml when the build crashed
    with the known Lombok/javac internal-compiler incompatibility. No LLM call
    needed -- this is a fixed, known remedy, not a code-comprehension problem, and
    no per-file edit could ever fix a pom.xml dependency-version mismatch."""
    pom_path = None
    for gf in project_state.developer_output.files:
        if os.path.basename(gf.path) == "pom.xml":
            pom_path = gf.path
            break
    if not pom_path:
        return None

    content = _read_generated(pom_path, project_state, project_root)
    match = re.search(r"<lombok\.version>([^<]+)</lombok\.version>", content)
    if not match:
        return None

    current_version = match.group(1)
    if current_version == MIN_SAFE_LOMBOK_VERSION:
        return None  # already at the safe version -- crash has a different cause

    new_content = content.replace(
        f"<lombok.version>{current_version}</lombok.version>",
        f"<lombok.version>{MIN_SAFE_LOMBOK_VERSION}</lombok.version>",
    )
    _write_and_register(pom_path, new_content, project_root, project_state)
    print(f"  Bumped Lombok {current_version} -> {MIN_SAFE_LOMBOK_VERSION} (javac/Lombok internal incompatibility)")

    return CodeFix(
        file_path=pom_path,
        updated_content=new_content,
        explanation=(
            f"Bumped lombok.version from {current_version} to {MIN_SAFE_LOMBOK_VERSION} -- "
            f"build was crashing with 'ExceptionInInitializerError: "
            f"com.sun.tools.javac.code.TypeTag :: UNKNOWN', a known Lombok/JDK javac "
            f"internals incompatibility unrelated to any generated source file."
        ),
        confidence="high",
    )


# ---------- missing @SpringBootApplication entry point ----------

def _has_main_application_class(project_state: ProjectState) -> bool:
    """True if any generated file is already annotated @SpringBootApplication."""
    return any("@SpringBootApplication" in (gf.content or "") for gf in project_state.developer_output.files)


def _guess_base_package(project_state: ProjectState) -> str | None:
    """Infers the project's base package by taking any generated file's package
    declaration and stripping a trailing layer name like .entity / .controller /
    .service, etc."""
    for gf in project_state.developer_output.files:
        m = PACKAGE_DECL_RE.search(gf.content or "")
        if not m:
            continue
        pkg = m.group(1)
        parts = pkg.split(".")
        if parts and parts[-1] in _LAYER_NAMES:
            return ".".join(parts[:-1])
    return None


def _application_class_name(base_package: str) -> str:
    last_segment = base_package.rsplit(".", 1)[-1]
    words = re.split(r"[_\-]+", last_segment)
    return "".join(w.capitalize() for w in words if w) + "Application"


def ensure_main_application_class(project_state: ProjectState, project_root: str) -> CodeFix | None:
    """Guarantees the generated project has a runnable @SpringBootApplication entry
    point. Mockito-based unit tests don't need a real Spring context, so `mvn test`
    can report success even when the project has no main class at all -- this check
    runs independently of test pass/fail so a missing entry point is always caught
    and fixed, not just silently shipped."""
    if _has_main_application_class(project_state):
        return None

    base_package = _guess_base_package(project_state)
    if not base_package:
        print("  Could not infer base package -- skipping main-class check.")
        return None

    class_name = _application_class_name(base_package)
    relative_path = os.path.join("src", "main", "java", *base_package.split("."), f"{class_name}.java")

    content = f"""package {base_package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {class_name} {{

    public static void main(String[] args) {{
        SpringApplication.run({class_name}.class, args);
    }}
}}
"""

    _write_and_register(relative_path, content, project_root, project_state)
    print(f"  Created missing Spring Boot entry point: {relative_path}")

    return CodeFix(
        file_path=relative_path,
        updated_content=content,
        explanation=(
            f"Created missing @SpringBootApplication main class ({class_name}) -- the generated "
            f"project had no runnable entry point, which unit tests alone don't catch."
        ),
        confidence="high",
    )


# ---------- project-wide compile repair ----------

def _repair_double_escaping(content: str) -> str:
    """Some models return content with literal \\n instead of real newlines."""
    if "\\n" in content or '\\"' in content or "\\t" in content:
        content = (
            content.replace('\\r\\n', '\n')
                   .replace('\\n', '\n')
                   .replace('\\t', '\t')
                   .replace('\\"', '"')
        )
    return content


def _write_and_register(relative_path: str, content: str, project_root: str, project_state: ProjectState) -> None:
    resolved = _resolve_path(relative_path, project_root)
    os.makedirs(os.path.dirname(resolved), exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as f:
        f.write(content)

    for gf in project_state.developer_output.files:
        if gf.path == relative_path:
            gf.content = content
            return

    existing_cls = type(project_state.developer_output.files[0]) if project_state.developer_output.files else None
    if existing_cls:
        project_state.developer_output.files.append(existing_cls(path=relative_path, content=content))


def fix_compile_errors_project_wide(
    project_state: ProjectState,
    project_root: str,
    error_output: str,
    max_files: int = 14,
) -> list[CodeFix] | None:
    """Repairs compile errors with the WHOLE project in context, returning every file
    that needs to change.

    javac reports an error at the call site, but the defect often lives in a
    collaborator that has no error of its own -- e.g. `JpaRepository<Object, Long>`
    makes `findAll()` return `List<Object>`, and javac blames the *service*. Patching
    files one at a time in isolation can never fix that, and tends to make it worse by
    "correcting" the caller to match the broken type. Returns None if the project is too
    large for this approach, so the caller can fall back to per-file patching.
    """
    java_files = [gf for gf in project_state.developer_output.files if gf.path.endswith(".java")]
    if not java_files or len(java_files) > max_files:
        return None

    files_block = "\n\n".join(
        f"--- {gf.path} ---\n{_read_generated(gf.path, project_state, project_root)}"
        for gf in java_files
    )

    prompt = f"""You are fixing compile errors in a Java Spring Boot (Maven, Java 17+) project.

{_plan_context(project_state)}

COMPILER ERRORS:
{error_output[:6000]}

ALL CURRENT PROJECT SOURCE FILES:
{files_block}

Diagnose the ROOT CAUSE, then return every file that must change to make the project
compile. Critical guidance:
- javac reports an error at the USE site, but the bug is often in the DECLARING file.
  Fix the declaring file, not the caller. For example, if a service gets
  "List<Object> cannot be converted to List<Book>", the real bug is the repository
  declaring JpaRepository<Object, Long> instead of JpaRepository<Book, Long>.
- Repositories MUST be JpaRepository<ConcreteEntity, IdType> -- never Object.
- If the compile error is INSIDE a file under src/test/java, the test is almost always
  wrong, not the production code -- update the TEST to match the current production
  method signatures and return types. Only change a src/main/java file's public method
  signature (return type, parameter types) if it is genuinely incorrect per ENTITIES/
  ENDPOINTS above. Never change a production method's signature back and forth between
  iterations -- once a signature is correct, keep it stable and fix callers/tests
  instead.
- If a getter/setter is missing, ADD it to the entity using the field list in ENTITIES
  above. Never delete or rename an entity field to silence an error, and never invent a
  field that is not in ENTITIES.
- Keep every package declaration, class name, and file path exactly as-is.
- Return complete, compilable file contents -- no placeholders, no "// TODO".

Respond with ONLY this JSON object:
{{
  "root_cause": "<one sentence>",
  "files": [
    {{"path": "<exact relative path from the list above>", "content": "<full corrected file>"}}
  ]
}}

Include ONLY files whose content actually changes. If a file is already correct, omit it."""

    raw = call_llm_json(prompt)

    if raw.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(
            f"Daily/rate token limit hit during project-wide compile repair, even after "
            f"retrying with backoff. Details: {raw}"
        )
    if raw.startswith("__LLM_CALL_FAILED__"):
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  Project-wide repair returned invalid JSON ({e}); falling back to per-file fixes.")
        return None

    root_cause = data.get("root_cause", "(not reported)")
    print(f"  Root cause: {root_cause}")

    known_paths = {gf.path for gf in project_state.developer_output.files}
    fixes = []

    for entry in data.get("files", []):
        path = entry.get("path")
        content = entry.get("content")
        if not path or content is None:
            continue

        normalized = os.path.normpath(path)
        if normalized.startswith("..") or os.path.isabs(normalized):
            print(f"  Skipping suspicious path from LLM: {path}")
            continue
        if not normalized.startswith(os.path.join("src", "")):
            print(f"  Skipping out-of-tree path from LLM: {path}")
            continue

        content = _repair_double_escaping(content)
        _write_and_register(normalized, content, project_root, project_state)

        verb = "Updated" if normalized in known_paths else "Created"
        print(f"  {verb} {normalized}")
        fixes.append(CodeFix(
            file_path=normalized,
            updated_content=content,
            explanation=f"{verb} during project-wide repair. Root cause: {root_cause}",
            confidence="high",
        ))

    return fixes or None


# ---------- existing patch-a-file logic ----------

def _find_source_file_for_test_error(error_summary: str, project_state: ProjectState) -> str | None:
    if not error_summary:
        return None
    m = FAILED_TEST_RE.search(error_summary)
    if not m:
        return None
    test_class = m.group(1)
    if test_class.endswith("Test"):
        target_class = test_class[: -len("Test")]
    else:
        target_class = test_class
    target_name = target_class + ".java"
    for gf in project_state.developer_output.files:
        if os.path.basename(gf.path) == target_name:
            return gf.path
    return None


def flag_for_human_review(fix: CodeFix, file_path: str):
    Path("review_needed").mkdir(exist_ok=True)

    review_note = {
        "file": file_path,
        "proposed_fix": fix.updated_content,
        "root_cause": getattr(fix, "root_cause", ""),
        "confidence": getattr(fix, "confidence", ""),
        "explanation": getattr(fix, "explanation", ""),
        "flagged_at": datetime.now().isoformat()
    }

    fname = f"review_needed/{Path(file_path).stem}_{int(time.time())}.json"

    with open(fname, "w", encoding="utf-8") as f:
        json.dump(review_note, f, indent=2)

    print(
        f"[Debugger] LOW CONFIDENCE — flagged for review, "
        f"NOT applied: {file_path}"
    )


def apply_fix_with_confidence_check(
    fix: CodeFix,
    file_path: str,
    project_root: str,
    project_state: ProjectState,
) -> bool:

    confidence = getattr(fix, "confidence", "low").lower()

    if confidence == "low":
        flag_for_human_review(fix, file_path)
        return False

    _write_and_register(
        fix.file_path,
        fix.updated_content,
        project_root,
        project_state,
    )

    return True


def fix_file(file_path: str, error_text: str, project_root: str, project_state: ProjectState) -> CodeFix | None:

    known = retrieve_known_fix(error_text)

    if known:
        print(
            f"[Debugger] Reusing learned fix "
            f"(reused {known['times_reused']} times, "
            f"sim={known['similarity']:.2f})"
        )

        fix = CodeFix(
            file_path=file_path,
            updated_content=known["fixed_code"],
            root_cause=known["root_cause"],
            explanation="Reused from self-improving RAG cache",
            confidence="high",
        )

        if apply_fix_with_confidence_check(
            fix,
            file_path,
            project_root,
            project_state,
        ):
            return fix

        return None

    resolved_path = _resolve_path(file_path, project_root)

    if not os.path.exists(resolved_path):
        return None

    original_content = open(resolved_path, encoding="utf-8").read()

    prompt = f"""You are fixing a Java file (Spring Boot project) that failed to compile or pass its tests.

{_plan_context(project_state)}

RELATED PROJECT FILES (for consistent names, types, getters and imports -- do NOT return these,
they are context only):
{_gather_related_files(file_path, project_state, project_root)}

FILE TO FIX: {file_path}
CURRENT CONTENT:
{original_content}

ERRORS:
{error_text}

Return the COMPLETE corrected file content only, no explanation, no markdown fences.
Keep the same package declaration and class name -- only fix what's causing the error.
Stay consistent with the ENTITIES field list above and with the related files: never
rename or drop an entity field, never invent a field that is not listed, and never widen
a generic type to Object to silence an error."""

    fixed_content = call_llm(prompt)

    if fixed_content.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(
            f"Daily/rate token limit hit while fixing '{file_path}', even after retrying with backoff. "
            f"Stopping debug pass now. Details: {fixed_content}"
        )

    if fixed_content.startswith("__LLM_CALL_FAILED__"):
        return None

    fixed_content = _strip_code_fence(fixed_content)

    fix = CodeFix(
        file_path=file_path,
        updated_content=fixed_content,
        explanation=f"Fixed: {error_text[:200]}",
        confidence="high",
    )

    if not apply_fix_with_confidence_check(
        fix,
        file_path,
        project_root,
        project_state,
    ):
        return None

    return fix


def run_debugger_agent(project_state: ProjectState) -> ProjectState:
    project_root = project_state.output_dir
    test_result = project_state.test_result

    # Always check for a missing Spring Boot entry point, regardless of whether
    # tests passed. Mockito-based unit tests don't spin up a real Spring context, so
    # `mvn test` can report success even when the project has no @SpringBootApplication
    # class at all. This runs unconditionally, before the early-return below.
    main_class_fix = ensure_main_application_class(project_state, project_root)
    if main_class_fix:
        project_state.debug_history.append(DebugResult(
            root_cause=main_class_fix.explanation,
            fixes=[main_class_fix],
            confidence="high",
        ))

    # NEW: fast-path for the Lombok/javac internal-compiler crash. This has no
    # per-file error location at all, so none of the file-based checks below could
    # ever catch it -- it must be checked before anything that assumes the failure
    # is attributable to a specific source file.
    if test_result is not None and not test_result.passed and LOMBOK_JAVAC_CRASH_RE.search(test_result.raw_output):
        lombok_fix = fix_lombok_javac_crash(project_state, project_root)
        if lombok_fix:
            project_state.debug_history.append(DebugResult(
                root_cause=lombok_fix.explanation,
                fixes=[lombok_fix],
                confidence="high",
            ))
            return project_state

    if test_result is None or test_result.passed:
        # Tests just passed -- if the previous debug pass produced fixes, they are now
        # CONFIRMED to work. Save them to the learned-pattern cache so future runs can
        # reuse them instantly instead of calling the LLM again.
        if test_result is not None and test_result.passed and project_state.debug_history:
            last_debug = project_state.debug_history[-1]
            for fix in last_debug.fixes:
                add_fix_as_pattern(
                    error_message=last_debug.root_cause,
                    root_cause=last_debug.root_cause,
                    fixed_code=fix.updated_content,
                    file_type=fix.file_path.split(".")[-1],
                )
        return project_state

    compile_errors = parse_maven_errors(test_result.raw_output)
    missing_classes = parse_missing_classes(test_result.raw_output)
    fixes = []

    try:
        # STEP 0: repair any file that's empty on disk -- this can never show up as a
        # compile error (an empty .java file is syntactically legal), so it has to be
        # handled before anything else that assumes javac reported something.
        empty_files = parse_empty_files(test_result.raw_output)
        for rel_path in empty_files:
            fix = fix_empty_file(rel_path, project_root, project_state)
            if fix:
                fixes.append(fix)

        # STEP 1: create any missing classes first -- this resolves the root cause
        # that would otherwise make every other fix attempt pointless.
        created_symbols = set()
        for mc in missing_classes:
            symbol, package = mc["symbol"], mc["package"]
            if _file_already_exists(symbol, project_state):
                continue
            fix = create_missing_file(symbol, package, project_root, project_state)
            if fix:
                fixes.append(fix)
                created_symbols.add(symbol)

        # STEP 2: repair remaining compile errors with the whole project in context, so
        # the fix can land in the file that actually causes the error rather than the
        # file javac happens to blame. Falls back to isolated per-file patching.
        if compile_errors:
            grouped = group_by_file(compile_errors)
            project_fixes = fix_compile_errors_project_wide(
                project_state, project_root, test_result.raw_output
            )

            if project_fixes:
                fixes.extend(project_fixes)
                strategy = f"project-wide repair of {len(project_fixes)} file(s)"
            else:
                missing_members = parse_missing_members(test_result.raw_output)
                targets = list(grouped.keys())

                for mm in missing_members:
                    declaring = _find_generated_path_for_class(mm["type"], project_state)
                    if declaring and declaring not in targets:
                        targets.insert(0, declaring)
                        print(f"  Routing missing member '{mm['member']}' to declaring class {mm['type']}")

                for file_path in targets:
                    file_errors = grouped.get(file_path, [])
                    lines = "\n".join(f"Line {e['line']}" for e in file_errors) or "(reported via another file)"
                    error_text = f"{lines}\n\nFull output:\n{test_result.raw_output[:1500]}"
                    fix = fix_file(file_path, error_text, project_root, project_state)
                    if fix:
                        fixes.append(fix)
                strategy = f"per-file repair of {len(targets)} file(s)"

            root_cause = (
                f"{len(compile_errors)} error location(s) across {len(grouped)} file(s); {strategy}"
                + (f"; created missing class(es): {', '.join(created_symbols)}" if created_symbols else "")
            )
        elif not missing_classes and not empty_files:
            target_path = _find_source_file_for_test_error(test_result.error_summary, project_state)
            if target_path:
                fix = fix_file(target_path, test_result.error_summary or "Test failed.", project_root, project_state)
                if fix:
                    fixes.append(fix)
            root_cause = test_result.error_summary or "Test failure with no identifiable source file."
        else:
            root_cause = (
                (f"created missing class(es): {', '.join(created_symbols)}" if created_symbols else "")
                or (f"repaired empty file(s): {', '.join(empty_files)}" if empty_files else "no actionable errors found")
            )
    except RateLimitStop as e:
        project_state.status = "failed"
        project_state.debug_history.append(DebugResult(
            root_cause=str(e),
            fixes=fixes,
            confidence="low",
        ))
        print(f"     STOPPING DEBUG PASS: {e}")
        return project_state

    if fixes:
        project_state.debug_history.append(DebugResult(
            root_cause=root_cause,
            fixes=fixes,
            confidence="medium" if compile_errors else "low",
        ))
    else:
        project_state.status = "failed"

    return project_state