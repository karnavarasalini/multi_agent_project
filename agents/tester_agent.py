import os
import re
import sys
import subprocess

from models.schemas import TestResult


PY_ERROR_RE = re.compile(r'File "(.+\.py)", line (\d+)')
PYTEST_SUMMARY_RE = re.compile(
    r"=+\s*(?:(\d+) failed,?\s*)?(?:(\d+) passed,?\s*)?(?:(\d+) error(?:s)?,?\s*)?(?:(\d+) skipped,?\s*)?.* in [\d.]+s\s*=+"
)
FAILED_TEST_LINE_RE = re.compile(r"^FAILED\s+(.+?)::(\S+)")


class TesterAgent:

    def _run(self, args: list[str], project_dir: str, timeout: int = 120) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _install_requirements(self, project_dir: str) -> None:
        req_path = os.path.join(project_dir, "requirements.txt")
        if os.path.exists(req_path) and os.path.getsize(req_path) > 0:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=180,
            )

    def _compile_check(self, project_dir: str) -> subprocess.CompletedProcess:
        """Byte-compiles every .py file to catch syntax errors before running anything."""
        py_files = []
        for root, _, files in os.walk(project_dir):
            for fname in files:
                if fname.endswith(".py"):
                    py_files.append(os.path.relpath(os.path.join(root, fname), project_dir))
        if not py_files:
            return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="No Python files found.")
        return self._run([sys.executable, "-m", "py_compile", *py_files], project_dir)

    def _summarize_compile_errors(self, output: str) -> str:
        lines = []
        for match in PY_ERROR_RE.finditer(output):
            file, ln = match.groups()
            lines.append(f"{file}:{ln}")
        return "\n".join(lines) if lines else output.strip()[:500] or "Compilation failed (see raw_output)."

    def _summarize_test_failures(self, output: str) -> str:
        lines = [m.group(0) for m in FAILED_TEST_LINE_RE.finditer(output)]
        return "\n".join(lines) if lines else output.strip()[-1000:] or "Some tests failed (see raw_output)."

    def test(self, project_root: str) -> TestResult:
        self._install_requirements(project_root)

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

        has_tests = os.path.isdir(os.path.join(project_root, "tests")) or any(
            f.startswith("test_") and f.endswith(".py")
            for f in os.listdir(project_root) if os.path.isfile(os.path.join(project_root, f))
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

        test_proc = self._run([sys.executable, "-m", "pytest", "-q"], project_root)
        test_output = test_proc.stdout + test_proc.stderr

        m = PYTEST_SUMMARY_RE.search(test_output)
        failed = int(m.group(1)) if m and m.group(1) else 0
        passed_count = int(m.group(2)) if m and m.group(2) else 0
        errors = int(m.group(3)) if m and m.group(3) else 0
        total = passed_count + failed + errors

        return TestResult(
            passed=(test_proc.returncode == 0),
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed + errors,
            raw_output=test_output,
            error_summary=self._summarize_test_failures(test_output) if (failed + errors) > 0 else None,
        )