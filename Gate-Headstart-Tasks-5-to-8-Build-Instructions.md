# Evidence Gate: Head-start Tasks 5–8 — One-Shot Build Instructions (for Claude CLI)

> **Covers Role Guide (Anil) Part 1 tasks:** 5 gate-config PR (shop-demo), 6 eval stubs, 7 Challenger prep, 8 loader + `validate` (stretch).
> **Not covered (human only):** the API-key request and team comms (drafts are in PART A).
> **Target:** everything pushed and PRs open by **Tue 3 Nov 2026, 18:00 IST**.
> **Owner:** Anil. **Builder:** Claude via Claude CLI.
> **Already done:** Tasks 1–4 (shop-demo `baseline-v1.0`, repos private, evidence-gate skeleton, `contract-v1.0`).

---

## PART A — For Anil (human)

### A1. Run the build

1. Both repos side by side (as before):
   ```
   C:\Users\anikumar\Desktop\HackathonProjects\
   ├── shop-demo\
   └── evidence-gate\
   ```
2. Put this file in `evidence-gate\`. Make sure both repos are on `main`, clean, and pulled (`git status`, `git pull`).
3. Find T2's GitHub username (the person who will review the gate-config PR). They must already be a collaborator on `shop-demo`.
4. Start Claude CLI in `evidence-gate` and let it also see `shop-demo`:
   ```powershell
   cd C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate
   claude --add-dir C:\Users\anikumar\Desktop\HackathonProjects\shop-demo
   ```
5. Paste:
   ```text
   Read Gate-Headstart-Tasks-5-to-8-Build-Instructions.md completely before doing anything. Then execute
   PART B end to end, phase by phase, running the checks after each phase.
   evidence-gate folder: C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate (remote https://github.com/AnilRDESTeam/evidence-gate.git)
   shop-demo folder: C:\Users\anikumar\Desktop\HackathonProjects\shop-demo (remote https://github.com/AnilRDESTeam/shop-demo.git)
   T2's GitHub username: <PASTE T2 USERNAME>
   Stop and ask me only for the items listed in "B11. When to stop and ask".
   At the end, give me the final report described in B9.
   ```
6. Approve commands as asked. Expected time: 1.5–3 hours.
7. Then do **PART C**.

### A2. Things only you can do (start these now, while Claude builds)

**Task 7 — API key request (send today).** Use your internal process for Hyland-approved AI access. Draft text (edit names and channel to match how your organisation handles it):

> Subject: Request: approved API access for AI-assist step in hackathon prototype (Evidence Gate)
>
> Hi, for the Product & Technology Hackathon (4–5 Nov) our prototype "Evidence Gate" has one optional step where an AI model reviews a code diff against a written spec (it never decides pass/fail). We would like an approved endpoint, API key and model ID for a Claude model, for use from a Python script on my laptop. Data sent: task specs and diffs from a fake demo shop app only. No customer, production or personal data. We follow Hyland's AI Use Requirements. If this is not possible before 4 Nov, we will run the step manually in the approved Claude chat instead. Could you tell me who approves this, and how long it takes? Thanks, Anil

**Task 9 — Comms.** Draft message for the team chat:

> Team: contract v1.0 is frozen (tag `contract-v1.0` in evidence-gate). Setup for tomorrow morning: clone both repos side by side, then in shop-demo run `.venv\Scripts\python -m pip install -e ..\evidence-gate` and `.venv\Scripts\evidence-gate --help`. Read the Handbook first, then your role guide (attached). Hackathon hours are assumed 09:30–18:30 IST; I'll confirm with the organisers. 20-minute rule: stuck for 20 minutes → post in this chat with a screenshot and the full error.

Also: share the Team Handbook and the T1/T2 guides, create the team chat, and confirm hackathon hours with the organisers.

---

## PART B — Instructions for the AI builder

### B1. Mission

Do four jobs, in this order. Two repos are involved: **evidence-gate** (jobs 6, 7, 8 — all on one branch `feat/headstart`, one PR) and **shop-demo** (job 5 — branch `gate-config`, one PR).

| Phase | Role Guide task | Repo |
|---|---|---|
| 1 | Task 6: eval CSV stubs | evidence-gate |
| 2 | Task 7: Challenger prompt template + hand-test kit | evidence-gate |
| 3 | Task 8: loader + `evidence-gate validate` | evidence-gate |
| 4 | Push evidence-gate branch, open PR (do not merge) | evidence-gate |
| 5 | Task 5: gate-config PR | shop-demo |

### B2. Ground rules

1. Beginner-level team: simple, readable code, short comments explaining *why*. Modules under ~150 lines.
2. Windows 11 + PowerShell first.
3. **`contract/` is frozen (v1.0). Do not edit anything inside it.** If a contract problem blocks you, stop and ask (B11).
4. **Do not implement** anything beyond B3–B8: no runner, compare, labeller, verdict, router, reporters, live Challenger, drivers' real code. Do not touch `drivers/http.py` or `drivers/browser.py` (T2 and T1 own them).
5. **Never decide expected values yourself.** The task specs are copied verbatim from `contract/examples/`.
6. Local only: no network calls except `git`. No keys, no secrets. Never paste or store an API key.
7. Run tests after every phase. If something fails 3 times in a row, stop and report.
8. Commit after each phase (`feat:`, `test:`, `docs:`, `chore:`). **Never commit directly to `main`.** Never force-push. Never merge a PR. Never change repo visibility.
9. Never commit `.venv`, `out/`, or keys.

### B3. Phase 0 — Prep (both repos)

- In `evidence-gate`: `git checkout main ; git pull`; confirm clean; run `.venv\Scripts\python -m pytest` (must be green; this is the starting point). If `.venv` is missing: `python -m venv .venv` then `.venv\Scripts\python -m pip install -e .[dev]`.
- In `shop-demo`: `git checkout main ; git pull`; confirm clean and the tag `baseline-v1.0` exists.
- In `evidence-gate`: `git checkout -b feat/headstart`.

### B4. Phase 1 — Task 6: eval stubs

Create two files in `evidence-gate/eval/`, **header line only** (exactly one line each, ending with a newline, no data rows, LF line endings):

`eval/cases.csv`
```
case_id,branch,task_file,commit,defect_origin,description
```

`eval/expected.csv`
```
case_id,branch,task,AC-1,AC-2,AC-3,AC-4,question_expected,verdict,route,notes
```

Rules: T1 fills `cases.csv` and T2 fills `expected.csv` later. **Do not add any example rows**, because the answer key must be written independently by T2. Keep `eval/.gitkeep`. Add a 5-line `eval/README.md`: who owns each file; allowed values of `defect_origin` = `none, natural, planted, induced`; label codes for expected.csv = `verified, failed, missing, could_not_run, unconfirmed, needs_human_review, n/a`; "expected.csv is written before the Gate is run; never edited to match results".

Check: each CSV has exactly 1 line and the exact header. Commit: `chore: add eval CSV stubs`.

### B5. Phase 2 — Task 7: Challenger prep

**Goal:** the prompt template exists, and Anil can test it by hand in Claude chat and check the JSON answer against `contract/challenge.schema.json`. No model calls from code.

Create:

```
src/evidence_gate/challenger/__init__.py        # empty (module is built later, step 7)
src/evidence_gate/challenger/prompt.md          # the template, EXACT text below
.gitattributes                                  # keeps prompt.md LF so its hash is stable on Windows
scripts/fill_challenge_prompt.py                # fills the template for hand-testing
scripts/validate_json.py                        # checks a JSON file against a contract schema
docs/challenger/README.md                       # how to hand-test (steps below)
docs/challenger/sample/task.yaml                # copy of contract/examples/SHOP-102.task.yaml
docs/challenger/sample/change.diff              # SAMPLE diff (see below)
docs/challenger/sample/changed_files.txt        # SAMPLE full text of changed files
tests/test_challenger_prompt.py
```

**`prompt.md` — write exactly this text, nothing else (the engine hashes this file as `prompt_hash`; do not "improve" the wording):**

```
You are a strict reviewer of an AI-written code change. You did NOT write it.
You get: (1) a task spec with numbered criteria, (2) the git diff, (3) the changed files' full text.
Do NOT judge whether the code is correct. Do NOT invent expected values for criteria.
Return ONLY JSON matching this shape:
{ "task": "...", "commit": "...", "coverage": [{"file": "...", "criteria": ["AC-1"]}],
  "uncovered": [{"file": "...", "why": "..."}],
  "questions": [{"id": "Q-1", "criterion": "AC-2 or null", "text": "..."}],
  "proposed_scenarios": [{"criterion": "AC-1", "input": {...}, "expected_guess": {...}, "why": "..."}] }
Rules: map each changed non-test file to the criteria it serves; list files no criterion explains as uncovered;
ask a question for any behaviour the spec does not define (edge cases, ordering of rules, user types);
propose at most 5 boundary/negative scenarios.
--- TASK SPEC ---
{task_yaml}
--- DIFF (commit {commit}) ---
{diff}
--- CHANGED FILES ---
{files}
```

**`.gitattributes`:** `src/evidence_gate/challenger/prompt.md text eol=lf` and `*.csv text eol=lf`.

**`scripts/fill_challenge_prompt.py`** (Python stdlib only). Arguments: `--task PATH --diff PATH --files PATH --commit SHA [--out PATH]` (default out `out/challenge-test-prompt.md`). It reads the template, normalises `\r\n` to `\n`, and replaces **only** the four exact tokens `{task_yaml}`, `{commit}`, `{diff}`, `{files}` using `str.replace` (never `str.format`; the template contains other braces). It writes the file and prints the sha256 of the **template** (normalised, UTF-8) as `prompt_hash`. The coding prompt must never be an input; there is no argument for it.

**`scripts/validate_json.py`**: `python scripts/validate_json.py <schema.json> <file.json>`. Validates with `jsonschema.Draft202012Validator`; prints `OK` (exit 0) or one line per error with the field path (exit 1). Be tolerant of a chat answer wrapped in ```json fences: strip a leading/trailing fence before parsing.

**Sample kit.** `change.diff` is a made-up, clearly labelled `SAMPLE` unified diff for commit `a41c9e2` that (a) changes `FREE_SHIPPING_THRESHOLD` in `app/config.py` from `50.00` to `75.00`, (b) updates `app/pricing/shipping.py` accordingly, and (c) **also** changes the NOTE-001 price in `app/data/products.json` from `8.50` to `9.50` (scope creep, which no SHOP-102 criterion covers). `changed_files.txt` contains the three files' resulting text, each preceded by a `=== path ===` line. Keep the sample small (under ~60 lines). It is fake data, no secrets.

**`docs/challenger/README.md`** — steps for Anil (plain English):
1. `.venv\Scripts\python scripts\fill_challenge_prompt.py --task docs\challenger\sample\task.yaml --diff docs\challenger\sample\change.diff --files docs\challenger\sample\changed_files.txt --commit a41c9e2`
2. Open `out\challenge-test-prompt.md`, copy everything, paste it into Claude chat (the approved tool).
3. Copy **only the JSON** answer into `out\challenge.json`.
4. `.venv\Scripts\python scripts\validate_json.py contract\challenge.schema.json out\challenge.json` → expect `OK`.
5. Sanity check by eye: `app/data/products.json` appears under `uncovered`; `coverage` maps `app/pricing/shipping.py` to AC ids; at least one question; at most 5 proposed scenarios; no invented criteria.
6. Rules: never give the Challenger the coding prompt; never put keys in files or chat.

**`tests/test_challenger_prompt.py`:** (a) `prompt.md` contains each of `{task_yaml}`, `{commit}`, `{diff}`, `{files}` exactly once; (b) running the fill script on the sample kit leaves none of those four tokens in the output, and the output contains the task id `SHOP-102` and `a41c9e2`; (c) the printed hash equals `hashlib.sha256` of the normalised template; (d) `validate_json.py` accepts `contract/examples/challenge.example.json` and rejects a copy with a 6th proposed scenario.

Check: `pytest` green; run the fill script once and show the first 15 lines of its output. Commit: `feat: Challenger prompt template and hand-test kit`.

### B6. Phase 3 — Task 8: loader + `validate`

Build exactly this, using the schemas in `contract/` (do not modify them).

**`src/evidence_gate/loader.py`**
- `class GateInputError(Exception)` with a `.problems: list[str]` of friendly messages.
- `find_contract_dir() -> Path`: env `EVIDENCE_GATE_CONTRACT_DIR` if set; else `<repo root>/contract` found by walking up from this file. If not found, raise `GateInputError` ("Cannot find the contract folder…").
- `load_yaml(path) -> dict`: `yaml.safe_load`; missing file → `GateInputError("File not found: <path>")`; YAML syntax error → message includes file and line number; top level must be a mapping.
- `load_task(path)`, `load_adapter(path)`, `load_policy(path)`: load YAML, validate against `task.schema.json`, `adapter.schema.json`, `policy.schema.json` with `Draft202012Validator`. Collect **all** errors (not just the first), sorted by path. Each problem reads like `requirements\SHOP-102.task.yaml: criteria[1].examples: required for a MUST criterion` (file, then field path written as `criteria[1].examples[0].expect`, then a short message). Use the JSON-Schema error message; where it is noisy (`if/then`, `anyOf`), add a one-line plain-English hint.
- `check_task_consistency(task: dict) -> list[str]` (plain Python, errors): criterion ids unique; every `criterion` in `open_questions`, `waivers`, `approved_scenarios` refers to an existing criterion id (null allowed for open_questions).
- `find_repo_root(task_path) -> Path`: nearest ancestor of the task file containing a `.evidence-gate/` folder; otherwise the current directory.

**`validate` command in `cli.py`** (replace the stub; the other three commands stay stubs):
1. Load the task file (schema + consistency). 
2. Repo root: if `<root>/.evidence-gate/policy.yaml` exists, validate it; if absent, print a `WARN`.
3. For each distinct adapter name in the `via` fields (`api` or `browser`): if `<root>/.evidence-gate/adapters/<name>.yaml` exists, validate it **and** check every `via` action exists in its `actions` (a missing action is an **error**). If the adapter file does not exist yet, print `WARN adapter '<name>' not found at <path> (T1/T2 add it)`; this is **not** an error.
4. Success: print `OK  <task path>  (<id>, <type>, <n> criteria, <m> examples)` plus any WARN lines; exit **0**.
5. Any problem: print `GATE ERROR: <file>` then one indented `- <problem>` line per problem, to stderr; exit **3** (rule V1: invalid input file = GATE ERROR).

**Tests** (`tests/test_loader.py`; use `tmp_path` and subprocess/`main()` for the CLI): valid SHOP-102 and SHOP-101 pass (exit 0); missing file → 3 with "File not found"; YAML syntax error → 3 with a line number; MUST criterion without examples → 3 and the message names `criteria[0].examples` (or the right index); `updated` without `previous_rule` → 3; duplicate `AC-1` → 3; open_question pointing to `AC-9` → 3; adapter present but action missing → 3; adapter absent → exit 0 with a WARN; invalid policy → 3. Update `tests/test_cli_stub.py`: `validate` is no longer a stub; the other three still exit 3 with "not implemented yet".

**Also in this phase:** add `responses` to the `dev` extra in `pyproject.toml` (T2's http-driver test needs it); re-run `pip install -e .[dev]`.

Check: `pytest` green; run `.venv\Scripts\evidence-gate validate --task contract\examples\SHOP-102.task.yaml` (expect OK, plus WARN lines for missing adapters/policy) and again on a deliberately broken temp copy (expect GATE ERROR, exit 3; show both outputs). Commit: `feat: loader and validate command`.

### B7. Phase 4 — Push evidence-gate

- Update `README.md`: `validate` now works (one example); a "Challenger hand-test" pointer to `docs/challenger/README.md`; eval CSVs exist. Commit `docs: update README`.
- Final: full `pytest` green; `git status` clean.
- `git push -u origin feat/headstart`. Open a PR to `main` titled "Head-start: eval stubs, Challenger prompt, loader + validate" if `gh` is installed and signed in (`gh pr create --base main --head feat/headstart --body ...`; body = the three sections and the test count). If `gh` is unavailable, print the compare URL `https://github.com/AnilRDESTeam/evidence-gate/compare/main...feat/headstart` and the PR text. **Do not merge.**
- **Leave `evidence-gate` checked out on `feat/headstart` until Phase 5 is done** (the editable install must expose `validate`).

### B8. Phase 5 — Task 5: gate-config PR in shop-demo

In `shop-demo` (never touch app code):

```powershell
cd C:\Users\anikumar\Desktop\HackathonProjects\shop-demo
git checkout main ; git pull
git checkout -b gate-config
.venv\Scripts\python -m pip install -e ..\evidence-gate      # editable; uses feat/headstart working tree
```

Create exactly these four files:

| File | Content |
|---|---|
| `.evidence-gate/policy.yaml` | exact copy of `evidence-gate/contract/policy.default.yaml` (high-risk: `app/payments/**`, `app/customers/**`) |
| `.evidence-gate/adapters/README.md` | short placeholder: T2 adds `api.yaml`, T1 adds `browser.yaml`; start from `evidence-gate/contract/examples/api.adapter.yaml` and `browser.adapter.yaml`; do not edit shop code to fit the adapter |
| `requirements/SHOP-102.task.yaml` | exact copy of `evidence-gate/contract/examples/SHOP-102.task.yaml` |
| `requirements/SHOP-101.task.yaml` | exact copy of `evidence-gate/contract/examples/SHOP-101.task.yaml` (keep the "Deliberately NOT defined" comments and `open_questions: []`) |

Do **not** create `adapters/api.yaml` or `browser.yaml`. Do not edit anything else.

Checks (show the output):
1. `.venv\Scripts\evidence-gate validate --task requirements\SHOP-102.task.yaml` → OK (WARN lines for the two missing adapters are expected).
2. Same for SHOP-101.
3. `git diff --stat main` lists only the four files.
4. `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` still green.

Then: commit `chore: gate config and draft task specs for SHOP-101/102`; `git push -u origin gate-config`. Open the PR to `main` (`gh pr create --base main --head gate-config --reviewer <T2 username>` if `gh` works; otherwise print the compare URL `https://github.com/AnilRDESTeam/shop-demo/compare/main...gate-config` and tell Anil to add T2 as reviewer). PR title: "Gate config + draft task specs (SHOP-101, SHOP-102)". PR body: list the four files; "Reviewer (T2): follow Role Guide Task 1; check every expected value against the business rule; the two SHOP-101 open questions must stay unanswered"; "**Do not merge until T2 approves (Anil merges at ~10:15 on 4 Nov).**" **Do not merge.**

Finally: `git checkout main` in shop-demo; `git checkout main` in evidence-gate (the PR branches stay on GitHub).

### B9. Final report to Anil (print at the end)

- What was built per phase (one short paragraph each); number of tests passed (evidence-gate); both PR links (or compare URLs).
- Exact commands for the checks Anil should rerun.
- **Every deviation from or gap in this spec, with the reason** (for example: wording of validate output, hint text, extra consistency checks, `responses` dev dependency).
- Anything that did not work.
- Reminder: PRs are open and unmerged; merge order must be **evidence-gate PR first, then (after T2 approves) gate-config**.

### B10. Must NOT build

Anything in the engine beyond loader + validate; a live Challenger; reporters; scenario/compare/runner code; `adapters/api.yaml` or `browser.yaml`; eval rows; `eval/results.csv`; CI files; any edit to `contract/`; any change to shop app code; the `SHOP-101/102` branches.

### B11. When to stop and ask Anil

- `gh` is unavailable and a PR needs a reviewer you cannot set (just print the instructions; do not stop).
- Any authentication failure on push.
- Any existing test fails before you changed anything (Phase 0).
- A contract schema rejects the official example files (this means a contract bug; do not fix it yourself).
- Anything in this spec seems contradictory.

---

## PART C — Anil's acceptance checklist

- [ ] evidence-gate PR is open from `feat/headstart`; its checks list shows: `eval/cases.csv`, `eval/expected.csv` (one header line each), `src/evidence_gate/challenger/prompt.md`, `loader.py`, tests. No `contract/` file changed.
- [ ] Header lines match your role guide / T2 guide exactly:
  - `case_id,branch,task_file,commit,defect_origin,description`
  - `case_id,branch,task,AC-1,AC-2,AC-3,AC-4,question_expected,verdict,route,notes`
- [ ] `prompt.md` matches the Challenger template in your Role Guide word for word.
- [ ] Pull and test the PR branch:
  ```powershell
  cd C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate
  git fetch origin ; git checkout feat/headstart ; git pull
  .venv\Scripts\python -m pytest
  cd ..\shop-demo ; git checkout gate-config
  .venv\Scripts\evidence-gate validate --task requirements\SHOP-102.task.yaml
  ```
  Expect `OK` (Task 8 done-check).
- [ ] **Read the two task specs yourself** (you decide every expected value): $75.00 → shipping 0.00; $74.99 → 5.99; $50.00 → 5.99; HOODIE+BAG+PEN = 45 + 25 + 4.99 = 74.99; HOODIE+BAG+NOTE = 45 + 25 + 8.50 = 78.50; 10% of 40.00 = 4.00; 10% of 33.35 = 3.335 → 3.34; MUG 12.00 → discount 1.20.
- [ ] `.evidence-gate/policy.yaml` has your high-risk paths (`app/payments/**`, `app/customers/**`).
- [ ] **Hand-test the Challenger** (Task 7 done-check): follow `docs/challenger/README.md`; `validate_json.py` prints `OK` for the answer you saved.
- [ ] Merge the evidence-gate PR (squash and merge, delete branch), post "merged, please git pull" later in the team chat. Leave the gate-config PR **open** for T2.
- [ ] Send the API-key request; send the team comms; confirm hackathon hours (Task 9).
- [ ] Update your Role Guide Part 1 checklist: tasks 1–8 ticked (task 7 once the key request is sent).
