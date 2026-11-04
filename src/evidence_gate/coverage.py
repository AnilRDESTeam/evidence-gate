"""Which changed files count, which are covered by a criterion, and which are high-risk."""

import re
from functools import lru_cache


def norm(path: str) -> str:
    """Forward slashes everywhere, so Windows paths match the same patterns."""
    return path.replace("\\", "/")


@lru_cache(maxsize=None)
def _regex(pattern: str) -> re.Pattern:
    """Glob -> regex. `**` matches any depth, `*` matches one path segment only."""
    pattern = norm(pattern)
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"          # any folders, or none: app/**/x.py matches app/x.py
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def matches(path: str, pattern: str) -> bool:
    return _regex(pattern).match(norm(path)) is not None


def matches_any(path: str, patterns) -> bool:
    return any(matches(path, p) for p in patterns)


def relevant_files(changed: list[str], ignore_paths: list[str]) -> list[str]:
    """Changed files minus the ignored ones (tests, requirements, docs...)."""
    return [norm(f) for f in changed if not matches_any(f, ignore_paths)]


def uncovered_by_scope(files: list[str], scope_paths: list[str]) -> list[str]:
    """Challenger off: a file is covered if it matches the task's scope.paths."""
    return [f for f in files if not matches_any(f, scope_paths)]


def uncovered_by_challenge(files: list[str], challenge: dict) -> list[str]:
    """Challenger saved: a file is covered if the AI mapped it to a criterion.

    A file the AI listed as uncovered, or did not mention at all, stays uncovered:
    when in doubt, a human looks at it.
    """
    covered = {norm(c["file"]) for c in challenge.get("coverage", []) if c.get("criteria")}
    flagged = {norm(u["file"]) for u in challenge.get("uncovered", [])}
    return [f for f in files if f not in covered or f in flagged]


def high_risk_files(files: list[str], high_risk_paths: list[str]) -> list[str]:
    return [f for f in files if matches_any(f, high_risk_paths)]
