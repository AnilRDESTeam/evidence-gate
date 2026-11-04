"""The compare rule (contract/RULES.md): the only place that decides pass or fail for a scenario."""

NUMBER_TOLERANCE = 0.005


def _is_number(value) -> bool:
    # bool is a subclass of int in Python, but True/False are not amounts.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _equal(expected, actual) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        # In Python 1 == True; a number must never match a yes/no value.
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    if _is_number(expected) and _is_number(actual):
        # round() hides float noise, so a difference of exactly 0.005 still counts as equal.
        return round(abs(expected - actual), 9) <= NUMBER_TOLERANCE
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip() == actual.strip()
    return expected == actual


def compare(expected: dict, actual: dict) -> tuple[str, list[dict]]:
    """Return ("pass" | "fail", mismatches). Only the fields listed in `expected` are looked at."""
    mismatches = []
    for field, want in expected.items():
        got = actual.get(field)  # a field the driver did not report counts as None
        if not _equal(want, got):
            mismatches.append({"field": field, "expected": want, "actual": got})
    return ("fail" if mismatches else "pass"), mismatches
