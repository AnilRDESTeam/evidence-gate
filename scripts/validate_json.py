"""Check a JSON file against a contract schema.

Usage: python scripts/validate_json.py <schema.json> <file.json>
Prints OK (exit 0) or one line per error (exit 1).
"""

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def strip_fences(text: str) -> str:
    # A chat answer is often wrapped in ```json ... ```; remove the fences.
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n", "", text)
    return re.sub(r"\n```\s*$", "", text)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_json.py <schema.json> <file.json>", file=sys.stderr)
        return 2
    schema = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    try:
        data = json.loads(strip_fences(Path(argv[1]).read_text(encoding="utf-8")))
    except json.JSONDecodeError as err:
        print(f"{argv[1]}: not valid JSON (line {err.lineno}): {err.msg}")
        return 1

    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    if not errors:
        print("OK")
        return 0
    for e in errors:
        path = "/".join(str(p) for p in e.absolute_path) or "(top level)"
        print(f"{path}: {e.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
