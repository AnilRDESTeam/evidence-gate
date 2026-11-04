"""CLI: help works and lists every command."""

import subprocess
import sys

import pytest

COMMANDS = {
    "validate": ["--task", "t.yaml"],
    "adapter-test": ["--adapter", "api", "--action", "quote_order", "--input-file", "in.json"],
    "challenge-prompt": ["--task", "t.yaml"],
    "check": ["--task", "t.yaml"],
}


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "evidence_gate.cli", *args],
        capture_output=True,
        text=True,
    )


def test_help_lists_commands():
    result = run_cli("--help")
    assert result.returncode == 0
    for name in COMMANDS:
        assert name in result.stdout
    assert "0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR" in result.stdout


@pytest.mark.parametrize("name", COMMANDS)
def test_command_help_exits_zero(name):
    assert run_cli(name, "--help").returncode == 0


# Every command is built now (validate: test_loader.py, adapter-test: test_http_driver.py, check: test_check.py,
# challenge-prompt: test_challenger.py), so there are no stubs left to test.
