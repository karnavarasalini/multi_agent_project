import os
import re
import time

from models.schemas import CodeFix, DebugResult, ProjectState
from openai import OpenAI, RateLimitError

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-120b"
MAVEN_COMPILE_ERROR_RE = re.compile(r"\[ERROR\]\s+(.+?\.java):\[(\d+),(\d+)\]")
FAILED_TEST_RE = re.compile(r"(\S+Test)[.#](\S+)")

# NEW: matches "cannot find symbol / symbol: class X / location: package Y" blocks
MISSING_CLASS_RE = re.compile(
    r"\[ERROR\]\s+.+?\.java:\[\d+,\d+\]\s+cannot find symbol\s+"
    r"symbol:\s+class\s+(?P<symbol>\w+)\s+"
    r"location:\s+package\s+(?P<package>[\w.]+)",
    re.MULTILINE,
)

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


def parse_maven_errors(output: str) -> list[dict]:
    """Parses javac-style Maven compile errors: '[ERROR] /path/File.java:[12,4] message'."""
    errors = []
    for match in MAVEN_COMPILE_ERROR_RE.finditer(output):
        file, line, col = match.groups()
        errors.append({"file": file, "line": int(line)})
    return errors


def group_by_file(errors: list[dict]) -> dict[str, list[dict]]:
    grouped = {}
    for e in errors:
        grouped.setdefault(e["file"], []).append(e)
    return grouped


# ---------- NEW: missing-class detection & creation ----------

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
    """Pulls in the content of any generated file that references the missing class,
    so the LLM knows what fields/methods it needs to have."""
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

    # Register the new file in project state so later passes/tests see it
    existing_file_cls = type(project_state.developer_output.files[0]) if project_state.developer_output.files else None
    if existing_file_cls:
        new_file = existing_file_cls(path=relative_path, content=generated)
        project_state.developer_output.files.append(new_file)

    return CodeFix(
        file_path=relative_path,
        updated_content=generated,
        explanation=f"Created missing class {symbol} in package {package} (was referenced but never generated)"
    )


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


def fix_file(file_path: str, error_text: str, project_root: str, project_state: ProjectState) -> CodeFix | None:
    resolved_path = _resolve_path(file_path, project_root)

    if not os.path.exists(resolved_path):
        return None

    original_content = open(resolved_path, encoding="utf-8").read()

    prompt = f"""You are fixing a Java file (Spring Boot project) that failed to compile or pass its tests.

FILE: {file_path}
CURRENT CONTENT:
{original_content}

ERRORS:
{error_text}

Return the COMPLETE corrected file content only, no explanation, no markdown fences.
Keep the same package declaration and class name -- only fix what's causing the error."""

    fixed_content = call_llm(prompt)

    if fixed_content.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(
            f"Daily/rate token limit hit while fixing '{file_path}', even after retrying with backoff. "
            f"Stopping debug pass now. Details: {fixed_content}"
        )

    if fixed_content.startswith("__LLM_CALL_FAILED__"):
        return None

    fixed_content = _strip_code_fence(fixed_content)

    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    for gf in project_state.developer_output.files:
        if gf.path == file_path:
            gf.content = fixed_content
            break

    return CodeFix(
        file_path=file_path,
        updated_content=fixed_content,
        explanation=f"Fixed: {error_text[:200]}"
    )


def run_debugger_agent(project_state: ProjectState) -> ProjectState:
    project_root = project_state.output_dir
    test_result = project_state.test_result

    if test_result is None or test_result.passed:
        return project_state

    compile_errors = parse_maven_errors(test_result.raw_output)
    missing_classes = parse_missing_classes(test_result.raw_output)
    fixes = []

    try:
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

        # STEP 2: for remaining compile errors NOT caused purely by the missing class
        # we just created, patch the reporting files as before.
        if compile_errors:
            grouped = group_by_file(compile_errors)
            for file_path, file_errors in grouped.items():
                error_text = "\n".join(f"Line {e['line']}" for e in file_errors) + f"\n\nFull output:\n{test_result.raw_output[:1500]}"
                fix = fix_file(file_path, error_text, project_root, project_state)
                if fix:
                    fixes.append(fix)
            root_cause = f"{len(compile_errors)} error location(s) across {len(grouped)} file(s)" + (
                f"; created missing class(es): {', '.join(created_symbols)}" if created_symbols else ""
            )
        elif not missing_classes:
            target_path = _find_source_file_for_test_error(test_result.error_summary, project_state)
            if target_path:
                fix = fix_file(target_path, test_result.error_summary or "Test failed.", project_root, project_state)
                if fix:
                    fixes.append(fix)
            root_cause = test_result.error_summary or "Test failure with no identifiable source file."
        else:
            root_cause = f"created missing class(es): {', '.join(created_symbols)}"
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