"""One test per rule row of contract/RULES.md (labels L1-L7, verdicts V1-V4, routes R1-R5),
plus first-match-wins tests and coverage tests. Test names say which rule they check."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evidence_gate import coverage
from evidence_gate.labeller import (NEEDS_REVIEW, NOT_VERIFIED, VERIFIED, VERIFIED_WAIVED, label_criteria,
                                    label_one, label_text, waiver_is_valid)
from evidence_gate.router import decide_route, next_action
from evidence_gate.verdict import decide_verdict

HEAD = "a41c9e2"
ROOT = Path(__file__).resolve().parent.parent


def rec(status, confirmed=True, criterion="AC-1", commit=HEAD, scenario="S-AC-1-1", mismatches=None):
    return {"criterion": criterion, "scenario": scenario, "confirmed": confirmed, "status": status,
            "commit": commit, "mismatches": mismatches or []}


def label(records, waived=False, question=False):
    return label_one(records, waived, question, HEAD)


def entry(cid="AC-1", priority="MUST", lbl=VERIFIED, reason=None):
    return {"id": cid, "priority": priority, "statement": f"{cid} statement", "label": lbl,
            "reason": reason, "scenarios": []}


# ===== Label rules (first match wins) =====

def test_label_rule1_valid_waiver_is_verified_waived():
    assert label([], waived=True) == (VERIFIED_WAIVED, None)


def test_label_rule1_waiver_beats_a_failed_scenario():
    assert label([rec("fail")], waived=True) == (VERIFIED_WAIVED, None)


@pytest.mark.parametrize("waiver, valid", [
    ({"who": "Anil", "why": "accepted risk", "when": "2026-11-04"}, True),
    ({"who": "Anil", "why": "", "when": "2026-11-04"}, False),
    ({"who": "  ", "why": "x", "when": "2026-11-04"}, False),
    ({"who": "Anil", "why": "x"}, False),
])
def test_label_rule1_waiver_needs_who_why_and_when(waiver, valid):
    assert waiver_is_valid(waiver) is valid


def test_label_rule1_invalid_waiver_is_ignored_by_label_criteria():
    task = {"criteria": [{"id": "AC-1", "priority": "MUST", "statement": "s"}],
            "waivers": [{"criterion": "AC-1", "who": "Anil", "why": "", "when": "2026-11-04"}]}
    assert label_criteria(task, [], [], HEAD)[0]["label"] == NOT_VERIFIED


def test_label_rule2_no_scenarios_is_missing():
    assert label([]) == (NOT_VERIFIED, "missing")


def test_label_rule3_failed():
    assert label([rec("fail")]) == (NOT_VERIFIED, "failed")


def test_label_rule3_failed_beats_passed():
    assert label([rec("pass"), rec("fail")]) == (NOT_VERIFIED, "failed")


def test_label_rule3_failed_beats_error():
    assert label([rec("error"), rec("fail")]) == (NOT_VERIFIED, "failed")


def test_label_rule4_error_is_could_not_run():
    assert label([rec("error")]) == (NOT_VERIFIED, "could_not_run")


def test_label_rule4_error_beats_passed():
    assert label([rec("pass"), rec("error")]) == (NOT_VERIFIED, "could_not_run")


def test_label_rule5_linked_question_is_needs_human_review():
    assert label([rec("pass")], question=True) == (NEEDS_REVIEW, None)


def test_label_rule5_question_beats_a_passed_scenario():
    assert label([rec("pass"), rec("pass")], question=True)[0] == NEEDS_REVIEW


def test_label_rule3_failed_beats_linked_question():
    assert label([rec("fail")], question=True) == (NOT_VERIFIED, "failed")


def test_label_rule2_missing_beats_linked_question():
    assert label([], question=True) == (NOT_VERIFIED, "missing")


def test_label_rule6_passed_on_current_commit_is_verified():
    assert label([rec("pass")]) == (VERIFIED, None)


def test_label_rule6_pass_on_another_commit_is_not_verified():
    assert label([rec("pass", commit="old1234")]) == (NOT_VERIFIED, "could_not_run")


def test_label_rule7_only_ai_scenarios_is_unconfirmed():
    assert label([rec("pass", confirmed=False)]) == (NOT_VERIFIED, "unconfirmed")


def test_label_rule7_ai_scenario_that_passed_never_makes_verified():
    assert label([rec("pass", confirmed=False), rec("pass", confirmed=False)])[0] != VERIFIED


def test_label_ai_failure_never_changes_a_verified_label():
    # Unconfirmed scenarios never change a label from rules 3-6.
    assert label([rec("pass"), rec("fail", confirmed=False)]) == (VERIFIED, None)


def test_label_ai_error_never_changes_a_verified_label():
    assert label([rec("pass"), rec("error", confirmed=False)]) == (VERIFIED, None)


def test_label_text_is_plain_words():
    assert label_text(NOT_VERIFIED, "could_not_run") == "Not verified: could not run"
    assert label_text(VERIFIED_WAIVED, None) == "Verified (waived)"


def test_label_criteria_matches_report_schema_shape():
    task = {"criteria": [{"id": "AC-1", "priority": "MUST", "statement": "s"}]}
    entries = label_criteria(task, [rec("pass")], [], HEAD)
    report_schema = json.loads((ROOT / "contract" / "report.schema.json").read_text(encoding="utf-8"))
    item_schema = report_schema["properties"]["criteria"]["items"]
    assert list(Draft202012Validator(item_schema).iter_errors(entries[0])) == []
    assert entries[0]["scenarios"] == ["S-AC-1-1"]


# ===== Verdict rules =====

def test_verdict_rule1_engine_error_is_gate_error():
    result = decide_verdict([entry()], [], engine_error="git is missing")
    assert (result.verdict, result.exit_code) == ("GATE ERROR", 3)


def test_verdict_rule1_gate_error_beats_blocked():
    result = decide_verdict([entry(lbl=NOT_VERIFIED, reason="failed")], [], engine_error="boom")
    assert result.verdict == "GATE ERROR"


def test_verdict_rule2_must_not_verified_is_blocked():
    result = decide_verdict([entry("AC-1"), entry("AC-2", lbl=NOT_VERIFIED, reason="failed")], [])
    assert (result.verdict, result.exit_code, result.blocking) == ("BLOCKED", 1, ["AC-2"])


def test_verdict_rule2_blocked_beats_needs_decision():
    criteria = [entry("AC-1", lbl=NOT_VERIFIED, reason="missing"), entry("AC-2", lbl=NEEDS_REVIEW)]
    assert decide_verdict(criteria, [{"id": "Q-1", "criterion": None, "text": "?"}]).verdict == "BLOCKED"


def test_verdict_rule3_needs_human_review_item_is_needs_decision():
    result = decide_verdict([entry("AC-1", lbl=NEEDS_REVIEW)], [])
    assert (result.verdict, result.exit_code, result.review) == ("NEEDS DECISION", 2, ["AC-1"])


def test_verdict_rule3_unlinked_question_is_needs_decision():
    result = decide_verdict([entry()], [{"id": "Q-1", "criterion": None, "text": "before or after discounts?"}])
    assert (result.verdict, result.review) == ("NEEDS DECISION", ["Q-1"])


def test_verdict_rule3_question_about_unknown_criterion_counts_as_new():
    result = decide_verdict([entry("AC-1")], [{"id": "Q-1", "criterion": "AC-9", "text": "?"}])
    assert result.verdict == "NEEDS DECISION"


def test_verdict_rule3_linked_question_alone_does_not_add_an_item():
    # The linked question already shows up as the criterion's Needs-human-review label.
    assert decide_verdict([entry("AC-1")], [{"id": "Q-1", "criterion": "AC-1", "text": "?"}]).verdict == "READY"


def test_verdict_rule4_everything_verified_is_ready():
    result = decide_verdict([entry("AC-1"), entry("AC-2", lbl=VERIFIED_WAIVED)], [])
    assert (result.verdict, result.exit_code, result.warnings) == ("READY", 0, [])


def test_verdict_should_not_verified_is_ready_with_a_warning():
    result = decide_verdict([entry("AC-1"), entry("AC-4", "SHOULD", NOT_VERIFIED, "failed")], [])
    assert result.verdict == "READY"
    assert result.warnings == ["AC-4 (SHOULD) is not verified (Not verified: failed)"]


def test_verdict_should_failures_block_policy_blocks():
    result = decide_verdict([entry("AC-4", "SHOULD", NOT_VERIFIED, "failed")], [], should_failures="block")
    assert result.verdict == "BLOCKED" and result.blocking == ["AC-4"]


# ===== Route rules =====

BLOCKED = decide_verdict([entry("AC-2", lbl=NOT_VERIFIED, reason="failed"),
                          entry("AC-3", lbl=NOT_VERIFIED, reason="failed"),
                          entry("AC-4", lbl=NOT_VERIFIED, reason="could_not_run")], [])
NEEDS = decide_verdict([entry()], [{"id": "Q-1", "criterion": None, "text": "before or after discounts?"}])
READY = decide_verdict([entry()], [])


def test_route_rule1_blocked_goes_back_to_developer():
    criteria = [entry("AC-2", lbl=NOT_VERIFIED, reason="failed"), entry("AC-3", lbl=NOT_VERIFIED, reason="failed"),
                entry("AC-4", lbl=NOT_VERIFIED, reason="could_not_run")]
    route, why = decide_route(BLOCKED, criteria, [], [], [])
    assert route == "back_to_developer"
    assert why == "AC-2, AC-3 failed; AC-4 could not run"


def test_route_rule2_needs_decision_goes_to_product_owner():
    route, why = decide_route(NEEDS, [entry()], [{"id": "Q-1", "criterion": None, "text": "before or after discounts?"}], [], [])
    assert route == "product_owner_decides"
    assert "Q-1" in why and "before or after discounts?" in why


def test_route_rule1_blocked_beats_high_risk():
    route, _ = decide_route(BLOCKED, [], [], ["app/payments/x.py"], ["app/y.py"])
    assert route == "back_to_developer"


def test_route_rule2_needs_decision_beats_high_risk():
    assert decide_route(NEEDS, [entry()], [], ["app/payments/x.py"], [])[0] == "product_owner_decides"


def test_route_rule3_high_risk_is_full_review():
    route, why = decide_route(READY, [entry()], [], ["app/payments/charge.py"], [])
    assert route == "full_review" and "app/payments/charge.py" in why


def test_route_rule3_high_risk_and_uncovered_is_full_review_not_focused():
    # Route 3 beats route 4.
    route, _ = decide_route(READY, [entry()], [], ["app/payments/charge.py"], ["app/data/products.json"])
    assert route == "full_review"


def test_route_rule4_uncovered_is_focused_review():
    route, why = decide_route(READY, [entry()], [], [], ["app/data/products.json"])
    assert route == "focused_review"
    assert why == "app/data/products.json changed but no criterion covers it"


def test_route_rule5_everything_else_is_light_review():
    assert decide_route(READY, [entry()], [], [], [])[0] == "light_review"


def test_route_gate_error_has_no_route():
    result = decide_verdict([], [], engine_error="boom")
    assert decide_route(result, [], [], [], [])[0] is None


# ===== next_action =====

def test_next_action_blocked_names_the_failed_field():
    criteria = [entry("AC-3", lbl=NOT_VERIFIED, reason="failed")]
    result = decide_verdict(criteria, [])
    records = [rec("fail", criterion="AC-3", mismatches=[{"field": "shipping", "expected": 5.99, "actual": 0.0}])]
    text = next_action(result, "back_to_developer", criteria, [], records, [], [])
    assert "AC-3" in text and "shipping: expected 5.99, got 0.0" in text and "rerun evidence-gate check" in text


def test_next_action_for_each_route():
    assert "Product owner" in next_action(NEEDS, "product_owner_decides", [entry()],
                                          [{"id": "Q-1", "criterion": None, "text": "q?"}], [], [], [])
    assert "full review" in next_action(READY, "full_review", [], [], [], ["a.py"], [])
    assert "Review only these files" in next_action(READY, "focused_review", [], [], [], [], ["a.py"])
    assert "Skim the evidence" in next_action(READY, "light_review", [], [], [], [], [])


# ===== Coverage =====

def test_glob_double_star_matches_any_depth_and_star_one_segment():
    assert coverage.matches("tests/a/b/test_x.py", "tests/**")
    assert coverage.matches("app/pricing/shipping.py", "app/**/*.py")
    assert coverage.matches("app/shipping.py", "app/**/*.py")
    assert coverage.matches("README.md", "*.md")
    assert not coverage.matches("docs/guide.md", "*.md")      # * stays inside one segment
    assert not coverage.matches("app/a/b.py", "app/*.py")


def test_glob_uses_forward_slashes_for_windows_paths():
    assert coverage.matches("app\\pricing\\shipping.py", "app/pricing/**")


def test_coverage_ignored_files_never_make_code_uncovered():
    ignore = ["tests/**", "requirements/**", "docs/**", "*.md", ".evidence-gate/**"]
    changed = ["tests/test_shipping.py", "requirements/SHOP-102.task.yaml", "README.md", "app/pricing/shipping.py"]
    files = coverage.relevant_files(changed, ignore)
    assert files == ["app/pricing/shipping.py"]
    assert coverage.uncovered_by_scope(files, ["app/pricing/**"]) == []


def test_coverage_challenger_off_uses_scope_paths():
    files = ["app/pricing/shipping.py", "app/data/products.json"]
    assert coverage.uncovered_by_scope(files, ["app/pricing/**"]) == ["app/data/products.json"]


def test_coverage_challenger_saved_uses_the_ai_map():
    challenge = {"coverage": [{"file": "app/pricing/shipping.py", "criteria": ["AC-1"]}],
                 "uncovered": [{"file": "app/data/products.json", "why": "price changed"}]}
    files = ["app/pricing/shipping.py", "app/data/products.json", "app/other.py"]
    # the flagged file and the file the AI never mentioned both stay uncovered
    assert coverage.uncovered_by_challenge(files, challenge) == ["app/data/products.json", "app/other.py"]


def test_coverage_challenger_file_with_no_criteria_is_uncovered():
    challenge = {"coverage": [{"file": "app/a.py", "criteria": []}], "uncovered": []}
    assert coverage.uncovered_by_challenge(["app/a.py"], challenge) == ["app/a.py"]


def test_coverage_high_risk_files():
    files = ["app/payments/charge.py", "app/pricing/shipping.py"]
    assert coverage.high_risk_files(files, ["app/payments/**", "app/customers/**"]) == ["app/payments/charge.py"]
