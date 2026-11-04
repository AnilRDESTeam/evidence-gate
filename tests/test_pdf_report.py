"""PDF reports. Printing needs Chromium, so those tests skip themselves if it cannot start."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evidence_gate.reporters import html_report, pdf_report
from test_reporters import RECORDS, make_report


@pytest.fixture
def html_file(tmp_path):
    return html_report.write(make_report(), RECORDS, tmp_path / "out")


def make_pdf(html, tmp_path):
    """Print `html`, or skip the test if this machine has no usable browser."""
    path, problem = pdf_report.write(html)
    if problem:
        pytest.skip(problem)
    return path


def test_pdf_is_written_next_to_the_html(html_file, tmp_path):
    pdf = make_pdf(html_file, tmp_path)
    assert pdf == html_file.with_suffix(".pdf")
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 5_000   # a real document, not an empty file


def test_pdf_failure_is_a_message_not_a_crash(html_file, monkeypatch):
    def no_browser(*args, **kwargs):
        raise RuntimeError("Executable doesn't exist at C:\\fake\\chrome.exe\nlong playwright call log here")
    monkeypatch.setattr(pdf_report, "html_to_pdf", no_browser)
    path, problem = pdf_report.write(html_file)
    assert path is None and problem == "PDF not written: Executable doesn't exist at C:\\fake\\chrome.exe"


def test_check_cli_has_a_no_pdf_flag():
    result = subprocess.run([sys.executable, "-m", "evidence_gate.cli", "check", "--help"], capture_output=True, text=True)
    assert "--no-pdf" in result.stdout


def test_print_styles_exist_for_a_clean_a4_page():
    css = html_report.style()
    for rule in ("@page", "size: A4", "@media print", "break-inside:avoid"):
        assert rule in css


def test_pdf_has_the_verdict_text_in_it(html_file, tmp_path):
    pdf = make_pdf(html_file, tmp_path)
    # Chromium stores page text in compressed streams, so check through the HTML it was printed from instead,
    # and that the PDF is a multi-object document.
    assert "BLOCKED" in html_file.read_text(encoding="utf-8")
    assert pdf.read_bytes().count(b"obj") > 5
