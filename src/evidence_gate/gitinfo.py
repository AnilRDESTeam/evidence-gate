"""Read facts about the repo under test (the shop) by running git. Never changes the repo."""

import subprocess
from pathlib import Path

from evidence_gate.loader import GateInputError


class GitError(GateInputError):
    """git is missing, or the folder is not a git repo. Reported as GATE ERROR (exit 3)."""

    def __init__(self, message: str):
        super().__init__([message])


def _git(repo, *args: str) -> str:
    """Run one git command inside `repo` and return its output."""
    # quotepath=off keeps non-ASCII file names readable instead of "\303\251" escapes.
    cmd = ["git", "-c", "core.quotepath=off", *args]
    try:
        done = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except FileNotFoundError:
        raise GitError("git was not found. Install git and make sure it is on PATH.")
    except NotADirectoryError:
        raise GitError(f"{repo} is not a folder.")
    if done.returncode != 0:
        detail = done.stderr.strip() or f"exit code {done.returncode}"
        raise GitError(f"git {' '.join(args)} failed in {repo}: {detail}")
    return done.stdout


def head_commit(repo) -> str:
    """Short hash of the commit the repo is on."""
    return _git(repo, "rev-parse", "--short", "HEAD").strip()


def changed_files(repo, base: str = "main") -> list[str]:
    """Files changed on this branch since it left `base`, with forward slashes."""
    # Three dots = compare against the merge-base, so new commits on base do not show up.
    out = _git(repo, "diff", "--name-only", f"{base}...HEAD")
    return [line.replace("\\", "/") for line in out.splitlines() if line.strip()]


def is_dirty(repo) -> bool:
    """True if there are uncommitted or untracked changes."""
    return bool(_git(repo, "status", "--porcelain").strip())


def diff_text(repo, base: str = "main") -> str:
    """The full diff of this branch against `base` (used by the Challenger prompt)."""
    return _git(repo, "diff", f"{base}...HEAD")


def file_text(repo, path: str) -> str:
    """Current text of one file in the repo; empty string if it was deleted."""
    target = Path(repo) / path
    if not target.is_file():
        return ""
    return target.read_text(encoding="utf-8", errors="replace")
