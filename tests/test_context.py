"""Tests for the existing-tests context. It is context only, so every failure here is a warning, never a crash."""

import sys

import pytest

from evidence_gate.context import parse_pytest_summary, run_existing_tests

PYTHON = f'"{sys.executable}"'


@pytest.mark.parametrize("output, expected", [
    ("56 passed, 2 deselected, 1 warning in 0.73s", {"tests_passed": 56, "tests_total": 56}),
    ("2 failed, 54 passed, 1 warning in 0.7s", {"tests_passed": 54, "tests_total": 56}),
    ("1 failed, 3 passed, 2 errors in 1.20s", {"tests_passed": 3, "tests_total": 6}),
    ("1 error in 0.10s", {"tests_passed": 0, "tests_total": 1}),
    ("== 7 passed in 0.05s ==", {"tests_passed": 7, "tests_total": 7}),
    ("noise\n12 passed in 1.00s\n", {"tests_passed": 12, "tests_total": 12}),
])
def test_parse_summary(output, expected):
    assert parse_pytest_summary(output) == expected


@pytest.mark.parametrize("output", ["", "........ [100%]", "no tests ran in 0.01s", "something else entirely"])
def test_parse_without_a_summary_is_none(output):
    assert parse_pytest_summary(output) is None


def test_run_reads_counts_from_the_command_output(tmp_path):
    context, warning = run_existing_tests(f'{PYTHON} -c "print(\'3 passed in 0.1s\')"', str(tmp_path))
    assert context == {"tests_passed": 3, "tests_total": 3} and warning is None


def test_failing_test_command_is_still_context(tmp_path):
    # pytest exits 1 when tests fail; the counts are still what we want.
    command = f'{PYTHON} -c "import sys; print(\'1 failed, 4 passed in 0.1s\'); sys.exit(1)"'
    context, warning = run_existing_tests(command, str(tmp_path))
    assert context == {"tests_passed": 4, "tests_total": 5} and warning is None


def test_unreadable_output_is_a_warning_not_an_error(tmp_path):
    context, warning = run_existing_tests(f'{PYTHON} -c "print(\'hello\')"', str(tmp_path))
    assert context is None and "no pytest summary" in warning


def test_command_that_does_not_exist_is_a_warning(tmp_path):
    context, warning = run_existing_tests("no-such-command-xyz", str(tmp_path))
    assert context is None and warning


def test_timeout_is_a_warning(tmp_path, monkeypatch):
    monkeypatch.setattr("evidence_gate.context.TIMEOUT_SECONDS", 1)
    context, warning = run_existing_tests(f'{PYTHON} -c "import time; time.sleep(5)"', str(tmp_path))
    assert context is None and "longer than 1 s" in warning


def test_no_command_means_no_context(tmp_path):
    assert run_existing_tests(None, str(tmp_path)) == (None, None)
