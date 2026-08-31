import os
import re
import subprocess

from models.schemas import TestResult


MAVEN_COMPILE_ERROR_RE = re.compile(r"\[ERROR\]\s+(.+?\.java):\[(\d+),(\d+)\]\s*(.*)")
SUREFIRE_SUMMARY_RE = re.compile(
    r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)"
)
FAILED_TEST_LINE_RE = re.compile(r"^(?:Tests in error:|Failed tests:)\s*$|^\s+(\S+Test)[.#](\S+)")


class TesterAgent:

    def _run(self, args: list[str], project_dir: str, timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

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
            file, ln, col, msg = match.groups()
            lines.append(f"{file}:{ln}: {msg.strip()}")
        return "\n".join(lines) if lines else output.strip()[-1500:] or "Compilation failed (see raw_output)."

    def _summarize_test_failures(self, output: str) -> str:
        lines = [f"{m.group(1)}.{m.group(2)}" for m in FAILED_TEST_LINE_RE.finditer(output) if m.group(1)]
        return "\n".join(lines) if lines else output.strip()[-1500:] or "Some tests failed (see raw_output)."

    def test(self, project_root: str) -> TestResult:
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

        if not has_tests:
            return TestResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output="No tests found -- compile check passed.",
                error_summary=None,
            )

        test_proc = self._run(["mvn", "-q", "-B", "test"], project_root)
        test_output = test_proc.stdout + test_proc.stderr

        m = SUREFIRE_SUMMARY_RE.search(test_output)
        if m:
            total, failed, errors, skipped = (int(g) for g in m.groups())
            passed_count = total - failed - errors - skipped
        else:
            total = passed_count = failed = errors = 0

        return TestResult(
            passed=(test_proc.returncode == 0),
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed + errors,
            raw_output=test_output,
            error_summary=self._summarize_test_failures(test_output) if (failed + errors) > 0 else None,
        )