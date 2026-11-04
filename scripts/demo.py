"""One command to see Evidence Gate work. For someone who has never seen this project.

    python scripts/demo.py setup        # first time only: installs everything (a few minutes)
    python scripts/demo.py              # runs the demo: two bad changes (E2, E4) and a good one (E1), then opens the reports
    python scripts/demo.py --all        # all five eval cases instead of three
    python scripts/demo.py --mode saved # also use the saved Challenger AI answers (adds questions and file coverage)

Needs: Python 3.11+, git, and the shop-demo folder next to this one. Standard library only.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEALTH_URL = "http://127.0.0.1:8080/api/health"
CASES = {
    "E2": "a BAD change: the coding AI kept the old $50 free-shipping rule and edited the tests to match",
    "E1": "a GOOD change: the coding AI did exactly what was asked",
    "E3": "a good change, but the spec leaves questions open (guests? discount before shipping?)",
    "E4": "a BAD change: the welcome discount also goes to returning customers, and every one of the shop's own tests passes",
    "E5": "a good change plus an unrequested price change (scope creep)",
}
EVAL_BRANCHES = ["eval/shop-102-correct", "eval/shop-102-old-rule", "eval/shop-101-correct",
                 "eval/shop-101-missing-negative", "eval/shop-102-scope-creep"]


def venv_python(folder: Path) -> Path:
    for candidate in (folder / ".venv" / "Scripts" / "python.exe", folder / ".venv" / "bin" / "python"):
        if candidate.exists():
            return candidate
    return folder / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run(command: list, cwd: Path) -> None:
    print(f"  $ {' '.join(str(c) for c in command)}", flush=True)
    subprocess.run([str(c) for c in command], cwd=cwd, check=True)


def shop_answers() -> bool:
    try:
        urllib.request.urlopen(HEALTH_URL, timeout=2).close()
        return True
    except (urllib.error.URLError, OSError):
        return False


def preflight(shop: Path) -> list[str]:
    """Everything that could stop the demo, as plain sentences. An empty list means ready."""
    problems = []
    if sys.version_info < (3, 11):
        problems.append(f"Python 3.11 or newer is needed (this is {sys.version.split()[0]}).")
    if shutil.which("git") is None:
        problems.append("git is not installed or not on PATH.")
    if not (shop / ".git").is_dir():
        problems.append(f"The shop-demo folder was not found at {shop}. Clone it next to this folder "
                        "(or pass --shop <folder>).")
        return problems
    if not venv_python(ROOT).exists() or not venv_python(shop).exists():
        problems.append("Not set up yet. Run:  python scripts/demo.py setup")
    elif shutil.which("git"):
        have = subprocess.run(["git", "branch", "--list", "eval/*", "--format=%(refname:short)"], cwd=shop,
                              capture_output=True, text=True).stdout.split()
        missing = [b for b in EVAL_BRANCHES if b not in have]
        if missing:
            problems.append("These test branches are missing in shop-demo: " + ", ".join(missing)
                            + ". Run:  python scripts/demo.py setup  (it fetches them).")
    if shop_answers():
        problems.append("Something is already running on port 8080. Stop that shop first; the demo starts its own "
                        "so each branch is tested on its own code.")
    return problems


def setup(shop: Path) -> int:
    print("Setting up. This installs packages and a test browser (a few minutes, needs internet).\n")
    for folder, install in ((ROOT, ["-e", "."]), (shop, ["-r", "requirements.txt"])):
        if not folder.is_dir():
            print(f"Cannot find {folder}.")
            return 3
        if not venv_python(folder).exists():
            print(f"Creating a virtual environment in {folder} ...")
            venv.create(folder / ".venv", with_pip=True)
        run([venv_python(folder), "-m", "pip", "install", "-q", *install], folder)
    # A fresh clone only has the test branches as origin/eval/*; the demo needs local ones.
    have = subprocess.run(["git", "branch", "--list", "eval/*", "--format=%(refname:short)"], cwd=shop,
                          capture_output=True, text=True).stdout.split()
    for branch in (b for b in EVAL_BRANCHES if b not in have):
        print(f"Fetching test branch {branch} ...")
        subprocess.run(["git", "fetch", "-q", "origin", f"refs/heads/{branch}:refs/heads/{branch}"], cwd=shop)
    print("Installing the browser used for the receipt check ...")
    try:
        run([venv_python(ROOT), "-m", "playwright", "install", "chromium"], ROOT)
    except subprocess.CalledProcessError:
        print("The browser download was blocked. Put `channel: msedge` in "
              "shop-demo/.evidence-gate/adapters/browser.yaml to use Edge instead.")
    print("\nDone. Now run:  python scripts/demo.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", nargs="?", choices=["setup"], help="'setup' installs everything (first time only)")
    parser.add_argument("--shop", type=Path, default=ROOT.parent / "shop-demo")
    parser.add_argument("--all", action="store_true", help="run all five cases instead of E2 and E1")
    parser.add_argument("--mode", choices=["off", "saved"], default="off")
    parser.add_argument("--no-open", action="store_true", help="do not open the reports in the browser")
    args = parser.parse_args()
    shop = args.shop.resolve()

    if args.action == "setup":
        return setup(shop)

    problems = preflight(shop)
    if problems:
        print("The demo cannot start yet:\n")
        for p in problems:
            print(f"  - {p}")
        return 3

    cases = ["E2", "E4", "E1", "E3", "E5"] if args.all else ["E2", "E4", "E1"]
    print("Evidence Gate demo. For each change an AI wrote, the Gate runs the examples from the written spec,")
    print("on a real running shop, and says how much human review the change still needs.\n")
    for case in cases:
        print(f"  {case}: {CASES[case]}")
    print("\nStarting (about a minute per case) ...\n")

    sys.stdout.flush()   # so this text appears before the runner's output
    results = Path(tempfile.mkdtemp()) / "demo-results.csv"   # keep the real eval/results.csv untouched
    code = subprocess.run([sys.executable, str(ROOT / "eval" / "run_eval.py"), "--cases", ",".join(cases),
                           "--runs", "1", "--mode", args.mode, "--shop", str(shop), "--results", str(results)]).returncode

    print("\nFull reports (open in a browser):")
    for case in cases:
        report = shop / "out" / case / "run1" / "report.html"
        if report.exists():
            print(f"  {case}: {report}")
            if not args.no_open:
                webbrowser.open(report.as_uri())
    print("\nVerdicts: READY = nothing found, a person only skims it. BLOCKED = a written example failed, "
          "back to the developer.\nNEEDS DECISION = the spec leaves a question open, the product owner answers it.")
    return code


if __name__ == "__main__":
    sys.exit(main())
