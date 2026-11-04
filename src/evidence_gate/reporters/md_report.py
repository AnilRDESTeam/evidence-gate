"""out/report.md: the text people paste into a pull request."""

from pathlib import Path

from evidence_gate.reporters.common import header, route_text, rows, tests_line, verdict_summary


def _cell(text: str) -> str:
    # A bare | would end the table cell early.
    return text.replace("|", "\\|").replace("\n", " ")


def render(report: dict, records: list[dict], full_report: str | None = None) -> str:
    lines = [header(report),
             f"Verdict: {report['verdict']} ({verdict_summary(report)})    Route: {route_text(report['route'])}",
             "",
             "| Criterion | Label | Evidence |",
             "|---|---|---|"]
    for cid, _priority, label, evidence in rows(report, records):
        lines.append(f"| {cid} | {_cell(label)} | {_cell(evidence)} |")
    lines.append("")
    for warning in report["warnings"]:
        lines.append(f"Warning: {warning}")
    if report.get("ai_suggestions"):
        lines.append("AI suggestions (not used for labels): " + "; ".join(
            f"{s['scenario']} {s['status']}" for s in report["ai_suggestions"]))
    tests = tests_line(report)
    if tests:
        lines.append(tests)
    lines.append(f"Next action: {report['next_action']}")
    if full_report:
        lines.append(f"Full report: {full_report}")
    return "\n".join(lines) + "\n"


def write(report: dict, records: list[dict], out_dir, full_report: str | None = None) -> Path:
    path = Path(out_dir) / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(report, records, full_report), encoding="utf-8")
    return path
