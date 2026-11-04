"""Tests for the browser driver. Most need no browser; the live ones run only if the shop answers."""

import pytest
import requests

from evidence_gate.drivers import build_driver
from evidence_gate.drivers.browser import BrowserDriver, _Stop, fill, parse_number

BASE = "http://127.0.0.1:8080"

CONFIG = {
    "type": "browser",
    "base_url": BASE,
    "headless": True,
    "channel": None,
    "timeout_ms": 5000,
    "before_each": [{"http": "POST /api/test/reset"}],
    "actions": {
        "checkout_and_read_receipt": {
            "defaults": {"customer": "returning-customer-01"},
            "steps": [
                {"goto": "/?customer={customer}#/"},
                {"for_each": "{add}", "do": [{"click": "[data-testid=add-to-cart-{item}]"}]},
                {"click": "[data-testid=nav-cart]"},
                {"wait_for": "[data-testid=cart-total]"},
                {"click": "[data-testid=place-order]"},
                {"wait_for": "[data-testid=receipt-total]"},
            ],
            "read": {
                "subtotal": {"number": "[data-testid=receipt-subtotal]"},
                "discount": {"number": "[data-testid=receipt-discount]", "missing": 0.0},
                "discount_label": {"text": "[data-testid=receipt-discount-label]"},
                "shipping": {"number": "[data-testid=receipt-shipping]"},
                "total": {"number": "[data-testid=receipt-total]"},
            },
            "screenshot": True,
        }
    },
    "safety": {"allowed_hosts": ["127.0.0.1", "localhost"]},
}


def make(**changes):
    return BrowserDriver({**CONFIG, **changes}, ".", "out")


# ---- no browser needed ----

def test_fill_replaces_placeholders():
    assert fill("[data-testid=add-to-cart-{item}]", {"item": "MUG-001"}) == "[data-testid=add-to-cart-MUG-001]"


def test_fill_missing_input_is_an_error():
    with pytest.raises(_Stop, match="missing input 'item'"):
        fill("{item}", {})


@pytest.mark.parametrize("text, expected", [("$1,234.50", 1234.5), (" $5.99 ", 5.99), ("0.00", 0.0), ("free", None)])
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_factory_builds_browser_driver():
    assert isinstance(build_driver(CONFIG, ".", "out"), BrowserDriver)


def test_blocked_host_is_refused_before_any_browser_starts():
    driver = make(base_url="http://example.com")
    result = driver.run("checkout_and_read_receipt", {"add": ["MUG-001"]})
    assert result.actual == {}
    assert "blocked by safety rule" in result.error
    assert driver._browser is None  # nothing was launched


def test_unknown_action_is_an_error_not_a_crash():
    result = make().run("nope", {})
    assert result.actual == {} and "unknown action 'nope'" in result.error


def test_shop_stopped_gives_clean_health_and_before_each_error(monkeypatch):
    def refuse(*args, **kwargs):
        raise requests.ConnectionError("refused")
    monkeypatch.setattr(requests, "request", refuse)
    driver = make()
    assert driver.health_commit() is None
    driver.before_each()
    result = driver.run("checkout_and_read_receipt", {"add": ["MUG-001"]})
    assert result.actual == {} and "before_each failed" in result.error and "cannot connect" in result.error


# ---- live: needs the shop on 127.0.0.1:8080 and an installed browser ----

def shop_is_up() -> bool:
    try:
        return requests.get(BASE + "/api/health", timeout=2).ok
    except requests.RequestException:
        return False


live = pytest.mark.skipif(not shop_is_up(), reason="shop is not running on 127.0.0.1:8080")


@pytest.fixture
def driver(tmp_path):
    d = BrowserDriver(CONFIG, ".", str(tmp_path))
    yield d
    d.close()


@live
def test_live_receipt_below_threshold_with_screenshot(driver, tmp_path):
    driver.before_each()
    result = driver.run("checkout_and_read_receipt", {"add": ["MUG-001"], "_scenario_id": "S-TEST-1"})
    if result.error and "cannot start browser" in result.error:
        pytest.skip(result.error)
    assert result.error is None
    # Mug only: $12.00, no discount, standard shipping. Same on every branch of the shop.
    assert result.actual == {"subtotal": 12.0, "discount": 0.0, "discount_label": None, "shipping": 5.99, "total": 17.99}
    assert (tmp_path / "screens" / "S-TEST-1.png").exists()
    assert result.artifacts["screenshot"].endswith("S-TEST-1.png")


@live
def test_live_missing_list_input_is_a_clean_error(driver):
    result = driver.run("checkout_and_read_receipt", {})  # no "add" list
    if result.error and "cannot start browser" in result.error:
        pytest.skip(result.error)
    assert result.actual == {} and "for_each needs a list input" in result.error


@live
def test_live_failing_step_is_reported_with_its_number(driver):
    config = {**CONFIG, "actions": {"bad": {"steps": [{"goto": "/"}, {"click": "[data-testid=no-such-button]"}]}}}
    bad = BrowserDriver({**config, "timeout_ms": 500}, ".", "out")
    try:
        result = bad.run("bad", {})
    finally:
        bad.close()
    if result.error and "cannot start browser" in result.error:
        pytest.skip(result.error)
    assert result.actual == {} and result.error.startswith("step 2 failed")


@live
def test_live_health_commit_is_returned(driver):
    assert driver.health_commit()
