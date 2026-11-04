"""Tests for scenarios, compare, safety and the runner. A fake driver stands in for the shop."""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evidence_gate.compare import compare
from evidence_gate.drivers.base import Driver, DriverResult
from evidence_gate.loader import load_task
from evidence_gate.runner import run_scenarios
from evidence_gate.safety import adapter_problem
from evidence_gate.scenarios import Scenario, build_scenarios

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "contract" / "examples"
EVIDENCE_SCHEMA = json.loads((ROOT / "contract" / "evidence.schema.json").read_text(encoding="utf-8"))

HEAD = "a41c9e2"
ADAPTERS = {"api": {"type": "http", "base_url": "http://127.0.0.1:8080", "safety": {"allowed_hosts": ["127.0.0.1"]}}}


class FakeDriver(Driver):
    """Returns canned results and remembers what it was asked."""

    def __init__(self, actual=None, error=None, commit=HEAD, artifacts=None):
        self.actual, self.error, self.commit, self.artifacts = actual or {}, error, commit, artifacts or {}
        self.calls, self.before_each_count, self.closed = [], 0, False

    def health_commit(self):
        return self.commit

    def before_each(self):
        self.before_each_count += 1

    def run(self, action, inputs):
        self.calls.append((action, inputs))
        return DriverResult(actual={} if self.error else self.actual, error=self.error, artifacts=self.artifacts)

    def close(self):
        self.closed = True


def scenario(sid="S-AC-1-1", expect=None, source="spec-example", confirmed=True, adapter="api"):
    return Scenario(sid, "AC-1", source, confirmed, adapter, "quote_order", {"subtotal": 50}, expect or {"shipping": 5.99})


def run(scenarios, driver, tmp_path, **kwargs):
    return run_scenarios(scenarios, kwargs.pop("adapters", ADAPTERS), "SHOP-102", HEAD, str(tmp_path / "out"),
                         driver_factory=lambda config, root, out: driver, **kwargs)


# ---- compare ----

def test_compare_pass():
    assert compare({"shipping": 5.99}, {"shipping": 5.99}) == ("pass", [])


def test_compare_fail_lists_mismatch():
    status, mismatches = compare({"shipping": 5.99}, {"shipping": 0.0})
    assert status == "fail"
    assert mismatches == [{"field": "shipping", "expected": 5.99, "actual": 0.0}]


@pytest.mark.parametrize("actual, status", [(5.99, "pass"), (5.994, "pass"), (5.995, "pass"), (5.9951, "fail"), (5.984, "fail")])
def test_compare_number_tolerance_is_plus_minus_half_a_cent(actual, status):
    assert compare({"shipping": 5.99}, {"shipping": actual})[0] == status


def test_compare_tolerance_edge_has_no_float_noise():
    assert compare({"x": 74.99}, {"x": 74.995})[0] == "pass"


def test_compare_int_equals_float():
    assert compare({"shipping": 0}, {"shipping": 0.0})[0] == "pass"


def test_compare_text_is_trimmed():
    assert compare({"label": "Welcome 10%"}, {"label": "  Welcome 10% "})[0] == "pass"


def test_compare_text_is_otherwise_exact():
    assert compare({"label": "Welcome 10%"}, {"label": "welcome 10%"})[0] == "fail"


def test_compare_only_expected_fields_are_checked():
    assert compare({"shipping": 5.99}, {"shipping": 5.99, "total": 999, "junk": "x"})[0] == "pass"


def test_compare_missing_actual_field_is_a_mismatch():
    status, mismatches = compare({"shipping": 5.99}, {})
    assert status == "fail" and mismatches[0]["actual"] is None


def test_compare_expected_null_matches_null():
    assert compare({"discount_label": None}, {"discount_label": None})[0] == "pass"
    assert compare({"discount_label": None}, {"discount_label": "Welcome 10%"})[0] == "fail"


def test_compare_number_does_not_equal_text_or_bool():
    assert compare({"x": 1}, {"x": "1"})[0] == "fail"
    assert compare({"x": 1}, {"x": True})[0] == "fail"


# ---- scenarios ----

def test_each_example_becomes_a_confirmed_scenario_with_numbered_id():
    task = load_task(EXAMPLES / "SHOP-102.task.yaml")
    scenarios, warnings = build_scenarios(task)
    ids = [s.id for s in scenarios]
    assert ids[:3] == ["S-AC-1-1", "S-AC-2-1", "S-AC-3-1"]
    assert "S-AC-4-1" in ids and "S-AC-4-2" in ids  # AC-4 has two examples
    assert warnings == []
    assert all(s.source == "spec-example" and s.confirmed for s in scenarios)


def test_via_is_split_into_adapter_and_action():
    task = load_task(EXAMPLES / "SHOP-102.task.yaml")
    s = build_scenarios(task)[0][0]
    assert (s.adapter, s.action) == ("api", "quote_order")
    browser = next(s for s in build_scenarios(task)[0] if s.adapter == "browser")
    assert browser.action == "checkout_and_read_receipt"


def test_approved_scenarios_are_confirmed_and_numbered_after_examples():
    task = load_task(EXAMPLES / "SHOP-102.task.yaml")
    task["approved_scenarios"] = [{"criterion": "AC-1", "via": "api.quote_order", "input": {"subtotal": 80},
                                   "expect": {"shipping": 0.0}, "approved_by": "Anil"}]
    approved = [s for s in build_scenarios(task)[0] if s.source == "approved"]
    assert len(approved) == 1
    assert approved[0].id == "S-AC-1-2" and approved[0].confirmed is True


def test_ai_proposed_scenarios_are_unconfirmed_and_use_the_guess():
    task = load_task(EXAMPLES / "SHOP-102.task.yaml")
    ideas = [{"criterion": "AC-2", "input": {"subtotal": 74.995}, "expected_guess": {"shipping": 5.99}, "why": "x"}]
    scenarios, warnings = build_scenarios(task, ideas)
    ai = scenarios[-1]
    assert (ai.source, ai.confirmed, ai.criterion) == ("ai-proposed", False, "AC-2")
    assert ai.expect == {"shipping": 5.99} and ai.input == {"subtotal": 74.995}
    assert (ai.adapter, ai.action) == ("api", "quote_order")  # copied from AC-2's example
    assert warnings == []


def test_ai_idea_without_a_usable_criterion_is_skipped_with_a_warning():
    task = load_task(EXAMPLES / "SHOP-102.task.yaml")
    ideas = [{"criterion": None, "input": {}, "expected_guess": {"a": 1}, "why": "x"}]
    scenarios, warnings = build_scenarios(task, ideas)
    assert not any(s.source == "ai-proposed" for s in scenarios)
    assert len(warnings) == 1 and "skipped" in warnings[0]


# ---- safety ----

def test_safety_allows_listed_host():
    assert adapter_problem(ADAPTERS["api"]) is None


def test_safety_blocks_unlisted_host():
    config = {**ADAPTERS["api"], "base_url": "http://example.com"}
    assert "example.com" in adapter_problem(config)


def test_safety_blocks_non_http_address():
    assert "not an http(s) address" in adapter_problem({**ADAPTERS["api"], "base_url": "file:///etc/passwd"})


# ---- runner ----

def test_runner_pass(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99}), tmp_path)
    assert record["status"] == "pass" and record["mismatches"] == [] and record["error"] is None


def test_runner_fail_has_mismatches(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 0.0}), tmp_path)
    assert record["status"] == "fail"
    assert record["mismatches"] == [{"field": "shipping", "expected": 5.99, "actual": 0.0}]


def test_runner_only_compares_expected_fields(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99, "total": 1}), tmp_path)
    assert record["status"] == "pass"


def test_runner_driver_error_is_error_status_with_null_actual(tmp_path):
    [record] = run([scenario()], FakeDriver(error="HTTP 422: bad"), tmp_path)
    assert record["status"] == "error" and record["error"] == "HTTP 422: bad" and record["actual"] is None


def test_runner_driver_that_raises_does_not_stop_the_run(tmp_path):
    class Crashy(FakeDriver):
        def run(self, action, inputs):
            raise RuntimeError("boom")
    records = run([scenario("S-AC-1-1"), scenario("S-AC-1-2")], Crashy(), tmp_path)
    assert [r["status"] for r in records] == ["error", "error"]
    assert "boom" in records[0]["error"]


def test_runner_commit_mismatch_makes_every_scenario_error(tmp_path):
    records = run([scenario("S-AC-1-1"), scenario("S-AC-2-1")], FakeDriver({"shipping": 5.99}, commit="zzz9999"), tmp_path)
    assert [r["status"] for r in records] == ["error", "error"]
    assert records[0]["error"] == "commit mismatch: shop runs zzz9999, branch is a41c9e2. Restart the shop."


def test_runner_mismatch_never_calls_run(tmp_path):
    driver = FakeDriver({"shipping": 5.99}, commit="zzz9999")
    run([scenario()], driver, tmp_path)
    assert driver.calls == [] and driver.before_each_count == 0


def test_runner_commit_prefix_counts_as_same_commit(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99}, commit=HEAD + "1234567"), tmp_path)
    assert record["status"] == "pass"


def test_runner_unreachable_shop(tmp_path):
    [record] = run([scenario()], FakeDriver(commit=None), tmp_path)
    assert record["status"] == "error" and record["error"] == "shop not reachable"


def test_runner_safety_blocks_before_any_driver_is_built(tmp_path):
    built = []
    adapters = {"api": {**ADAPTERS["api"], "base_url": "http://example.com"}}
    [record] = run_scenarios([scenario()], adapters, "SHOP-102", HEAD, str(tmp_path / "out"),
                             driver_factory=lambda *a: built.append(a))
    assert record["status"] == "error" and record["error"].startswith("blocked by safety rule")
    assert built == []


def test_runner_unknown_adapter_is_error(tmp_path):
    [record] = run([scenario(adapter="browser")], FakeDriver(), tmp_path)
    assert record["status"] == "error" and "browser" in record["error"]


def test_runner_driver_that_cannot_be_built_is_error(tmp_path):
    def broken(*args):
        raise ImportError("playwright is not installed")
    [record] = run_scenarios([scenario()], ADAPTERS, "SHOP-102", HEAD, str(tmp_path / "out"), driver_factory=broken)
    assert record["status"] == "error" and "playwright" in record["error"]


def test_runner_calls_before_each_per_scenario_and_passes_scenario_id(tmp_path):
    driver = FakeDriver({"shipping": 5.99})
    run([scenario("S-AC-1-1"), scenario("S-AC-2-1")], driver, tmp_path)
    assert driver.before_each_count == 2
    assert driver.calls[0] == ("quote_order", {"subtotal": 50, "_scenario_id": "S-AC-1-1"})
    assert driver.calls[1][1]["_scenario_id"] == "S-AC-2-1"


def test_runner_one_driver_per_adapter_and_it_is_closed(tmp_path):
    made = []

    def factory(config, root, out):
        made.append(FakeDriver({"shipping": 5.99}))
        return made[-1]
    run_scenarios([scenario("S-AC-1-1"), scenario("S-AC-2-1")], ADAPTERS, "SHOP-102", HEAD,
                  str(tmp_path / "out"), driver_factory=factory)
    assert len(made) == 1 and made[0].closed


def test_runner_closes_driver_even_after_a_commit_mismatch(tmp_path):
    driver = FakeDriver(commit="zzz9999")
    run([scenario()], driver, tmp_path)
    assert driver.closed


def test_runner_ai_proposed_scenario_is_run_but_stays_unconfirmed(tmp_path):
    ai = scenario("S-AI-1", source="ai-proposed", confirmed=False)
    [record] = run([ai], FakeDriver({"shipping": 0.0}), tmp_path)
    assert record["source"] == "ai-proposed" and record["confirmed"] is False and record["status"] == "fail"


def test_runner_keeps_artifacts(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99}, artifacts={"screenshot": "out/screens/S-AC-1-1.png"}), tmp_path)
    assert record["artifacts"] == {"screenshot": "out/screens/S-AC-1-1.png"}


def test_runner_input_in_evidence_has_no_engine_fields(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99}), tmp_path)
    assert record["input"] == {"subtotal": 50}


def test_runner_run_id_format_and_commit(tmp_path):
    [record] = run([scenario()], FakeDriver({"shipping": 5.99}), tmp_path)
    assert re.fullmatch(r"r-\d{8}-\d{6}", record["run_id"])
    assert record["commit"] == HEAD and record["task"] == "SHOP-102"


def test_runner_writes_schema_valid_evidence_file_one_line_per_scenario(tmp_path):
    challenger = {"mode": "saved", "model": "claude (chat)", "prompt_hash": "9b1f"}
    run([scenario("S-AC-1-1"), scenario("S-AC-2-1", expect={"shipping": 0})], FakeDriver({"shipping": 5.99}),
        tmp_path, challenger=challenger, run_id="r-20261105-101403")
    lines = (tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    validator = Draft202012Validator(EVIDENCE_SCHEMA)
    for line in lines:
        record = json.loads(line)
        assert list(validator.iter_errors(record)) == []
        assert record["challenger"] == challenger and record["run_id"] == "r-20261105-101403"


def test_runner_error_records_are_also_schema_valid(tmp_path):
    run([scenario()], FakeDriver(commit="zzz9999"), tmp_path)
    record = json.loads((tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(EVIDENCE_SCHEMA).iter_errors(record)) == []


def test_runner_overwrites_evidence_file_each_run(tmp_path):
    run([scenario("S-AC-1-1"), scenario("S-AC-2-1")], FakeDriver({"shipping": 5.99}), tmp_path)
    run([scenario("S-AC-1-1")], FakeDriver({"shipping": 5.99}), tmp_path)
    assert len((tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_runner_creates_missing_out_folder(tmp_path):
    run([scenario()], FakeDriver({"shipping": 5.99}), tmp_path)
    assert (tmp_path / "out" / "evidence.jsonl").exists()


def test_runner_no_scenarios_writes_empty_file(tmp_path):
    assert run([], FakeDriver(), tmp_path) == []
    assert (tmp_path / "out" / "evidence.jsonl").read_text(encoding="utf-8") == ""
