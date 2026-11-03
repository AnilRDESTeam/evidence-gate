# Evidence Gate

Evidence Gate checks AI-written code changes against a written contract (a task spec with worked examples).
It proves what it can with executed evidence and points human reviewers at what it cannot prove.
It decides how much human review a change needs. It never removes human review.

Status: skeleton + Contract v1.0. `validate` works; the other CLI commands are still stubs (exit code 3, "not implemented yet").

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

Check a task spec (and the policy and adapters it uses) against the contract:

```powershell
.venv\Scripts\evidence-gate validate --task contract\examples\SHOP-102.task.yaml
```

It prints `OK ...` (exit 0, with WARN lines for files not added yet) or `GATE ERROR: <file>` with one line per problem (exit 3).

## Challenger hand-test

The Challenger prompt template is `src/evidence_gate/challenger/prompt.md`. To try it by hand in Claude chat, follow `docs/challenger/README.md`.

Exit codes: 0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR.

## Repo map

| Path | What it holds |
|------|---------------|
| `contract/` | Gate Contract v1.0: JSON Schemas, default policy, `RULES.md`, examples (frozen) |
| `src/evidence_gate/` | The engine. For now `cli.py` (`validate` built, rest stubs), `loader.py` and the driver interface |
| `src/evidence_gate/drivers/` | `base.py` (the interface), `http.py` (T2), `browser.py` (T1) |
| `scripts/` | Hand-test helpers for the Challenger prompt |
| `tests/` | Unit tests, including a check of every contract example |
| `eval/` | Evaluation CSVs: `cases.csv` and `expected.csv` (header only for now); see `eval/README.md` |
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
