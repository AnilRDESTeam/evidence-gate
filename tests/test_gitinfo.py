"""Tests for gitinfo, run against the real shop-demo repo (read-only: they never change it).

Each result is cross-checked against git itself, so the tests stay true on any branch.
They are skipped when shop-demo is not next to this repo.
"""

import os
import subprocess
from pathlib import Path

import pytest

from evidence_gate import gitinfo

# Override with EVIDENCE_GATE_SHOP if the shop lives somewhere else.
SHOP = Path(os.environ.get("EVIDENCE_GATE_SHOP", Path(__file__).resolve().parents[2] / "shop-demo"))

pytestmark = pytest.mark.skipif(not (SHOP / ".git").exists(), reason="shop-demo repo not found next to evidence-gate")


def raw_git(*args):
    """Ask git directly, as the expected value."""
    return subprocess.run(["git", *args], cwd=SHOP, capture_output=True, text=True, check=True).stdout


def test_head_commit_matches_git():
    assert gitinfo.head_commit(SHOP) == raw_git("rev-parse", "--short", "HEAD").strip()


def test_changed_files_match_git_and_use_forward_slashes():
    expected = raw_git("diff", "--name-only", "main...HEAD").split()
    got = gitinfo.changed_files(SHOP, "main")
    assert got == expected
    assert all("\\" not in f for f in got)


def test_changed_files_empty_on_main():
    if raw_git("branch", "--show-current").strip() != "main":
        pytest.skip("shop-demo is not on main")
    assert gitinfo.changed_files(SHOP, "main") == []


def test_is_dirty_matches_git_status():
    assert gitinfo.is_dirty(SHOP) == bool(raw_git("status", "--porcelain").strip())


def test_diff_text_matches_git():
    assert gitinfo.diff_text(SHOP, "main") == raw_git("diff", "main...HEAD")


def test_file_text_reads_a_real_file():
    text = gitinfo.file_text(SHOP, "requirements/SHOP-102.task.yaml")
    assert "SHOP-102" in text


def test_file_text_missing_file_is_empty():
    assert gitinfo.file_text(SHOP, "no/such/file.py") == ""


def test_unknown_base_branch_is_a_gate_error():
    with pytest.raises(gitinfo.GitError):
        gitinfo.changed_files(SHOP, "no-such-branch-xyz")


def test_folder_that_is_not_a_repo_is_a_gate_error(tmp_path):
    with pytest.raises(gitinfo.GitError):
        gitinfo.head_commit(tmp_path)


def test_missing_folder_is_a_gate_error(tmp_path):
    with pytest.raises(gitinfo.GitError):
        gitinfo.head_commit(tmp_path / "nope")


def test_git_not_installed_is_a_gate_error(monkeypatch):
    # With an empty PATH, git cannot be found, so we must get the friendly error (not a crash).
    monkeypatch.setenv("PATH", "")
    with pytest.raises(gitinfo.GitError) as err:
        gitinfo.head_commit(SHOP)
    assert "git was not found" in err.value.problems[0]
