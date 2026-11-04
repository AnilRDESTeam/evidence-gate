"""Run scenarios through the drivers, compare with the compare rule, and write the evidence file."""

import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_gate.compare import compare
from evidence_gate.drivers import build_driver
from evidence_gate.safety import adapter_problem

NO_CHALLENGER = {"mode": "off", "model": None, "prompt_hash": None}


def _same_commit(shop: str, branch: str) -> bool:
    # git short hashes can differ in length between machines, so compare as prefixes.
    return shop.startswith(branch) or branch.startswith(shop)


def _prepare(name: str, adapters: dict, head: str, repo_root: str, out_dir: str, driver_factory):
    """Safety check, build the driver, commit check. Returns (driver, None) or (None, reason it cannot run)."""
    config = adapters.get(name)
    if config is None:
        return None, f"adapter '{name}' was not found in .evidence-gate/adapters"
    problem = adapter_problem(config)
    if problem:
        return None, problem
    try:
        driver = driver_factory(config, repo_root, out_dir)
    except Exception as err:  # e.g. Playwright not installed; must not stop the other adapters
        return None, f"cannot build the '{config.get('type')}' driver: {err}"
    shop_commit = driver.health_commit()
    if shop_commit is None:
        driver.close()
        return None, "shop not reachable"
    if not _same_commit(shop_commit, head):
        driver.close()
        return None, f"commit mismatch: shop runs {shop_commit}, branch is {head}. Restart the shop."
    return driver, None


def run_scenarios(scenarios, adapters: dict, task_id: str, head_commit: str, out_dir: str, repo_root: str = ".",
                  challenger: dict | None = None, run_id: str | None = None, driver_factory=build_driver) -> list[dict]:
    """Run every scenario, write <out_dir>/evidence.jsonl (overwritten each run), return the records."""
    now = datetime.now(timezone.utc)
    run_id = run_id or now.strftime("r-%Y%m%d-%H%M%S")
    challenger = challenger or NO_CHALLENGER
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    prepared: dict[str, tuple] = {}  # one driver (or one failure reason) per adapter per run
    records = []
    try:
        with open(out / "evidence.jsonl", "w", encoding="utf-8") as evidence_file:
            for s in scenarios:
                if s.adapter not in prepared:
                    prepared[s.adapter] = _prepare(s.adapter, adapters, head_commit, repo_root, str(out), driver_factory)
                driver, blocked = prepared[s.adapter]

                actual, error, artifacts, mismatches = None, blocked, {}, []
                if driver is not None:
                    try:
                        driver.before_each()
                        # _scenario_id lets a driver name its screenshot after the scenario.
                        result = driver.run(s.action, {**s.input, "_scenario_id": s.id})
                        error, artifacts = result.error, result.artifacts
                        if error is None:
                            actual = result.actual
                    except Exception as err:  # drivers should never raise, but one bad scenario must not stop the run
                        error = f"driver crashed: {err}"

                if error is not None:
                    status = "error"
                else:
                    status, mismatches = compare(s.expect, actual)

                record = {
                    "run_id": run_id, "task": task_id, "criterion": s.criterion, "scenario": s.id,
                    "source": s.source, "confirmed": s.confirmed, "commit": head_commit,
                    "adapter": s.adapter, "action": s.action, "input": s.input, "expected": s.expect,
                    "actual": actual, "status": status, "error": error, "mismatches": mismatches,
                    "artifacts": artifacts, "challenger": challenger,
                    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                records.append(record)
                evidence_file.write(json.dumps(record) + "\n")
    finally:
        for driver, _ in prepared.values():
            if driver is not None:
                driver.close()
    return records
