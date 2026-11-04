"""Safety checks the runner makes before it touches an app.

The drivers also check every single request or page they open. This is the earlier, whole-adapter
check, so a bad adapter file stops the run before anything is sent.
"""

from urllib.parse import urlparse


def adapter_problem(config: dict) -> str | None:
    """Return the reason this adapter must not be used, or None if it is safe."""
    parsed = urlparse(config.get("base_url", ""))
    if parsed.scheme not in ("http", "https"):
        return f"blocked by safety rule: base_url '{config.get('base_url')}' is not an http(s) address"
    allowed = config.get("safety", {}).get("allowed_hosts", [])
    if parsed.hostname not in allowed:
        return f"blocked by safety rule: host '{parsed.hostname}' is not in allowed_hosts"
    return None
