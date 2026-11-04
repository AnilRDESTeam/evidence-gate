"""Run the Gate on every eval case, several times, and compare with the answer key.

For each case in eval/cases.csv this script: checks out the branch in the shop, starts the shop on that commit,
runs `evidence-gate check` N times, and stops the shop. At the end it compares the results with eval/expected.csv.

Standard library only (plus the evidence-gate it launches). It always puts the shop back on `main` and stops the
shop, even after an error.

    python eval/run_eval.py                          # Challenger off, 5 runs per case
    python eval/run_eval.py --mode saved --runs 5    # use saved Challenger answers from eval/challenges/
    python eval/run_eval.py --cases E2,E4 --runs 1   # a quick try on two cases
"""

import argparse
import csv
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the evidence-gate repo
EVAL = Path(__file__).resolve().parent
HEALTH_URL = "http://127.0.0.1:8080/api/health"
AC_COLUMNS = ["AC-1", "AC-2", "AC-3", "AC-4"]          # the answer key has four criteria per task
RESULT_COLUMNS = ["case_id", "run", "mode", "verdict", "route", *AC_COLUMNS]


# ---- small helpers ----

def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return [row for row in csv.DictReader(f) if row.get("case_id")]


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {done.stderr.strip()}")
    return done.stdout.strip()


def venv_python(folder: Path) -> str:
    """The python inside a project's .venv (Windows or Linux/Mac); this python if there is none."""
    for candidate in (folder / ".venv" / "Scripts" / "python.exe", folder / ".venv" / "bin" / "python"):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def shop_health() -> dict | None:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def label_code(criterion: dict) -> str:
    """The report's (label, reason) in the words the answer key uses."""
    if criterion["label"] == "not_verified":
        return {"failed": "failed", "missing": "missing", "could_not_run": "could_not_run",
                "unconfirmed": "unconfirmed"}.get(criterion["reason"], "failed")
    return "verified" if criterion["label"] == "verified_waived" else criterion["label"]


# ---- the shop ----

class Shop:
    """The shop under test: one branch checked out and one server running at a time."""

    def __init__(self, folder: Path, adapter_source: Path):
        self.folder = folder
        self.process = None
        self.injected: list[Path] = []
        self.overwritten: list[Path] = []
        adapters = folder / ".evidence-gate" / "adapters"
        files = list(adapters.glob("*.yaml")) if adapters.is_dir() else []
        # The adapters come from this repo (eval/adapters), not from the branch under test: a coding AI's branch
        # must not control how it is checked. Older branches do not contain adapters at all, so they are laid over
        # each branch and removed again before the next checkout. Without eval/adapters, use the shop's own.
        source = list(adapter_source.glob("*.yaml")) if adapter_source.is_dir() else []
        self.adapters = {p.name: p.read_bytes() for p in (source or files)}
        # Untracked adapter files already in the shop would block checking out a branch that tracks the same
        # file, so they are set aside now and put back when the run ends.
        self.set_aside = {p.name: p.read_bytes() for p in files if not self.tracked(p)}
        for p in files:
            if p.name in self.set_aside:
                p.unlink()

    def tracked(self, path: Path) -> bool:
        return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=self.folder,
                              capture_output=True).returncode == 0

    def restore_set_aside(self) -> None:
        target = self.folder / ".evidence-gate" / "adapters"
        target.mkdir(parents=True, exist_ok=True)
        for name, data in self.set_aside.items():
            if not (target / name).exists():
                (target / name).write_bytes(data)

    def checkout(self, branch: str) -> str:
        self.remove_injected()
        git(self.folder, "checkout", "-q", branch)
        target = self.folder / ".evidence-gate" / "adapters"
        target.mkdir(parents=True, exist_ok=True)
        for name, data in self.adapters.items():
            path = target / name
            if not path.exists():
                path.write_bytes(data)
                self.injected.append(path)
            elif path.read_bytes().replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
                path.write_bytes(data)       # the branch carries its own copy; ours wins, so every case is checked alike
                self.overwritten.append(path)
        return git(self.folder, "rev-parse", "--short", "HEAD")

    def remove_injected(self) -> None:
        for path in self.injected:
            if path.exists() and not self.tracked(path):
                path.unlink()
        self.injected = []
        for path in self.overwritten:        # give the branch its own file back, so the checkout stays clean
            subprocess.run(["git", "checkout", "--", str(path)], cwd=self.folder, capture_output=True)
        self.overwritten = []

    def start(self, head: str) -> None:
        if shop_health() is not None:
            raise RuntimeError("something already answers on 127.0.0.1:8080. Stop that shop first, "
                               "so every case runs against its own commit.")
        log = open(self.folder / "out" / "eval-server.log", "w", encoding="utf-8") if (self.folder / "out").is_dir() \
            else subprocess.DEVNULL
        self.process = subprocess.Popen(
            [venv_python(self.folder), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080"],
            cwd=self.folder, stdout=log, stderr=subprocess.STDOUT)
        deadline = time.time() + 30
        while time.time() < deadline:
            health = shop_health()
            if health and str(health.get("commit", "")).startswith(head[:7]):
                return
            if self.process.poll() is not None:
                break
            time.sleep(0.5)
        raise RuntimeError("the shop did not come up on this commit within 30 seconds")

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None


# ---- running the Gate ----

def challenge_file(case_id: str, shop: Path) -> Path | None:
    for folder in (EVAL / "challenges", shop / "out" / "challenges"):
        candidate = folder / f"{case_id}.json"
        if candidate.exists():
            return candidate
    return None


def report_folder(case_id: str, mode: str, run: int) -> str:
    """Where one run's reports go, relative to the shop. The mode is part of the path so that a saved-mode run
    never overwrites the Challenger-off reports of the same case."""
    return f"out/{case_id}/{mode}/run{run}"


def run_gate(shop: Path, case: dict, run: int, mode: str, pdf: bool = False) -> dict:
    saved = challenge_file(case["case_id"], shop) if mode == "saved" else None
    used = "saved" if saved else "off"
    out = report_folder(case["case_id"], used, run)
    command = [venv_python(ROOT), "-m", "evidence_gate.cli", "check", "--task", case["task_file"], "--out", out]
    if saved:
        command += ["--challenger", "saved", "--challenge-file", str(saved)]
    if not pdf:
        command.append("--no-pdf")   # a PDF per run would add minutes to a 25-run evaluation; the overview has one
    done = subprocess.run(command, cwd=shop, capture_output=True, text=True, encoding="utf-8")
    result = {"case_id": case["case_id"], "run": run, "mode": used, "verdict": "GATE ERROR", "route": "",
              **{column: "n/a" for column in AC_COLUMNS}}
    try:
        report = json.loads((shop / out / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        result["error"] = (done.stderr or done.stdout).strip()[:300]
        return result
    result["verdict"] = report["verdict"].replace(" ", "_")
    result["route"] = report["route"] or ""
    for criterion in report["criteria"]:
        if criterion["id"] in AC_COLUMNS:
            result[criterion["id"]] = label_code(criterion)
    return result


def signature(result: dict) -> tuple:
    return tuple(result[c] for c in ("verdict", "route", *AC_COLUMNS))


# ---- the comparison ----

def compare(results: list[dict], expected: dict[str, dict], cases: dict[str, dict] | None = None,
            shop_folder: Path | None = None, summary_path: Path | None = None, mode: str = "off") -> int:
    """Print the summary and (with summary_path) write it as JSON for the overview document.
    Returns 1 if a defect was missed or a correct change raised an alarm."""
    cases = cases or {}
    by_case: dict[str, list[dict]] = {}
    for r in results:
        by_case.setdefault(r["case_id"], []).append(r)

    misses, false_alarms, differences, light_defects, known, unwanted_questions = [], [], [], [], [], []
    case_summaries = []
    print("\n=== Results vs answer key ===")
    for case_id, runs in by_case.items():
        common, count = Counter(signature(r) for r in runs).most_common(1)[0]
        got = dict(zip(("verdict", "route", *AC_COLUMNS), common))
        want = expected.get(case_id)
        stable = 100 * count // len(runs)
        print(f"{case_id}: got {got['verdict']} / {got['route'] or '-'}  labels " + ",".join(got[c] for c in AC_COLUMNS)
              + f"   stable {stable}% of {len(runs)} runs")
        status, notes = "match", []
        if want is None:
            print("    (no row in expected.csv)")
            status, notes = "differs", ["no row in the answer key"]
        else:
            print(f"    expected {want['verdict']} / {want['route']}  labels " + ",".join(want[c] for c in AC_COLUMNS))
            if want["verdict"] != "READY" and got["route"] == "light_review":
                light_defects.append(case_id)
            if want["verdict"] == "BLOCKED" and got["verdict"] == "READY":
                misses.append(case_id)
                status = "miss"
            elif want["verdict"] == "READY" and got["verdict"] == "BLOCKED":
                false_alarms.append(case_id)
                status = "false_alarm"
            elif want["verdict"] == "READY" and got["verdict"] == "NEEDS_DECISION":
                # A correct change that the Challenger's questions held up: a person is asked something needlessly.
                unwanted_questions.append(case_id)
                status = "held_up"
            elif (got["verdict"], got["route"]) != (want["verdict"], want["route"]):
                if runs[0]["mode"] == "off" and want["question_expected"] == "yes" and got["verdict"] == "READY":
                    # The key expects a question that only the Challenger AI can raise; with it off the Gate cannot.
                    note = (f"{got['verdict']}/{got['route']}; the key expects {want['verdict']} "
                            "because the Challenger raises the open questions")
                    known.append(f"{case_id}: {note}")
                    status, notes = "known", [note]
                else:
                    differences.append(f"{case_id}: verdict/route {got['verdict']}/{got['route']} "
                                       f"instead of {want['verdict']}/{want['route']}")
                    status = "differs"
            for column in AC_COLUMNS:
                if got[column] == want[column]:
                    continue
                # With an open question the Gate must not call a criterion Verified, so this is expected, not an error.
                if got[column] == "needs_human_review" and want["question_expected"] == "yes":
                    continue
                differences.append(f"{case_id}: {column} is {got[column]}, the key says {want[column]}")
                notes.append(f"{column} is {got[column].replace('_', ' ')}, the key says {want[column].replace('_', ' ')}")
                if status == "match":
                    status = "differs"
        last_run = max(r["run"] for r in runs)
        case_summaries.append({
            "case_id": case_id, "branch": cases.get(case_id, {}).get("branch", ""),
            "description": cases.get(case_id, {}).get("description", ""),
            "origin": cases.get(case_id, {}).get("defect_origin", ""), "runs": len(runs), "stable_pct": stable,
            "got": {"verdict": got["verdict"], "route": got["route"], "labels": {c: got[c] for c in AC_COLUMNS}},
            "expected": None if want is None else {"verdict": want["verdict"], "route": want["route"],
                                                   "labels": {c: want[c] for c in AC_COLUMNS}},
            "status": status, "notes": notes,
            "report_dir": str(shop_folder / report_folder(case_id, runs[0]["mode"], last_run)) if shop_folder else None})

    light = sum(r["route"] == "light_review" for r in results)
    stabilities = [100 * Counter(signature(r) for r in runs).most_common(1)[0][1] // len(runs)
                   for runs in by_case.values()]
    light_share = f"{100 * light // max(len(results), 1)}% ({light} of {len(results)})"
    print("\n=== Summary ===")
    print(f"Misses (expected BLOCKED, got READY):            {len(misses)} {misses or ''}")
    print(f"False alarms (expected READY, got BLOCKED):      {len(false_alarms)} {false_alarms or ''}")
    print(f"Correct changes held up by questions (READY->NEEDS DECISION): {len(unwanted_questions)} {unwanted_questions or ''}")
    print(f"Defective changes routed to light review:        {len(light_defects)} {light_defects or ''}")
    print(f"Label stability (identical results across runs): min {min(stabilities)}%, per case {stabilities}")
    print(f"Share of runs routed to light review:            {light_share}")
    if known:
        print("Known limitation (Challenger off, run with --mode saved to see the questions):")
        for k in known:
            print("  - " + k)
    if differences:
        print("Other differences from the key:")
        for d in differences:
            print("  - " + d)

    if summary_path:
        summary = {"mode": mode, "generated": time.strftime("%Y-%m-%d %H:%M"),
                   "runs": max(len(r) for r in by_case.values()),
                   "metrics": {"misses": misses, "false_alarms": false_alarms, "held_up": unwanted_questions,
                               "light_defects": light_defects, "stability_min": min(stabilities),
                               "light_share": light_share},
                   "known": known, "differences": differences, "cases": case_summaries}
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 1 if misses or false_alarms or light_defects or unwanted_questions else 0


def build_overview(summary_path: Path) -> None:
    """Hand the summary to the engine, which writes overview-<mode>.html and .pdf next to it.
    (Done through the CLI so this script stays standard-library only.)"""
    done = subprocess.run([venv_python(ROOT), "-m", "evidence_gate.cli", "overview", "--summary", str(summary_path)],
                          capture_output=True, text=True, encoding="utf-8")
    print("\n" + (done.stdout.strip() or done.stderr.strip()))
    if done.stdout.strip() and done.stderr.strip():
        print(done.stderr.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["off", "saved"], default="off")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--shop", type=Path, default=ROOT.parent / "shop-demo")
    parser.add_argument("--cases", help="comma-separated case ids to run (default: all in cases.csv)")
    parser.add_argument("--results", type=Path, default=EVAL / "results.csv")
    parser.add_argument("--compare-only", action="store_true",
                        help="do not run anything: summarise the rows already in results.csv for --mode")
    parser.add_argument("--pdf", action="store_true", help="also write report.pdf for every single run (slower)")
    parser.add_argument("--overview-dir", type=Path, default=EVAL / "overview",
                        help="where the overview (every case and its status, as HTML and PDF) is written")
    parser.add_argument("--no-overview", action="store_true", help="do not build the overview document")
    args = parser.parse_args()

    shop_folder = args.shop.resolve()
    summary_path = None if args.no_overview else args.overview_dir / f"summary-{args.mode}.json"
    case_rows = {c["case_id"]: c for c in read_csv(EVAL / "cases.csv")}

    def finish(rows: list[dict], expected: dict[str, dict]) -> int:
        code = compare(rows, expected, case_rows, shop_folder, summary_path, args.mode)
        if summary_path:
            build_overview(summary_path)
        return code

    if args.compare_only:
        rows = [r for r in read_csv(args.results) if r["mode"] == args.mode]
        expected = {row["case_id"]: row for row in read_csv(EVAL / "expected.csv")}
        for r in rows:
            r["run"] = int(r["run"])
        return finish(rows, expected) if rows else (print(f"No '{args.mode}' rows in {args.results}") or 3)

    cases = read_csv(EVAL / "cases.csv")
    if args.cases:
        wanted = {c.strip() for c in args.cases.split(",")}
        cases = [c for c in cases if c["case_id"] in wanted]
    if not cases:
        print("No cases to run.", file=sys.stderr)
        return 3
    expected = {row["case_id"]: row for row in read_csv(EVAL / "expected.csv")}

    started_on = git(shop_folder, "rev-parse", "--abbrev-ref", "HEAD")
    shop = Shop(shop_folder, EVAL / "adapters")
    results: list[dict] = []
    new_file = not args.results.exists()
    try:
        with open(args.results, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_COLUMNS, extrasaction="ignore")
            if new_file:
                writer.writeheader()
            for case in cases:
                print(f"\n--- {case['case_id']}  {case['branch']} ---", flush=True)
                head = shop.checkout(case["branch"])
                shop.start(head)
                try:
                    for run in range(1, args.runs + 1):
                        result = run_gate(shop_folder, case, run, args.mode, args.pdf)
                        results.append(result)
                        writer.writerow(result)
                        f.flush()
                        print(f"  run {run}: {result['verdict']} / {result['route'] or '-'}  "
                              + ",".join(result[c] for c in AC_COLUMNS) + f"  [challenger {result['mode']}]", flush=True)
                        if result.get("error"):
                            print(f"    {result['error']}")
                finally:
                    shop.stop()
    except RuntimeError as err:
        print(f"\nGATE ERROR: {err}", file=sys.stderr)
        return 3
    finally:
        shop.stop()
        shop.remove_injected()
        try:
            git(shop_folder, "checkout", "-q", "main")   # leave the shop the way we found it (main)
        except RuntimeError as err:
            print(f"Could not return the shop to main: {err}", file=sys.stderr)
        shop.restore_set_aside()                         # put back adapter files that were there before we started
        if started_on not in ("main", "HEAD"):
            print(f"Note: the shop was on '{started_on}' when this started; it is now on main.")
    return finish(results, expected)


if __name__ == "__main__":
    sys.exit(main())
