"""Tests for the HTTP driver. HTTP is faked with `responses`, so no shop needs to be running."""

import json
import subprocess
import sys

import pytest
import requests
import responses

from evidence_gate.drivers import build_driver
from evidence_gate.drivers.http import HttpDriver, resolve_path

BASE = "http://127.0.0.1:8080"

CONFIG = {
    "type": "http",
    "base_url": BASE,
    "health": {"request": "GET /api/health", "commit_field": "$.commit"},
    "before_each": [{"request": "POST /api/test/reset"}],
    "actions": {
        "quote_order": {
            "request": "POST /api/cart/quote",
            "defaults": {"customer": "returning-customer-01"},
            "body": {"customer_id": "{customer}",
                     "items": [{"sku": "TEST-SKU", "qty": 1, "unit_price": "{subtotal}"}]},
            "read": {"shipping": "$.shipping", "total": "$.total", "first_qty": "$.items[0].qty",
                     "missing": "$.no.such.field"},
        }
    },
    "safety": {"allowed_hosts": ["127.0.0.1", "localhost"], "blocked_paths": ["/api/payments/*"],
               "max_requests_per_run": 200},
}


def make(**changes):
    config = {**CONFIG, **changes}
    return HttpDriver(config, ".", "out")


def sent_json(call):
    return json.loads(call.request.body)


@responses.activate
def test_happy_path_reads_fields():
    responses.post(f"{BASE}/api/cart/quote", json={"shipping": 5.99, "total": 55.99, "items": [{"qty": 1}]})
    result = make().run("quote_order", {"subtotal": 50})
    assert result.error is None
    assert result.actual["shipping"] == 5.99
    assert result.actual["total"] == 55.99
    assert result.actual["first_qty"] == 1


@responses.activate
def test_number_placeholder_stays_a_number():
    responses.post(f"{BASE}/api/cart/quote", json={})
    make().run("quote_order", {"subtotal": 74.99})
    unit_price = sent_json(responses.calls[0])["items"][0]["unit_price"]
    assert unit_price == 74.99 and isinstance(unit_price, float)


@responses.activate
def test_defaults_fill_missing_input_and_input_wins():
    responses.post(f"{BASE}/api/cart/quote", json={})
    driver = make()
    driver.run("quote_order", {"subtotal": 1})
    driver.run("quote_order", {"subtotal": 1, "customer": "guest"})
    assert sent_json(responses.calls[0])["customer_id"] == "returning-customer-01"
    assert sent_json(responses.calls[1])["customer_id"] == "guest"


@responses.activate
def test_engine_inputs_starting_with_underscore_are_not_sent():
    responses.post(f"{BASE}/api/cart/quote", json={})
    make().run("quote_order", {"subtotal": 1, "_scenario_id": "S-AC-1-1"})
    assert "_scenario_id" not in json.dumps(sent_json(responses.calls[0]))


@responses.activate
def test_text_placeholder_inside_a_longer_string_becomes_text():
    config = {**CONFIG, "actions": {"a": {"request": "POST /x", "body": {"note": "order for {customer}"},
                                          "read": {}}}}
    responses.post(f"{BASE}/x", json={})
    HttpDriver(config, ".", "out").run("a", {"customer": "guest"})
    assert sent_json(responses.calls[0]) == {"note": "order for guest"}


@responses.activate
def test_missing_input_without_default_is_an_error_not_a_crash():
    result = make().run("quote_order", {})  # no subtotal anywhere
    assert result.actual == {}
    assert "missing input 'subtotal'" in result.error
    assert len(responses.calls) == 0


def test_blocked_host_sends_nothing():
    with responses.RequestsMock() as mock:  # fails the test if any request is made
        driver = make(base_url="http://example.com")
        result = driver.run("quote_order", {"subtotal": 50})
    assert result.actual == {}
    assert result.error.startswith("blocked by safety rule")
    assert "example.com" in result.error
    assert len(mock.calls) == 0


def test_blocked_path_sends_nothing():
    config = {**CONFIG, "actions": {"pay": {"request": "POST /api/payments/charge", "read": {}}}}
    with responses.RequestsMock() as mock:
        result = HttpDriver(config, ".", "out").run("pay", {})
    assert result.error.startswith("blocked by safety rule")
    assert "/api/payments/charge" in result.error
    assert len(mock.calls) == 0


@responses.activate
def test_request_limit_is_enforced():
    responses.post(f"{BASE}/api/cart/quote", json={})
    driver = make(safety={**CONFIG["safety"], "max_requests_per_run": 2})
    assert driver.run("quote_order", {"subtotal": 1}).error is None
    assert driver.run("quote_order", {"subtotal": 1}).error is None
    third = driver.run("quote_order", {"subtotal": 1})
    assert "max_requests_per_run" in third.error
    assert len(responses.calls) == 2


@responses.activate
def test_server_down_gives_clean_error():
    responses.post(f"{BASE}/api/cart/quote", body=requests.ConnectionError("refused"))
    result = make().run("quote_order", {"subtotal": 50})
    assert result.actual == {}
    assert result.error == "request failed: cannot connect to 127.0.0.1:8080 (is the app running?)"


@responses.activate
def test_timeout_gives_clean_error():
    responses.post(f"{BASE}/api/cart/quote", body=requests.Timeout("too slow"))
    result = make().run("quote_order", {"subtotal": 50})
    assert "request failed" in result.error


@responses.activate
def test_non_2xx_reports_status_and_body():
    responses.post(f"{BASE}/api/cart/quote", status=422, body='{"error":{"code":"VALIDATION_ERROR"}}')
    result = make().run("quote_order", {"subtotal": 50})
    assert result.actual == {}
    assert result.error.startswith("HTTP 422: ")
    assert "VALIDATION_ERROR" in result.error


@responses.activate
def test_response_that_is_not_json_is_an_error():
    responses.post(f"{BASE}/api/cart/quote", body="<html>oops</html>")
    result = make().run("quote_order", {"subtotal": 50})
    assert "not JSON" in result.error


@responses.activate
def test_missing_json_path_is_none_not_error():
    responses.post(f"{BASE}/api/cart/quote", json={"shipping": 5.99})
    result = make().run("quote_order", {"subtotal": 50})
    assert result.error is None
    assert result.actual["missing"] is None
    assert result.actual["total"] is None


def test_unknown_action_is_an_error():
    result = make().run("no_such_action", {})
    assert "unknown action" in result.error


@responses.activate
def test_health_commit_returns_value():
    responses.get(f"{BASE}/api/health", json={"commit": "a41c9e2"})
    assert make().health_commit() == "a41c9e2"


@responses.activate
def test_health_commit_none_when_server_down_or_field_missing():
    responses.get(f"{BASE}/api/health", body=requests.ConnectionError("refused"))
    assert make().health_commit() is None
    responses.replace(responses.GET, f"{BASE}/api/health", json={"status": "ok"})
    assert make().health_commit() is None


@responses.activate
def test_before_each_sends_every_request():
    responses.post(f"{BASE}/api/test/reset", json={"status": "reset"})
    make().before_each()
    assert len(responses.calls) == 1


@responses.activate
def test_failed_before_each_is_reported_by_the_next_run():
    responses.post(f"{BASE}/api/test/reset", status=403, body="FORBIDDEN_IN_MODE")
    driver = make()
    driver.before_each()  # must not raise
    result = driver.run("quote_order", {"subtotal": 50})
    assert result.actual == {}
    assert "before_each failed" in result.error and "403" in result.error
    assert len(responses.calls) == 1  # the quote was not sent on unreset data


@pytest.mark.parametrize("path, expected", [
    ("$.shipping", 5.99),
    ("$.items[1].qty", 2),
    ("$.a.b", "deep"),
    ("$.items[5].qty", None),   # index out of range
    ("$.shipping.nope", None),  # walking into a number
    ("shipping", None),         # not a JSON path
])
def test_resolve_path(path, expected):
    data = {"shipping": 5.99, "items": [{"qty": 1}, {"qty": 2}], "a": {"b": "deep"}}
    assert resolve_path(path, data) == expected


def test_build_driver_picks_http():
    assert isinstance(build_driver(CONFIG, ".", "out"), HttpDriver)


# ---- adapter-test command ----

def run_adapter_test(cwd, *args):
    return subprocess.run([sys.executable, "-m", "evidence_gate.cli", "adapter-test", *args],
                          cwd=cwd, capture_output=True, text=True)


def test_adapter_test_unknown_adapter_exits_3(tmp_path):
    (tmp_path / "in.json").write_text("{}", encoding="utf-8")
    result = run_adapter_test(tmp_path, "--adapter", "nope", "--action", "x", "--input-file", "in.json")
    assert result.returncode == 3
    assert "File not found" in result.stderr


def test_adapter_test_blocked_host_prints_error_and_exits_3(tmp_path):
    # Real run of the CLI; the host is blocked before any request, so no shop is needed.
    adapters = tmp_path / ".evidence-gate" / "adapters"
    adapters.mkdir(parents=True)
    (adapters / "api.yaml").write_text(
        "type: http\nbase_url: http://example.com\n"
        "actions:\n  ping:\n    request: GET /x\n    read: { a: \"$.a\" }\n"
        "safety:\n  allowed_hosts: [127.0.0.1]\n", encoding="utf-8")
    (tmp_path / "in.json").write_text("{}", encoding="utf-8")
    result = run_adapter_test(tmp_path, "--adapter", "api", "--action", "ping", "--input-file", "in.json")
    assert result.returncode == 3
    out = json.loads(result.stdout)
    assert out["actual"] == {} and out["error"].startswith("blocked by safety rule")
