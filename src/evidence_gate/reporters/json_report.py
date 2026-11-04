"""out/report.json: the single source the other reports are built from."""

import json
from pathlib import Path


def write(report: dict, out_dir) -> Path:
    path = Path(out_dir) / "report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path
