"""The evaluation overview: every case and its status, then one page per case."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evidence_gate.reporters import overview_report
from test_reporters import RECORDS, make_report

# A 1x1 PNG, so there is a real image to embed.
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")

LABELS = {"AC-1": "verified", "AC-2": "failed", "AC-3": "failed", "AC-4": "failed"}


def make_case_folder(root: Path, name: str, with_screenshot=False) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    records = [dict(r) for r in RECORDS]
    if with_screenshot:
        (folder / "screens").mkdir()
        (folder / "screens" / "S-AC-1-1.png").write_bytes(PNG)
        # The recorded path is relative to the folder `check` ran in, so it does not exist from here.
        records[0]["artifacts"] = {"screenshot": "out/E2/off/run1/screens/S-AC-1-1.png"}
    (folder / "report.json").write_text(json.dumps(make_report()), encoding="utf-8")
    (folder / "evidence.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return folder


def case(case_id, status="match", report_dir=None, notes=(), expected=True, description="Old rule kept"):
    return {"case_id": case_id, "branch": f"eval/{case_id}", "description": description, "origin": "planted",
            "runs": 5, "stable_pct": 100,
            "got": {"verdict": "BLOCKED", "route": "back_to_developer", "labels": LABELS},
            "expected": {"verdict": "BLOCKED", "route": "back_to_developer", "labels": LABELS} if expected else None,
            "status": status, "notes": list(notes), "report_dir": str(report_dir) if report_dir else None}


def summary(cases, mode="off", **changes):
    base = {"mode": mode, "generated": "2026-11-04 17:00", "runs": 5,
            "metrics": {"misses": [], "false_alarms": [], "held_up": [], "light_defects": [], "stability_min": 100,
                        "light_share": "20% (5 of 25)"},
            "known": [], "differences": [], "cases": cases}
    base.update(changes)
    return base


def test_overview_lists_every_case_with_its_status_and_the_key(tmp_path):
    cases = [case("E2", "match", make_case_folder(tmp_path, "E2")),
             case("E3", "known", make_case_folder(tmp_path, "E3"), notes=["READY; the key expects NEEDS_DECISION"]),
             case("E5", "held_up", make_case_folder(tmp_path, "E5"))]
    html = overview_report.render(summary(cases), tmp_path)
    for text in ("E2", "E3", "E5", "MATCHES THE KEY", "KNOWN LIMITATION", "HELD UP BY QUESTIONS",
                 "BLOCKED / back to developer", "AC-1 verified", "AC-2 failed", "identical in 100% of 5 runs",
                 "READY; the key expects NEEDS_DECISION"):
        assert text in html, text


def test_overview_shows_the_headline_numbers():
    html = overview_report.render(summary([case("E2")], metrics={
        "misses": ["E9"], "false_alarms": [], "held_up": ["E1", "E5"], "light_defects": [], "stability_min": 93,
        "light_share": "20% (5 of 25)"}), ".")
    assert "defects missed" in html and "correct changes held up by questions" in html
    assert "<b>1</b>defects missed" in html and "<b>2</b>correct changes held up by questions" in html
    assert "<b>93%</b>" in html and "20% (5 of 25)" in html


def test_every_case_gets_its_own_page_with_the_full_report_inside(tmp_path):
    cases = [case("E2", report_dir=make_case_folder(tmp_path, "E2")), case("E4", report_dir=make_case_folder(tmp_path, "E4"))]
    html = overview_report.render(summary(cases), tmp_path)
    assert html.count('<section class="case">') == 2
    assert html.count("<h2>Criteria</h2>") == 2 and html.count("Evidence: every scenario that was run") == 2
    assert "shipping 0.00 (expected 5.99)" in html        # evidence text from the case's own report


def test_a_case_whose_report_files_are_gone_says_so_instead_of_failing(tmp_path):
    html = overview_report.render(summary([case("E2", report_dir=tmp_path / "missing"), case("E9", report_dir=None)]), tmp_path)
    assert html.count("report files for this case were not found") == 2


def test_case_without_an_answer_key_row_is_called_out():
    assert "no row in the answer key" in overview_report.render(summary([case("E7", "differs", expected=False)]), ".")


def test_screenshots_are_embedded_so_the_overview_stands_alone(tmp_path):
    folder = make_case_folder(tmp_path, "E2", with_screenshot=True)
    html = overview_report.render(summary([case("E2", report_dir=folder)]), tmp_path)
    assert "data:image/png;base64,iVBORw0KGgo" in html
    assert str(tmp_path) not in html                       # no local paths leak into the document


def test_text_from_outside_is_escaped(tmp_path):
    html = overview_report.render(summary([case("E2", description="<script>alert(1)</script>")],
                                          known=["<b>bold</b>"]), tmp_path)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>bold</b>" not in html


def test_overview_is_self_contained(tmp_path):
    html = overview_report.render(summary([case("E2", report_dir=make_case_folder(tmp_path, "E2"))]), tmp_path)
    for forbidden in ("http://", "https://", "<link", "<script"):
        assert forbidden not in html


def test_write_names_the_file_after_the_mode(tmp_path):
    html_path, pdf_path, problem = overview_report.write(summary([case("E2")], mode="saved"), tmp_path / "o", pdf=False)
    assert html_path.name == "overview-saved.html" and html_path.exists() and pdf_path is None and problem is None


def test_case_pdfs_are_made_from_existing_reports_and_missing_ones_are_skipped(tmp_path):
    from evidence_gate.reporters import html_report
    folder = make_case_folder(tmp_path, "E2")
    html_report.write(make_report(), RECORDS, folder)          # the case's report.html that `check` would have written
    cases = [case("E2", report_dir=folder), case("E4", report_dir=tmp_path / "gone"), case("E9", report_dir=None)]
    written, problem = overview_report.write_case_pdfs(summary(cases))
    if problem:
        pytest.skip(problem)
    assert written == [folder / "report.pdf"] and written[0].read_bytes().startswith(b"%PDF")


def test_overview_command_also_writes_a_pdf_for_each_case(tmp_path):
    from evidence_gate.reporters import html_report
    folder = make_case_folder(tmp_path, "E2")
    html_report.write(make_report(), RECORDS, folder)
    path = tmp_path / "summary-off.json"
    path.write_text(json.dumps(summary([case("E2", report_dir=folder)])), encoding="utf-8")
    result = run_cli("overview", "--summary", str(path))
    assert result.returncode == 0, result.stderr
    if "Note:" in result.stderr:
        pytest.skip(result.stderr.strip())
    assert (tmp_path / "overview-off.pdf").exists() and (folder / "report.pdf").exists()
    assert (tmp_path / "cases-off" / "E2.pdf").read_bytes().startswith(b"%PDF")   # the copy beside the overview
    assert "case:" in result.stdout and "E2.pdf" in result.stdout


def test_write_makes_a_pdf_when_there_is_a_browser(tmp_path):
    _, pdf_path, problem = overview_report.write(summary([case("E2", report_dir=make_case_folder(tmp_path, "E2"))]),
                                                 tmp_path / "o")
    if problem:
        pytest.skip(problem)
    assert pdf_path.name == "overview-off.pdf" and pdf_path.read_bytes().startswith(b"%PDF")


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "evidence_gate.cli", *args], capture_output=True, text=True,
                          encoding="utf-8")


def test_overview_command_builds_the_document_next_to_the_summary(tmp_path):
    path = tmp_path / "summary-off.json"
    path.write_text(json.dumps(summary([case("E2", report_dir=make_case_folder(tmp_path, "E2"))])), encoding="utf-8")
    result = run_cli("overview", "--summary", str(path), "--no-pdf")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "overview-off.html").exists() and "Overview:" in result.stdout


def test_overview_command_with_a_bad_summary_is_a_gate_error(tmp_path):
    missing = run_cli("overview", "--summary", str(tmp_path / "nope.json"))
    assert missing.returncode == 3 and "cannot build the overview" in missing.stderr
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert run_cli("overview", "--summary", str(broken)).returncode == 3
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"mode": "off"}), encoding="utf-8")   # no "cases"
    assert run_cli("overview", "--summary", str(incomplete)).returncode == 3
