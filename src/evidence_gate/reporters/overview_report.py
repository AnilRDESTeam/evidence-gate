"""The evaluation overview: one document with every case and its status, then one page per case.
Built from the summary that eval/run_eval.py writes, plus each case's own report files."""

import json
import shutil
from pathlib import Path

from evidence_gate.reporters import html_report, pdf_report

# How a case's comparison with the answer key is worded on the page, and which colour class it gets.
_STATUS = {
    "match": ("MATCHES THE KEY", "match"),
    "known": ("KNOWN LIMITATION", "known"),
    "differs": ("DIFFERS FROM THE KEY", "differs"),
    "miss": ("MISSED A DEFECT", "differs"),
    "false_alarm": ("FALSE ALARM", "differs"),
    "held_up": ("HELD UP BY QUESTIONS", "differs"),
}


def _labels(labels: dict) -> str:
    return " · ".join(f"{ac} {code.replace('_', ' ')}" for ac, code in labels.items())


def _case_report(report_dir: str | None, out_dir) -> dict | None:
    """The full per-case context (the same body as report.html), or None if that run's files are gone."""
    if not report_dir:
        return None
    folder = Path(report_dir)
    try:
        report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
        records = [json.loads(line) for line in (folder / "evidence.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, ValueError):
        return None
    # Screenshots are embedded so the overview still works after it is moved or emailed.
    return html_report.build_context(report, records, out_dir, embed_images=True, screens_dir=folder / "screens")


def build_context(summary: dict, out_dir) -> dict:
    cases = []
    for case in summary["cases"]:
        label, css = _STATUS.get(case["status"], (case["status"].upper(), "differs"))
        cases.append({**case, "status_text": label, "status_css": css,
                      "got_text": f"{case['got']['verdict'].replace('_', ' ')} / {(case['got']['route'] or '-').replace('_', ' ')}",
                      "key_text": f"{case['expected']['verdict'].replace('_', ' ')} / {case['expected']['route'].replace('_', ' ')}"
                      if case.get("expected") else "no row in the answer key",
                      "got_labels": _labels(case["got"]["labels"]),
                      "report": _case_report(case.get("report_dir"), out_dir)})
    return {"summary": summary, "cases": cases}


def render(summary: dict, out_dir) -> str:
    return html_report.ENV.get_template("overview.html").render(
        o=build_context(summary, out_dir), style=html_report.style())


def write_case_pdfs(summary: dict, copy_to=None) -> tuple[list[Path], str | None]:
    """A report.pdf next to each case's report.html, built from reports that already exist (nothing is re-run).
    With copy_to, each one is also copied there as <case id>.pdf, so every report sits in one folder.
    Returns (the PDFs written, the first reason one could not be made)."""
    written, problem = [], None
    for case in summary["cases"]:
        html = Path(case["report_dir"]) / "report.html" if case.get("report_dir") else None
        if html is None or not html.exists():
            continue
        pdf_path, why = pdf_report.write(html)
        if pdf_path:
            if copy_to:
                Path(copy_to).mkdir(parents=True, exist_ok=True)
                pdf_path = Path(shutil.copyfile(pdf_path, Path(copy_to) / f"{case['case_id']}.pdf"))
            written.append(pdf_path)
        elif problem is None:
            problem = why
    return written, problem


def write(summary: dict, out_dir, pdf: bool = True) -> tuple[Path, Path | None, str | None]:
    """Write overview-<mode>.html (and .pdf). Returns (html path, pdf path or None, why there is no pdf)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / f"overview-{summary['mode']}.html"
    html_path.write_text(render(summary, out), encoding="utf-8")
    if not pdf:
        return html_path, None, None
    pdf_path, problem = pdf_report.write(html_path)
    return html_path, pdf_path, problem
