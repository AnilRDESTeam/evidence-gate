# Evidence Gate — PLAN (v4 working copy = Team Handbook)

> Source: EvidenceGate-Team-Handbook.docx converted to Markdown. Section numbers match the handbook (2 = Glossary, 8 = How a change flows, 9 = Evaluation cases).

**EVIDENCE GATE**

**Team Handbook**

Hackathon build guide: 4–5 November 2026

**For:** the whole team (Anil, T1, T2). Read this first, then your personal role guide.

**Scope:** Gate Contract + Gate Engine, run locally. Adapters: API + Browser. CI and the coding-agent loop are parked for later.

**Starting point:** the baseline Shop Demo app is on GitHub main (tag baseline-v1.0) and runs on every laptop on the morning of 4 Nov.

> **About the times in this document**
> 
> Times assume hackathon hours of **09:30–18:30 IST**. The organisers have not announced the final hours yet. If they differ, keep the order of the blocks and shift the clock times.

What is in this handbook

  - 1\. Goal and demo story

  - 2\. Glossary: the words we use

  - 3\. How one Gate run works

  - 4\. Where AI comes in

  - 5\. Team roles and file ownership

  - 6\. Repos, folders, and using the Gate inside the shop repo

  - 7\. The Gate Contract and the fixed rules

  - 8\. How a change flows through the Gate

  - 9\. Evaluation cases

  - 10\. Schedule for 4–5 Nov

  - 11\. GitHub workflow

  - 12\. Using AI: where yes, where no

  - 13\. Demo, success measures, risks

  - Appendix: example YAML files

## 1. Goal and demo story

**Problem:** AI now writes code several times faster, but every change still has to be checked. The bottleneck has moved from writing code to verifying it.

**Our product, Evidence Gate,** checks every AI-written change automatically against a written contract. It proves what it can with executed evidence, and points human reviewers at exactly what it cannot prove. It decides how much human review a change needs. It never removes human review.

> **The story we will show the judges**
> 
> Every existing test passes, yet the Gate proves with executed evidence that the old $50 free-shipping rule is still active. Verdict: **BLOCKED**, route: **back to developer**, zero reviewer minutes spent.
> 
> After the fix: **READY → light review**. Then the browser adapter proves the customer actually sees **"Welcome 10%"** on the receipt, and the Gate asks the product owner a question the spec never answered.

What we deliver in two days

|                          |                                                                                                       |                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------ |
| **Deliverable**          | **What it is**                                                                                        | **Must / stretch** |
| Gate Contract            | JSON Schemas + policy + RULES.md defining task specs, adapters, evidence, reports and the fixed rules | Must               |
| Gate Engine              | The evidence-gate command: load, challenge, run, label, verdict, route, report                        | Must               |
| API adapter              | http driver + api.yaml for the shop                                                                   | Must               |
| Browser adapter          | browser driver (Playwright) + browser.yaml, checks the receipt                                        | Must               |
| Reports                  | Terminal, report.json, report.md, report.html                                                         | Must               |
| Evaluation               | 5 cases × 5 runs compared with our answer key                                                         | Must (never cut)   |
| CLI adapter, CI template | Proves "not only web apps"; pipeline step                                                             | Stretch            |

## 2. Glossary: the words we use

**Analogy:** the Gate is an exam invigilator for code changes. The **task spec** is the exam paper with model answers. The **adapter** is how the invigilator talks to the student. The **labeller** marks each answer. The **verdict** is pass or fail. The **route** says how carefully a teacher must re-mark it.

|                         |                                                                                                                                                                         |                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **Term**                | **Plain-English meaning**                                                                                                                                               | **Where it lives**                   |
| System under test (SUT) | The app being checked: the Shop Demo.                                                                                                                                   | shop-demo repo                       |
| Baseline                | The "before" shop: $50 free shipping, no discounts. Tag baseline-v1.0.                                                                                                  | shop-demo                            |
| Change                  | A code edit made by an AI or a developer, on a branch.                                                                                                                  | shop-demo branches                   |
| Gate                    | The whole Evidence Gate command-line tool. You run evidence-gate check … and get a verdict and reports. **The Gate is not the adapter.**                                | evidence-gate repo                   |
| Gate Contract           | The rule book and form templates: what a task spec, adapter config, policy, evidence record and report must look like (JSON Schemas), plus the fixed rules in RULES.md. | evidence-gate/contract/              |
| JSON Schema             | A file that describes the allowed shape of another file (required fields, types). The engine uses it to reject badly written YAML with a clear message.                 | contract/\*.schema.json              |
| YAML                    | Human-friendly text format for config. Indentation matters: 2 spaces, never tabs.                                                                                       | everywhere                           |
| Gate Engine             | The Python program that applies the contract: load → challenge → run → label → verdict → route → report.                                                                | evidence-gate/src/evidence\_gate/    |
| Task spec               | One YAML file per user story: request, numbered criteria and worked examples with exact expected results. Written **before** coding.                                    | shop-demo/requirements/              |
| Criterion (AC)          | One testable statement, e.g. "AC-1: an order of exactly $75 ships free". Priority is MUST or SHOULD.                                                                    | inside task spec                     |
| Worked example          | Input + expected output for a criterion. **Only worked examples (or human-approved values) can make a criterion Verified.**                                             | inside task spec                     |
| Scenario                | One concrete check the engine runs, built from a worked example or proposed by the AI.                                                                                  | engine                               |
| Confirmed / unconfirmed | Confirmed = expected value from the spec or approved by a human. Unconfirmed = guessed by AI; can never produce Verified.                                               | evidence record                      |
| Adapter driver          | Python code in the engine that knows how to talk to a **kind** of system: http (API) or browser (web page via Playwright). Written once.                                | evidence-gate/.../drivers/           |
| Adapter config          | YAML in the app repo saying **which** URL, button or field to use for this app. Written once per app.                                                                   | shop-demo/.evidence-gate/adapters/   |
| Action                  | A named operation in an adapter config, e.g. quote\_order. Examples point to it with via: api.quote\_order.                                                             | adapter config                       |
| Runner                  | Takes each scenario, checks safety, calls the driver, compares expected vs actual, records evidence.                                                                    | runner.py                            |
| Evidence record         | One JSON line per scenario: input, expected, actual, pass/fail/error, commit, time. **This is the proof.**                                                              | out/evidence.jsonl                   |
| Challenger (AI)         | The only AI step in the Gate. Reads spec + diff; flags unclear requirements, maps changed files to criteria, suggests extra scenarios. **Never decides a label.**       | challenger/                          |
| Labeller                | Fixed rules that give each criterion one label: Verified / Not verified (failed, missing, could not run, unconfirmed) / Needs human review.                             | labeller.py                          |
| Verdict                 | One answer per change: READY (exit 0), BLOCKED (1), NEEDS DECISION (2). GATE ERROR (3) if the Gate itself failed.                                                       | verdict.py                           |
| Policy                  | YAML with the team rules: what READY means, high-risk paths, route order, spot-check rate.                                                                              | shop-demo/.evidence-gate/policy.yaml |
| High-risk path          | Code that always gets full human review. Shop: app/payments/\*\*, app/customers/\*\*.                                                                                   | policy                               |
| Uncovered code          | Changed files no criterion explains. Sent to focused review.                                                                                                            | report                               |
| Route                   | How much human review is still needed: back to developer / product owner decides / full / focused / light.                                                              | router.py                            |
| Reporter                | Writes results 4 ways: terminal, report.json (machines), report.md (PR comment), report.html (humans, demo).                                                            | reporters/                           |
| Ground truth            | Our answer key: the expected label, verdict and route for each evaluation branch, written before running the Gate.                                                      | evidence-gate/eval/expected.csv      |
| Evaluation branch       | A shop-demo branch with a known-good or known-bad change. Never merged.                                                                                                 | shop-demo eval/...                   |
| Spot-check              | QA fully re-checks light-routed changes to measure the miss rate.                                                                                                       | eval                                 |

## 3. How one Gate run works

You type one command inside the shop repo, on a branch. The engine runs 9 steps. Only step 3 uses AI, and step 3 is optional.

|             |                                                                                                     |                       |
| ----------- | --------------------------------------------------------------------------------------------------- | --------------------- |
| **Step**    | **What happens**                                                                                    | **Fixed rule or AI?** |
| 1 Load      | Read task spec, adapters, policy; validate them against the contract schemas                        | Fixed                 |
| 2 Git       | Which commit am I on? Which files changed compared with main?                                       | Fixed                 |
| 3 Challenge | AI reads spec + diff → questions, file→criterion map, extra scenario ideas                          | AI (optional)         |
| 4 Scenarios | Worked examples become confirmed scenarios; AI ideas become unconfirmed                             | Fixed                 |
| 5 Run       | Each scenario: safety check → driver → adapter config → the running shop. One evidence record each. | Fixed                 |
| 6 Label     | Each criterion gets one label                                                                       | Fixed                 |
| 7 Verdict   | READY / BLOCKED / NEEDS DECISION + exit code                                                        | Fixed                 |
| 8 Route     | Back to developer / PO decides / full / focused / light review                                      | Fixed                 |
| 9 Report    | Terminal + out/report.json + out/report.md + out/report.html                                        | Fixed                 |

### Walk-through: SHOP-102 on the buggy branch

  - Load: the API criteria. AC-1: $75 → free. AC-2: $74.99 → $5.99. AC-3: $50 → $5.99. (AC-4, the browser receipt check, fails the same way.)

  - Git: commit a41c9e2. Changed: app/config.py, app/pricing/shipping.py (test files ignored by policy).

  - Run: the http driver calls the quote API 3 times. Actual shipping is 0.00, **0.00**, **0.00**. The old $50 rule still gives free shipping.

  - Label: AC-1 Verified, **AC-2 and AC-3 Not verified: failed** (expected 5.99, got 0.00).

  - Verdict: **BLOCKED**, exit code 1. Route: **back to developer**.

  - Report: red banner, evidence table, and "Existing tests: all passed (context only)".

Three rules that make the Gate trustworthy

  - **Expected results come from the spec, never from the code or the AI.**

  - **Verified needs executed proof on the exact commit.** If the shop is running a different commit than the branch, the result is "could not run".

  - **AI proposes, rules decide.** Labels, verdicts and routes are plain rules anyone can read in RULES.md.

## 4. Where AI comes in

There are three different AIs in this project. Don’t mix them up.

|                  |                                               |                             |                                                                    |
| ---------------- | --------------------------------------------- | --------------------------- | ------------------------------------------------------------------ |
| **AI role**      | **Part of the product?**                      | **Model**                   | **What it does**                                                   |
| A. Builder AI    | No, a tool we use to write code faster        | Anil: Claude. T1/T2: OpenAI | Helps write the engine, drivers, YAML files, tests, scripts.       |
| B. Coding AI     | No, it plays "the AI developer" being checked | OpenAI (T1)                 | Implements SHOP-101/102 on evaluation branches.                    |
| C. Challenger AI | Yes, step 3 of the Gate                       | Claude (Anil)               | Questions, file→criterion map, extra scenario ideas. Never labels. |

The Coding AI (OpenAI) and the Challenger (Claude) are deliberately **different models**, so they don’t share blind spots.

Why the Challenger needs model access, and our fallbacks

In live mode the engine calls the model **from Python code**. A chat window or VS Code assistant cannot be called by a program, so live mode needs a Hyland-approved API key or endpoint. We may not have one, so the engine supports three modes:

|               |              |                                                                                                                             |                                                        |
| ------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **Mode**      | **API key?** | **How it works**                                                                                                            | **What we lose**                                       |
| Plan A: live  | Yes          | Engine calls the Hyland-approved endpoint from Python, validates the JSON answer, caches it by commit + prompt hash.        | Nothing                                                |
| Plan B: saved | No           | Engine prints the prompt → Anil pastes it into Claude chat → saves the JSON answer as out/challenge.json → engine reads it. | Not automatic; repeat runs cannot measure AI variation |
| Plan C: off   | No           | No AI. Questions only from the spec’s open\_questions. Coverage from the spec’s scope.paths.                                | No automatic ambiguity detection; coarser coverage     |

> Labels, verdicts and routes work fully in **all three modes**. The core SHOP-102 story needs no AI at all. Anil decides the mode at 09:30 on 5 Nov.

## 5. Team roles and file ownership

|            |                                               |                                                                |                                                                                                                                                                                                                 |
| ---------- | --------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Person** | **Role**                                      | **Main repo**                                                  | **Owns (only this person edits these)**                                                                                                                                                                         |
| Anil       | Lead, Gate implementer, presenter             | evidence-gate                                                  | contract/, engine core (cli, loader, gitinfo, scenarios, runner, compare, safety, labeller, verdict, router, challenger, reporters), shop-demo/.evidence-gate/policy.yaml, merging all PRs, demo                |
| T1         | Builder: Coding-AI branches + browser adapter | shop-demo (eval branches), evidence-gate (browser driver)      | shop-demo eval/\* branches + prompts/, shop-demo/.evidence-gate/adapters/browser.yaml, evidence-gate/src/evidence\_gate/drivers/browser.py, eval/cases.csv, demo video                                          |
| T2         | QA / requirement owner + API adapter          | shop-demo (specs, api.yaml), evidence-gate (http driver, eval) | shop-demo/requirements/\*.task.yaml (final review), shop-demo/.evidence-gate/adapters/api.yaml, evidence-gate/src/evidence\_gate/drivers/http.py, eval/expected.csv, eval/run\_eval.py, results, LIMITATIONS.md |

**QA in one sentence:** T2 decides what "correct" means (specs, answer key), owns the API adapter that collects the proof, and measures whether the Gate itself was right (evaluation and spot-checks). T2 never edits shop code, which keeps the answer key independent.

Team working rules

  - Each person edits only their own files, so merge conflicts stay rare.

  - Push small PRs every 2–3 hours. Anil reviews within 30 minutes.

  - **20-minute rule:** stuck for 20 minutes? Post in the team chat with a screenshot and the full error.

  - Checkpoints: 13:00 and 17:30 on 4 Nov; 12:30 feature freeze on 5 Nov.

## 6. Repos and folders

We use **two GitHub repositories**. The Gate is built once in its own repo and then **used inside the shop repo**, just like pytest is installed once and used in any project.

|               |                                                                                                            |                            |
| ------------- | ---------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Repo**      | **What it holds**                                                                                          | **Changes per app?**       |
| evidence-gate | The tool: contract (schemas, rules), engine code, drivers, evaluation scripts, docs                        | No, the same for every app |
| shop-demo     | The app being checked + its Gate config: .evidence-gate/ (policy, adapters) and requirements/ (task specs) | Yes, config only           |

**Why two repos?** The evaluation switches the shop between old branches. If everything lived in one repo, switching branches would also roll back the Gate code.

> C:\\hack\\
> 
> ├── shop-demo\\ system under test (baseline already here)
> 
> │ ├── app\\ tests\\ scripts\\ baseline code (change on main only via PR)
> 
> │ ├── .evidence-gate\\
> 
> │ │ ├── policy.yaml Anil
> 
> │ │ └── adapters\\
> 
> │ │ ├── api.yaml T2
> 
> │ │ └── browser.yaml T1
> 
> │ ├── requirements\\
> 
> │ │ ├── SHOP-101.task.yaml drafted by Anil, finalised by T2
> 
> │ │ └── SHOP-102.task.yaml
> 
> │ ├── prompts\\ coding-AI prompts (on eval branches only)
> 
> │ └── out\\ Gate output (git-ignored)
> 
> └── evidence-gate\\
> 
> ├── contract\\ schemas, policy.default.yaml, RULES.md (Anil)
> 
> ├── src\\evidence\_gate\\ engine (Anil) + drivers\\http.py (T2) + drivers\\browser.py (T1)
> 
> ├── tests\\ unit tests
> 
> ├── eval\\ cases.csv (T1), expected.csv + run\_eval.py + results.csv (T2)
> 
> └── docs\\ PLAN, ADOPTION, LIMITATIONS, DEMO

Using the Gate inside the shop repo (one-time setup, 4 Nov morning)

> \# Once per laptop, on the morning of 4 Nov (both repos cloned side by side in C:\\hack)
> 
> cd C:\\hack
> 
> git clone \<evidence-gate repo URL\>
> 
> cd C:\\hack\\shop-demo
> 
> git checkout main
> 
> git pull
> 
> .venv\\Scripts\\python -m pip install -e ..\\evidence-gate
> 
> .venv\\Scripts\\evidence-gate --help \# should print the commands

\-e means "editable": when Anil pushes engine fixes, you only run git pull in evidence-gate. No reinstall needed.

**In VS Code:** open two windows (one per repo), or add both folders to one workspace (File → Add Folder to Workspace). Always run Gate commands in a terminal opened in shop-demo, with the shop server running in a second terminal (powershell -ExecutionPolicy Bypass -File scripts\\run.ps1).

Gate commands

> evidence-gate validate --task requirements\\SHOP-102.task.yaml
> 
> Set-Content out\\in.json '{"subtotal": 75}' \# write the test input to a file
> 
> evidence-gate adapter-test --adapter api --action quote\_order --input-file out\\in.json
> 
> evidence-gate challenge-prompt --task requirements\\SHOP-102.task.yaml \> out\\challenge-prompt.md
> 
> evidence-gate check --task requirements\\SHOP-102.task.yaml
> 
> \[--base main\] \[--challenger off|saved|live\]
> 
> \[--challenge-file out\\challenge.json\] \[--out out\] \[--no-tests\]
> 
> \# Always run from inside C:\\hack\\shop-demo, with the shop server running in another terminal.

## 7. The Gate Contract and the fixed rules

The contract is **frozen at 09:30 on 4 Nov (v1.0)**. After that, any change needs Anil’s OK, because drivers and specs depend on it.

|                                          |                                                                               |               |
| ---------------------------------------- | ----------------------------------------------------------------------------- | ------------- |
| **Contract file**                        | **Purpose**                                                                   | **Example**   |
| task.schema.json                         | Shape of a task spec (id, type, criteria, examples, open\_questions, waivers) | Appendix A    |
| adapter.schema.json                      | Shape of an adapter config (type http or browser, actions, read, safety)      | Appendix B, C |
| policy.schema.json + policy.default.yaml | Readiness, high-risk paths, routes, spot-check                                | Appendix D    |
| evidence.schema.json                     | One evidence record per scenario run                                          | Below         |
| challenge.schema.json                    | What the Challenger AI must return                                            | Below         |
| report.schema.json                       | report.json, the source for the md and html reports                           | Below         |
| RULES.md                                 | The fixed label, verdict, coverage and route rules (tables below)             | This section  |

Task spec fields

|                                        |              |                                                                            |
| -------------------------------------- | ------------ | -------------------------------------------------------------------------- |
| **Field**                              | **Required** | **Meaning**                                                                |
| id, type, title, request               | yes          | Story ID; new or updated; what is asked                                    |
| previous\_rule, revised\_rule          | if updated   | Old and new rule in words (helps catch "old rule not removed")             |
| scope.paths                            | no           | Where the change is expected; used for coverage when the Challenger is off |
| criteria\[\].id / priority / statement | yes          | AC-1…; MUST or SHOULD; one testable sentence                               |
| criteria\[\].examples\[\]              | yes for MUST | via (adapter.action), input, expect                                        |
| open\_questions\[\]                    | no           | Known unclear points → Needs human review even with AI off                 |
| waivers\[\], approved\_scenarios\[\]   | no           | Human decisions recorded in the spec                                       |

**Placeholders in adapter configs:** "{subtotal}" is replaced with the example’s input value. If the whole value is exactly one placeholder, the number stays a number. defaults: fill inputs an example didn’t give.

**Compare rule:** numbers are equal within ±0.005; text is equal after trimming spaces; only the fields listed in expect are compared.

Evidence record (one JSON line per scenario, out/evidence.jsonl)

> {"run\_id":"r-20261105-101403","task":"SHOP-102","criterion":"AC-3","scenario":"S-AC-3-1",
> 
> "source":"spec-example","confirmed":true,"commit":"a41c9e2","adapter":"api","action":"quote\_order",
> 
> "input":{"subtotal":50.00},"expected":{"shipping":5.99},"actual":{"shipping":0.00},
> 
> "status":"fail","error":null,"mismatches":\[{"field":"shipping","expected":5.99,"actual":0.00}\],
> 
> "challenger":{"mode":"saved","model":"claude (chat)","prompt\_hash":"9b1f..."},"ts":"2026-11-05T10:14:03Z"}

Challenge file (out/challenge.json)

> { "task": "SHOP-102", "commit": "a41c9e2", "model": "claude", "prompt\_hash": "9b1f3c...",
> 
> "coverage": \[ { "file": "app/pricing/shipping.py", "criteria": \["AC-1","AC-2","AC-3"\] } \],
> 
> "uncovered": \[ { "file": "app/catalog/products.py", "why": "Price changed; no criterion asks for this." } \],
> 
> "questions": \[ { "id": "Q-1", "criterion": null, "text": "Is the threshold checked before or after discounts?" } \],
> 
> "proposed\_scenarios": \[ { "criterion": "AC-2", "input": { "subtotal": 74.995 },
> 
> "expected\_guess": { "shipping": 5.99 }, "why": "Rounding at the boundary" } \] }

**report.json fields:** task, title, type, commit, base, run\_id, timestamp, challenger, criteria (id, priority, statement, label, reason, scenarios), questions, changed\_files, uncovered\_files, verdict, exit\_code, route, route\_reason, next\_action, context (tests passed/total), warnings.

Label rules

|        |                                                                                       |                             |
| ------ | ------------------------------------------------------------------------------------- | --------------------------- |
| **\#** | **Condition (checked top to bottom, first match wins)**                               | **Label**                   |
| 1      | Criterion has a valid waiver (who, why, when)                                         | Verified (waived)           |
| 2      | No scenarios at all                                                                   | Not verified: missing       |
| 3      | Any confirmed scenario has status fail                                                | Not verified: failed        |
| 4      | Any confirmed scenario has status error (adapter error, server down, commit mismatch) | Not verified: could not run |
| 5      | An open question is linked to this criterion                                          | Needs human review          |
| 6      | At least one confirmed scenario passed on the current commit                          | Verified                    |
| 7      | Only unconfirmed (AI-proposed) scenarios exist                                        | Not verified: unconfirmed   |

Unconfirmed (AI-proposed) scenarios are run and shown as "AI suggestions", but they never change a label from rules 3–6. Questions not linked to a criterion appear as extra "(new)" rows with the label Needs human review.

Verdict rules

|                                     |                |               |
| ----------------------------------- | -------------- | ------------- |
| **Condition (in order)**            | **Verdict**    | **Exit code** |
| Engine error or invalid input file  | GATE ERROR     | 3             |
| Any MUST criterion is Not verified  | BLOCKED        | 1             |
| Any Needs-human-review item is open | NEEDS DECISION | 2             |
| Otherwise                           | READY          | 0             |

Coverage rules

  - Changed files = git diff --name-only main...HEAD, minus ignore\_paths.

  - A file is covered if the Challenger maps it to a criterion. With AI off, it is covered if it matches the task’s scope.paths.

  - A file is high-risk if it matches high\_risk\_paths in the policy.

Route rules (first match wins)

|           |                                       |                       |                                                 |
| --------- | ------------------------------------- | --------------------- | ----------------------------------------------- |
| **Order** | **When**                              | **Route**             | **What the human does**                         |
| 1         | Verdict is BLOCKED                    | Back to developer     | Nothing yet. Fix first, rerun.                  |
| 2         | Verdict is NEEDS DECISION             | Product owner decides | Answers the question; spec updated; rerun.      |
| 3         | Change touches a high-risk path       | Full review           | Normal deep review, whatever the evidence says. |
| 4         | Changed code that no criterion covers | Focused review        | Reviews only the uncovered files.               |
| 5         | Everything else                       | Light review          | Skims evidence and approves (\~10 min).         |

> Correction from plan v3: **full review is checked before focused review.** Otherwise a high-risk change with uncovered code would wrongly get only a focused review.

## 8. How a change flows through the Gate

This is the daily flow we demo. T1 follows it to create the evaluation branches.

<table>
<tbody>
<tr class="odd">
<td><strong>Step</strong></td>
<td><strong>Who</strong></td>
<td><strong>What</strong></td>
<td><strong>Command / file</strong></td>
</tr>
<tr class="even">
<td>1</td>
<td>Requirement owner</td>
<td>Task spec written before coding, merged to main</td>
<td>requirements/SHOP-102.task.yaml</td>
</tr>
<tr class="odd">
<td>2</td>
<td>Developer</td>
<td>Update local main</td>
<td>git checkout main; git pull</td>
</tr>
<tr class="even">
<td>3</td>
<td>Developer</td>
<td>Create a branch</td>
<td>git checkout -b eval/shop-102-correct</td>
</tr>
<tr class="odd">
<td>4</td>
<td>Developer</td>
<td>Save the coding prompt before using it</td>
<td>prompts/shop-102-correct.md</td>
</tr>
<tr class="even">
<td>5</td>
<td>Coding AI</td>
<td>Implements the change</td>
<td>OpenAI in VS Code</td>
</tr>
<tr class="odd">
<td>6</td>
<td>Developer</td>
<td>Run existing tests</td>
<td>scripts\test.ps1</td>
</tr>
<tr class="even">
<td>7</td>
<td>Developer</td>
<td>Commit</td>
<td>git add -A; git commit -m "SHOP-102: ..."</td>
</tr>
<tr class="odd">
<td>8</td>
<td>Developer</td>
<td>Restart the shop so it runs this commit</td>
<td>scripts\run.ps1</td>
</tr>
<tr class="even">
<td>9</td>
<td>Developer</td>
<td>Run the Gate</td>
<td>evidence-gate check --task requirements\SHOP-102.task.yaml</td>
</tr>
<tr class="odd">
<td>10</td>
<td>Developer</td>
<td>Read the verdict</td>
<td>terminal + out\report.html</td>
</tr>
<tr class="even">
<td>11</td>
<td></td>
<td><p>BLOCKED → fix and repeat from step 6.</p>
<p>NEEDS DECISION → requirement owner updates the spec, rerun.</p>
<p>READY → push, open a PR, paste out\report.md into it.</p></td>
<td></td>
</tr>
<tr class="odd">
<td>12</td>
<td>Reviewer</td>
<td>Light: skim evidence. Focused: review uncovered files only. Full: deep review.</td>
<td>GitHub PR</td>
</tr>
</tbody>
</table>

## 9. Evaluation cases

T1 creates the branches from baseline-v1.0 after the task specs are on main. T2 writes the expected results in eval/expected.csv **before** running the Gate. Each case runs 5 times.

|          |                                |                                                                                                                                   |                                                                     |
| -------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Case** | **Branch (shop-demo)**         | **What it contains**                                                                                                              | **Expected verdict → route**                                        |
| E1       | eval/shop-102-correct          | Threshold correctly 75                                                                                                            | READY → light review                                                |
| E2       | eval/shop-102-old-rule         | 75 added, but a leftover \>= 50 free-shipping condition is still active and the tests were adjusted to match (natural or PLANTED) | BLOCKED (AC-2, AC-3, AC-4 failed) → back to developer               |
| E3       | eval/shop-101-correct          | Welcome discount correct; receipt shows label                                                                                     | NEEDS DECISION (open question) → PO decides; READY after AC-5 added |
| E4       | eval/shop-101-missing-negative | Discount also given to returning customers                                                                                        | BLOCKED (AC-2 failed) → back to developer                           |
| E5       | eval/shop-102-scope-creep      | Correct threshold plus an unrequested edit (catalog price, or app/payments touched)                                               | READY → focused review (catalog) or full review (payments)          |

  - If the Coding AI writes correct code where we need a defect, plant it by hand in a **separate commit** whose message starts with PLANTED:. We never hide this.

  - After the Gate config (adapters, policy) is merged to main, T1 runs git merge main into every eval branch, so each branch has the config. The Gate ignores those files, so it still sees only the Coding AI’s change.

  - Measured: defects caught with the right criterion, false alarms, label stability (target ≥ 90% identical), and the share routed to light review.

## 10. Schedule for 4–5 Nov

> **About the times in this document**
> 
> Times assume hackathon hours of **09:30–18:30 IST**. The organisers have not announced the final hours yet. If they differ, keep the order of the blocks and shift the clock times.

Wednesday 4 Nov. Goal: end-to-end check works for SHOP-102 with the API adapter

|             |                                                                                          |                                                                  |                                                                  |
| ----------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Time**    | **Anil**                                                                                 | **T1**                                                           | **T2**                                                           |
| 09:30–09:45 | Kickoff for everyone: contract v1.0 frozen; walk through this handbook                   |                                                                  |                                                                  |
| 09:45–10:30 | Help with setup; unblock                                                                 | Morning setup (clone, install engine); read the driver interface | Review and finalise task specs + policy; merge to shop-demo main |
| 10:30–13:00 | Loader/validate, gitinfo, scenarios, compare, runner                                     | Eval branches E1, E2, E5 with OpenAI                             | http driver + api.yaml                                           |
| 13:00–13:45 | Lunch                                                                                    | Lunch                                                            | Lunch                                                            |
| 13:45–16:00 | Labeller, verdict, router + unit tests                                                   | browser driver                                                   | adapter-test working; failure handling                           |
| 16:00–17:30 | Reporters; integrate the http driver                                                     | browser.yaml + adapter-test on the receipt                       | expected.csv (answer key)                                        |
| 17:30–18:30 | CHECKPOINT: E1 = READY, E2 = BLOCKED (API, AI off). Merge everything. List what is left. |                                                                  |                                                                  |

Thursday 5 Nov. Goal: complete Gate, evaluation, demo

|             |                                                            |                                                 |                                       |
| ----------- | ---------------------------------------------------------- | ----------------------------------------------- | ------------------------------------- |
| **Time**    | **Anil**                                                   | **T1**                                          | **T2**                                |
| 09:30       | Decide Challenger mode (live or saved)                     |                                                 |                                       |
| 09:30–11:30 | Challenger + coverage routes + HTML report                 | Browser driver into check; eval branches E3, E4 | eval/run\_eval.py                     |
| 11:30–12:30 | HTML polish; context test count                            | Bug fixing with Anil                            | Dry-run eval on E1, E2                |
| 12:30       | FEATURE FREEZE. Only bug fixes after this.                 |                                                 |                                       |
| 13:15–14:30 | Saved-run backups for every demo case                      | Record the backup demo video                    | Full evaluation (5 × 5) + spot-checks |
| 14:30–15:30 | README, ADOPTION.md                                        | Help with slides and visuals                    | LIMITATIONS.md                        |
| 15:30–16:30 | Rehearsal ×2 (everyone)                                    |                                                 |                                       |
| 16:30–      | Submit (organiser deadline); shop running; laptops charged |                                                 |                                       |

**Stretch (only if the 4 Nov checkpoint is green):** CLI adapter for a small retention-date tool, built in 1 hour with no engine changes; a 10-line CI pipeline template for the "what’s next" slide.

## 11. GitHub workflow

> \# Start of every work session (in each repo you use)
> 
> cd C:\\hack\\shop-demo \# or C:\\hack\\evidence-gate
> 
> git checkout main
> 
> git pull
> 
> \# Start a task on a new branch
> 
> git checkout -b feat/http-driver \# names: feat/..., fix/..., eval/..., adapters/..., docs/...
> 
> \# Save work often
> 
> git status
> 
> git add -A
> 
> git commit -m "http driver: add quote\_order action"
> 
> git push -u origin feat/http-driver \# first push; afterwards just: git push
> 
> \# On GitHub: "Compare & pull request" -\> reviewer: Anil -\> Anil merges

  - Never commit to main directly. Always branch → push → pull request.

  - Pull main before starting any task.

  - Small PRs: at most about 3 hours of work each.

  - Never commit .venv, out/ or any key.

  - Evaluation branches (eval/...) are never merged.

  - If git shows a conflict: stop and call Anil. Do not guess.

## 12. Using AI: where yes, where no

|                                                        |                            |                                                                                                     |
| ------------------------------------------------------ | -------------------------- | --------------------------------------------------------------------------------------------------- |
| **Task**                                               | **Use AI?**                | **How / rule**                                                                                      |
| Turning plain-English requirements into task-spec YAML | Yes, draft only            | AI formats the YAML. A human sets every expected value from the business rule, never from the code. |
| Adapter config YAML (api.yaml, browser.yaml)           | Yes                        | Paste the contract example + API.md or the list of data-testids. Test with adapter-test.            |
| policy.yaml                                            | Yes, draft                 | Human decides the high-risk paths and route order (Anil owns).                                      |
| Contract JSON Schemas and RULES.md                     | Yes (Anil)                 | AI writes schemas from the field tables; Anil checks every rule row.                                |
| Driver code (http, browser)                            | Yes                        | Use the copy-paste prompts in your role guide. Always ask for tests.                                |
| Engine core                                            | Yes (Anil, Claude CLI)     | One module at a time, with unit tests for every rule row.                                           |
| Unit tests, scripts, README, LIMITATIONS.md            | Yes                        | Review and run everything it writes.                                                                |
| Changes on evaluation branches                         | Yes, this IS the Coding AI | OpenAI only. Save the exact prompt. Never paste expected values into it.                            |
| Challenger                                             | Yes, Claude only           | Anil runs it (live or saved). Never show it the coding prompt.                                      |
| Expected values and ground truth (expected.csv)        | NO                         | Human judgment from the business rule. This is our answer key.                                      |
| Deciding labels, verdicts, routes                      | NO                         | Fixed rules in code. That is the point of the product.                                              |
| Merging PRs, resolving conflicts                       | NO                         | Anil merges. Conflicts: stop and call Anil.                                                         |
| API keys, passwords, customer or production data       | NEVER                      | Never paste into any AI chat, file or commit.                                                       |

Good habits with your AI assistant

  - **Give context first:** paste the relevant section of the handbook (e.g. the driver interface + the YAML example) and name the exact file to create.

  - **One small step at a time.** Run it before asking for more. Never accept 500 lines you cannot test.

  - **Always ask:** "Also write a pytest test for this and tell me the exact PowerShell command to run it."

  - **Errors:** paste the full error text back, not a summary.

  - **Stay in your lane:** do not let the AI edit files outside your area (see the ownership table).

  - **Be honest:** if you do not understand what the AI wrote, ask it to explain in simple words before you commit.

> **Compliance**
> 
> Use only approved AI tools (Claude for Anil, OpenAI tools for T1/T2), following Hyland’s AI Use Requirements. Never paste keys, passwords, customer or production data into any AI tool.

## 13. Demo, success measures, risks

Demo script (about 6 minutes, Anil presents)

|          |                                   |                                                                                  |
| -------- | --------------------------------- | -------------------------------------------------------------------------------- |
| **Time** | **Show**                          | **Say**                                                                          |
| 0:00     | Title                             | AI writes code fast. Verifying it is now the bottleneck.                         |
| 0:30     | SHOP-102 spec + policy            | This is the contract: what "good" means, written before any code.                |
| 1:15     | E2: existing tests all green      | Every existing test passes…                                                      |
| 1:45     | Gate on E2 → red HTML             | …yet the Gate proves the $50 rule is still live. BLOCKED, zero reviewer minutes. |
| 2:45     | E1 → READY, light review          | Fixed: about 10 minutes of review, not 2 hours.                                  |
| 3:15     | E3: receipt screenshot + question | It checks what customers see, and asks the PO instead of guessing.               |
| 4:00     | Add AC-5, rerun → READY           | The answer becomes a rule for next time.                                         |
| 4:30     | Evaluation table                  | 5 cases × 5 runs: caught, false alarms, stability.                               |
| 5:15     | Business case + adoption path     | About half the verification effort, to be confirmed in a pilot.                  |

Success measures

|                                                         |                                            |
| ------------------------------------------------------- | ------------------------------------------ |
| **Measure**                                             | **Target**                                 |
| Defect cases caught with the correct criterion (E2, E4) | 2 of 2 (+ E5 routed to full or focused)    |
| Verified without an executed, confirmed scenario        | 0 (hard rule)                              |
| Defective change routed to light review                 | 0 (hard rule)                              |
| Label stability over 5 runs                             | ≥ 90% identical; every difference reported |
| Ambiguous requirement sent to a person (E3)             | Yes, every run (live or saved mode)        |
| Adapters demonstrated                                   | API + Browser                              |

Risks and cut list

|                                                  |                                                                                                                                                                               |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Risk**                                         | **Mitigation**                                                                                                                                                                |
| No API key                                       | Plan B (saved) for the demo, Plan C for the repeat runs                                                                                                                       |
| Playwright Chromium blocked on corporate laptops | Set channel: msedge to use the installed Edge                                                                                                                                 |
| Someone gets stuck                               | Copy-paste prompts in role guides; 20-minute rule; small PRs                                                                                                                  |
| Shop runs an old commit after switching branch   | Health commit check → "could not run" with the message "restart the shop"                                                                                                     |
| Planted bugs look staged                         | AI writes first; plant only if needed; PLANTED: label; we publish it                                                                                                          |
| Running out of time                              | Cut in this order: CLI adapter → live Challenger (use saved) → AI-proposed scenarios → HTML polish. NEVER cut: rules + tests, API adapter, receipt browser check, evaluation. |

## Appendix: example YAML files

A1. shop-demo/requirements/SHOP-102.task.yaml

> id: SHOP-102
> 
> type: updated
> 
> title: Raise free-shipping threshold
> 
> request: Raise the free-shipping threshold from $50 to $75.
> 
> previous\_rule: Orders of $50 or more ship free.
> 
> revised\_rule: Orders of $75 or more ship free.
> 
> check\_type: functional
> 
> scope:
> 
> paths: \["app/config.py", "app/pricing/\*\*"\]
> 
> criteria:
> 
> \- id: AC-1
> 
> priority: MUST
> 
> statement: An order of exactly $75.00 ships free.
> 
> examples:
> 
> \- { via: api.quote\_order, input: { subtotal: 75.00 }, expect: { shipping: 0.00 } }
> 
> \- id: AC-2
> 
> priority: MUST
> 
> statement: An order of $74.99 pays standard shipping ($5.99).
> 
> examples:
> 
> \- { via: api.quote\_order, input: { subtotal: 74.99 }, expect: { shipping: 5.99 } }
> 
> \- id: AC-3
> 
> priority: MUST
> 
> statement: An order of $50.00 no longer ships free (old rule removed).
> 
> examples:
> 
> \- { via: api.quote\_order, input: { subtotal: 50.00 }, expect: { shipping: 5.99 } }
> 
> \- id: AC-4
> 
> priority: MUST
> 
> statement: The customer's receipt shows the correct shipping on both sides of $75.
> 
> examples:
> 
> \- via: browser.checkout\_and\_read\_receipt
> 
> input: { customer: returning-customer-01, add: \["HOODIE-001", "BAG-001", "PEN-001"\] } \# 74.99
> 
> expect: { shipping: 5.99 }
> 
> \- via: browser.checkout\_and\_read\_receipt
> 
> input: { customer: returning-customer-01, add: \["HOODIE-001", "BAG-001", "NOTE-001"\] } \# 78.50
> 
> expect: { shipping: 0.00 }

A2. shop-demo/requirements/SHOP-101.task.yaml

> id: SHOP-101
> 
> type: new
> 
> title: First-order welcome discount
> 
> request: Give new customers 10% off their first order. The receipt must show "Welcome 10%".
> 
> check\_type: functional
> 
> scope:
> 
> paths: \["app/pricing/\*\*", "app/static/\*\*"\]
> 
> criteria:
> 
> \- id: AC-1
> 
> priority: MUST
> 
> statement: A registered customer with no previous orders gets 10% off the subtotal.
> 
> examples:
> 
> \- { via: api.quote\_order, input: { customer: new-customer-01, subtotal: 40.00 },
> 
> expect: { discount: 4.00, discount\_label: "Welcome 10%" } }
> 
> \- id: AC-2
> 
> priority: MUST
> 
> statement: A returning customer gets no welcome discount.
> 
> examples:
> 
> \- { via: api.quote\_order, input: { customer: returning-customer-01, subtotal: 40.00 }, expect: { discount: 0.00 } }
> 
> \- id: AC-3
> 
> priority: MUST
> 
> statement: The receipt shows the label "Welcome 10%" for a new customer's first order.
> 
> examples:
> 
> \- via: browser.checkout\_and\_read\_receipt
> 
> input: { customer: new-customer-01, add: \["MUG-001"\] }
> 
> expect: { discount\_label: "Welcome 10%", discount: 1.20 }
> 
> \- id: AC-4
> 
> priority: SHOULD
> 
> statement: The discount is rounded to the nearest cent.
> 
> examples:
> 
> \- { via: api.quote\_order, input: { customer: new-customer-01, subtotal: 33.35 }, expect: { discount: 3.34 } }
> 
> \# Deliberately NOT defined (the Challenger should find these):
> 
> \# - Does a guest count as a "new customer"?
> 
> \# - Is the $50 free-shipping threshold checked before or after the discount?
> 
> open\_questions: \[\] \# fill these in only for Plan C (AI off) runs

B. shop-demo/.evidence-gate/adapters/api.yaml

> type: http
> 
> base\_url: http://127.0.0.1:8080 \# local test copy only, never production
> 
> health:
> 
> request: GET /api/health
> 
> commit\_field: "$.commit" \# engine compares with git HEAD; mismatch = could not run
> 
> before\_each:
> 
> \- request: POST /api/test/reset \# clean data before every scenario
> 
> actions:
> 
> quote\_order:
> 
> request: POST /api/cart/quote
> 
> defaults: { customer: returning-customer-01 }
> 
> body:
> 
> customer\_id: "{customer}"
> 
> items: \[ { sku: "TEST-SKU", qty: 1, unit\_price: "{subtotal}" } \]
> 
> read:
> 
> subtotal: "$.subtotal"
> 
> shipping: "$.shipping"
> 
> discount: "$.discount"
> 
> discount\_label: "$.discount\_label"
> 
> total: "$.total"
> 
> safety:
> 
> allowed\_hosts: \["127.0.0.1", "localhost"\]
> 
> blocked\_paths: \["/api/payments/\*"\]
> 
> max\_requests\_per\_run: 200
> 
> context:
> 
> tests\_command: ".venv\\\\Scripts\\\\python -m pytest -q" \# existing tests: context only

C. shop-demo/.evidence-gate/adapters/browser.yaml

> type: browser
> 
> base\_url: http://127.0.0.1:8080
> 
> headless: true
> 
> channel: null \# set to "msedge" if Playwright's Chromium is blocked
> 
> timeout\_ms: 5000
> 
> before\_each:
> 
> \- http: POST /api/test/reset
> 
> actions:
> 
> checkout\_and\_read\_receipt:
> 
> defaults: { customer: returning-customer-01 }
> 
> steps:
> 
> \- goto: "/?customer={customer}\#/"
> 
> \- for\_each: "{add}" \# list of SKUs from the example input
> 
> do:
> 
> \- click: "\[data-testid=add-to-cart-{item}\]"
> 
> \- click: "\[data-testid=nav-cart\]"
> 
> \- wait\_for: "\[data-testid=cart-total\]"
> 
> \- click: "\[data-testid=place-order\]"
> 
> \- wait\_for: "\[data-testid=receipt-total\]"
> 
> read: \# a missing element reads as null (or the 'missing' value), not an error
> 
> subtotal: { number: "\[data-testid=receipt-subtotal\]" }
> 
> discount: { number: "\[data-testid=receipt-discount\]", missing: 0.00 }
> 
> discount\_label: { text: "\[data-testid=receipt-discount-label\]" }
> 
> shipping: { number: "\[data-testid=receipt-shipping\]" }
> 
> total: { number: "\[data-testid=receipt-total\]" }
> 
> screenshot: true \# saved to out/screens/\<scenario\>.png and linked from the HTML report
> 
> safety:
> 
> allowed\_hosts: \["127.0.0.1", "localhost"\]

D. shop-demo/.evidence-gate/policy.yaml

> version: 1
> 
> ready\_when: all\_must\_verified\_or\_waived
> 
> should\_failures: warn
> 
> high\_risk\_paths: \["app/payments/\*\*", "app/customers/\*\*"\]
> 
> ignore\_paths: \["tests/\*\*", "requirements/\*\*", "prompts/\*\*", "docs/\*\*", "\*.md", ".evidence-gate/\*\*"\]
> 
> routes: \# top to bottom, first match wins
> 
> \- { route: back\_to\_developer, when: verdict\_blocked }
> 
> \- { route: product\_owner\_decides, when: verdict\_needs\_decision }
> 
> \- { route: full\_review, when: touches\_high\_risk\_paths }
> 
> \- { route: focused\_review, when: uncovered\_changed\_code }
> 
> \- { route: light\_review, when: always }
> 
> spot\_check:
> 
> sample\_rate: 0.10
> 
> pause\_light\_route\_if\_miss\_rate\_above: 0.02

E. Driver interface (evidence-gate/src/evidence\_gate/drivers/base.py)

> \# evidence\_gate/drivers/base.py (written by Anil; T1 and T2 build to this)
> 
> from dataclasses import dataclass, field
> 
> @dataclass
> 
> class DriverResult:
> 
> actual: dict \# e.g. {"shipping": 0.0, "total": 75.0}
> 
> error: str | None = None \# None = ran fine; text = could not run
> 
> artifacts: dict = field(default\_factory=dict) \# e.g. {"screenshot": "out/screens/S-AC-3-1.png"}
> 
> class Driver:
> 
> def \_\_init\_\_(self, config: dict, repo\_root: str, out\_dir: str): ...
> 
> def health\_commit(self) -\> str | None: ... \# commit reported by the running app
> 
> def before\_each(self) -\> None: ... \# e.g. reset data
> 
> def run(self, action: str, inputs: dict) -\> DriverResult: ...
> 
> def close(self) -\> None: ...
> 
> \# Drivers NEVER decide pass/fail. They only report what they saw. The runner compares.
