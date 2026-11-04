"""Give each criterion one label. The rules are contract/RULES.md L1-L7: first match wins, no AI."""

VERIFIED = "verified"
VERIFIED_WAIVED = "verified_waived"
NOT_VERIFIED = "not_verified"
NEEDS_REVIEW = "needs_human_review"

# What a person reads for each (label, reason). The report stores the codes, reporters show the text.
_TEXT = {
    (VERIFIED, None): "Verified",
    (VERIFIED_WAIVED, None): "Verified (waived)",
    (NOT_VERIFIED, "missing"): "Not verified: missing",
    (NOT_VERIFIED, "failed"): "Not verified: failed",
    (NOT_VERIFIED, "could_not_run"): "Not verified: could not run",
    (NOT_VERIFIED, "unconfirmed"): "Not verified: unconfirmed",
    (NEEDS_REVIEW, None): "Needs human review",
}


def label_text(label: str, reason: str | None) -> str:
    return _TEXT[(label, reason)]


def waiver_is_valid(waiver: dict) -> bool:
    """A waiver needs who, why and when, all filled in."""
    return all(str(waiver.get(key) or "").strip() for key in ("who", "why", "when"))


def label_one(records: list[dict], waived: bool, has_open_question: bool, head_commit: str) -> tuple[str, str | None]:
    """Return (label, reason) for one criterion. `records` are its evidence lines."""
    # L1
    if waived:
        return VERIFIED_WAIVED, None
    # L2
    if not records:
        return NOT_VERIFIED, "missing"
    # Unconfirmed (AI-proposed) scenarios are ignored from here on until L7.
    confirmed = [r for r in records if r["confirmed"]]
    # L3
    if any(r["status"] == "fail" for r in confirmed):
        return NOT_VERIFIED, "failed"
    # L4
    if any(r["status"] == "error" for r in confirmed):
        return NOT_VERIFIED, "could_not_run"
    # L5
    if has_open_question:
        return NEEDS_REVIEW, None
    # L6
    if any(r["status"] == "pass" and r["commit"] == head_commit for r in confirmed):
        return VERIFIED, None
    # L7
    if not confirmed:
        return NOT_VERIFIED, "unconfirmed"
    # Not in the table: confirmed scenarios passed, but on another commit. Proof for the exact commit
    # is missing, so it counts as could-not-run (trust rule 2). The runner never produces this.
    return NOT_VERIFIED, "could_not_run"


def unlinked_questions(criteria_ids: set[str], questions: list[dict]) -> list[dict]:
    """Questions that belong to no criterion of this task: they become '(new)' rows."""
    return [q for q in questions if q.get("criterion") not in criteria_ids]


def label_criteria(task: dict, records: list[dict], questions: list[dict], head_commit: str) -> list[dict]:
    """One report-shaped entry per criterion: id, priority, statement, label, reason, scenarios."""
    waived = {w["criterion"] for w in task.get("waivers", []) if waiver_is_valid(w)}
    entries = []
    for criterion in task["criteria"]:
        cid = criterion["id"]
        mine = [r for r in records if r["criterion"] == cid]
        label, reason = label_one(mine, cid in waived, any(q.get("criterion") == cid for q in questions), head_commit)
        entries.append({"id": cid, "priority": criterion["priority"], "statement": criterion["statement"],
                        "label": label, "reason": reason, "scenarios": [r["scenario"] for r in mine]})
    return entries
