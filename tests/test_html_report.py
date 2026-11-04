"""HTML report tests: build the page from a hand-made report and check what a reader would see."""

import pytest

from evidence_gate.reporters import html_report
from test_reporters import RECORDS, make_report


def page(report=None, records=None, out_dir="out"):
    return html_report.render(report or make_report(), RECORDS if records is None else records, out_dir)


@pytest.mark.parametrize("verdict, route, css", [
    ("READY", "light_review", "banner ready"),
    ("BLOCKED", "back_to_developer", "banner blocked"),
    ("NEEDS DECISION", "product_owner_decides", "banner decision"),
])
def test_banner_names_the_verdict_in_words_and_colour(verdict, route, css):
    html = page(make_report(verdict=verdict, route=route))
    assert f'class="{css}"' in html and f'<div class="verdict">{verdict}</div>' in html


def test_gate_error_report_without_criteria_still_renders():
    html = page(make_report(verdict="GATE ERROR", exit_code=3, route=None, criteria=[], questions=[],
                            route_reason="The Gate could not finish: x"), records=[])
    assert 'class="banner error"' in html and "none (the Gate could not finish)" in html
    assert "No scenarios were run." in html


def test_route_box_has_route_reason_and_next_action():
    html = page()
    assert "back to developer" in html and "AC-3 failed; AC-4 could not run" in html
    assert "Fix the code, then rerun evidence-gate check." in html


def test_criteria_table_has_every_criterion_and_the_new_question_row():
    html = page()
    for text in ("AC-1", "AC-3", "AC-4", "Verified", "Not verified: failed", "Not verified: could not run", "(new)"):
        assert text in html


def test_mismatched_field_is_highlighted_matching_field_is_not():
    records = [dict(RECORDS[1], mismatches=[{"field": "shipping", "expected": 5.99, "actual": 0.0}]), RECORDS[0]]
    html = page(records=records)
    assert '<span class="bad">shipping 0.00 &ne; 5.99</span>' in html
    assert "shipping 0.00<br>" in html   # AC-1's field matches, so it is plain text


def test_scenario_that_could_not_run_shows_why():
    html = page()
    assert '<span class="bad">could not run</span>' in html and "adapter &#39;browser&#39; was not found" in html


def test_ai_suggestions_are_marked_and_kept_out_of_the_evidence_table():
    html = page()
    assert "AI suggestions <span" in html and "not used for labels" in html and "S-AI-1" in html
    evidence = html.split("Evidence: every scenario that was run")[1].split("AI suggestions")[0]
    assert "S-AI-1" not in evidence          # the unconfirmed AI scenario is not evidence
    assert "S-AC-3-1" in evidence


def test_screenshot_is_linked_relative_to_the_report(tmp_path):
    shot = tmp_path / "out" / "screens" / "S-AC-4-1.png"
    records = [dict(RECORDS[0], artifacts={"screenshot": str(shot)})]
    html = page(records=records, out_dir=tmp_path / "out")
    assert 'src="screens/S-AC-4-1.png"' in html and str(tmp_path) not in html


def test_text_from_outside_is_escaped():
    report = make_report(questions=[{"id": "Q-1", "criterion": None, "text": "<script>alert(1)</script>"}],
                         changed_files=["app/<b>x</b>.py"])
    html = page(report)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "app/<b>x</b>.py" not in html


def test_page_is_self_contained():
    html = page()
    for forbidden in ("http://", "https://", "<link", "<script"):
        assert forbidden not in html


def test_footer_has_tests_line_ai_disclosure_commit_and_run():
    html = page()
    for text in ("Existing tests: 42/42 passed (context only)", "off: no AI was used", "a41c9e2", "r-20261105-101403"):
        assert text in html


def test_footer_names_the_model_and_short_prompt_hash_in_saved_mode():
    report = make_report(challenger={"mode": "saved", "model": "claude-test", "prompt_hash": "0123456789abcdef"})
    assert "saved: model claude-test, prompt 0123456789ab" in page(report)


def test_write_creates_report_html(tmp_path):
    path = html_report.write(make_report(), RECORDS, tmp_path / "out")
    assert path.name == "report.html" and "<!doctype html>" in path.read_text(encoding="utf-8")
