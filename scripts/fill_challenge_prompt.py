"""Fill the Challenger prompt template so a person can paste it into Claude chat.

Stdlib only. The coding prompt is never an input (there is no argument for it).
"""

import argparse
import hashlib
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "src" / "evidence_gate" / "challenger" / "prompt.md"


def read_text(path: Path) -> str:
    # Normalise line endings so the output and the hash are the same on every machine.
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task", required=True, type=Path)
    p.add_argument("--diff", required=True, type=Path)
    p.add_argument("--files", required=True, type=Path)
    p.add_argument("--commit", required=True)
    p.add_argument("--out", type=Path, default=Path("out/challenge-test-prompt.md"))
    args = p.parse_args()

    template = read_text(TEMPLATE)
    # str.replace, not str.format: the template has other braces (the JSON shape).
    filled = (template
              .replace("{task_yaml}", read_text(args.task))
              .replace("{commit}", args.commit)
              .replace("{diff}", read_text(args.diff))
              .replace("{files}", read_text(args.files)))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(filled, encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    print("prompt_hash", hashlib.sha256(template.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
