"""Decide how much human review is still needed. Route rules R1-R5 in contract/RULES.md: first match wins.

The order is fixed by the contract (full review before focused review), so policy.yaml's `routes`
list is not used to reorder it.
"""

from evidence_gate.verdict import VerdictResult

_REASON_WORDS = {
    "failed": "failed",
    "missing": "has no scenarios",
    "could_not_run": "could not run",
    "unconfirmed": "has only unconfirmed AI scenarios",
}


def _join(items: list[str]) -> str:
    return ", ".join(items)


def _question_texts(questions: list[dict]) -> dict[str, str]:
    """Look up a question's text by its own id (Q-1) or by the criterion it is linked to (AC-2)."""
    texts = {}
    for q in questions:
        texts[q["id"]] = q["text"]
        if q.get("criterion"):
            texts.setdefault(q["criterion"], q["text"])
    return texts


def _blocking_reason(result: VerdictResult, criteria: list[dict]) -> str:
    """'AC-2, AC-3 failed; AC-4 could not run'"""
    by_reason: dict[str, list[str]] = {}
    for c in criteria:
        if c["id"] in result.blocking:
            by_reason.setdefault(c["reason"], []).append(c["id"])
    return "; ".join(f"{_join(ids)} {_REASON_WORDS[reason]}" for reason, ids in by_reason.items())


def decide_route(result: VerdictResult, criteria: list[dict], questions: list[dict],
                 high_risk: list[str], uncovered: list[str]) -> tuple[str | None, str]:
    """Return (route, route_reason). The route is None for GATE ERROR (nothing to review yet)."""
    if result.verdict == "GATE ERROR":
        return None, "The Gate could not finish: " + _join(result.warnings)
    # R1
    if result.verdict == "BLOCKED":
        return "back_to_developer", _blocking_reason(result, criteria)
    # R2
    if result.verdict == "NEEDS DECISION":
        texts = _question_texts(questions)
        items = [f"{i} ({texts[i]})" if i in texts else f"{i} (needs a human decision)" for i in result.review]
        return "product_owner_decides", "Open questions: " + _join(items)
    # R3
    if high_risk:
        return "full_review", f"{_join(high_risk)} is in a high-risk path"
    # R4
    if uncovered:
        return "focused_review", f"{_join(uncovered)} changed but no criterion covers it"
    # R5
    return "light_review", "All MUST criteria are verified, every changed file is covered, no high-risk paths changed"


def _first_failure(record_list: list[dict], criterion_id: str) -> str:
    """'shipping: expected 5.99, got 0.0' for the first failed scenario of a criterion."""
    for r in record_list:
        if r["criterion"] == criterion_id and r["confirmed"] and r["status"] == "fail" and r["mismatches"]:
            m = r["mismatches"][0]
            return f"{m['field']}: expected {m['expected']}, got {m['actual']}"
    return ""


def next_action(result: VerdictResult, route: str | None, criteria: list[dict], questions: list[dict],
                records: list[dict], high_risk: list[str], uncovered: list[str]) -> str:
    """One plain-words instruction for what happens next."""
    if result.verdict == "GATE ERROR":
        return "Fix the problem described above, then rerun evidence-gate check."
    if route == "back_to_developer":
        parts = []
        for c in criteria:
            if c["id"] not in result.blocking:
                continue
            if c["reason"] == "failed":
                detail = _first_failure(records, c["id"])
                parts.append(f"{c['id']} \"{c['statement']}\"" + (f" ({detail})" if detail else ""))
            elif c["reason"] == "could_not_run":
                parts.append(f"{c['id']} could not run (restart the shop on this commit and check the adapter)")
            elif c["reason"] == "missing":
                parts.append(f"{c['id']} has no worked example (add one to the task spec)")
            else:
                parts.append(f"{c['id']} is only covered by AI suggestions (a person must confirm an example)")
        return "Fix the code so these hold, then rerun evidence-gate check: " + "; ".join(parts) + "."
    if route == "product_owner_decides":
        texts = _question_texts(questions)
        asked = [f"{i}: {texts[i]}" if i in texts else i for i in result.review]
        return "Product owner: answer " + "; ".join(asked) + ". Update the task spec, then rerun evidence-gate check."
    if route == "full_review":
        return f"Do a full review. High-risk files changed: {_join(high_risk)}."
    if route == "focused_review":
        return f"Review only these files, no criterion covers them: {_join(uncovered)}."
    return "Skim the evidence and approve (about 10 minutes)."
