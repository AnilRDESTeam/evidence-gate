"""Turn a task spec (and optional Challenger ideas) into the scenarios the runner executes."""

from dataclasses import dataclass


@dataclass
class Scenario:
    id: str                 # e.g. S-AC-3-1
    criterion: str | None   # AC id, or None for an AI idea not tied to a criterion
    source: str             # spec-example | approved | ai-proposed
    confirmed: bool         # True only when a human wrote the expected value
    adapter: str            # e.g. api
    action: str             # e.g. quote_order
    input: dict
    expect: dict


def split_via(via: str) -> tuple[str, str]:
    """'api.quote_order' -> ('api', 'quote_order')"""
    adapter, action = via.split(".", 1)
    return adapter, action


def build_scenarios(task: dict, proposed: list[dict] | None = None) -> tuple[list[Scenario], list[str]]:
    """Return (scenarios, warnings). Order: spec examples, approved scenarios, AI proposals."""
    scenarios: list[Scenario] = []
    warnings: list[str] = []
    count: dict[str, int] = {}  # scenarios made so far per criterion, for the S-<AC>-<n> ids

    def add(criterion, source, via, inputs, expect, confirmed):
        n = count[criterion] = count.get(criterion, 0) + 1
        adapter, action = split_via(via)
        scenarios.append(Scenario(f"S-{criterion}-{n}", criterion, source, confirmed, adapter, action,
                                  dict(inputs), dict(expect)))

    for criterion in task["criteria"]:
        for example in criterion.get("examples", []):
            add(criterion["id"], "spec-example", example["via"], example["input"], example["expect"], True)
    for item in task.get("approved_scenarios", []):
        add(item["criterion"], "approved", item["via"], item["input"], item["expect"], True)

    # An AI idea has no `via`, so it borrows the adapter and action of its criterion's first example.
    # Why: the AI should vary the input, not pick how the app is driven.
    first_via = {c["id"]: c["examples"][0]["via"] for c in task["criteria"] if c.get("examples")}
    for n, idea in enumerate(proposed or [], start=1):
        via = first_via.get(idea.get("criterion"))
        if via is None:
            warnings.append(f"AI suggestion {n} skipped: criterion {idea.get('criterion')} has no example to copy the adapter from")
            continue
        adapter, action = split_via(via)
        scenarios.append(Scenario(f"S-AI-{n}", idea["criterion"], "ai-proposed", False, adapter, action,
                                  dict(idea["input"]), dict(idea["expected_guess"])))
    return scenarios, warnings
