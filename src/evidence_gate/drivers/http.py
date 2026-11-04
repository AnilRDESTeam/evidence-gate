"""HTTP driver: calls the app's API and reports what it saw. It never decides pass/fail."""

import fnmatch
import re
from urllib.parse import urlparse

import requests

from evidence_gate.drivers.base import Driver, DriverResult

TIMEOUT_SECONDS = 5
_WHOLE_PLACEHOLDER = re.compile(r"^\{(\w+)\}$")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class _Stop(Exception):
    """Internal only: carries the message for a DriverResult. Never leaves this module."""


def resolve_path(path: str, data):
    """Tiny JSON path reader: $.shipping, $.items[0].qty. Returns None if anything is missing."""
    if not isinstance(path, str) or not path.startswith("$"):
        return None
    current = data
    # Tokens are either a key name or an [index].
    for key, index in re.findall(r"\.([^.\[\]]+)|\[(\d+)\]", path[1:]):
        try:
            current = current[key] if key else current[int(index)]
        except (KeyError, IndexError, TypeError):
            return None
    return current


def fill(template, values: dict):
    """Replace "{name}" placeholders. A value that is exactly "{name}" keeps the input's type."""
    if isinstance(template, dict):
        return {k: fill(v, values) for k, v in template.items()}
    if isinstance(template, list):
        return [fill(v, values) for v in template]
    if not isinstance(template, str):
        return template

    def lookup(name):
        if name not in values:
            raise _Stop(f"missing input '{name}' (no value given and no default)")
        return values[name]

    whole = _WHOLE_PLACEHOLDER.match(template)
    if whole:
        return lookup(whole.group(1))  # keep number as number
    return _PLACEHOLDER.sub(lambda m: str(lookup(m.group(1))), template)


class HttpDriver(Driver):
    def __init__(self, config: dict, repo_root: str, out_dir: str):
        self.config = config
        self.repo_root = repo_root
        self.out_dir = out_dir
        self.base_url = config["base_url"].rstrip("/")
        self.safety = config.get("safety", {})
        self.session = requests.Session()
        self.request_count = 0
        # before_each cannot return an error, so a failure is kept and reported by the next run().
        self._before_error: str | None = None

    # ---- sending ----

    def _check_safety(self, url: str) -> None:
        """Raise _Stop if this call is not allowed. Checked before EVERY request."""
        parsed = urlparse(url)
        if parsed.hostname not in self.safety.get("allowed_hosts", []):
            raise _Stop(f"blocked by safety rule: host '{parsed.hostname}' is not in allowed_hosts")
        for pattern in self.safety.get("blocked_paths", []):
            if fnmatch.fnmatch(parsed.path, pattern):
                raise _Stop(f"blocked by safety rule: path '{parsed.path}' matches blocked path '{pattern}'")
        limit = self.safety.get("max_requests_per_run")
        if limit is not None and self.request_count >= limit:
            raise _Stop(f"blocked by safety rule: more than max_requests_per_run ({limit}) requests")

    def _send(self, request: str, body=None):
        """Send "METHOD /path". Returns the response for any 2xx; raises _Stop otherwise."""
        method, _, path = request.strip().partition(" ")
        if not method or not path.strip():
            raise _Stop(f"bad request text '{request}' (expected 'METHOD /path')")
        url = self.base_url + path.strip()
        self._check_safety(url)
        self.request_count += 1
        try:
            response = self.session.request(method.upper(), url, json=body, timeout=TIMEOUT_SECONDS)
        except requests.ConnectionError:
            # The raw message is a long urllib3 dump; this is what a person needs to know.
            raise _Stop(f"request failed: cannot connect to {urlparse(url).netloc} (is the app running?)")
        except requests.RequestException as err:
            raise _Stop(f"request failed: {err}")
        if not response.ok:
            raise _Stop(f"HTTP {response.status_code}: {response.text[:500]}")
        return response

    @staticmethod
    def _json(response):
        try:
            return response.json()
        except ValueError:
            raise _Stop("response was not JSON")

    # ---- Driver interface ----

    def health_commit(self) -> str | None:
        health = self.config.get("health")
        if not health:
            return None
        try:
            value = resolve_path(health["commit_field"], self._json(self._send(health["request"])))
        except _Stop:
            return None
        return None if value is None else str(value)

    def before_each(self) -> None:
        self._before_error = None
        for step in self.config.get("before_each", []):
            try:
                self._send(step["request"])
            except _Stop as stop:
                self._before_error = f"before_each failed: {stop}"
                return

    def run(self, action: str, inputs: dict) -> DriverResult:
        if self._before_error:
            return DriverResult(actual={}, error=self._before_error)
        spec = self.config.get("actions", {}).get(action)
        if spec is None:
            return DriverResult(actual={}, error=f"unknown action '{action}' for this adapter")
        try:
            # Inputs win over defaults; names starting with "_" (like _scenario_id) are for the engine.
            values = {**spec.get("defaults", {}), **{k: v for k, v in inputs.items() if not k.startswith("_")}}
            body = fill(spec["body"], values) if "body" in spec else None
            data = self._json(self._send(spec["request"], body))
        except _Stop as stop:
            return DriverResult(actual={}, error=str(stop))
        return DriverResult(actual={name: resolve_path(path, data) for name, path in spec["read"].items()})

    def close(self) -> None:
        self.session.close()
