# evidence_gate/drivers/base.py (written by Anil; T1 and T2 build to this)

from dataclasses import dataclass, field


@dataclass
class DriverResult:
    actual: dict                      # e.g. {"shipping": 0.0, "total": 75.0}
    error: str | None = None          # None = ran fine; text = could not run
    artifacts: dict = field(default_factory=dict)  # e.g. {"screenshot": "out/screens/S-AC-3-1.png"}


class Driver:
    def __init__(self, config: dict, repo_root: str, out_dir: str): ...

    def health_commit(self) -> str | None: ...   # commit reported by the running app

    def before_each(self) -> None: ...           # e.g. reset data

    def run(self, action: str, inputs: dict) -> DriverResult: ...

    def close(self) -> None: ...

# Drivers NEVER decide pass/fail. They only report what they saw. The runner compares.
