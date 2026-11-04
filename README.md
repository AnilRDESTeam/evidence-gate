# Evidence Gate

AI now writes a lot of code, and a person still has to decide if it is safe to merge. Evidence Gate gives that person **proof instead of a diff to read**.
A written spec contains worked examples ("a $74.99 order pays $5.99 shipping"). The Gate runs every example against the real, running app, for the exact commit being reviewed, and reports what it proved and what it could not.
It decides **how much human review a change needs**. It never removes human review.

## See it work (about 5 minutes from a fresh clone: roughly 3 minutes of setup, then about a minute for the demo)

You need Python 3.11+, git, and the `shop-demo` folder next to this one (`shop-demo` is the small web shop the Gate checks).

```powershell
python scripts/demo.py setup     # first time only: installs packages and a test browser
python scripts/demo.py           # runs two BAD changes and a GOOD one, then opens the reports
```

Three AI-written changes are checked, each on its own branch of the shop:

| Change | Verdict | What it means |
|---|---|---|
| E2: the AI kept the old $50 free-shipping rule and edited the tests to match | **BLOCKED** | A written example failed: a $74.99 order shipped free. Back to the developer. |
| E4: the AI gave the new-customer discount to returning customers too, and edited the tests to match | **BLOCKED** | A written example failed. **All 58 of the shop's own tests pass**, which is why a green test run is not proof. |
| E1: correct change | **READY**, light review | Every written example passed on this commit. A person skims the evidence and approves. |

`python scripts/demo.py --all` runs all five cases. `python scripts/demo.py --mode saved` also uses a second AI (the "Challenger") that asks questions and flags changed files nobody asked for.
Presenting this? See [docs/DEMO.md](docs/DEMO.md) for a script.

## How a decision is made

```
task spec (examples written by a person)
   -> scenarios -> drivers run them on the live app (API and browser) -> evidence
   -> compare with the spec's expected values -> label each criterion
   -> verdict -> route (how much human review)  -> report.html / report.md / report.json
```

| Label | Meaning |
|---|---|
| Verified | An executed example passed on this exact commit |
| Not verified: failed / could not run / missing | An example failed, could not run (server down, wrong commit), or none exists |
| Needs human review | An open question is linked to the criterion |

| Verdict | Exit code | Route |
|---|---|---|
| READY | 0 | light review, or focused review if changed code is covered by no criterion, or full review if it touches a high-risk path |
| BLOCKED | 1 | back to the developer |
| NEEDS DECISION | 2 | the product owner answers the open question |
| GATE ERROR | 3 | the Gate itself could not finish (bad input file, git problem) |

The rules are fixed in [contract/RULES.md](contract/RULES.md), first match wins, and are covered by one unit test per rule row. Three trust rules sit under everything:

1. **Expected values come from the written spec, never from the code or an AI.**
2. **"Verified" needs executed proof on the exact commit.** If the running app is on a different commit than the branch, the result is "could not run".
3. **AI proposes, rules decide.** AI suggestions are shown, marked "not used for labels", and can never change a label.

## Run it by hand

Open two terminals. Terminal 1 starts the shop on the branch you want to check (restart it every time you switch branch):

```powershell
cd ..\shop-demo
git checkout eval/shop-102-old-rule
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Terminal 2 runs the Gate from the shop folder. The adapter files (how to talk to this shop) live in `eval\adapters`; copy them in once:

```powershell
cd ..\shop-demo
copy ..\evidence-gate\eval\adapters\*.yaml .evidence-gate\adapters\
..\evidence-gate\.venv\Scripts\evidence-gate check --task requirements\SHOP-102.task.yaml
echo $LASTEXITCODE
```

It prints the verdict and writes `out\report.html` (the readable report), `out\report.md` (paste into a pull request), `out\report.json` and `out\evidence.jsonl` (every scenario that ran).

Other commands:

```powershell
evidence-gate validate --task requirements\SHOP-102.task.yaml          # check a spec and its adapters
evidence-gate adapter-test --adapter api --action quote_order --input-file in.json   # try one action by hand
evidence-gate challenge-prompt --task requirements\SHOP-102.task.yaml  # the prompt to give the Challenger AI
evidence-gate check --task ... --challenger saved --challenge-file challenge.json    # use its saved answer
evidence-gate check --task ... --no-tests                              # skip the shop's own tests
```

## The evaluation

`eval/` holds five test changes (E1 to E5): correct changes, planted defects, and an unrequested extra change, each with an answer key written **before** the Gate was run.

```powershell
python eval/run_eval.py --mode off --runs 5       # Challenger off
python eval/run_eval.py --mode saved --runs 5     # saved Challenger answers from eval/challenges/
```

It prints misses, false alarms, label stability and the share routed to light review. Results go to `eval/results.csv`. What the Gate cannot do is written down in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Use it on another project

[docs/ADOPTION.md](docs/ADOPTION.md) shows how to add the Gate to a new repository in about an hour.

## Repo map

| Path | What it holds |
|---|---|
| `contract/` | Gate Contract v1.0: JSON Schemas, default policy, `RULES.md`, examples (frozen) |
| `src/evidence_gate/` | The engine: loader, scenarios, runner, compare, labeller, verdict, router, coverage, reporters |
| `src/evidence_gate/drivers/` | `http.py` (API checks) and `browser.py` (receipt checks with Playwright) |
| `src/evidence_gate/challenger/` | The Challenger prompt template and the saved-answer loader |
| `src/evidence_gate/reporters/` | Terminal, markdown, JSON and HTML reports |
| `eval/` | The five cases, the answer key, saved Challenger answers, adapters, `run_eval.py`, results |
| `scripts/` | `demo.py` (the one-command demo) and Challenger hand-test helpers |
| `tests/` | Unit tests, including one per rule row and a check of every contract example |
| `docs/` | Demo script, adoption guide, limitations, and the plans |

## Install and test

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest
```

(`python scripts/demo.py setup` does the install for you, for both folders.) Tests that need a running shop skip themselves if none is up.

## Contract change rule

`contract/` is frozen at version 1.0. Any change needs Anil's approval and a version bump.

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
