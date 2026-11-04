"""Drivers talk to the app under test. build_driver picks the right one from the adapter's `type`."""


def build_driver(config: dict, repo_root: str, out_dir: str):
    kind = config["type"]
    if kind == "http":
        from evidence_gate.drivers.http import HttpDriver
        return HttpDriver(config, repo_root, out_dir)
    if kind == "browser":
        # Imported only when needed, so the API checks work without Playwright installed.
        from evidence_gate.drivers.browser import BrowserDriver
        return BrowserDriver(config, repo_root, out_dir)
    raise ValueError(f"unknown adapter type '{kind}'")
