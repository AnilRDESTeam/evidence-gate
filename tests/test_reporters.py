"""Reporter tests: build the output from a hand-made report and check the fields and table rows."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from evidence_gate.reporters import json_report, md_report, terminal

ROOT = Path(__file__).resolve().parent.parent
REPORT_SCHEMA = json.loads((ROOT / "contract" / "report.schema.json").read_text(encoding="utf-8"))


def record(scenario, criterion, status, subtotal, expected, actual, error=None, confirmed=True):
    return {"scenario": scenario, "criterion": criterion, "confirmed": confirmed, "status": status,
            "input": {"subtotal": subtotal}, "expected": {"shipping": expected},
            "actual": None if actual is None else {"shipping": actual}, "error": error}


RECORDS = [
    record("S-AC-1-1", "AC-1", "pass", 75.0, 0.0, 0.0),
    record("S-AC-3-1", "AC-3", "fail", 50.0, 5.99, 0.0),
    record("S-AC-4-1", "AC-4", "error", 74.99, 5.99, None, error="adapter 'browser' was not found"),
    record("S-AI-1", "AC-2", "fail", 74.995, 5.99, 0.0, confirmed=False),
]


def make_report(**changes):
    report = {
        "task": "SHOP-102", "title": "Raise free-shipping threshold", "type": "updated", "commit": "a41c9e2",
        "base": "main", "run_id": "r-20261105-101403", "timestamp": "2026-11-05T10:14:05Z",
        "challenger": {"mode": "off", "model": None, "prompt_hash": None},
        "criteria": [
            {"id": "AC-1", "priority": "MUST", "statement": "s1", "label": "verified", "reason": None, "scenarios": ["S-AC-1-1"]},
            {"id": "AC-3", "priority": "MUST", "statement": "s3", "label": "not_verified", "reason": "failed", "scenarios": ["S-AC-3-1"]},
            {"id": "AC-4", "priority": "MUST", "statement": "s4", "label": "not_verified", "reason": "could_not_run", "scenarios": ["S-AC-4-1"]},
        ],
        "questions": [{"id": "Q-1", "criterion": None, "text": "Is the threshold checked before or after discounts?"}],
        "changed_files": ["app/pricing/shipping.py"], "uncovered_files": [], "high_risk_files": [],
        "ai_suggestions": [{"scenario": "S-AI-1", "criterion": "AC-2", "input": {"subtotal": 74.995},
                            "expected": {"shipping": 5.99}, "actual": {"shipping": 0.0}, "status": "fail", "error": None}],
        "verdict": "BLOCKED", "exit_code": 1, "route": "back_to_developer",
        "route_reason": "AC-3 failed; AC-4 could not run",
        "next_action": "Fix the code, then rerun evidence-gate check.",
        "context": {"tests_passed": 42, "tests_total": 42}, "warnings": [], "contract_version": "1.0",
    }
    report.update(changes)
    return report


def test_hand_made_report_follows_the_contract_schema():
    assert list(Draft202012Validator(REPORT_SCHEMA).iter_errors(make_report())) == []


def test_old_report_without_the_new_optional_fields_is_still_valid():
    report = make_report()
    del report["ai_suggestions"], report["high_risk_files"]
    assert list(Draft202012Validator(REPORT_SCHEMA).iter_errors(report)) == []


def test_json_report_is_written_with_all_fields(tmp_path):
    path = json_report.write(make_report(), tmp_path / "out")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.name == "report.json"
    for field in ("task", "title", "type", "commit", "base", "run_id", "timestamp", "challenger", "criteria",
                  "questions", "ai_suggestions", "changed_files", "uncovered_files", "high_risk_files", "verdict",
                  "exit_code", "route", "route_reason", "next_action", "context", "warnings"):
        assert field in data
    assert data["verdict"] == "BLOCKED" and data["exit_code"] == 1


def test_md_report_first_two_lines():
    lines = md_report.render(make_report(), RECORDS).splitlines()
    assert lines[0] == "Evidence Gate - SHOP-102 (updated requirement) - commit a41c9e2"
    assert lines[1] == "Verdict: BLOCKED (2 MUST criteria not verified)    Route: back to developer"


def test_md_report_table_rows():
    text = md_report.render(make_report(), RECORDS)
    assert "| Criterion | Label | Evidence |" in text
    assert "| AC-1 | Verified | subtotal=75.00 -> shipping 0.00 (expected 0.00) |" in text
    assert "| AC-3 | Not verified: failed | subtotal=50.00 -> shipping 0.00 (expected 5.99) |" in text
    assert "| AC-4 | Not verified: could not run | subtotal=74.99 -> could not run: adapter 'browser' was not found |" in text
    assert "| (new) | Needs human review | Is the threshold checked before or after discounts? |" in text


def test_md_report_ai_scenarios_are_not_shown_as_criterion_evidence():
    text = md_report.render(make_report(), RECORDS)
    assert "74.99" in text and "74.995" not in text.split("AI suggestions")[0]


def test_md_report_footer_lines():
    text = md_report.render(make_report(), RECORDS, full_report="out/report.html")
    assert "Existing tests: 42/42 passed (context only)." in text
    assert "Next action: Fix the code, then rerun evidence-gate check." in text
    assert text.rstrip().endswith("Full report: out/report.html")
    assert "AI suggestions (not used for labels): S-AI-1 fail" in text


def test_md_report_leaves_out_tests_line_and_full_report_when_unknown():
    text = md_report.render(make_report(context=None), RECORDS)
    assert "Existing tests" not in text and "Full report" not in text


def test_md_report_pipe_in_evidence_does_not_break_the_table():
    records = [record("S-AC-1-1", "AC-1", "error", 1.0, 1.0, None, error="a | b")]
    text = md_report.render(make_report(), records)
    assert "a \\| b" in text


def test_md_report_needs_decision_summary():
    report = make_report(verdict="NEEDS DECISION", exit_code=2, route="product_owner_decides",
                         criteria=[make_report()["criteria"][0]])
    assert "Verdict: NEEDS DECISION (1 open question)" in md_report.render(report, RECORDS)


def test_md_report_ready_summary_and_warning():
    report = make_report(verdict="READY", exit_code=0, route="light_review", questions=[],
                         criteria=[make_report()["criteria"][0]], warnings=["AC-9 (SHOULD) is not verified"])
    text = md_report.render(report, RECORDS)
    assert "Verdict: READY (all MUST criteria verified or waived)    Route: light review" in text
    assert "Warning: AC-9 (SHOULD) is not verified" in text


def test_terminal_report_has_verdict_route_rows_questions_and_next_action():
    text = terminal.render(make_report(), RECORDS)
    lines = text.splitlines()
    assert lines[0].startswith("Evidence Gate - SHOP-102")
    assert "VERDICT: BLOCKED (2 MUST criteria not verified)" in text
    assert "ROUTE:   back to developer - AC-3 failed; AC-4 could not run" in text
    assert any(l.startswith("AC-3") and "Not verified: failed" in l and "shipping 0.00 (expected 5.99)" in l for l in lines)
    assert "Q-1 (new): Is the threshold checked before or after discounts?" in text
    assert "Existing tests: 42/42 passed (context only)." in text
    assert text.rstrip().endswith("Next action: Fix the code, then rerun evidence-gate check.")


def test_terminal_verdict_comes_before_the_criteria_lines():
    text = terminal.render(make_report(), RECORDS)
    assert text.index("VERDICT:") < text.index("AC-1")


def test_criterion_without_scenarios_says_so():
    report = make_report(criteria=[{"id": "AC-7", "priority": "SHOULD", "statement": "s", "label": "not_verified",
                                    "reason": "missing", "scenarios": []}], verdict="READY", exit_code=0, questions=[])
    assert "| AC-7 | Not verified: missing | no scenarios |" in md_report.render(report, [])


def test_same_error_on_every_scenario_of_a_criterion_is_said_once():
    records = [record("S-AC-4-1", "AC-4", "error", 1.0, 1.0, None, error="adapter 'browser' was not found"),
               record("S-AC-4-2", "AC-4", "error", 2.0, 1.0, None, error="adapter 'browser' was not found")]
    report = make_report(criteria=[make_report()["criteria"][2]], questions=[])
    text = md_report.render(report, records)
    assert "| AC-4 | Not verified: could not run | could not run: adapter 'browser' was not found (2 scenarios) |" in text
