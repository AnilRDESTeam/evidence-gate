"""What the person running `evidence-gate check` reads in the terminal."""

from evidence_gate.reporters.common import header, route_text, rows, tests_line, verdict_summary


def render(report: dict, records: list[dict], full_report: str | None = None) -> str:
    lines = [header(report), "",
             f"VERDICT: {report['verdict']} ({verdict_summary(report)})",
             f"ROUTE:   {route_text(report['route'])} - {report['route_reason']}", ""]
    table = rows(report, records)
    id_width = max((len(r[0]) for r in table), default=0)
    label_width = max((len(r[2]) for r in table), default=0)
    for cid, priority, label, evidence in table:
        lines.append(f"{cid:<{id_width}}  {priority:<6}  {label:<{label_width}}  {evidence}")
    if report["questions"]:
        lines += ["", "Questions:"]
        lines += [f"  {q['id']} ({q['criterion'] or 'new'}): {q['text']}" for q in report["questions"]]
    if report.get("ai_suggestions"):
        lines += ["", "AI suggestions (not used for labels):"]
        lines += [f"  {s['scenario']} {s['status']}" for s in report["ai_suggestions"]]
    for warning in report["warnings"]:
        lines.append(f"Warning: {warning}")
    tests = tests_line(report)
    lines += ["", *( [tests] if tests else [] ), f"Next action: {report['next_action']}"]
    if full_report:
        lines.append(f"Full report: {full_report}")
    return "\n".join(lines) + "\n"
