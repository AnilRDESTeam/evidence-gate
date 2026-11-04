"""out/report.html: one self-contained page (inline CSS, no network) that a person reads, even on a projector."""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evidence_gate.reporters.common import header, route_text, rows, tests_line, value_text, verdict_summary

# autoescape is on: question text, file names and AI output come from outside and must not become markup.
_ENV = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   autoescape=select_autoescape(["html"]))

# Verdict -> CSS class. The page also says the verdict in words, so colour is never the only signal.
_BANNER = {"READY": "ready", "BLOCKED": "blocked", "NEEDS DECISION": "decision", "GATE ERROR": "error"}


def _screenshot_href(artifacts: dict | None, out_dir) -> str | None:
    """Relative link (screens/S-AC-4-1.png) so the page still works after out/ is zipped or moved."""
    path = (artifacts or {}).get("screenshot")
    if not path:
        return None
    try:
        return Path(os.path.relpath(path, out_dir)).as_posix()
    except ValueError:  # another drive on Windows: no relative path exists
        return None


def _fields(record: dict) -> list[dict]:
    """One entry per expected field: what was wanted, what was seen, and whether they differ."""
    wrong = {m["field"] for m in record.get("mismatches") or []}
    actual = record.get("actual") or {}
    return [{"name": name, "expected": value_text(want), "actual": value_text(actual.get(name)),
             "bad": name in wrong} for name, want in (record.get("expected") or {}).items()]


def _scenario_row(record: dict, priority: str | None, out_dir) -> dict:
    return {"id": record["scenario"], "criterion": record.get("criterion") or "-", "priority": priority or "",
            "input": ", ".join(f"{k}={value_text(v)}" for k, v in record["input"].items()),
            "fields": _fields(record), "status": record["status"], "error": record.get("error"),
            "screenshot": _screenshot_href(record.get("artifacts"), out_dir)}


def render(report: dict, records: list[dict], out_dir=".") -> str:
    priority = {c["id"]: c["priority"] for c in report["criteria"]}
    confirmed = [r for r in records if r.get("confirmed")]
    challenger = report["challenger"]
    context = {
        "report": report,
        "title": header(report),
        "banner": _BANNER.get(report["verdict"], "error"),
        "summary": verdict_summary(report),
        "route": route_text(report["route"]),
        "criteria": rows(report, records),
        "evidence": [_scenario_row(r, priority.get(r.get("criterion")), out_dir) for r in confirmed],
        # AI ideas are shown apart and marked "not used for labels"; their expected values are guesses.
        "suggestions": [{"id": s["scenario"], "criterion": s.get("criterion") or "-",
                         "input": ", ".join(f"{k}={value_text(v)}" for k, v in s["input"].items()),
                         "expected": ", ".join(f"{k} {value_text(v)}" for k, v in s["expected"].items()),
                         "actual": ", ".join(f"{k} {value_text(v)}" for k, v in (s.get("actual") or {}).items())
                         or (s.get("error") or "-"),
                         "status": s["status"]} for s in report.get("ai_suggestions") or []],
        "screenshots": [{"scenario": row["id"], "href": row["screenshot"]}
                        for row in (_scenario_row(r, None, out_dir) for r in confirmed) if row["screenshot"]],
        "tests_line": tests_line(report),
        "challenger_text": ("off: no AI was used; questions come from the spec and coverage from its scope paths"
                            if challenger["mode"] == "off" else
                            f"{challenger['mode']}: model {challenger['model']}, "
                            f"prompt {(challenger['prompt_hash'] or '')[:12]}"),
    }
    return _ENV.get_template("report.html").render(**context)


def write(report: dict, records: list[dict], out_dir) -> Path:
    path = Path(out_dir) / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(report, records, out_dir), encoding="utf-8")
    return path
