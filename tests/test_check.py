"""End-to-end tests of `check`. Each test builds a small git project in tmp_path and fakes the HTTP
calls with `responses`, so the real shop is never touched or needed."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import responses
from jsonschema import Draft202012Validator

from evidence_gate import check as check_module
from evidence_gate.check import run_check

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8080"
REPORT_SCHEMA = json.loads((ROOT / "contract" / "report.schema.json").read_text(encoding="utf-8"))

TASK = """\
id: T-1
type: new
title: Shipping
request: r
scope: { paths: ["app/pricing/**"] }
criteria:
  - id: AC-1
    priority: MUST
    statement: A $50.00 order pays $5.99 shipping.
    examples:
      - { via: api.quote_order, input: { subtotal: 50 }, expect: { shipping: 5.99 } }
"""


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def head(repo):
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def project(tmp_path):
    """A shop-like repo on main with the Gate's config. Output goes outside it so the tree stays clean."""
    repo = tmp_path / "shop"
    (repo / ".evidence-gate" / "adapters").mkdir(parents=True)
    (repo / "requirements").mkdir()
    (repo / "app" / "pricing").mkdir(parents=True)
    shutil.copy(ROOT / "contract" / "examples" / "api.adapter.yaml", repo / ".evidence-gate" / "adapters" / "api.yaml")
    shutil.copy(ROOT / "contract" / "policy.default.yaml", repo / ".evidence-gate" / "policy.yaml")
    (repo / "requirements" / "T.task.yaml").write_text(TASK, encoding="utf-8")
    (repo / "app" / "pricing" / "shipping.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "init", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "base")
    return repo


def fake_shop(repo, shipping, commit=None):
    responses.get(f"{BASE}/api/health", json={"commit": commit or head(repo)})
    responses.post(f"{BASE}/api/test/reset", json={"status": "reset"})
    responses.post(f"{BASE}/api/cart/quote", json={"shipping": shipping, "subtotal": 50.0, "total": 50.0})


def check(repo, tmp_path, **kwargs):
    kwargs.setdefault("pdf", False)   # a PDF needs a browser start; tests/test_pdf_report.py covers it
    return run_check(str(repo / "requirements" / "T.task.yaml"), out_dir=str(tmp_path / "out"), **kwargs)


def report_of(tmp_path):
    return json.loads((tmp_path / "out" / "report.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_real_test_run(monkeypatch):
    """The example adapter's tests_command points at a .venv the temp repo does not have, so by default
    no tests are run here. The tests at the bottom of the file replace this stub."""
    monkeypatch.setattr(check_module.context, "run_existing_tests", lambda command, cwd: (None, None))


@responses.activate
def test_check_ready_exit_0_and_all_reports_written(project, tmp_path, capsys):
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert (report["verdict"], report["exit_code"], report["route"]) == ("READY", 0, "light_review")
    assert list(Draft202012Validator(REPORT_SCHEMA).iter_errors(report)) == []
    for name in ("report.json", "report.md", "evidence.jsonl"):
        assert (tmp_path / "out" / name).exists()
    assert "VERDICT: READY" in capsys.readouterr().out
    assert "Verdict: READY" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")


@responses.activate
def test_check_blocked_exit_1_back_to_developer(project, tmp_path, capsys):
    fake_shop(project, shipping=0.0)  # the old $50 rule is still there
    assert check(project, tmp_path) == 1
    report = report_of(tmp_path)
    assert (report["verdict"], report["route"]) == ("BLOCKED", "back_to_developer")
    assert report["criteria"][0]["label"] == "not_verified" and report["criteria"][0]["reason"] == "failed"
    assert "shipping 0.00 (expected 5.99)" in capsys.readouterr().out


@responses.activate
def test_check_needs_decision_exit_2_from_spec_question(project, tmp_path):
    task = project / "requirements" / "T.task.yaml"
    task.write_text(TASK + "open_questions:\n  - { id: Q-1, text: guests too?, criterion: null }\n", encoding="utf-8")
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 2
    assert report_of(tmp_path)["route"] == "product_owner_decides"


@responses.activate
def test_check_question_linked_to_criterion_gives_needs_human_review(project, tmp_path):
    task = project / "requirements" / "T.task.yaml"
    task.write_text(TASK + "open_questions:\n  - { id: Q-1, text: rounding?, criterion: AC-1 }\n", encoding="utf-8")
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 2
    assert report_of(tmp_path)["criteria"][0]["label"] == "needs_human_review"


@responses.activate
def test_check_stale_shop_commit_is_could_not_run(project, tmp_path):
    fake_shop(project, shipping=5.99, commit="deadbee")
    assert check(project, tmp_path) == 1
    report = report_of(tmp_path)
    assert report["criteria"][0]["reason"] == "could_not_run"
    evidence = json.loads((tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8"))
    assert "commit mismatch: shop runs deadbee" in evidence["error"]


@responses.activate
def test_check_uncovered_changed_file_gives_focused_review(project, tmp_path):
    git(project, "checkout", "-b", "feature")
    (project / "app" / "data.json").write_text("{}", encoding="utf-8")
    (project / "app" / "pricing" / "shipping.py").write_text("x = 2\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-m", "change")
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert report["route"] == "focused_review"
    assert report["uncovered_files"] == ["app/data.json"]
    assert report["changed_files"] == ["app/data.json", "app/pricing/shipping.py"]


@responses.activate
def test_check_high_risk_file_gives_full_review(project, tmp_path):
    git(project, "checkout", "-b", "feature")
    (project / "app" / "payments").mkdir()
    (project / "app" / "payments" / "charge.py").write_text("x\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-m", "pay")
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert report["route"] == "full_review" and report["high_risk_files"] == ["app/payments/charge.py"]


@responses.activate
def test_check_dirty_tree_is_a_warning(project, tmp_path):
    (project / "stray.txt").write_text("x", encoding="utf-8")
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    assert any("uncommitted" in w for w in report_of(tmp_path)["warnings"])


def test_check_invalid_task_exit_3_with_message(project, tmp_path, capsys):
    (project / "requirements" / "T.task.yaml").write_text(TASK.replace("    priority: MUST\n", ""), encoding="utf-8")
    assert check(project, tmp_path) == 3
    assert "'priority' is required" in capsys.readouterr().err


def test_check_missing_task_exit_3(project, tmp_path, capsys):
    assert run_check(str(project / "nope.yaml"), out_dir=str(tmp_path / "out")) == 3
    assert "File not found" in capsys.readouterr().err


def test_check_not_a_git_repo_exit_3(tmp_path, capsys):
    (tmp_path / ".evidence-gate").mkdir()
    task = tmp_path / "T.task.yaml"
    task.write_text(TASK, encoding="utf-8")
    assert run_check(str(task), out_dir=str(tmp_path / "out")) == 3
    assert "git" in capsys.readouterr().err


def test_check_live_challenger_is_refused(project, tmp_path, capsys):
    assert check(project, tmp_path, challenger="live") == 3
    assert "--challenger live is not available" in capsys.readouterr().err


def test_check_saved_challenger_needs_a_challenge_file(project, tmp_path, capsys):
    assert check(project, tmp_path, challenger="saved") == 3
    assert "--challenge-file" in capsys.readouterr().err


@responses.activate
def test_check_unexpected_error_is_short_exit_3_and_writes_a_gate_error_report(project, tmp_path, capsys, monkeypatch):
    fake_shop(project, shipping=5.99)

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(check_module, "run_scenarios", boom)
    assert check(project, tmp_path) == 3
    err = capsys.readouterr().err
    assert "unexpected problem: RuntimeError: kaboom" in err and "Traceback" not in err
    report = report_of(tmp_path)
    assert (report["verdict"], report["exit_code"], report["route"]) == ("GATE ERROR", 3, None)
    assert list(Draft202012Validator(REPORT_SCHEMA).iter_errors(report)) == []


@responses.activate
def test_check_missing_adapter_file_makes_scenarios_error_not_crash(project, tmp_path):
    (project / ".evidence-gate" / "adapters" / "api.yaml").unlink()
    git(project, "add", "-A")
    git(project, "commit", "-m", "no adapter")
    assert check(project, tmp_path) == 1
    assert report_of(tmp_path)["criteria"][0]["reason"] == "could_not_run"


# ---- existing-tests context ----

@responses.activate
def test_check_existing_tests_go_into_report_terminal_and_md(project, tmp_path, capsys, monkeypatch):
    calls = []

    def fake_run(command, cwd):
        calls.append((command, cwd))
        return {"tests_passed": 41, "tests_total": 42}, None
    monkeypatch.setattr(check_module.context, "run_existing_tests", fake_run)
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert report["context"] == {"tests_passed": 41, "tests_total": 42}
    assert list(Draft202012Validator(REPORT_SCHEMA).iter_errors(report)) == []
    assert "Existing tests: 41/42 passed (context only)" in capsys.readouterr().out
    assert "Existing tests: 41/42 passed (context only)" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    # The command comes from api.yaml and runs in the project folder.
    assert calls == [(".venv\\Scripts\\python -m pytest -q", str(project))]


@responses.activate
def test_check_no_tests_flag_skips_the_run(project, tmp_path, monkeypatch):
    def must_not_run(command, cwd):
        raise AssertionError("tests were run")
    monkeypatch.setattr(check_module.context, "run_existing_tests", must_not_run)
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path, no_tests=True) == 0
    assert report_of(tmp_path)["context"] is None


@responses.activate
def test_check_failing_existing_tests_never_change_the_verdict(project, tmp_path, monkeypatch):
    monkeypatch.setattr(check_module.context, "run_existing_tests",
                        lambda command, cwd: ({"tests_passed": 0, "tests_total": 42}, None))
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert (report["verdict"], report["route"]) == ("READY", "light_review")


@responses.activate
def test_check_unreadable_test_output_is_a_warning(project, tmp_path, monkeypatch):
    monkeypatch.setattr(check_module.context, "run_existing_tests",
                        lambda command, cwd: (None, "Existing tests were skipped: no pytest summary"))
    fake_shop(project, shipping=5.99)
    assert check(project, tmp_path) == 0
    report = report_of(tmp_path)
    assert report["context"] is None and any("Existing tests were skipped" in w for w in report["warnings"])
