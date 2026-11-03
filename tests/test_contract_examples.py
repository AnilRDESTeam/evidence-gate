"""Checks that the contract schemas are valid and that every example follows them."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contract"
EXAMPLES = CONTRACT / "examples"


def load(path: Path):
    """Read a .json or .yaml file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    return YAML(typ="safe").load(text)


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(load(CONTRACT / f"{name}.schema.json"))


def error_text(path: Path, errors) -> str:
    """Message that names the file and the field path."""
    lines = []
    for e in errors:
        field = "/".join(str(p) for p in e.absolute_path) or "(top level)"
        lines.append(f"{path.name}: {field}: {e.message}")
    return "\n".join(lines)


# (example file, schema name)
EXAMPLE_FILES = [
    (EXAMPLES / "SHOP-101.task.yaml", "task"),
    (EXAMPLES / "SHOP-102.task.yaml", "task"),
    (EXAMPLES / "api.adapter.yaml", "adapter"),
    (EXAMPLES / "browser.adapter.yaml", "adapter"),
    (EXAMPLES / "policy.example.yaml", "policy"),
    (CONTRACT / "policy.default.yaml", "policy"),
    (EXAMPLES / "evidence.example.json", "evidence"),
    (EXAMPLES / "challenge.example.json", "challenge"),
    (EXAMPLES / "report.example.json", "report"),
]


@pytest.mark.parametrize("schema_file", sorted(CONTRACT.glob("*.schema.json")), ids=lambda p: p.name)
def test_schema_is_valid(schema_file):
    Draft202012Validator.check_schema(load(schema_file))


@pytest.mark.parametrize("path,schema", EXAMPLE_FILES, ids=lambda v: v.name if isinstance(v, Path) else v)
def test_example_matches_schema(path, schema):
    errors = list(validator(schema).iter_errors(load(path)))
    assert not errors, error_text(path, errors)


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.task.yaml")), ids=lambda p: p.name)
def test_criteria_ids_unique(path):
    # JSON Schema cannot check uniqueness by one field, so we do it here.
    ids = [c["id"] for c in load(path)["criteria"]]
    assert len(ids) == len(set(ids)), f"{path.name}: duplicate criteria ids {ids}"


def test_default_policy_equals_example():
    assert (CONTRACT / "policy.default.yaml").read_text(encoding="utf-8") == (
        EXAMPLES / "policy.example.yaml"
    ).read_text(encoding="utf-8")


# ---- Negative tests: each broken document must be rejected ----

def broken_task_must_without_examples():
    doc = load(EXAMPLES / "SHOP-102.task.yaml")
    del doc["criteria"][0]["examples"]
    return "task", doc


def broken_task_updated_without_previous_rule():
    doc = load(EXAMPLES / "SHOP-102.task.yaml")
    del doc["previous_rule"]
    return "task", doc


def broken_task_priority_maybe():
    doc = load(EXAMPLES / "SHOP-102.task.yaml")
    doc["criteria"][0]["priority"] = "MAYBE"
    return "task", doc


def broken_policy_route_when_sometimes():
    doc = load(CONTRACT / "policy.default.yaml")
    doc["routes"][0]["when"] = "sometimes"
    return "policy", doc


def broken_evidence_ai_proposed_confirmed():
    doc = load(EXAMPLES / "evidence.example.json")
    doc["source"] = "ai-proposed"
    doc["confirmed"] = True
    return "evidence", doc


def broken_report_blocked_exit_0():
    doc = load(EXAMPLES / "report.example.json")
    doc["exit_code"] = 0
    return "report", doc


def broken_report_not_verified_without_reason():
    doc = load(EXAMPLES / "report.example.json")
    doc["criteria"][1]["reason"] = None
    return "report", doc


def broken_adapter_ftp():
    doc = load(EXAMPLES / "api.adapter.yaml")
    doc["type"] = "ftp"
    return "adapter", doc


NEGATIVE_CASES = [
    broken_task_must_without_examples,
    broken_task_updated_without_previous_rule,
    broken_task_priority_maybe,
    broken_policy_route_when_sometimes,
    broken_evidence_ai_proposed_confirmed,
    broken_report_blocked_exit_0,
    broken_report_not_verified_without_reason,
    broken_adapter_ftp,
]


@pytest.mark.parametrize("make_case", NEGATIVE_CASES, ids=lambda f: f.__name__)
def test_broken_document_is_rejected(make_case):
    schema, doc = make_case()
    assert list(validator(schema).iter_errors(copy.deepcopy(doc))), "should have been rejected"


# ---- RULES.md guard ----

@pytest.mark.parametrize("row_id", [f"L{i}" for i in range(1, 8)] + [f"V{i}" for i in range(1, 5)] + [f"R{i}" for i in range(1, 6)])
def test_rules_has_row(row_id):
    text = (CONTRACT / "RULES.md").read_text(encoding="utf-8")
    assert f"| {row_id} |" in text, f"RULES.md is missing row {row_id}"
