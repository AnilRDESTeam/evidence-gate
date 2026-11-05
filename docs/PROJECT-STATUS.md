# Evidence Gate: project status and handoff

Last updated: 2026-11-05. Written so a new Claude session (or a person) can continue without the earlier conversation. Read the repo's `CLAUDE.md` first; its rules apply to everyone.

## 1. What this is

Evidence Gate checks AI-written code changes against a written spec. The spec has worked examples ("a $74.99 order pays $5.99 shipping") whose expected values a **person** wrote. The Gate runs every example on the real running app (API calls and browser clicks), for the exact git commit under review, then labels each criterion, gives a verdict (READY / BLOCKED / NEEDS DECISION / GATE ERROR) and a route (how much human review: light, focused, full, back to developer, product owner decides). It never removes human review. Built for a hackathon; the audience is judges.

Two repos, side by side in `C:\Users\anikumar\Desktop\HackathonProjects\`:

| Repo | Role | Remote |
|---|---|---|
| `evidence-gate` | The Gate (engine, contract, evaluation, docs) | `github.com/AnilRDESTeam/evidence-gate`, work is on `main` |
| `shop-demo` | The small shop the Gate checks (FastAPI + a web UI) | `github.com/AnilRDESTeam/shop-demo` |

The plan that drove the build is `docs/BUILD-PLAN.md` (steps 1 to 16, and section 4, the definition of done). The older handbook is `docs/PLAN.md`.

## 2. Where everything is

| Thing | Location |
|---|---|
| Frozen contract (schemas, `RULES.md`, examples) | `evidence-gate/contract/` (v1.0, do not edit without Anil) |
| Engine | `evidence-gate/src/evidence_gate/` (`check.py` is the `check` command; also `loader`, `scenarios`, `runner`, `compare`, `labeller`, `verdict`, `router`, `coverage`, `context`, `gitinfo`) |
| Drivers | `drivers/http.py` (API), `drivers/browser.py` (Playwright) |
| Challenger | `challenger/` (prompt template, saved-answer loader) |
| Reports | `reporters/`: terminal, markdown, json, `html_report.py`, `pdf_report.py`, `overview_report.py`, `templates/` |
| Evaluation | `evidence-gate/eval/`: `cases.csv`, `expected.csv` (answer key), `challenges/E1..E5.json`, `adapters/`, `run_eval.py`, `results.csv`, `spotchecks.csv`, `overview/` |
| One-command demo | `evidence-gate/scripts/demo.py` |
| Docs | `README.md`, `docs/ADOPTION.md`, `docs/DEMO.md`, `docs/LIMITATIONS.md`, this file |
| Tests | `evidence-gate/tests/` |
| Task specs | `shop-demo/requirements/SHOP-101.task.yaml`, `SHOP-102.task.yaml` |
| Shop adapters | `shop-demo/.evidence-gate/adapters/api.yaml`, `browser.yaml` (also copied in `evidence-gate/eval/adapters/`) |

## 3. The reports (where to look)

All in `evidence-gate/eval/overview/` and committed:

- `overview-off.pdf` / `overview-saved.pdf`: **every case and its status in one document** (headline numbers, a table of the five cases against the key, then one section per case with screenshots). HTML copies beside them.
- `cases-off/E1.pdf` to `E5.pdf` and `cases-saved/E1.pdf` to `E5.pdf`: one PDF per test case.
- A single `check` run writes `out/report.html`, `report.pdf`, `report.md`, `report.json`, `evidence.jsonl` (`--no-pdf` skips the PDF).

## 4. The five evaluation cases

Each is a branch in `shop-demo` (pushed to origin), all cut from the original baseline. **Never merge them into `main`**: E2/E4 hold planted defects, the Gate diffs against `main`, and each saved Challenger answer is bound to its branch tip's commit hash.

| Case | Branch (commit) | What it is | Key says |
|---|---|---|---|
| E1 | `eval/shop-102-correct` (12a4eb8) | Correct: free-shipping threshold $50 to $75 | READY, light review |
| E2 | `eval/shop-102-old-rule` (b7d0762) | Planted: old $50 rule kept, tests edited (57/58 of the shop's tests pass, one left failing) | BLOCKED |
| E3 | `eval/shop-101-correct` (c32d975) | Correct: 10% welcome discount (written by a separate coding agent) | NEEDS DECISION in saved mode (spec leaves questions open) |
| E4 | `eval/shop-101-missing-negative` (3964fcb) | Planted: returning customers get the discount too; tests edited (58/58 pass) | BLOCKED |
| E5 | `eval/shop-102-scope-creep` (643a2d8) | Threshold change plus an unrequested NOTE-001 price change | READY, focused review |

## 5. Results (5 cases x 5 runs, each mode)

| | Challenger off | Challenger saved |
|---|---|---|
| Defects missed | 0 of 2 | 0 of 2 |
| Defects routed to light review | 0 | 0 |
| Correct changes wrongly BLOCKED | 0 | 0 |
| Correct changes held up by questions | 0 of 2 | **2 of 2 (E1, E5)** |
| Identical across 5 runs | 100% | 100% |
| Runs routed to light review | 20% (E1) | 0% |

- E2 and E4 were caught and blocked in both modes, naming the right criteria.
- E3 with the Challenger off gives READY (focused review): the known limitation, since only the Challenger raises the open questions.
- **The saved Challenger over-asks** (6 to 9 questions on every change, including correct ones), so two correct changes got NEEDS DECISION. This is the weakest result and is not tuned away on purpose.
- The 100% stability only proves the engine is deterministic: Challenger answers were saved, so live-AI variation was **not** measured.
- `run_eval.py` exits 1 in saved mode because of the held-up changes. That is intentional, not a crash.
- Full detail and honest caveats: `docs/LIMITATIONS.md`.

## 6. Definition of done (section 4 of the plan)

| Item | Status |
|---|---|
| E2 and E4 caught, naming the right criterion | Met |
| E5 routed to focused or full review | Met with the Challenger off only (saved: NEEDS DECISION) |
| E3 raises a question (saved mode) | Met |
| 0 Verified labels without an executed, confirmed scenario | Met (31 Verified labels audited, 0 without proof) |
| 0 defective changes routed to light review | Met |
| Label stability >= 90% | Met (100%, with the caveat above) |
| 0 false alarms on E1/E3 MUST criteria | Met with the Challenger off only |
| API and browser evidence both in the report | Met (171 API and 50 browser evidence lines, all browser lines with a screenshot) |
| >= 20 rule unit tests | Met (54 in `tests/test_rules.py`) |
| Fresh clone to E2 result in < 15 min | Met in a cold test: 246 s total (clone 5 s, setup 173 s, demo 68 s). Measured before the PDF feature was added, so a repeat will be somewhat slower. Windows + Python 3.15 only, Chromium already cached |

## 7. What was built when

- Steps 2 to 7 (loader, git info, http driver core, scenarios/runner, labeller/verdict/router, reporters and `check`) predate this handoff's session.
- Done in the latest working session: the shop `api.yaml` and `browser.yaml` (steps 4 and 10), the browser driver, existing-tests context (step 11), the Challenger saved mode and `challenge-prompt` (step 12), the E3/E4 branches (step 13), the HTML report (14), the evaluation runner (15), README/ADOPTION/LIMITATIONS/DEMO (16), the one-command demo, a cold test from fresh clones, PDF reports and the all-cases overview.
- Milestones 1 and 2 were run and matched the plan's expectations.
- Step 8/9 (branches, answer key) were Anil's. The answer key `eval/expected.csv` was written before the Gate was run and has never been edited to fit results.

## 8. How to run

```powershell
python scripts/demo.py setup      # first time only (installs both repos' packages, test branches, Chromium)
python scripts/demo.py            # E2 + E4 + E1, opens overview PDF and a PDF per case
python scripts/demo.py --all      # all five; add --mode saved for the Challenger
python eval/run_eval.py --mode off --runs 5      # full evaluation, off
python eval/run_eval.py --mode saved --runs 5    # full evaluation, saved Challenger answers
python eval/run_eval.py --compare-only --mode off   # rebuild the summary/overview from results.csv
.venv\Scripts\python -m pytest -q
```

By hand: start the shop on the branch (`uvicorn app.main:app --host 127.0.0.1 --port 8080`, restart after every branch switch), copy `eval\adapters\*.yaml` to `shop-demo\.evidence-gate\adapters\`, then `evidence-gate check --task requirements\SHOP-102.task.yaml` from `shop-demo`.

## 9. Open items

1. **E1 spot check by a person**: `eval/spotchecks.csv` has E1 marked PENDING (the plan requires every light-routed case to be confirmed by hand).
2. **Anil checks every command in the docs** (Step 16 asks for it).
3. **`git tag m1-core`** (Milestone 1) was never created.
4. **Local `shop-demo` `main` has diverged from `origin/main`** (it holds the pre-squash commit; origin has the squashed PR plus the adapters commit `3ce9b60`). Content is identical. Sync with `git checkout main && git reset --hard origin/main` when convenient.
5. **Decision for Anil**: leave the Challenger over-asking as a documented limitation (current), or tighten its prompt and run a second round (record it as round 2, do not overwrite round 1).
6. **Cosmetic**: reports for branches checked in by the evaluation show "working tree has uncommitted changes" (the runner lays adapter files over each branch). Harmless but odd in a handout; could be suppressed for evaluation runs.
7. **Optional**: repeat the cold test now that PDFs were added, for fresh timing numbers.
8. A pull request or merge on the `eval/*` branches should be closed, not merged (see section 4).

## 10. Decisions and gotchas worth knowing

- **Adapters come from the Gate, not the branch.** `eval/adapters/` is laid over every branch by `run_eval.py` (and restored afterwards), so a coding AI's branch cannot control how it is checked. E1's branch carries its own `api.yaml`; ours wins during a run.
- **Independence of the AI parts.** Every Challenger answer in `eval/challenges/` came from a fresh agent that saw only the prompt (not the key or the results). E3's code came from a separate coding agent that saw only the developer prompt. E2 and E4's plants were written by the assistant, not by a coding AI trying to be correct. All of it is the same model family as the engine's author, which `LIMITATIONS.md` states.
- **Python 3.15 on this machine**: PyYAML has no wheel, so the engine uses `ruamel.yaml`; `uvicorn[standard]` (shop requirements) fails there, so `demo.py setup` retries without the extras. The shop's own `.venv` is Python 3.14.8.
- **The shop's `pytest.ini` already has `-q`**: do not add another in `context.tests_command` (two hide the summary line the Gate parses). The Gate warns, it does not guess.
- **Commit check**: the Gate refuses evidence from a shop running a different commit than the branch ("commit mismatch"). Restart the shop after switching branch; `run_eval.py` does this itself.
- **Reports per mode**: `out/<case>/<mode>/run<N>/`, so a saved-mode run never overwrites a Challenger-off one.
- **Questions outrank review routes.** An open question gives NEEDS DECISION before any focused or full review. That is why E5 in saved mode is not routed to focused review.
- **Windows line endings**: files are CRLF. Byte-level edits must account for it.
- **Tooling quirks seen in the earlier session** (relevant if a Claude session edits via shell): doubled backslashes in shell commands can be collapsed to one, which silently turned `\n` escapes into real newlines in generated Python. Use the Edit/Write tools for code, or build a backslash with `chr(92)`. The environment also blocks `rm -rf` with variable-expanded paths and blanket process kills (`taskkill /IM python.exe`).
- **Repo rules** (from `CLAUDE.md`): `contract/` is frozen; labels/verdicts/routes only from `RULES.md` with one unit test per rule row; drivers never decide pass/fail; expected values only from task specs; no secrets, no `out/`, no `.venv` in git; run `pytest` before committing; the README says branch + pull request, but Anil explicitly approved pushing to `main` for this work.
- Organisation policy: AI use must comply with Hyland's AI Use Requirements (linked in the managed settings).

## 11. Test status

Historical result from 2026-11-04: **287 passed, 4 skipped**, excluding `tests/test_check.py` and `tests/test_http_driver.py`. The four skips required a running shop; 54 passing tests covered the rule rows.

Verification on 2026-11-05 used fresh local copies on Windows with Python 3.12.14, `evidence-gate` commit `65b7436`, and `shop-demo` commit `3ce9b60`. The declared development dependencies, including `responses` and PyYAML, installed successfully on this Python version.

| Test scope | Result |
|---|---|
| Previously pending `tests/test_http_driver.py` and `tests/test_check.py` | **47 passed** |
| Full Evidence Gate suite, before the test browser and shop were available | **328 passed, 10 skipped** |
| `tests/test_pdf_report.py`, `tests/test_overview_report.py`, and `tests/test_challenger.py`, with Playwright Chromium available | **48 passed, 0 skipped** |
| `tests/test_browser_driver.py`, with Chromium and the local shop running | **14 passed, 0 skipped**, including the four live checks |

These runs overlap, so their counts must not be added together. The full suite was not rerun with both the browser and shop available. The report and browser runs completed without failures or skips. The shop health response reported `mode: test`, commit `3ce9b60`, and `dirty: false`.

This verification did not rerun the five-case evaluation or complete the independent human E1 spot check. The evaluation results in section 5 and the remaining open items are unchanged.
