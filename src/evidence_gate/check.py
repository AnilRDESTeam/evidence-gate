"""The `check` command: load -> git -> challenger -> scenarios -> run -> label -> verdict -> route -> report."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from evidence_gate import challenger as challenger_module  # not `challenger`: run_check has a parameter by that name
from evidence_gate import context, coverage, gitinfo
from evidence_gate.labeller import label_criteria
from evidence_gate.loader import (GateInputError, check_task_consistency, find_contract_dir, find_repo_root,
                                  load_adapter, load_policy, load_task)
from evidence_gate.reporters import html_report, json_report, md_report, pdf_report, terminal
from evidence_gate.router import decide_route, next_action
from evidence_gate.runner import NO_CHALLENGER, run_scenarios
from evidence_gate.scenarios import build_scenarios
from evidence_gate.verdict import decide_verdict


def load_policy_or_default(config_dir: Path, warnings: list[str]) -> dict:
    path = config_dir / "policy.yaml"
    if path.exists():
        return load_policy(path)
    warnings.append(f"{path} not found, using the default policy")
    return load_policy(find_contract_dir() / "policy.default.yaml")


def _load_adapters(config_dir: Path, task: dict) -> dict:
    """Load only the adapters this task uses. A missing file is not fatal: its scenarios become errors."""
    adapters = {}
    for name in sorted({ex["via"].split(".")[0] for c in task["criteria"] for ex in c.get("examples", [])}
                       | {a["via"].split(".")[0] for a in task.get("approved_scenarios", [])}):
        path = config_dir / "adapters" / f"{name}.yaml"
        if path.exists():
            adapters[name] = load_adapter(path)
    return adapters


def _tests_command(config_dir: Path) -> str | None:
    """The tests command lives in api.yaml (context.tests_command). No api.yaml means no context line."""
    path = config_dir / "adapters" / "api.yaml"
    if not path.exists():
        return None
    return load_adapter(path).get("context", {}).get("tests_command")


def _ai_suggestions(records: list[dict]) -> list[dict]:
    keys = ("scenario", "criterion", "input", "actual", "status", "error")
    return [{**{k: r[k] for k in keys}, "expected": r["expected"]} for r in records if r["source"] == "ai-proposed"]


def _error_report(task, head, base, run_id, message) -> dict:
    """Best-effort report when something went wrong after the task was loaded."""
    return {"task": task["id"], "title": task["title"], "type": task["type"], "commit": head, "base": base,
            "run_id": run_id, "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "challenger": NO_CHALLENGER, "criteria": [], "questions": [], "changed_files": [],
            "uncovered_files": [], "verdict": "GATE ERROR", "exit_code": 3, "route": None,
            "route_reason": "The Gate could not finish: " + message,
            "next_action": "Fix the problem described above, then rerun evidence-gate check.",
            "context": None, "warnings": [message], "contract_version": "1.0"}


def run_check(task_path: str, base: str = "main", out_dir: str = "out", challenger: str = "off",
              challenge_file: str | None = None, no_tests: bool = False, pdf: bool = True) -> int:
    task = head = None
    run_id = datetime.now(timezone.utc).strftime("r-%Y%m%d-%H%M%S")
    try:
        if challenger == "live":
            # Only off and saved exist; refuse clearly instead of silently running with AI off.
            raise GateInputError(["--challenger live is not available; use --challenger off or --challenger saved"])
        if challenger == "saved" and not challenge_file:
            raise GateInputError(["--challenger saved needs --challenge-file <path to the saved challenge JSON>"])

        task = load_task(task_path)
        problems = check_task_consistency(task)
        if problems:
            raise GateInputError([f"{task_path}: {p}" for p in problems])
        repo = find_repo_root(task_path)
        config_dir = repo / ".evidence-gate"
        warnings: list[str] = []
        policy = load_policy_or_default(config_dir, warnings)
        adapters = _load_adapters(config_dir, task)

        head = gitinfo.head_commit(repo)
        if gitinfo.is_dirty(repo):
            warnings.append("The working tree has uncommitted changes; the evidence is for the files as they are now.")
        files = coverage.relevant_files(gitinfo.changed_files(repo, base), policy["ignore_paths"])

        high_risk = coverage.high_risk_files(files, policy["high_risk_paths"])
        if challenger == "saved":
            # Saved: the Challenger's answer decides coverage and adds questions and unconfirmed scenario ideas.
            # None of it can change a label: ideas are unconfirmed, and coverage only picks the review route.
            answer = challenger_module.load_challenge(challenge_file, head, task["id"])
            challenger_info = {"mode": "saved", "model": answer.get("model") or "unknown",
                               "prompt_hash": challenger_module.prompt_hash()}
            questions = challenger_module.merge_questions(task.get("open_questions", []), answer["questions"])
            uncovered = coverage.uncovered_by_challenge(files, answer)
            proposed = answer["proposed_scenarios"]
        else:
            # Off: questions come from the spec, coverage from scope.paths, no AI suggestions.
            challenger_info = NO_CHALLENGER
            questions = list(task.get("open_questions", []))
            uncovered = coverage.uncovered_by_scope(files, task.get("scope", {}).get("paths", []))
            proposed = None

        scenarios, scenario_warnings = build_scenarios(task, proposed)
        warnings += scenario_warnings
        records = run_scenarios(scenarios, adapters, task["id"], head, out_dir, str(repo), challenger_info, run_id)

        # Run after the scenarios so the project's own tests cannot disturb the shop state they used.
        tests_context = None
        if not no_tests:
            tests_context, tests_warning = context.run_existing_tests(_tests_command(config_dir), str(repo))
            if tests_warning:
                warnings.append(tests_warning)

        criteria = label_criteria(task, records, questions, head)
        result = decide_verdict(criteria, questions, should_failures=policy["should_failures"])
        route, route_reason = decide_route(result, criteria, questions, high_risk, uncovered)
        report = {
            "task": task["id"], "title": task["title"], "type": task["type"], "commit": head, "base": base,
            "run_id": run_id, "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "challenger": challenger_info, "criteria": criteria, "questions": questions,
            "changed_files": files, "uncovered_files": uncovered, "high_risk_files": high_risk,
            "ai_suggestions": _ai_suggestions(records), "verdict": result.verdict, "exit_code": result.exit_code,
            "route": route, "route_reason": route_reason,
            "next_action": next_action(result, route, criteria, questions, records, high_risk, uncovered),
            "context": tests_context, "warnings": warnings + result.warnings, "contract_version": "1.0",
        }
        full_report = Path(out_dir, "report.html").as_posix()
        json_report.write(report, out_dir)
        html_path = html_report.write(report, records, out_dir)
        if pdf:
            # A PDF is a convenience: if there is no browser, say so and carry on; it never changes the verdict.
            _, pdf_problem = pdf_report.write(html_path, adapters.get("browser", {}).get("channel"))
            if pdf_problem:
                print(f"Note: {pdf_problem}", file=sys.stderr)
            else:
                full_report += f" and {Path(out_dir, 'report.pdf').as_posix()}"
        md_report.write(report, records, out_dir, full_report)
        print(terminal.render(report, records, full_report), end="")
        return report["exit_code"]

    except GateInputError as err:
        print("GATE ERROR", file=sys.stderr)
        for problem in err.problems:
            print(f"  - {problem}", file=sys.stderr)
        message = "; ".join(err.problems)
    except Exception as err:  # anything unexpected: short message, no traceback, exit 3
        message = f"unexpected problem: {type(err).__name__}: {err}"
        print(f"GATE ERROR: {message}", file=sys.stderr)

    # Write what we can: only possible once the task and commit are known.
    if task is not None and head is not None:
        try:
            json_report.write(_error_report(task, head, base, run_id, message), out_dir)
        except Exception:
            pass
    return 3
