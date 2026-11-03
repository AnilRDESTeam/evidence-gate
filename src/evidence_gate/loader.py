"""Load and check the input files (task, adapter, policy) against the frozen contract schemas."""

import datetime
import json
import os
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError


class GateInputError(Exception):
    """An input file is missing or invalid. .problems holds friendly messages."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def find_contract_dir() -> Path:
    env = os.environ.get("EVIDENCE_GATE_CONTRACT_DIR")
    if env:
        return Path(env)
    # Walk up from this file so it works from the repo and from an editable install.
    for folder in Path(__file__).resolve().parents:
        if (folder / "contract" / "task.schema.json").exists():
            return folder / "contract"
    raise GateInputError(["Cannot find the contract folder. Set EVIDENCE_GATE_CONTRACT_DIR to its path."])


def _plain(value):
    # YAML turns 2026-11-04 into a date object; the schema wants the string.
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def load_yaml(path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise GateInputError([f"File not found: {path}"])
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except MarkedYAMLError as err:
        line = err.problem_mark.line + 1 if err.problem_mark else "?"
        raise GateInputError([f"{path}: YAML syntax error at line {line}: {err.problem}"])
    if not isinstance(data, dict):
        raise GateInputError([f"{path}: the top level must be a mapping (key: value), not a list or text"])
    return _plain(data)


def _field_path(parts) -> str:
    # deque(["criteria", 1, "examples"]) -> criteria[1].examples
    text = ""
    for part in parts:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text


def _describe(error) -> tuple[str, str]:
    """Return (field path, message), adding a plain-English hint where the schema message is noisy."""
    path = _field_path(error.absolute_path)
    message = error.message
    if error.validator == "required":
        missing = re.match(r"'(.+?)' is a required property", message)
        name = missing.group(1) if missing else "?"
        path = f"{path}.{name}" if path else name
        hints = {
            "examples": "required for a MUST criterion",
            "previous_rule": "required when type is 'updated'",
            "revised_rule": "required when type is 'updated'",
        }
        message = hints.get(name, "required field is missing")
    elif error.validator == "minItems" and path.endswith("examples"):
        message = "a MUST criterion needs at least one example"
    elif error.validator in ("anyOf", "oneOf", "if", "then"):
        message += " (check the value against the contract README)"
    return path or "(top level)", message


def _validate(path, data: dict, schema_name: str) -> dict:
    schema = json.loads((find_contract_dir() / schema_name).read_text(encoding="utf-8"))
    errors = sorted((_describe(e) for e in Draft202012Validator(schema).iter_errors(data)))
    if errors:
        raise GateInputError([f"{path}: {where}: {msg}" for where, msg in errors])
    return data


def load_task(path) -> dict:
    return _validate(path, load_yaml(path), "task.schema.json")


def load_adapter(path) -> dict:
    return _validate(path, load_yaml(path), "adapter.schema.json")


def load_policy(path) -> dict:
    return _validate(path, load_yaml(path), "policy.schema.json")


def check_task_consistency(task: dict) -> list[str]:
    """Rules a JSON schema cannot express: unique ids and references to real criteria."""
    problems = []
    ids = [c["id"] for c in task.get("criteria", [])]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"criteria: id {dup} is used more than once")
    for section in ("open_questions", "waivers", "approved_scenarios"):
        for n, item in enumerate(task.get(section, [])):
            ref = item.get("criterion")
            if ref is not None and ref not in ids:
                problems.append(f"{section}[{n}].criterion: {ref} is not a criterion of this task")
    return problems


def find_repo_root(task_path) -> Path:
    """Nearest folder above the task file that has a .evidence-gate/ folder, else the current folder."""
    for folder in Path(task_path).resolve().parents:
        if (folder / ".evidence-gate").is_dir():
            return folder
    return Path.cwd()
