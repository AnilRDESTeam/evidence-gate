"""Browser driver: clicks through the app with Playwright and reports what the page showed.
It never decides pass/fail."""

import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from evidence_gate.drivers.base import Driver, DriverResult

HTTP_TIMEOUT_SECONDS = 5
READ_TIMEOUT_MS = 2000  # a missing element is normal (e.g. no discount row), so do not wait long
_WHOLE_PLACEHOLDER = re.compile(r"^\{(\w+)\}$")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class _Stop(Exception):
    """Internal only: carries the message for a DriverResult. Never leaves this module."""


def fill(template: str, values: dict) -> str:
    """Replace "{name}" placeholders in a selector, URL or text."""
    def lookup(match):
        name = match.group(1)
        if name not in values:
            raise _Stop(f"missing input '{name}' (no value given and no default)")
        return str(values[name])
    return _PLACEHOLDER.sub(lookup, template)


def parse_number(text: str) -> float | None:
    """'$1,234.50' -> 1234.5. None if the text is not a number."""
    try:
        return float(text.replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _first_line(err: Exception) -> str:
    # Playwright errors carry a long call log after the first line.
    return (str(err).strip().splitlines() or [type(err).__name__])[0]


class BrowserDriver(Driver):
    def __init__(self, config: dict, repo_root: str, out_dir: str):
        self.config = config
        self.repo_root = repo_root
        self.out_dir = out_dir
        self.base_url = config["base_url"].rstrip("/")
        self.safety = config.get("safety", {})
        self.timeout_ms = config.get("timeout_ms", 5000)
        # Started on the first real run, so the safety checks and error paths work without a browser.
        self._playwright = None
        self._browser = None
        # before_each cannot return an error, so a failure is kept and reported by the next run().
        self._before_error: str | None = None

    # ---- safety and plain HTTP (health, reset) ----

    def _check_host(self, url: str) -> None:
        host = urlparse(url).hostname
        if host not in self.safety.get("allowed_hosts", []):
            raise _Stop(f"blocked by safety rule: host '{host}' is not in allowed_hosts")

    def _send(self, request: str):
        method, _, path = request.strip().partition(" ")
        if not method or not path.strip():
            raise _Stop(f"bad request text '{request}' (expected 'METHOD /path')")
        url = self.base_url + path.strip()
        self._check_host(url)
        try:
            response = requests.request(method.upper(), url, timeout=HTTP_TIMEOUT_SECONDS)
        except requests.ConnectionError:
            raise _Stop(f"request failed: cannot connect to {urlparse(url).netloc} (is the app running?)")
        except requests.RequestException as err:
            raise _Stop(f"request failed: {err}")
        if not response.ok:
            raise _Stop(f"HTTP {response.status_code}: {response.text[:500]}")
        return response

    # ---- Driver interface ----

    def health_commit(self) -> str | None:
        try:
            value = self._send("GET /api/health").json().get("commit")
        except (_Stop, ValueError, AttributeError):
            return None
        return None if value is None else str(value)

    def before_each(self) -> None:
        self._before_error = None
        for step in self.config.get("before_each", []):
            try:
                self._send(step["http"])
            except _Stop as stop:
                self._before_error = f"before_each failed: {stop}"
                return

    def run(self, action: str, inputs: dict) -> DriverResult:
        if self._before_error:
            return DriverResult(actual={}, error=self._before_error)
        spec = self.config.get("actions", {}).get(action)
        if spec is None:
            return DriverResult(actual={}, error=f"unknown action '{action}' for this adapter")
        page = None
        try:
            self._check_host(self.base_url)  # before any browser is started
            # Inputs win over defaults; names starting with "_" (like _scenario_id) are for the engine.
            values = {**spec.get("defaults", {}), **{k: v for k, v in inputs.items() if not k.startswith("_")}}
            page = self._new_page()
            for number, step in enumerate(spec.get("steps", []), start=1):
                try:
                    self._step(page, step, values)
                except (PlaywrightError, _Stop) as err:
                    # Screenshot the failure too: it shows what the page looked like.
                    self._screenshot(page, spec, inputs)
                    message = err if isinstance(err, _Stop) else _first_line(err)
                    return DriverResult(actual={}, error=f"step {number} failed: {message}")
            actual = {name: self._read(page, read) for name, read in spec.get("read", {}).items()}
            artifacts = self._screenshot(page, spec, inputs)
            return DriverResult(actual=actual, error=None, artifacts=artifacts)
        except _Stop as stop:
            return DriverResult(actual={}, error=str(stop))
        except Exception as err:  # the contract says a driver never raises
            return DriverResult(actual={}, error=f"browser error: {_first_line(err)}")
        finally:
            if page is not None:
                try:
                    page.context.close()  # fresh page per scenario, so no state leaks between them
                except Exception:
                    pass

    def close(self) -> None:
        for closer in (self._browser and self._browser.close, self._playwright and self._playwright.stop):
            try:
                if closer:
                    closer()
            except Exception:
                pass
        self._browser = self._playwright = None

    # ---- browser plumbing ----

    def _new_page(self):
        if self._browser is None:
            try:
                self._playwright = sync_playwright().start()
                options = {"headless": self.config.get("headless", True)}
                if self.config.get("channel"):
                    options["channel"] = self.config["channel"]
                self._browser = self._playwright.chromium.launch(**options)
            except Exception as err:
                self.close()
                raise _Stop(
                    f"cannot start browser: {_first_line(err)} "
                    "(run `python -m playwright install chromium`, or set channel: msedge in the adapter)")
        page = self._browser.new_context().new_page()
        page.set_default_timeout(self.timeout_ms)
        return page

    def _step(self, page, step: dict, values: dict) -> None:
        if "goto" in step:
            url = self.base_url + fill(step["goto"], values)
            self._check_host(url)
            page.goto(url)
        elif "click" in step:
            page.click(fill(step["click"], values))
        elif "fill" in step:
            page.fill(fill(step["fill"], values), fill(str(step.get("value", "")), values))
        elif "select" in step:
            page.select_option(fill(step["select"], values), fill(str(step.get("value", "")), values))
        elif "wait_for" in step:
            page.wait_for_selector(fill(step["wait_for"], values))
        elif "for_each" in step:
            whole = _WHOLE_PLACEHOLDER.match(step["for_each"])
            items = values.get(whole.group(1)) if whole else None
            if not isinstance(items, list):
                raise _Stop(f"for_each needs a list input, got '{step['for_each']}'")
            for item in items:
                for inner in step.get("do", []):
                    self._step(page, inner, {**values, "item": item})
        else:
            raise _Stop(f"unknown step {list(step)}")

    def _read(self, page, read: dict):
        kind = "number" if "number" in read else "text" if "text" in read else None
        if kind is None:
            raise _Stop(f"read needs 'text' or 'number', got {list(read)}")
        locator = page.locator(read[kind]).first
        try:
            locator.wait_for(state="visible", timeout=READ_TIMEOUT_MS)
            text = locator.inner_text().strip()
        except PlaywrightTimeout:
            return read.get("missing")  # not found is a result, not an error
        return parse_number(text) if kind == "number" else text

    def _screenshot(self, page, spec: dict, inputs: dict) -> dict:
        if not spec.get("screenshot"):
            return {}
        path = Path(self.out_dir) / "screens" / f"{inputs.get('_scenario_id', 'scenario')}.png"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path))
        except Exception:
            return {}
        return {"screenshot": str(path)}
