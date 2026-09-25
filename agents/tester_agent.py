import os
import re
import subprocess
import time
import glob
import urllib.request
import urllib.error
from typing import Optional

from models.schemas import TestResult, ProjectPlan


# FIXED: matches BOTH Maven-wrapped errors ([ERROR] /path/File.java:[12,4] message)
# AND plain javac errors (/path/File.java:9: message). The old pattern required a
# literal "[ERROR]" prefix and "[line,col]" brackets and matched nothing on plain
# javac output, which silently produced zero fixes and false "failed" statuses.
MAVEN_COMPILE_ERROR_RE = re.compile(
    r"(?:\[ERROR\]\s*)?([^\s:]+\.java):\[?(\d+)(?:,(\d+))?\]?:?\s*(.*)"
)
SUREFIRE_SUMMARY_RE = re.compile(
    r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)"
)
FAILED_TEST_LINE_RE = re.compile(r"^(?:Tests in error:|Failed tests:)\s*$|^\s+(\S+Test)[.#](\S+)")

SMOKE_TEST_PORT = 8099
SMOKE_TEST_STARTUP_TIMEOUT = 30  # seconds


class TesterAgent:

    def _run(self, args: list[str], project_dir: str, timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=os.name == "nt",
        )

    # ---------- empty-file detection (NEW) ----------

    def _find_empty_source_files(self, project_dir: str) -> list[str]:
        """Scans every .java file for empty/whitespace-only content. A trivially
        empty .java file is syntactically legal per the JLS and compiles with zero
        errors while silently producing no class -- javac never flags this, so it
        must be caught by reading file content directly, before mvn ever runs.
        Root cause is almost always a duplicate GeneratedFile entry (e.g. one
        relative path, one absolute path resolving to the same file) where the
        empty entry was written last and clobbered real content."""
        empty_files = []
        for root, _, files in os.walk(project_dir):
            for f in files:
                if not f.endswith(".java"):
                    continue
                full_path = os.path.join(root, f)
                try:
                    content = open(full_path, encoding="utf-8").read()
                except OSError:
                    continue
                if not content.strip():
                    empty_files.append(os.path.relpath(full_path, project_dir).replace("\\", "/"))
        return empty_files

    # ---------- compile check ----------

    def _compile_check(self, project_dir: str) -> subprocess.CompletedProcess:
        """Runs `mvn compile` to catch Java compile errors before running any tests."""
        pom_path = os.path.join(project_dir, "pom.xml")
        if not os.path.exists(pom_path):
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="No pom.xml found -- not a valid Maven project."
            )
        return self._run(["mvn", "-q", "-B", "-DskipTests", "compile"], project_dir)

    def _summarize_compile_errors(self, output: str) -> str:
        lines = []
        for match in MAVEN_COMPILE_ERROR_RE.finditer(output):
            file, ln, _col, msg = match.groups()
            lines.append(f"{file}:{ln}: {msg.strip()}")
        return "\n".join(lines) if lines else output.strip()[-3000:] or "Compilation failed (see raw_output)."

    def _summarize_test_failures(self, output: str) -> str:
        lines = [f"{m.group(1)}.{m.group(2)}" for m in FAILED_TEST_LINE_RE.finditer(output) if m.group(1)]
        return "\n".join(lines) if lines else output.strip()[-3000:] or "Some tests failed (see raw_output)."

    # ---------- live API smoke test ----------

    def _package_app(self, project_dir: str) -> subprocess.CompletedProcess:
        return self._run(["mvn", "-q", "-B", "-DskipTests", "package"], project_dir)

    def _find_jar(self, project_dir: str) -> Optional[str]:
        candidates = [
            f for f in glob.glob(os.path.join(project_dir, "target", "*.jar"))
            if not f.endswith(".original")
        ]
        return candidates[0] if candidates else None

    def _wait_for_startup(self, port: int, timeout: int) -> bool:
        deadline = time.time() + timeout
        url = f"http://localhost:{port}/"
        while time.time() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1)
                return True
            except urllib.error.HTTPError:
                # Any HTTP response (even 404 on "/") means the server is up.
                return True
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(1)
        return False

    def _substitute_path_vars(self, path: str) -> str:
        return re.sub(r"\{[^}/]+\}", "1", path)

    def _check_endpoint(self, base_url: str, method: str, path: str) -> Optional[str]:
        """Returns None if the route exists (any status other than 404/405),
        or a failure description string if it doesn't."""
        url = base_url + self._substitute_path_vars(path)
        body = b"{}" if method.upper() in ("POST", "PUT", "PATCH") else None
        req = urllib.request.Request(url, data=body, method=method.upper())
        if body is not None:
            req.add_header("Content-Type", "application/json")
        try:
            urllib.request.urlopen(req, timeout=5)
            return None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return f"{method.upper()} {path} -> 404 Not Found (route does not exist)"
            if e.code == 405:
                return f"{method.upper()} {path} -> 405 Method Not Allowed (path exists, wrong HTTP method)"
            return None  # any other status (400, 500, etc.) means the route exists
        except (urllib.error.URLError, ConnectionRefusedError, OSError) as e:
            return f"{method.upper()} {path} -> connection error ({e})"

    def _live_smoke_test(self, project_dir: str, plan: Optional[ProjectPlan]) -> tuple[bool, str]:
        """Boots the packaged app and hits every plan.endpoints entry, checking only
        that the route exists (not 404/405) -- business-logic correctness is already
        covered by the generated MockMvc/unit tests in `mvn test`."""
        if not plan or not plan.endpoints:
            return True, "No endpoints declared in plan -- skipping live smoke test."

        package_proc = self._package_app(project_dir)
        if package_proc.returncode != 0:
            return False, f"Packaging failed before smoke test could run:\n{(package_proc.stdout + package_proc.stderr)[-2000:]}"

        jar_path = self._find_jar(project_dir)
        if not jar_path:
            return False, "Packaging succeeded but no runnable jar was found under target/."

        proc = subprocess.Popen(
            ["java", "-jar", jar_path, f"--server.port={SMOKE_TEST_PORT}"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            if not self._wait_for_startup(SMOKE_TEST_PORT, SMOKE_TEST_STARTUP_TIMEOUT):
                startup_log = proc.stdout.read() if proc.stdout else ""
                return False, f"Application did not start within {SMOKE_TEST_STARTUP_TIMEOUT}s.\n{startup_log[-2000:]}"

            base_url = f"http://localhost:{SMOKE_TEST_PORT}"
            failures = []
            for ep in plan.endpoints:
                result = self._check_endpoint(base_url, ep.method, ep.path)
                if result:
                    failures.append(result)

            if failures:
                return False, "Live API smoke test found routing mismatches:\n" + "\n".join(failures)
            return True, f"Live API smoke test passed -- all {len(plan.endpoints)} declared endpoint(s) are routed."
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    # ---------- main entry point ----------

    def test(self, project_root: str, plan: Optional[ProjectPlan] = None) -> TestResult:
        # NEW: check for empty source files FIRST -- this can never surface as a
        # compile error (an empty .java file is syntactically legal), so it has to
        # be caught by reading file content directly, before mvn even runs.
        empty_files = self._find_empty_source_files(project_root)
        if empty_files:
            lines = [
                f"[ERROR] {p}: file is empty -- likely overwritten by a duplicate "
                f"generated-file entry for the same class"
                for p in empty_files
            ]
            raw = "\n".join(lines)
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output=raw,
                error_summary=raw,
            )

        compile_proc = self._compile_check(project_root)
        compile_output = compile_proc.stdout + compile_proc.stderr

        if compile_proc.returncode != 0:
            return TestResult(
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output=compile_output,
                error_summary=self._summarize_compile_errors(compile_output),
            )

        test_src = os.path.join(project_root, "src", "test", "java")
        has_tests = os.path.isdir(test_src) and any(
            f.endswith(".java") for _, _, files in os.walk(test_src) for f in files
        )

        total = passed_count = failed = errors = 0
        unit_raw_output = "No tests found -- compile check passed."
        unit_passed = True

        if has_tests:
            test_proc = self._run(["mvn", "-q", "-B", "test"], project_root)
            unit_raw_output = test_proc.stdout + test_proc.stderr
            unit_passed = test_proc.returncode == 0

            m = SUREFIRE_SUMMARY_RE.search(unit_raw_output)
            if m:
                total, failed, errors, skipped = (int(g) for g in m.groups())
                passed_count = total - failed - errors - skipped

            if not unit_passed:
                return TestResult(
                    passed=False,
                    total_tests=total,
                    passed_tests=passed_count,
                    failed_tests=failed + errors,
                    raw_output=unit_raw_output,
                    error_summary=self._summarize_test_failures(unit_raw_output),
                )

        # Compile + unit/integration tests passed (or none existed) -- now verify the
        # REST endpoints actually exist at the paths the Plan declared. This is the
        # only phase that can catch a controller mapped to the wrong base path.
        smoke_passed, smoke_message = self._live_smoke_test(project_root, plan)

        combined_output = unit_raw_output + "\n\n--- LIVE API SMOKE TEST ---\n" + smoke_message

        return TestResult(
            passed=unit_passed and smoke_passed,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed + errors,
            raw_output=combined_output,
            error_summary=None if smoke_passed else smoke_message,
        )