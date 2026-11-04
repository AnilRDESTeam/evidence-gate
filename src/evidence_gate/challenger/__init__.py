"""The Challenger: a second AI that asks questions and maps files to criteria. It never decides a label.
Here the engine only builds its prompt and reads a saved answer; no AI is called."""

import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from evidence_gate import coverage, gitinfo
from evidence_gate.loader import GateInputError, find_contract_dir

TEMPLATE = Path(__file__).with_name("prompt.md")
_TOKEN = re.compile(r"\{(task_yaml|commit|diff|files)\}")


def _read(path) -> str:
    # Normalise line endings so the text and the hash are the same on every machine.
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def prompt_hash() -> str:
    """sha256 of the template file, so a result can be traced to the exact prompt wording."""
    return hashlib.sha256(_read(TEMPLATE).encode("utf-8")).hexdigest()


def build_prompt(task_path, repo, base: str, ignore_paths: list[str]) -> str:
    """The template filled with the task, the commit, the diff and the changed files' text."""
    # The coding AI's prompts must never reach the Challenger, whatever the policy says.
    files = coverage.relevant_files(gitinfo.changed_files(repo, base), [*ignore_paths, "prompts/**"])
    values = {
        "task_yaml": _read(task_path),
        "commit": gitinfo.head_commit(repo),
        "diff": gitinfo.diff_text(repo, base, files),
        "files": "\n".join(f"--- {f} ---\n{gitinfo.file_text(repo, f) or '(deleted in this change)'}\n" for f in files),
    }
    # One pass, not four replaces: a diff that happens to contain "{files}" must stay as it is.
    return _TOKEN.sub(lambda m: values[m.group(1)], _read(TEMPLATE))


def _strip_fences(text: str) -> str:
    # A chat answer is often wrapped in ```json ... ```; remove the fences.
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*\n", "", text)
    return re.sub(r"\n```\s*$", "", text)


def _same_commit(a: str, b: str) -> bool:
    # git short hashes can differ in length between machines, so compare as prefixes.
    return a.startswith(b) or b.startswith(a)


def load_challenge(path, head: str, task_id: str) -> dict:
    """Read a saved challenge file. Raises GateInputError if it is unreadable, invalid or for another commit."""
    name = Path(path).name
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as err:
        raise GateInputError([f"{path}: cannot read the challenge file: {err}"])
    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError as err:
        raise GateInputError([f"{path}: not valid JSON (line {err.lineno}): {err.msg}"])
    schema = json.loads((find_contract_dir() / "challenge.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    if errors:
        raise GateInputError([f"{path}: {'/'.join(map(str, e.absolute_path)) or '(top level)'}: {e.message}"
                              for e in errors])
    if not _same_commit(data["commit"], head):
        raise GateInputError([f"{name} is for commit {data['commit']}, branch is at {head}. "
                              "Run challenge-prompt again."])
    if data["task"] != task_id:
        raise GateInputError([f"{name} is for task {data['task']}, not {task_id}. Run challenge-prompt again."])
    return data


def merge_questions(spec_questions: list[dict], challenge_questions: list[dict]) -> list[dict]:
    """Spec questions stay as they are; the Challenger's are added. Both number from Q-1, so a clash is renumbered
    (the reports look questions up by id)."""
    merged = list(spec_questions)
    used = {q["id"] for q in merged}
    # Reserve the AI's own ids first, so renumbering a clash never steals an id another AI question already has.
    reserved = {q["id"] for q in challenge_questions}
    next_number = 1
    for q in challenge_questions:
        qid = q["id"]
        if qid in used:
            while f"Q-{next_number}" in used | reserved:
                next_number += 1
            qid = f"Q-{next_number}"
        used.add(qid)
        merged.append({**q, "id": qid})
    return merged
