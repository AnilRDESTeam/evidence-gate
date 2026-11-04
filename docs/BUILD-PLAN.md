# Evidence Gate: build plan for Claude CLI

> **For Claude CLI.** Read this whole file first. Then do **only the step Anil names** (for example "do Step 4"). When that step is finished: run its tests, show the results, list the files you changed, and **stop**. Do not start the next step on your own.
>
> **For Anil.** Put this file at `evidence-gate\docs\BUILD-PLAN.md`. Open Claude CLI in the `evidence-gate` folder and start each session with:
> `Read docs/BUILD-PLAN.md. Do Step N.`
> Run the "Anil checks" yourself before you commit. Steps marked **ANIL ONLY** are not for Claude.

---

## 0. Ground rules (apply to every step)

### Folders
| What | Path |
|---|---|
| Gate (this repo) | `C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate` |
| Shop (the app being checked) | `C:\Users\anikumar\Desktop\HackathonProjects\shop-demo` |
| Python | the shop's venv: `shop-demo\.venv` (Gate installed with `pip install -e ..\evidence-gate`) |

Shell is **PowerShell on Windows**. Always give commands in PowerShell syntax and use the venv: `.venv\Scripts\python`, `.venv\Scripts\evidence-gate`.

### What Claude may and may not do
- **May:** write and change code in `evidence-gate\src\`, `evidence-gate\tests\`, `evidence-gate\eval\run_eval.py`, `evidence-gate\docs\`, and the adapter YAML files in `shop-demo\.evidence-gate\adapters\` when a step says so.
- **Must not:** change anything in `evidence-gate\contract\` (frozen v1.0) unless Anil says so. Must not change shop app code (`shop-demo\app\`). Must not change `shop-demo\requirements\*.task.yaml`, `shop-demo\.evidence-gate\policy.yaml`, or `eval\expected.csv`.
- **Must never** invent or compute expected values for task specs or the answer key. Those come from Anil.
- **Must never** read or use anything in `shop-demo\prompts\` (the coding-AI prompts). The Challenger must stay independent of them.
- Never commit secrets. No API keys are used in this build.

### How to work
- Keep code simple and commented for a reader new to Python.
- Write **pytest** tests for every rule and edge case. Run them and show the output.
- Small modules, one job each. No new dependencies beyond: `pyyaml`, `jsonschema`, `requests`, `jinja2`, `playwright`, plus `responses` and `pytest` for tests.
- Drivers **never** decide pass/fail. They only report what they saw. The runner compares.
- If something in this plan conflicts with `contract\RULES.md` or a schema, **stop and ask Anil**.

### Decisions already made
- **Challenger mode: `off` and `saved` only.** No live API mode. In saved mode, Anil pastes the prompt into Claude chat and saves the JSON answer as `out\challenge.json`.
- Adapters: **API (http)** and **browser** (Playwright). The CLI adapter is not in scope.
- Exit codes: `0` READY, `1` BLOCKED, `2` NEEDS DECISION, `3` GATE ERROR.

---

## 1. What the Gate does (one run)

`evidence-gate check --task requirements\SHOP-102.task.yaml` is run **from inside `shop-demo`**, with the shop server running on `http://127.0.0.1:8080`.

| # | Part | Module | What it does |
|---|---|---|---|
| 1 | Load | `loader.py` | Read the task spec, adapters (`.evidence-gate\adapters\*.yaml`) and `policy.yaml`; validate against `contract\*.schema.json` |
| 2 | Git | `gitinfo.py` | HEAD short commit; changed files vs base (`main`); dirty flag |
| 3 | Challenger | `challenger\` | off: questions from `open_questions`, coverage from `scope.paths`. saved: read `out\challenge.json` |
| 4 | Scenarios | `scenarios.py` | Each worked example → one confirmed scenario. Challenger ideas → unconfirmed scenarios |
| 5 | Run | `runner.py` + `drivers\` | Safety check → commit check → `before_each` → driver → compare → one evidence line |
| 6 | Label | `labeller.py` | One label per criterion (rules below) |
| 7 | Verdict | `verdict.py` | READY / BLOCKED / NEEDS DECISION / GATE ERROR |
| 8 | Route | `router.py` | back to developer / product owner decides / full / focused / light review |
| 9 | Report | `reporters\` | terminal, `out\report.json`, `out\report.md`, `out\report.html` |

### Fixed rules (must match `contract\RULES.md` exactly)

**Compare:** only the fields listed in `expect`. Numbers are equal within ±0.005. Text is equal after trimming spaces.

**Label rules** (per criterion, top to bottom, first match wins):

| # | Condition | Label |
|---|---|---|
| 1 | Criterion has a valid waiver (who, why, when) | Verified (waived) |
| 2 | No scenarios at all | Not verified: missing |
| 3 | Any confirmed scenario has status `fail` | Not verified: failed |
| 4 | Any confirmed scenario has status `error` | Not verified: could not run |
| 5 | An open question is linked to this criterion | Needs human review |
| 6 | At least one confirmed scenario passed on the current commit | Verified |
| 7 | Only unconfirmed (AI-proposed) scenarios exist | Not verified: unconfirmed |

Unconfirmed scenarios are run and shown as "AI suggestions", but never change a label from rules 3–6. Questions not linked to a criterion appear as extra "(new)" rows labelled Needs human review.

**Verdict rules** (in order):

| Condition | Verdict | Exit |
|---|---|---|
| Engine error or invalid input file | GATE ERROR | 3 |
| Any MUST criterion is Not verified | BLOCKED | 1 |
| Any Needs-human-review item is open | NEEDS DECISION | 2 |
| Otherwise | READY | 0 |

SHOULD criteria that are Not verified give a **warning** only (`should_failures: warn` in policy).

**Coverage rules:**
- Changed files = `git diff --name-only <base>...HEAD`, minus policy `ignore_paths`.
- A file is **covered** if the Challenger maps it to a criterion (saved mode), or, with the Challenger off, if it matches the task's `scope.paths`.
- A file is **high-risk** if it matches policy `high_risk_paths`.

**Route rules** (first match wins):

| # | When | Route |
|---|---|---|
| 1 | Verdict is BLOCKED | `back_to_developer` |
| 2 | Verdict is NEEDS DECISION | `product_owner_decides` |
| 3 | A changed file is high-risk | `full_review` |
| 4 | A changed file is uncovered | `focused_review` |
| 5 | Everything else | `light_review` |

Glob matching for paths: `**` matches any depth, `*` one segment. Use forward slashes internally.

### File formats

**Evidence record** (one JSON line per scenario in `out\evidence.jsonl`):
```json
{"run_id":"r-20261105-101403","task":"SHOP-102","criterion":"AC-3","scenario":"S-AC-3-1",
 "source":"spec-example","confirmed":true,"commit":"a41c9e2","adapter":"api","action":"quote_order",
 "input":{"subtotal":50.00},"expected":{"shipping":5.99},"actual":{"shipping":0.00},
 "status":"fail","error":null,"mismatches":[{"field":"shipping","expected":5.99,"actual":0.00}],
 "artifacts":{},"challenger":{"mode":"saved","model":"claude (chat)","prompt_hash":"9b1f..."},
 "ts":"2026-11-05T10:14:03Z"}
```
`status` is `pass`, `fail` or `error`. `source` is `spec-example`, `approved` or `ai-proposed`.

**Challenge file** (`out\challenge.json`, saved mode):
```json
{ "task": "SHOP-102", "commit": "a41c9e2", "model": "claude (chat)", "prompt_hash": "9b1f3c...",
  "coverage": [ { "file": "app/pricing/shipping.py", "criteria": ["AC-1","AC-2","AC-3"] } ],
  "uncovered": [ { "file": "app/catalog/products.py", "why": "Price changed; no criterion asks for this." } ],
  "questions": [ { "id": "Q-1", "criterion": null, "text": "Is the threshold checked before or after discounts?" } ],
  "proposed_scenarios": [ { "criterion": "AC-2", "input": { "subtotal": 74.995 },
    "expected_guess": { "shipping": 5.99 }, "why": "Rounding at the boundary" } ] }
```

**report.json fields:** `task, title, type, commit, base, run_id, timestamp, challenger {mode, model, prompt_hash}, criteria [ {id, priority, statement, label, reason, scenarios[]} ], questions[], ai_suggestions[], changed_files[], uncovered_files[], high_risk_files[], verdict, exit_code, route, route_reason, next_action, context {tests_passed, tests_total}, warnings[]`.

**Driver interface** (already in `src\evidence_gate\drivers\base.py`, do not change):
```python
@dataclass
class DriverResult:
    actual: dict
    error: str | None = None
    artifacts: dict = field(default_factory=dict)

class Driver:
    def __init__(self, config: dict, repo_root: str, out_dir: str): ...
    def health_commit(self) -> str | None: ...
    def before_each(self) -> None: ...
    def run(self, action: str, inputs: dict) -> DriverResult: ...
    def close(self) -> None: ...
```

---

## 2. Build order

| Step | What | Who | Priority |
|---|---|---|---|
| 1 | Finalise task specs | **ANIL ONLY** | Core |
| 2 | Loader + `validate` | Claude | Core |
| 3 | Git info | Claude | Core |
| 4 | http driver + `api.yaml` + `adapter-test` | Claude | Core |
| 5 | Scenarios, compare, safety, runner | Claude | Core |
| 6 | Labeller, verdict, router + rule tests | Claude | Core |
| 7 | Reporters (terminal, json, md) + `check` command | Claude | Core |
| M1 | Milestone 1 on baseline main | Anil runs | Core |
| 8 | Coding-AI branches E1, E2, E5 | **ANIL ONLY** | Core |
| 9 | Answer key `expected.csv` | **ANIL ONLY** | Core |
| M2 | Milestone 2: E1, E2, E5 | Anil runs | Core |
| 10 | Browser driver + `browser.yaml` | Claude | Must |
| 11 | Existing-tests context line | Claude | Must |
| 12 | Challenger (off + saved) + `challenge-prompt` | Claude | Must |
| 13 | SHOP-101 branches E3, E4 | **ANIL ONLY** | Must |
| 14 | HTML report | Claude | Must |
| 15 | Evaluation script + run | Claude writes, Anil runs | Must |
| 16 | README, ADOPTION, LIMITATIONS | Claude drafts, Anil checks | Must |

If a step from section 2 of the solo guide (validate) already works, Claude should check it against this plan, add any missing tests, and move on.

---

## 3. Steps

### Step 1. Finalise task specs (ANIL ONLY)
Claude: do nothing. Anil checks every expected value in `shop-demo\requirements\SHOP-101.task.yaml` and `SHOP-102.task.yaml` by hand against the business rules, then commits.

---

### Step 2. Loader + `validate`
**Build:** `src\evidence_gate\loader.py`, wire `evidence-gate validate --task <file>` in `cli.py`.
- Load YAML with `yaml.safe_load`. Validate task, every adapter in `.evidence-gate\adapters\`, and `.evidence-gate\policy.yaml` against the matching schema in `contract\` (jsonschema, draft 2020-12).
- Find `contract\` relative to the installed package (the repo root of evidence-gate), not the current folder.
- Extra checks the schema can't do: every MUST criterion has at least one example; every `via` names an adapter file and an action that exist.
- Error messages in plain words: file name, field path, what is wrong. Example: `requirements\SHOP-102.task.yaml: criteria[0]: 'priority' is required`.
- Any invalid file → print errors, exit code **3**.

**Tests:** valid examples from `contract\examples\` pass; missing required field; wrong type; MUST without example; `via` pointing to an unknown adapter/action; YAML syntax error (tab indentation).

**Anil checks** (in `shop-demo`, venv active):
```powershell
evidence-gate validate --task requirements\SHOP-102.task.yaml   # OK, exit 0
echo $LASTEXITCODE
```
Copy the spec to `out\bad.yaml`, delete one `priority:` line, validate it → clear message, exit 3.

---

### Step 3. Git info
**Build:** `src\evidence_gate\gitinfo.py`
- `head_commit(repo)` → `git rev-parse --short HEAD`
- `changed_files(repo, base="main")` → `git diff --name-only base...HEAD`, forward slashes
- `is_dirty(repo)` → `git status --porcelain` not empty
- `diff_text(repo, base)` and `file_text(repo, path)` (needed later by the Challenger prompt)
- Run git with `cwd=repo` (the shop folder). Clear GATE ERROR if git is missing or the folder is not a repo.

**Tests:** use a temporary git repo created in the test (tmp_path): commit, branch, change a file, check results.

**Anil checks:** on shop-demo `main`, changed files is empty and the commit matches `git rev-parse --short HEAD`.

---

### Step 4. API adapter: http driver, `api.yaml`, `adapter-test`
**Build:** `src\evidence_gate\drivers\http.py`, `tests\test_http_driver.py`, `adapter-test` command, and `shop-demo\.evidence-gate\adapters\api.yaml`.

Driver:
- `requests`, 5 s timeout. `request: "POST /api/cart/quote"` = method, space, path appended to `base_url`.
- Placeholders `"{name}"` in the body are filled from inputs. If a value is **exactly** `"{name}"`, keep the input's type (a number stays a number). Missing inputs come from the action's `defaults`.
- Before any request: host must be in `safety.allowed_hosts`, path must not match `safety.blocked_paths` (`*` wildcard), and count ≤ `max_requests_per_run`. Otherwise `DriverResult(actual={}, error="blocked by safety rule: ...")`.
- `read:` uses simple JSON paths like `$.shipping`, `$.items[0].qty` (small resolver, no library). Missing path → `None`.
- Network error or non-2xx → `DriverResult(actual={}, error="HTTP 422: <body>")`. **Never raise.**
- `health_commit()` → run `health.request`, return value at `commit_field`, `None` on failure.
- `before_each()` → send each `before_each` request.

`adapter-test`:
```
evidence-gate adapter-test --adapter <name> --action <action> --input-file <json>
```
Loads `.evidence-gate\adapters\<name>.yaml` from the current folder, builds the driver, calls `before_each` then `run`, prints `actual`, `error`, `artifacts` as pretty JSON. Exit 0 if no error, 3 otherwise.

`api.yaml`: start from the contract example (`contract\examples\`). Check the endpoint, body and response fields against `shop-demo\docs\API.md`. Do not change shop code.

**Tests:** with `responses`: happy path; number placeholder stays a number; defaults fill missing input; blocked host; blocked path; server down; non-2xx; missing JSON path → None.

**Anil checks** (shop running in a second terminal: `powershell -ExecutionPolicy Bypass -File scripts\run.ps1`):
```powershell
Set-Content out\in.json '{"subtotal": 50}'
evidence-gate adapter-test --adapter api --action quote_order --input-file out\in.json
```
| Try | Expect |
|---|---|
| subtotal 50 on baseline | shipping 0.0, error null (old $50 rule) |
| subtotal 75 | shipping 0.0, total 75.0 |
| shop stopped | clean error, no crash |
| `base_url` changed to `http://example.com` | "blocked by safety rule" (then change it back) |

---

### Step 5. Scenarios, compare, safety, runner
**Build:** `scenarios.py`, `compare.py`, `safety.py`, `runner.py`.
- Scenarios: each example of each criterion → `S-<AC>-<n>` (e.g. `S-AC-3-1`), `source: spec-example`, `confirmed: true`. `approved_scenarios` in the spec → `source: approved`, confirmed. Challenger `proposed_scenarios` → `source: ai-proposed`, `confirmed: false`, expected = `expected_guess`.
- `via: api.quote_order` → adapter `api`, action `quote_order`. Pick the driver class by the adapter's `type` (`http` or `browser`). One driver instance per adapter per run; call `close()` at the end.
- Commit check, once per adapter before running: `health_commit()` must equal git HEAD. If not, every scenario for that adapter gets `status: error`, `error: "commit mismatch: shop runs <x>, branch is <y>. Restart the shop."`. If health returns None: `error: "shop not reachable"`.
- Per scenario: `before_each()` → pass `_scenario_id` in inputs → `run()` → compare → write one evidence line.
- `compare(expected, actual)` returns `(status, mismatches)` using the compare rule. Driver error → `status: error`.
- `run_id` = `r-YYYYMMDD-HHMMSS`. Write to `<out>\evidence.jsonl` (create folder; overwrite per run).

**Tests:** with a **fake driver** (no shop needed): pass, fail with mismatches, ±0.005 tolerance, text trim, only `expect` fields compared, driver error → error status, commit mismatch → all error, ai-proposed scenarios are unconfirmed.

**Anil checks:** `pytest` green.

---

### Step 6. Labeller, verdict, router
**Build:** `labeller.py`, `verdict.py`, `router.py`, `coverage.py` (or inside router).
- Implement **exactly** the tables in section 1. First match wins.
- Coverage: `changed_files` minus `ignore_paths`; covered via Challenger coverage (saved) or `scope.paths` (off); high-risk via `high_risk_paths`.
- Waiver is valid only if it has `who`, `why` and `when`.
- `route_reason` in plain words, e.g. "AC-2, AC-3 failed", "app/data/products.json changed but no criterion covers it".
- `next_action` in plain words, e.g. "Fix the code so a $50.00 order pays $5.99 shipping, then rerun evidence-gate check."

**Tests:** **one test per row** of the label, verdict and route tables, plus first-match-wins tests:
- failed + passed confirmed scenarios → failed (rule 3 beats 6)
- only ai-proposed scenarios → unconfirmed, never Verified
- error + passed → could not run
- linked question + passed → Needs human review
- SHOULD failed only → READY with a warning
- high-risk + uncovered → `full_review` (route 3 beats 4)
- ignored files (tests/, requirements/) never make code uncovered

At least 20 tests. Name each test after its rule, e.g. `test_label_rule3_failed_beats_passed`.

**Anil checks:** read every test name; `pytest` green.

---

### Step 7. Reporters + `check`
**Build:** `reporters\terminal.py`, `reporters\json_report.py`, `reporters\md_report.py`, and the full `check` command:
```
evidence-gate check --task <file> [--base main] [--out out] [--challenger off|saved]
                    [--challenge-file out\challenge.json] [--no-tests]
```
- Runs: load → git → challenger → scenarios → run → label → verdict → route → report. Exit with the verdict's code. Any unexpected exception → print a short message, write what you can, exit 3.
- Terminal: verdict and route on top, then one line per criterion (label + short evidence like `$50.00 -> shipping 0.00 (expected 5.99)`), then questions, then next action.
- `report.md` in this shape (it's the PR comment):
```
Evidence Gate - SHOP-102 (updated requirement) - commit a41c9e2
Verdict: BLOCKED (2 MUST criteria not verified)    Route: back to developer

| Criterion | Label | Evidence |
|---|---|---|
| AC-1 | Verified | $75.00 -> shipping 0.00 (expected 0.00) |
| AC-3 | Not verified - failed | $50.00 -> shipping 0.00 (expected 5.99) |
| (new) | Needs human review | Is the threshold checked before or after discounts? |

Existing tests: 42/42 passed (context only).
Next action: ...
Full report: out/report.html
```

**Tests:** build a report from a hand-made result object; check JSON fields and md table rows.

---

### Milestone 1 (Anil runs)
Shop running on `main` (baseline still has the $50 rule):
```powershell
evidence-gate check --task requirements\SHOP-102.task.yaml
echo $LASTEXITCODE
```
**Expect:** AC-1 Verified · AC-2 failed · AC-3 failed · AC-4 could not run (no browser driver yet) · BLOCKED · back to developer · exit 1. Then `git tag m1-core`.

---

### Step 8. Coding-AI branches E1, E2, E5 (ANIL ONLY)
Claude: do nothing. Anil creates the branches in shop-demo with a separate Coding AI and records them in `eval\cases.csv`.

### Step 9. Answer key (ANIL ONLY)
Claude: do nothing and do not open `eval\expected.csv`. Anil writes it before running the Gate on any branch.

### Milestone 2 (Anil runs)
For each branch: `git checkout <branch>`, **restart the shop**, run `check`. E2 → BLOCKED; E1 → READY (light once AC-4 works); E5 → READY, focused review.

---

### Step 10. Browser driver + `browser.yaml`
**Build:** `drivers\browser.py`, `tests\test_browser_driver.py`, `shop-demo\.evidence-gate\adapters\browser.yaml` (from the contract example).
- Playwright **sync** API. Chromium headless; if config `channel` is set (e.g. `msedge`), use it.
- Steps: `goto`, `click`, `fill`, `select`, `wait_for`, `for_each` (loop over a list input; `{item}` is the current element). Placeholders from inputs and `defaults`.
- `read` kinds: `text` (trimmed) and `number` (strip `$` and `,`, float). Element not found within 2 s → its `missing` value if given, else `None`. **Not an error.**
- A failing step → `DriverResult(actual={}, error="step N failed: ...")`. **Never raise.**
- `screenshot: true` → save `<out>\screens\<scenario id>.png`, return the path in `artifacts`.
- `before_each` entries `{http: "POST /api/test/reset"}` → send with `requests`.
- Safety: host in `allowed_hosts` before every `goto`. `health_commit()` → `GET /api/health` → `commit`.
- Check `data-testid` names against the shop's HTML in `shop-demo\app\static\` (read only). If they differ, change `browser.yaml`, never the shop.
- Tests run only if `http://127.0.0.1:8080/api/health` answers (skip otherwise).

**Anil checks:**
```powershell
.venv\Scripts\python -m playwright install chromium   # if blocked: channel: msedge
Set-Content out\in.json '{"customer": "returning-customer-01", "add": ["MUG-001"]}'
evidence-gate adapter-test --adapter browser --action checkout_and_read_receipt --input-file out\in.json
```
Expect subtotal 12.0, discount 0.0, shipping 5.99, total 17.99, a screenshot in `out\screens\`. Shop stopped → clean error. Rerun Milestone 1: AC-4 is now **failed**, not "could not run".

---

### Step 11. Existing-tests context
**Build:** `context.py`. Run `context.tests_command` from `api.yaml` in the shop folder; parse `N passed` / `N failed` from pytest output; add `context {tests_passed, tests_total}` to report.json and a line `Existing tests: N/N passed (context only)` to terminal and md. `--no-tests` skips it. A failing test command is context only: it never changes the verdict.

---

### Step 12. Challenger (off + saved only)
**Build:** `challenger\__init__.py` (or `challenger.py`), `challenge-prompt` command.
- `evidence-gate challenge-prompt --task <file> [--base main]` prints the filled prompt from `challenger\prompt.md`: `{task_yaml}`, `{commit}`, `{diff}` (diff vs base, minus ignore_paths), `{files}` (full text of each changed non-ignored file). Never include anything from `prompts\`.
- `prompt_hash` = sha256 of the **template file** `challenger\prompt.md`.
- **off:** questions = spec `open_questions` (each may have `criterion`); coverage from `scope.paths`; no AI suggestions.
- **saved:** read `--challenge-file`, validate against `contract\challenge.schema.json`. `commit` must equal HEAD, else GATE ERROR: "challenge.json is for commit X, branch is at Y. Run challenge-prompt again." Use its `coverage`/`uncovered` for routing, its `questions` as Needs-human-review items, its `proposed_scenarios` as unconfirmed AI suggestions. Store `{mode, model, prompt_hash}` in report.json and every evidence line.
- Questions with a `criterion` link to that criterion (label rule 5). Questions with `criterion: null` become "(new)" items.

**Tests:** off mode uses scope.paths; saved happy path; wrong commit → exit 3; invalid JSON shape → exit 3; linked vs unlinked questions; AI suggestions never change labels.

**Anil checks** (on E5, shop restarted):
```powershell
evidence-gate challenge-prompt --task requirements\SHOP-102.task.yaml > out\challenge-prompt.md
# paste into Claude chat, save ONLY the JSON answer as out\challenge.json
evidence-gate check --task requirements\SHOP-102.task.yaml --challenger saved --challenge-file out\challenge.json
```
Expect: the products file listed as uncovered → `focused_review`.

---

### Step 13. SHOP-101 branches E3, E4 (ANIL ONLY)
Claude: do nothing. Expected after Anil builds them: E3 (saved) → NEEDS DECISION; E3 (off) → READY (known limitation); E4 → BLOCKED (AC-2 failed).

---

### Step 14. HTML report
**Build:** `reporters\html_report.py` + Jinja2 template inside the package. One self-contained `out\report.html`, inline CSS, built from report.json:
- Verdict banner: green READY, red BLOCKED, amber NEEDS DECISION, grey GATE ERROR.
- Route box with `route_reason` and `next_action`.
- Evidence table: criterion, priority, label, input, expected, actual, status. Mismatched fields highlighted.
- Screenshots as relative links/thumbnails (`screens\...png`).
- Questions list; AI suggestions (clearly marked "not used for labels"); changed / uncovered / high-risk files.
- Footer: existing-tests context line; AI disclosure (Challenger mode, model, prompt hash); commit, run id, time.
- Large readable fonts (it will be shown on a projector).

**Anil checks:** open `out\report.html` for E2 and E1.

---

### Step 15. Evaluation
**Build:** `eval\run_eval.py` (standard library + subprocess + urllib only).
- Args: `--mode off|saved` (default off), `--runs` (default 5), `--shop ..\shop-demo`.
- Read `eval\cases.csv` (`case_id,branch,task_file,commit,defect_origin,description`).
- For each case: `git checkout <branch>` in the shop; start the shop with `<shop>\.venv\Scripts\python -m uvicorn app.main:app --port 8080` (cwd = shop); wait for `/api/health` (max 30 s); run `evidence-gate check --task <task_file> --challenger <mode> --out out\<case>\run<N>` `<runs>` times (saved mode: use `out\challenges\<case>.json` if present); append to `eval\results.csv`: `case_id, run, verdict, route, AC-1..AC-n labels`; stop the shop.
- At the end, compare with `eval\expected.csv` and print: misses (expected BLOCKED, got READY), false alarms (expected READY, got BLOCKED), label stability per case (% of runs identical to the most common result), share routed to `light_review`.
- Always check out `main` and stop the shop at the end, even after an error (`try/finally`).

**Anil runs:** `python eval\run_eval.py --mode saved --runs 5`, then spot-checks every light-routed case by hand and records them in `eval\spotchecks.csv`.

---

### Step 16. Docs
**Draft** (Anil checks every command works):
- `README.md`: what it is (3 lines), install (both repos side by side), start the shop, run E2 and E1, read the report. Target: fresh clone to E2 result in under 15 minutes.
- `docs\ADOPTION.md`: add the Gate to a new repo in about an hour: copy `.evidence-gate\`, write `api.yaml`, pick a policy, write one task spec, run `validate` then `check`.
- `docs\LIMITATIONS.md` (Anil provides the facts): Challenger in saved mode (no live AI variation measured); small sample with planted/induced defects (list them); out of scope (security, performance, accessibility, visual layout); browser checks depend on stable `data-testid`s; expected values depend on spec quality; E3 needs saved mode to raise questions; every miss, false alarm and unstable label.

---

## 4. Definition of done
- [ ] E2 and E4 caught, naming the correct criterion
- [ ] E5 routed to focused (or full) review
- [ ] E3 raises a question to the product owner in saved mode
- [ ] 0 Verified labels without an executed, confirmed scenario
- [ ] 0 defective changes routed to light review
- [ ] Label stability ≥ 90% over 5 runs
- [ ] 0 false alarms on E1/E3 MUST criteria
- [ ] API and browser evidence both in the report
- [ ] ≥ 20 rule unit tests green
- [ ] Fresh clone to E2 result via README in < 15 minutes
