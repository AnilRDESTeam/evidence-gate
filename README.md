# Evidence Gate

Evidence Gate checks AI-written code changes against a written contract (a task spec with worked examples).
It proves what it can with executed evidence and points human reviewers at what it cannot prove.
It decides how much human review a change needs. It never removes human review.

Status: skeleton + Contract v1.0. The CLI commands are stubs (exit code 3, "not implemented yet").

## Install (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
```

Bash equivalent:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

## Run the tests

```powershell
.venv\Scripts\python -m pytest
```

Bash: `.venv/bin/python -m pytest`

## Use it from shop-demo

```powershell
cd ..\shop-demo
.venv\Scripts\python -m pip install -e ..\evidence-gate
.venv\Scripts\evidence-gate --help
```

Exit codes: 0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR.

## Repo map

| Path | What it holds |
|------|---------------|
| `contract/` | Gate Contract v1.0: JSON Schemas, default policy, `RULES.md`, examples (frozen) |
| `src/evidence_gate/` | The engine. For now only `cli.py` stubs and the driver interface |
| `src/evidence_gate/drivers/` | `base.py` (the interface), `http.py` (T2), `browser.py` (T1) |
| `tests/` | Unit tests, including a check of every contract example |
| `eval/` | Evaluation files (added later) |
| `docs/` | `PLAN.md` (team handbook) and the build instructions |

## Contract change rule

`contract/` is frozen at version 1.0.0. Any change needs Anil's approval and a version bump.

## Git workflow

Branch, push, pull request. Never commit to `main` directly.

```powershell
git checkout main
git pull
git checkout -b feat/my-change
git add -A
git commit -m "feat: describe the change"
git push -u origin feat/my-change
```

Then open a pull request on GitHub. Anil merges.
