"""Words and short evidence lines shared by the terminal and markdown reports."""

from evidence_gate.labeller import NEEDS_REVIEW, NOT_VERIFIED, label_text, unlinked_questions

_ROUTE_TEXT = {
    "back_to_developer": "back to developer",
    "product_owner_decides": "product owner decides",
    "full_review": "full review",
    "focused_review": "focused review",
    "light_review": "light review",
    None: "none (the Gate could not finish)",
}


def route_text(route: str | None) -> str:
    return _ROUTE_TEXT[route]


def _value(v) -> str:
    """Numbers with two decimals (money), lists comma-joined, everything else as plain text."""
    if isinstance(v, bool) or v is None:
        return str(v).lower() if isinstance(v, bool) else "none"
    if isinstance(v, (int, float)):
        return f"{v:.2f}"
    if isinstance(v, list):
        return ",".join(_value(i) for i in v)
    return str(v)


value_text = _value  # the public name, for the HTML reporter


def evidence_line(record: dict) -> str:
    """'subtotal=50.00 -> shipping 0.00 (expected 5.99)' for one scenario."""
    given = ", ".join(f"{k}={_value(v)}" for k, v in record["input"].items())
    if record["status"] == "error":
        return f"{given} -> could not run: {record['error']}"
    seen = ", ".join(f"{field} {_value((record['actual'] or {}).get(field))} (expected {_value(want)})"
                     for field, want in record["expected"].items())
    return f"{given} -> {seen}"


def header(report: dict) -> str:
    kind = "updated requirement" if report["type"] == "updated" else "new requirement"
    return f"Evidence Gate - {report['task']} ({kind}) - commit {report['commit']}"


def verdict_summary(report: dict) -> str:
    """The short reason in brackets after the verdict, e.g. '2 MUST criteria not verified'."""
    verdict, criteria = report["verdict"], report["criteria"]
    if verdict == "BLOCKED":
        not_verified = [c for c in criteria if c["label"] == NOT_VERIFIED]
        musts = [c for c in not_verified if c["priority"] == "MUST"] or not_verified
        kind = "MUST " if any(c["priority"] == "MUST" for c in not_verified) else ""
        return f"{len(musts)} {kind}criteria not verified"
    if verdict == "NEEDS DECISION":
        open_items = sum(c["label"] == NEEDS_REVIEW for c in criteria) + \
            len(unlinked_questions({c["id"] for c in criteria}, report["questions"]))
        return f"{open_items} open question{'s' if open_items != 1 else ''}"
    if verdict == "READY":
        return "all MUST criteria verified or waived"
    return "see warnings"


def criterion_evidence(criterion: dict, records: list[dict], questions: list[dict]) -> str:
    """Evidence text for one criterion: its confirmed scenarios, plus the linked question if any."""
    mine = [r for r in records if r["criterion"] == criterion["id"] and r["confirmed"]]
    errors = [r for r in mine if r["status"] == "error"]
    distinct = {r["error"] for r in errors}
    if len(errors) > 1 and len(distinct) == 1:
        # Same reason for every scenario (e.g. adapter missing): say it once, not once per scenario.
        parts = [evidence_line(r) for r in mine if r["status"] != "error"]
        parts.append(f"could not run: {distinct.pop()} ({len(errors)} scenarios)")
    else:
        parts = [evidence_line(r) for r in mine]
    parts += [q["text"] for q in questions if q.get("criterion") == criterion["id"]]
    return "; ".join(parts) if parts else "no scenarios"


def rows(report: dict, records: list[dict]) -> list[tuple[str, str, str, str]]:
    """(id, priority, label text, evidence) per criterion, then a '(new)' row per unlinked question."""
    out = []
    for c in report["criteria"]:
        out.append((c["id"], c["priority"], label_text(c["label"], c["reason"]),
                    criterion_evidence(c, records, report["questions"])))
    ids = {c["id"] for c in report["criteria"]}
    for q in unlinked_questions(ids, report["questions"]):
        out.append(("(new)", "", label_text(NEEDS_REVIEW, None), q["text"]))
    return out


def tests_line(report: dict) -> str | None:
    context = report.get("context")
    if not context:
        return None
    return f"Existing tests: {context['tests_passed']}/{context['tests_total']} passed (context only)."
