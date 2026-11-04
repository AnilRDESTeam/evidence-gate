"""One verdict for the whole change. The rules are contract/RULES.md V1-V4: first match wins."""

from dataclasses import dataclass, field

from evidence_gate.labeller import NEEDS_REVIEW, NOT_VERIFIED, label_text, unlinked_questions

EXIT_CODES = {"READY": 0, "BLOCKED": 1, "NEEDS DECISION": 2, "GATE ERROR": 3}


@dataclass
class VerdictResult:
    verdict: str
    exit_code: int
    blocking: list[str] = field(default_factory=list)   # criteria that caused BLOCKED
    review: list[str] = field(default_factory=list)     # criteria / questions waiting for a human
    warnings: list[str] = field(default_factory=list)


def decide_verdict(criteria: list[dict], questions: list[dict], engine_error: str | None = None,
                   should_failures: str = "warn") -> VerdictResult:
    """`criteria` are the labelled entries; `questions` are all open questions."""
    # V1
    if engine_error:
        return VerdictResult("GATE ERROR", EXIT_CODES["GATE ERROR"], warnings=[engine_error])

    blocking, warnings = [], []
    for c in criteria:
        if c["label"] != NOT_VERIFIED:
            continue
        if c["priority"] == "MUST" or should_failures == "block":
            blocking.append(c["id"])
        else:
            # SHOULD criteria only warn when the policy says should_failures: warn.
            warnings.append(f"{c['id']} (SHOULD) is not verified ({label_text(c['label'], c['reason'])})")
    # V2
    if blocking:
        return VerdictResult("BLOCKED", EXIT_CODES["BLOCKED"], blocking=blocking, warnings=warnings)

    review = [c["id"] for c in criteria if c["label"] == NEEDS_REVIEW]
    review += [q["id"] for q in unlinked_questions({c["id"] for c in criteria}, questions)]
    # V3
    if review:
        return VerdictResult("NEEDS DECISION", EXIT_CODES["NEEDS DECISION"], review=review, warnings=warnings)
    # V4
    return VerdictResult("READY", EXIT_CODES["READY"], warnings=warnings)
