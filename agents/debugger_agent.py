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
PY_ERROR_RE = re.compile(r'File "(.+\.py)", line (\d+)')
FAILED_TEST_RE = re.compile(r"^FAILED\s+(.+?)::(\S+)")

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


def parse_python_errors(output: str) -> list[dict]:
    errors = []
    for match in PY_ERROR_RE.finditer(output):
        file, line = match.groups()
        errors.append({"file": file, "line": int(line)})
    return errors


def group_by_file(errors: list[dict]) -> dict[str, list[dict]]:
    grouped = {}
    for e in errors:
        grouped.setdefault(e["file"], []).append(e)
    return grouped


def _find_source_file_for_test_error(error_summary: str, project_state: ProjectState) -> str | None:
    """
    error_summary looks like 'tests/test_calculator.py::test_add - AssertionError...'.
    Map the test module back to the production module it's most likely testing,
    by stripping the 'test_' prefix, then find that file's actual path.
    """
    if not error_summary:
        return None
    m = FAILED_TEST_RE.search(error_summary)
    if not m:
        return None
    test_file = m.group(1)  # e.g. "tests/test_calculator.py"
    base = os.path.basename(test_file)
    if base.startswith("test_"):
        target_name = base[len("test_"):]
    else:
        target_name = base
    for gf in project_state.developer_output.files:
        if os.path.basename(gf.path) == target_name:
            return gf.path
    return None


def fix_file(file_path: str, error_text: str, project_root: str, project_state: ProjectState) -> CodeFix | None:
    resolved_path = _resolve_path(file_path, project_root)

    if not os.path.exists(resolved_path):
        return None

    original_content = open(resolved_path, encoding="utf-8").read()

    prompt = f"""You are fixing a Python file that failed to compile or pass its tests.

FILE: {file_path}
CURRENT CONTENT:
{original_content}

ERRORS:
{error_text}

Return the COMPLETE corrected file content only, no explanation, no markdown fences."""

    fixed_content = call_llm(prompt)

    if fixed_content.startswith(RATE_LIMIT_FLAG):
        raise RateLimitStop(
            f"Daily/rate token limit hit while fixing '{file_path}', even after retrying with backoff. "
            f"Stopping debug pass now. Details: {fixed_content}"
        )

    if fixed_content.startswith("__LLM_CALL_FAILED__"):
        return None

    fixed_content = fixed_content.strip().removeprefix("```python").removeprefix("```py").removesuffix("```").strip()

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

    compile_errors = parse_python_errors(test_result.raw_output)
    fixes = []

    try:
        if compile_errors:
            grouped = group_by_file(compile_errors)
            for file_path, file_errors in grouped.items():
                error_text = "\n".join(f"Line {e['line']}" for e in file_errors) + f"\n\nFull output:\n{test_result.raw_output[:1500]}"
                fix = fix_file(file_path, error_text, project_root, project_state)
                if fix:
                    fixes.append(fix)
            root_cause = f"{len(compile_errors)} error location(s) across {len(grouped)} file(s)"
        else:
            target_path = _find_source_file_for_test_error(test_result.error_summary, project_state)
            if target_path:
                fix = fix_file(target_path, test_result.error_summary or "Test failed.", project_root, project_state)
                if fix:
                    fixes.append(fix)
            root_cause = test_result.error_summary or "Test failure with no identifiable source file."
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