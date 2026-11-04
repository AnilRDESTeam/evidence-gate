"""Command-line entry point: `validate`, `adapter-test`, `challenge-prompt` and `check`."""

import argparse
import json
import sys
from pathlib import Path

from evidence_gate.loader import (GateInputError, check_task_consistency, find_repo_root,
                                  load_adapter, load_policy, load_task)

EXIT_HELP = "Exit codes: 0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidence-gate", epilog=EXIT_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("validate", help="validate a task spec against the contract")
    p.add_argument("--task", required=True, metavar="PATH")

    p = sub.add_parser("adapter-test", help="run one adapter action by hand")
    p.add_argument("--adapter", required=True, metavar="NAME")
    p.add_argument("--action", required=True, metavar="NAME")
    p.add_argument("--input-file", required=True, metavar="PATH")

    p = sub.add_parser("challenge-prompt", help="print the prompt for the Challenger AI")
    p.add_argument("--task", required=True, metavar="PATH")
    p.add_argument("--base", default="main")

    p = sub.add_parser("check", help="run the full gate on the current branch")
    p.add_argument("--task", required=True, metavar="PATH")
    p.add_argument("--base", default="main")
    p.add_argument("--challenger", choices=["off", "saved", "live"])
    p.add_argument("--challenge-file", metavar="PATH")
    p.add_argument("--out", default="out")
    p.add_argument("--no-tests", action="store_true")
    p.add_argument("--no-pdf", action="store_true", help="do not write report.pdf next to report.html")

    p = sub.add_parser("overview", help="build the evaluation overview (every case and its status) as HTML and PDF")
    p.add_argument("--summary", required=True, metavar="PATH", help="the summary JSON written by eval/run_eval.py")
    p.add_argument("--out", metavar="DIR", help="where to write it (default: next to the summary)")
    p.add_argument("--no-pdf", action="store_true")
    return parser


def used_actions(task: dict) -> dict[str, set[str]]:
    """Map adapter name -> actions the task asks for (from every `via: adapter.action`)."""
    found: dict[str, set[str]] = {}
    items = [ex for c in task["criteria"] for ex in c.get("examples", [])]
    items += task.get("approved_scenarios", [])
    for item in items:
        name, action = item["via"].split(".", 1)
        found.setdefault(name, set()).add(action)
    return found


def validate(task_path: str) -> int:
    """Check the task, the policy and the adapters it uses. Exit 0 if fine, 3 (GATE ERROR) if not."""
    errors: list[tuple[str, list[str]]] = []  # (file, problems)
    warns: list[str] = []

    def attempt(path, loader):
        try:
            return loader(path)
        except GateInputError as err:
            errors.append((str(path), err.problems))

    task = attempt(task_path, load_task)
    if task is None:
        return report_errors(errors)
    problems = check_task_consistency(task)
    if problems:
        errors.append((task_path, [f"{task_path}: {p}" for p in problems]))

    config = find_repo_root(task_path) / ".evidence-gate"
    policy = config / "policy.yaml"
    if policy.exists():
        attempt(policy, load_policy)
    else:
        warns.append(f"WARN policy not found at {policy} (the default policy will be needed)")

    # Schema-check every adapter file, even ones this task does not use, so a broken file is caught early.
    adapters = {}
    for path in sorted((config / "adapters").glob("*.yaml")):
        adapters[path.stem] = (path, attempt(path, load_adapter))

    for name, actions in sorted(used_actions(task).items()):
        if name not in adapters:
            # Not an error: T1/T2 add the adapter files later.
            path = config / "adapters" / f"{name}.yaml"
            warns.append(f"WARN adapter '{name}' not found at {path} (T1/T2 add it)")
            continue
        path, adapter = adapters[name]
        if adapter:
            missing = sorted(actions - set(adapter["actions"]))
            if missing:
                errors.append((str(path), [f"{path}: action '{a}' is used by the task but not defined" for a in missing]))

    if errors:
        return report_errors(errors)
    examples = sum(len(c.get("examples", [])) for c in task["criteria"])
    print(f"OK  {task_path}  ({task['id']}, {task['type']}, {len(task['criteria'])} criteria, {examples} examples)")
    for line in warns:
        print(line)
    return 0


def adapter_test(adapter_name: str, action: str, input_file: str) -> int:
    """Run one adapter action by hand and print what the driver saw. Exit 0 if no error, else 3."""
    from evidence_gate.drivers import build_driver

    try:
        path = Path.cwd() / ".evidence-gate" / "adapters" / f"{adapter_name}.yaml"
        config = load_adapter(path)
        inputs = json.loads(Path(input_file).read_text(encoding="utf-8"))
        if not isinstance(inputs, dict):
            raise GateInputError([f"{input_file}: the input must be a JSON object like {{\"subtotal\": 50}}"])
    except GateInputError as err:
        return report_errors([(str(adapter_name), err.problems)])
    except (OSError, ValueError) as err:
        return report_errors([(str(input_file), [f"{input_file}: cannot read input: {err}"])])

    try:
        driver = build_driver(config, str(Path.cwd()), str(Path.cwd() / "out"))
    except (ImportError, ValueError) as err:
        return report_errors([(adapter_name, [f"cannot build the '{config['type']}' driver: {err}"])])
    try:
        driver.before_each()
        result = driver.run(action, inputs)
    finally:
        driver.close()
    print(json.dumps({"actual": result.actual, "error": result.error, "artifacts": result.artifacts}, indent=2))
    return 3 if result.error else 0


def challenge_prompt(task_path: str, base: str) -> int:
    """Print the filled Challenger prompt to paste into a chat. The prompt hash goes to stderr, so a `>` file stays clean."""
    from evidence_gate import challenger
    from evidence_gate.check import load_policy_or_default

    try:
        task = load_task(task_path)
        problems = check_task_consistency(task)
        if problems:
            raise GateInputError([f"{task_path}: {p}" for p in problems])
        repo = find_repo_root(task_path)
        warnings: list[str] = []
        policy = load_policy_or_default(repo / ".evidence-gate", warnings)
        prompt = challenger.build_prompt(task_path, repo, base, policy["ignore_paths"])
    except GateInputError as err:  # includes GitError
        return report_errors([(task_path, err.problems)])
    for warning in warnings:
        print(f"WARN {warning}", file=sys.stderr)
    # utf-8 and LF whatever the console, so a redirected file pastes the same everywhere.
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.write(prompt)
    print(f"prompt_hash {challenger.prompt_hash()}", file=sys.stderr)
    return 0


def overview(summary_path: str, out_dir: str | None, pdf: bool) -> int:
    """Build the evaluation overview from the summary JSON that eval/run_eval.py writes."""
    from evidence_gate.reporters import overview_report

    try:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        html_path, pdf_path, problem = overview_report.write(summary, out_dir or Path(summary_path).parent, pdf)
    except (OSError, ValueError, KeyError) as err:
        return report_errors([(summary_path, [f"cannot build the overview: {err!r}"])])
    print(f"Overview: {html_path}")
    if pdf_path:
        print(f"PDF:      {pdf_path}")
        # Copies go beside the overview (cases-off/E1.pdf ...), so every report is in one folder.
        case_pdfs, case_problem = overview_report.write_case_pdfs(summary, html_path.parent / f"cases-{summary['mode']}")
        for case_pdf in case_pdfs:
            print(f"  case:   {case_pdf}")
        if case_problem:
            print(f"Note: {case_problem}", file=sys.stderr)
    elif problem:
        print(f"Note: {problem}", file=sys.stderr)
    return 0


def report_errors(errors: list[tuple[str, list[str]]]) -> int:
    for file, problems in errors:
        print(f"GATE ERROR: {file}", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
    return 3


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "validate":
        return validate(args.task)
    if args.command == "check":
        from evidence_gate.check import run_check
        return run_check(args.task, args.base, args.out, args.challenger or "off", args.challenge_file, args.no_tests,
                         pdf=not args.no_pdf)
    if args.command == "overview":
        return overview(args.summary, args.out, not args.no_pdf)
    if args.command == "adapter-test":
        return adapter_test(args.adapter, args.action, args.input_file)
    if args.command == "challenge-prompt":
        return challenge_prompt(args.task, args.base)
    # Stub: the real engine is built later, one module per session.
    print(f"evidence-gate {args.command}: not implemented yet", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
