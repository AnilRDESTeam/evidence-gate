"""Command-line entry point. Only `validate` is built; the other commands are stubs for now."""

import argparse
import sys

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

    p = sub.add_parser("check", help="run the full gate on the current branch")
    p.add_argument("--task", required=True, metavar="PATH")
    p.add_argument("--base", default="main")
    p.add_argument("--challenger", choices=["off", "saved", "live"])
    p.add_argument("--challenge-file", metavar="PATH")
    p.add_argument("--out", default="out")
    p.add_argument("--no-tests", action="store_true")
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
    # Stub: the real engine is built later, one module per session.
    print(f"evidence-gate {args.command}: not implemented yet", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
