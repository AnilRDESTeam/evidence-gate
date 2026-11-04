"""Tests for the loader and the `validate` command. Each test builds a tiny repo in tmp_path."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "contract" / "examples"

API_ADAPTER_OK = EXAMPLES / "api.adapter.yaml"


def validate(task_path):
    return subprocess.run([sys.executable, "-m", "evidence_gate.cli", "validate", "--task", str(task_path)],
                          capture_output=True, text=True)


def make_task(tmp_path, text):
    task = tmp_path / "requirements" / "T.task.yaml"
    task.parent.mkdir(exist_ok=True)
    task.write_text(text, encoding="utf-8")
    return task


def with_config(tmp_path):
    """Give tmp_path a .evidence-gate folder so it counts as the repo root."""
    (tmp_path / ".evidence-gate" / "adapters").mkdir(parents=True)
    return tmp_path / ".evidence-gate"


GOOD = """\
id: T-1
type: new
title: t
request: r
criteria:
  - id: AC-1
    priority: MUST
    statement: s
    examples:
      - { via: api.quote_order, input: { subtotal: 1 }, expect: { shipping: 0 } }
"""


@pytest.mark.parametrize("name", ["SHOP-102", "SHOP-101"])
def test_official_examples_pass(name):
    result = validate(EXAMPLES / f"{name}.task.yaml")
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK")


def test_missing_file(tmp_path):
    result = validate(tmp_path / "nope.yaml")
    assert result.returncode == 3
    assert "File not found" in result.stderr


def test_yaml_syntax_error_has_line_number(tmp_path):
    task = make_task(tmp_path, "id: T-1\ncriteria: [unclosed\n  - x\n")
    result = validate(task)
    assert result.returncode == 3
    assert "line" in result.stderr and "GATE ERROR" in result.stderr


def test_top_level_must_be_mapping(tmp_path):
    result = validate(make_task(tmp_path, "- a\n- b\n"))
    assert result.returncode == 3
    assert "mapping" in result.stderr


def test_must_without_examples(tmp_path):
    result = validate(make_task(tmp_path, GOOD.split("    examples:")[0]))
    assert result.returncode == 3
    assert "criteria[0]: 'examples' is required for a MUST criterion" in result.stderr


def test_missing_priority_message_is_plain(tmp_path):
    result = validate(make_task(tmp_path, GOOD.replace("    priority: MUST\n", "")))
    assert result.returncode == 3
    assert "T.task.yaml: criteria[0]: 'priority' is required" in result.stderr


def test_wrong_type_is_reported_with_field_path(tmp_path):
    # examples must be a list, not a string
    text = GOOD.split("    examples:")[0] + "    examples: nope\n"
    result = validate(make_task(tmp_path, text))
    assert result.returncode == 3
    assert "criteria[0].examples" in result.stderr


def test_tab_indentation_is_a_yaml_error(tmp_path):
    # Tabs are not allowed for YAML indentation; the user should get a line number, not a traceback.
    task = make_task(tmp_path, "id: T-1\ncriteria:\n\t- id: AC-1\n")
    result = validate(task)
    assert result.returncode == 3
    assert "YAML syntax error at line" in result.stderr
    assert "Traceback" not in result.stderr


def test_unused_invalid_adapter_is_still_reported(tmp_path):
    config = with_config(tmp_path)
    (config / "adapters" / "browser.yaml").write_text("type: browser\n", encoding="utf-8")
    result = validate(make_task(tmp_path, GOOD))
    assert result.returncode == 3
    assert "browser.yaml" in result.stderr


def test_updated_without_previous_rule(tmp_path):
    result = validate(make_task(tmp_path, GOOD.replace("type: new", "type: updated")))
    assert result.returncode == 3
    assert "previous_rule" in result.stderr


def test_duplicate_criterion_id(tmp_path):
    extra = "  - id: AC-1\n    priority: SHOULD\n    statement: again\n"
    result = validate(make_task(tmp_path, GOOD + extra))
    assert result.returncode == 3
    assert "AC-1 is used more than once" in result.stderr


def test_open_question_points_to_missing_criterion(tmp_path):
    text = GOOD + "open_questions:\n  - { id: Q-1, text: why, criterion: AC-9 }\n"
    result = validate(make_task(tmp_path, text))
    assert result.returncode == 3
    assert "AC-9" in result.stderr


def test_open_question_with_null_criterion_is_fine(tmp_path):
    text = GOOD + "open_questions:\n  - { id: Q-1, text: why, criterion: null }\n"
    assert validate(make_task(tmp_path, text)).returncode == 0


def test_adapter_present_but_action_missing(tmp_path):
    config = with_config(tmp_path)
    shutil.copy(API_ADAPTER_OK, config / "adapters" / "api.yaml")
    text = GOOD.replace("api.quote_order", "api.no_such_action")
    result = validate(make_task(tmp_path, text))
    assert result.returncode == 3
    assert "no_such_action" in result.stderr


def test_adapter_present_with_action_passes(tmp_path):
    config = with_config(tmp_path)
    shutil.copy(API_ADAPTER_OK, config / "adapters" / "api.yaml")
    assert validate(make_task(tmp_path, GOOD)).returncode == 0


def test_adapter_absent_is_only_a_warning(tmp_path):
    with_config(tmp_path)
    result = validate(make_task(tmp_path, GOOD))
    assert result.returncode == 0
    assert "WARN adapter 'api' not found" in result.stdout


def test_valid_policy_passes_and_invalid_policy_fails(tmp_path):
    config = with_config(tmp_path)
    task = make_task(tmp_path, GOOD)
    shutil.copy(EXAMPLES / "policy.example.yaml", config / "policy.yaml")
    assert validate(task).returncode == 0
    (config / "policy.yaml").write_text("version: 2\n", encoding="utf-8")
    result = validate(task)
    assert result.returncode == 3
    assert "policy.yaml" in result.stderr
