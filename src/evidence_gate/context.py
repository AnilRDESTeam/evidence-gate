"""Existing-tests context: run the project's own tests and count passes. Context only, it never changes the verdict."""

import re
import subprocess

TIMEOUT_SECONDS = 300
_COUNT = re.compile(r"(\d+) (passed|failed|errors?)\b")


def parse_pytest_summary(output: str) -> dict | None:
    """Read 'N passed' / 'N failed' from the pytest summary line, e.g. '2 failed, 54 passed, 1 warning in 0.7s'.
    Returns None if there is no summary line (for example when pytest ran with -qq)."""
    for line in reversed(output.strip().splitlines()):
        # The summary is the last line that ends with the run time ("in 0.73s").
        if re.search(r"\bin [\d.]+s\b", line):
            counts = {}
            for number, word in _COUNT.findall(line):
                counts[word.rstrip("s")] = int(number)  # "errors" -> "error"
            if not counts:
                return None
            passed = counts.get("passed", 0)
            # Errors count as tests that ran and did not pass.
            total = passed + counts.get("failed", 0) + counts.get("error", 0)
            return {"tests_passed": passed, "tests_total": total}
    return None


def run_existing_tests(command: str | None, cwd: str) -> tuple[dict | None, str | None]:
    """Returns (context, warning). A test command that fails or cannot be read is a warning, never an error."""
    if not command:
        return None, None
    try:
        # shell=True because the command is a line from the adapter file, such as ".venv\\Scripts\\python -m pytest".
        done = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return None, f"Existing tests were skipped: '{command}' took longer than {TIMEOUT_SECONDS} s."
    except OSError as err:
        return None, f"Existing tests were skipped: cannot run '{command}' ({err})."
    context = parse_pytest_summary(done.stdout + "\n" + done.stderr)
    if context is None:
        return None, (f"Existing tests were skipped: no pytest summary in the output of '{command}' "
                      "(exit code " + str(done.returncode) + "). Check context.tests_command.")
    return context, None
