"""Challenger off + saved: the prompt builder, the saved-file loader, and how `check` uses them.
The `check` tests inject a fake driver, so no shop, no network and no `responses` are needed."""

import hashlib
import json
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path

import pytest

from evidence_gate import challenger, check as check_module
from evidence_gate.check import run_check
from evidence_gate.drivers.base import Driver, DriverResult
from evidence_gate.loader import GateInputError

ROOT = Path(__file__).resolve().parent.parent

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
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                          cwd=repo, check=True, capture_output=True, text=True).stdout


def head(repo):
    return git(repo, "rev-parse", "--short", "HEAD").strip()


@pytest.fixture
def project(tmp_path):
    """A shop-like repo: main, then a branch that changes pricing code (in scope), a product file (not in scope),
    a test (ignored) and a coding prompt (must never reach the Challenger)."""
    repo = tmp_path / "shop"
    (repo / ".evidence-gate" / "adapters").mkdir(parents=True)
    for folder in ("requirements", "app/pricing", "app/catalog", "tests", "prompts"):
        (repo / folder).mkdir(parents=True)
    shutil.copy(ROOT / "contract" / "examples" / "api.adapter.yaml", repo / ".evidence-gate" / "adapters" / "api.yaml")
    shutil.copy(ROOT / "contract" / "policy.default.yaml", repo / ".evidence-gate" / "policy.yaml")
    (repo / "requirements" / "T.task.yaml").write_text(TASK, encoding="utf-8")
    (repo / "app" / "pricing" / "shipping.py").write_text("THRESHOLD = 50\n", encoding="utf-8")
    (repo / "app" / "catalog" / "products.py").write_text("NOTE = 3.00\n", encoding="utf-8")
    git(repo, "init", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "base")
    git(repo, "checkout", "-b", "feature")
    (repo / "app" / "pricing" / "shipping.py").write_text("THRESHOLD = 75\n", encoding="utf-8")
    (repo / "app" / "catalog" / "products.py").write_text("NOTE = 3.50\n", encoding="utf-8")
    (repo / "tests" / "test_x.py").write_text("SECRET_TEST_TEXT = 1\n", encoding="utf-8")
    (repo / "prompts" / "coding.md").write_text("SECRET_CODING_PROMPT\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "change")
    return repo


def task_path(repo):
    return repo / "requirements" / "T.task.yaml"


# ---- the prompt ----

def build(repo, ignore=("tests/**", "requirements/**", "docs/**", "*.md", ".evidence-gate/**")):
    return challenger.build_prompt(task_path(repo), repo, "main", list(ignore))


def test_prompt_has_task_commit_diff_and_changed_file_text(project):
    prompt = build(project)
    assert "id: T-1" in prompt and f"commit {head(project)}" in prompt
    assert "THRESHOLD = 75" in prompt and "-THRESHOLD = 50" in prompt   # the diff
    assert "--- app/pricing/shipping.py ---" in prompt and "--- app/catalog/products.py ---" in prompt
    for token in ("{task_yaml}", "{commit}", "{diff}", "{files}"):
        assert token not in prompt


def test_prompt_leaves_out_ignored_files_and_never_includes_prompts(project):
    # Even a policy that forgot prompts/** must not leak the coding prompt.
    prompt = build(project, ignore=["tests/**"])
    assert "SECRET_TEST_TEXT" not in prompt
    assert "SECRET_CODING_PROMPT" not in prompt


def test_prompt_with_only_ignored_changes_has_an_empty_diff_not_the_whole_diff(project):
    git(project, "checkout", "-b", "docs-only", "main")
    (project / "tests").mkdir(exist_ok=True)  # git does not keep empty folders, and main has no tests/ yet
    (project / "tests" / "test_y.py").write_text("ONLY_TEST_CHANGE = 1\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-m", "tests only")
    assert "ONLY_TEST_CHANGE" not in build(project)


def test_text_that_looks_like_a_token_is_left_alone(project):
    (project / "app" / "pricing" / "shipping.py").write_text("X = '{files} {commit}'\n", encoding="utf-8")
    git(project, "add", ".")
    git(project, "commit", "-m", "odd text")
    assert "X = '{files} {commit}'" in build(project)


def test_prompt_hash_is_sha256_of_the_template():
    template = challenger.TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert challenger.prompt_hash() == hashlib.sha256(template.encode("utf-8")).hexdigest()


def run_cli(repo, *args):
    return subprocess.run([sys.executable, "-m", "evidence_gate.cli", *args], cwd=repo, capture_output=True, text=True,
                          encoding="utf-8")


def test_challenge_prompt_command_prints_prompt_and_hash_separately(project):
    result = run_cli(project, "challenge-prompt", "--task", str(task_path(project)))
    assert result.returncode == 0, result.stderr
    assert "THRESHOLD = 75" in result.stdout and "prompt_hash" not in result.stdout
    assert f"prompt_hash {challenger.prompt_hash()}" in result.stderr


def test_challenge_prompt_command_bad_task_is_gate_error(project):
    result = run_cli(project, "challenge-prompt", "--task", str(project / "nope.yaml"))
    assert result.returncode == 3 and "File not found" in result.stderr


# ---- the saved file ----

def answer(commit, **changes):
    base = {"task": "T-1", "commit": commit,
            "coverage": [{"file": "app/pricing/shipping.py", "criteria": ["AC-1"]}],
            "uncovered": [{"file": "app/catalog/products.py", "why": "Price changed; no criterion asks for it."}],
            "questions": [], "proposed_scenarios": []}
    return {**base, **changes}


def save(tmp_path, data, name="challenge.json", fenced=False):
    text = json.dumps(data) if isinstance(data, dict) else data
    path = tmp_path / name
    path.write_text(f"```json\n{text}\n```\n" if fenced else text, encoding="utf-8")
    return path


def test_load_happy_path_and_fenced_answer(tmp_path):
    data = answer("a41c9e2")
    assert challenger.load_challenge(save(tmp_path, data), "a41c9e2", "T-1") == data
    assert challenger.load_challenge(save(tmp_path, data, fenced=True), "a41c9e2", "T-1") == data


def test_load_accepts_short_and_long_forms_of_the_same_commit(tmp_path):
    path = save(tmp_path, answer("a41c9e2f0b"))
    assert challenger.load_challenge(path, "a41c9e2", "T-1")


def test_load_wrong_commit_says_to_run_challenge_prompt_again(tmp_path):
    with pytest.raises(GateInputError) as err:
        challenger.load_challenge(save(tmp_path, answer("a41c9e2")), "b52d0f3", "T-1")
    assert "challenge.json is for commit a41c9e2, branch is at b52d0f3. Run challenge-prompt again." in err.value.problems[0]


def test_load_wrong_task_is_refused(tmp_path):
    with pytest.raises(GateInputError, match="is for task SHOP-101, not T-1"):
        challenger.load_challenge(save(tmp_path, answer("a41c9e2", task="SHOP-101")), "a41c9e2", "T-1")


@pytest.mark.parametrize("bad, message", [
    ("this is not json", "not valid JSON"),
    ({"task": "T-1", "commit": "a41c9e2"}, "'coverage' is a required property"),
    (answer("a41c9e2", questions=[{"id": "one", "criterion": None, "text": "?"}]), "questions/0/id"),
    (answer("a41c9e2", proposed_scenarios=[{"criterion": None, "input": {}, "expected_guess": {}, "why": "w"}] * 6),
     "proposed_scenarios"),
])
def test_load_invalid_file_is_a_gate_error(tmp_path, bad, message):
    with pytest.raises(GateInputError, match=message):
        challenger.load_challenge(save(tmp_path, bad), "a41c9e2", "T-1")


def test_load_missing_file_is_a_gate_error(tmp_path):
    with pytest.raises(GateInputError, match="cannot read"):
        challenger.load_challenge(tmp_path / "nope.json", "a41c9e2", "T-1")


def test_merge_questions_renumbers_a_clash_with_the_spec_question():
    spec = [{"id": "Q-1", "criterion": None, "text": "from the spec"}]
    ai = [{"id": "Q-1", "criterion": "AC-1", "text": "from the AI"}, {"id": "Q-2", "criterion": None, "text": "second"}]
    merged = challenger.merge_questions(spec, ai)
    assert [q["text"] for q in merged] == ["from the spec", "from the AI", "second"]
    assert [q["id"] for q in merged] == ["Q-1", "Q-3", "Q-2"]


# ---- through `check` ----

class FakeShop(Driver):
    """Answers every quote with free shipping at 75 and up, like the new rule."""

    def __init__(self, commit, shipping=5.99):
        self.commit, self.shipping = commit, shipping

    def health_commit(self):
        return self.commit

    def before_each(self):
        pass

    def run(self, action, inputs):
        return DriverResult(actual={"shipping": self.shipping})

    def close(self):
        pass


@pytest.fixture
def check_with_fake_shop(project, tmp_path, monkeypatch):
    monkeypatch.setattr(check_module, "run_scenarios",
                        partial(check_module.run_scenarios, driver_factory=lambda *a: FakeShop(head(project))))

    def run(**kwargs):
        kwargs.setdefault("pdf", False)   # a PDF needs a browser start; only the PDF tests ask for one
        code = run_check(str(task_path(project)), out_dir=str(tmp_path / "out"), no_tests=True, **kwargs)
        report = json.loads((tmp_path / "out" / "report.json").read_text(encoding="utf-8"))
        return code, report
    return run


def test_off_mode_uses_scope_paths_and_records_no_ai(check_with_fake_shop, tmp_path, capsys):
    code, report = check_with_fake_shop()
    assert "<!doctype html>" in (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "Full report: " in capsys.readouterr().out
    assert report["challenger"] == {"mode": "off", "model": None, "prompt_hash": None}
    assert report["uncovered_files"] == ["app/catalog/products.py"]      # not in scope.paths
    assert (code, report["route"]) == (0, "focused_review") and report["ai_suggestions"] == []


def test_check_writes_report_pdf_next_to_the_html_and_points_to_it(check_with_fake_shop, tmp_path, capsys):
    code, _ = check_with_fake_shop(pdf=True)
    out = capsys.readouterr()
    pdf = tmp_path / "out" / "report.pdf"
    if not pdf.exists():
        pytest.skip("no browser to print with: " + out.err.strip())
    assert code == 0 and pdf.read_bytes().startswith(b"%PDF")
    assert "report.html and " in out.out and out.out.rstrip().endswith("report.pdf")
    assert "report.html and" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")


def test_a_pdf_that_cannot_be_made_is_a_note_and_never_changes_the_result(check_with_fake_shop, tmp_path, capsys,
                                                                         monkeypatch):
    monkeypatch.setattr(check_module.pdf_report, "write", lambda html, channel=None: (None, "PDF not written: no browser"))
    code, report = check_with_fake_shop(pdf=True)
    out = capsys.readouterr()
    assert code == 0 and report["verdict"] == "READY"      # the missing PDF changed nothing
    assert "Note: PDF not written: no browser" in out.err
    assert not (tmp_path / "out" / "report.pdf").exists() and "report.pdf" not in out.out


def test_no_pdf_means_no_browser_is_started(check_with_fake_shop, tmp_path, monkeypatch):
    monkeypatch.setattr(check_module.pdf_report, "write", lambda *a, **k: pytest.fail("a PDF was requested"))
    check_with_fake_shop(pdf=False)
    assert (tmp_path / "out" / "report.html").exists()


def test_saved_mode_uses_the_challenge_coverage_and_records_the_ai(check_with_fake_shop, project, tmp_path):
    # The AI maps both files to AC-1, so nothing is uncovered, unlike off mode.
    data = answer(head(project), model="claude-test",
                  coverage=[{"file": "app/pricing/shipping.py", "criteria": ["AC-1"]},
                            {"file": "app/catalog/products.py", "criteria": ["AC-1"]}], uncovered=[])
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, data)))
    assert report["challenger"] == {"mode": "saved", "model": "claude-test", "prompt_hash": challenger.prompt_hash()}
    assert (code, report["route"], report["uncovered_files"]) == (0, "light_review", [])
    lines = (tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines and all(json.loads(line)["challenger"]["mode"] == "saved" for line in lines)


def test_saved_mode_uncovered_file_gives_focused_review(check_with_fake_shop, project, tmp_path):
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, answer(head(project)))))
    assert (code, report["route"]) == (0, "focused_review")
    assert report["uncovered_files"] == ["app/catalog/products.py"]


def test_saved_mode_a_file_the_ai_did_not_mention_stays_uncovered(check_with_fake_shop, project, tmp_path):
    data = answer(head(project), coverage=[], uncovered=[])
    _, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, data)))
    assert sorted(report["uncovered_files"]) == ["app/catalog/products.py", "app/pricing/shipping.py"]


def test_saved_question_linked_to_a_criterion_needs_human_review(check_with_fake_shop, project, tmp_path):
    data = answer(head(project), questions=[{"id": "Q-1", "criterion": "AC-1", "text": "Before or after discounts?"}])
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, data)))
    assert report["criteria"][0]["label"] == "needs_human_review"
    assert (code, report["route"]) == (2, "product_owner_decides")


def test_saved_question_without_a_criterion_is_a_new_item(check_with_fake_shop, project, tmp_path):
    data = answer(head(project), questions=[{"id": "Q-1", "criterion": None, "text": "What about guests?"}])
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, data)))
    assert report["criteria"][0]["label"] == "verified"                  # the criterion itself is untouched
    assert (code, report["route"]) == (2, "product_owner_decides")
    assert [q["text"] for q in report["questions"]] == ["What about guests?"]


def test_ai_suggestions_are_listed_but_never_change_a_label(check_with_fake_shop, project, tmp_path):
    # The AI guesses 0.0 shipping, the shop says 5.99: the guess "fails", and AC-1 must stay Verified.
    idea = {"criterion": "AC-1", "input": {"subtotal": 74.99}, "expected_guess": {"shipping": 0.0}, "why": "boundary"}
    data = answer(head(project), proposed_scenarios=[idea])
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, data)))
    assert (code, report["criteria"][0]["label"]) == (0, "verified")
    assert [(s["scenario"], s["status"]) for s in report["ai_suggestions"]] == [("S-AI-1", "fail")]


def test_saved_challenge_for_another_commit_is_a_gate_error(check_with_fake_shop, project, tmp_path, capsys):
    code, report = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, answer("0000000"))))
    assert code == 3 and report["verdict"] == "GATE ERROR"
    assert "Run challenge-prompt again" in capsys.readouterr().err


def test_saved_invalid_challenge_is_a_gate_error(check_with_fake_shop, project, tmp_path, capsys):
    code, _ = check_with_fake_shop(challenger="saved", challenge_file=str(save(tmp_path, "not json")))
    assert code == 3 and "not valid JSON" in capsys.readouterr().err
