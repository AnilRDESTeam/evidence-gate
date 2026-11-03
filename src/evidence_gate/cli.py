"""Command-line entry point. Every command is a stub for now."""

import argparse
import sys

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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    # Stub: the real engine is built later, one module per session.
    print(f"evidence-gate {args.command}: not implemented yet", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main())
