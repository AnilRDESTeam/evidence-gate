# Evidence Gate: Skeleton + Contract v1.0 — One-Shot Build Instructions (for Claude CLI)

> **Project:** Evidence Gate hackathon (4–5 Nov 2026). Covers **Role Guide Task 3 (skeleton)** and **Task 4 (Contract v1.0)**.
> **Target:** repo `evidence-gate` on GitHub `main` with tag `contract-v1.0`, by **Tue 3 Nov 2026, 18:00 IST**.
> **Owner:** Anil (team lead). **Builder:** Claude via Claude CLI.

---

## PART A — For Anil (human)

1. Prerequisites: Task 1 done (`shop-demo` built, tag `baseline-v1.0`). Python 3.12, Git, Claude CLI as before.
2. GitHub: the `evidence-gate` repo must exist, be **Private**, and be empty or nearly empty. Have its URL ready (you will paste it in the prompt below). Branch protection (Task 2) may already be on; section B12 handles that.
3. Create the folder **next to shop-demo** and put these two files in it:
   ```powershell
   mkdir C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate
   cd C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate
   # copy into this folder (same names):
   #   Gate-Skeleton-and-Contract-Build-Instructions.md
   #   PLAN.md            (the Team Handbook converted to Markdown; the builder moves it to docs/PLAN.md)
   ```
   Note: the handbook says `C:\hack\...`, but Task 1 used `...\Desktop\HackathonProjects\`. Keep both repos side by side in the same parent folder. Avoid OneDrive-synced folders.
4. Start Claude CLI **in that folder** (`cd` first, then `claude`) and paste:
   ```text
   Read Gate-Skeleton-and-Contract-Build-Instructions.md completely before doing anything. Then execute
   PART B end to end, phase by phase, running the checks after each phase.
   Project folder: C:\Users\anikumar\Desktop\HackathonProjects\evidence-gate (build here, not in a subfolder).
   GitHub remote URL: <PASTE YOUR evidence-gate REPO URL>
   Stop and ask me only for the items listed in "B13. When to stop and ask".
   At the end, give me the final report described in B12.
   ```
5. Approve commands as asked. Expected time: 1–2 hours.
6. Then do **PART C** yourself. Part C item 3 (reading the rule tables) is not optional: you never delegate rules.

---

## PART B — Instructions for the AI builder

### B1. Mission

Create the **`evidence-gate`** Python project: package skeleton + CLI stubs + driver interface (Task 3), and the **Gate Contract v1.0**: JSON Schemas, default policy, RULES.md, examples and a test that validates every example (Task 4). **No engine logic** (loader, runner, labeller, etc.) is built here; those come later, one module per session.

### B2. Ground rules

1. Beginner-level team: simple, readable code, short comments explaining *why*.
2. Windows 11 + PowerShell first. Scripts/commands must work in PowerShell; give bash equivalents only in README.
3. Python 3.11–3.13. Use `src/` layout.
4. **Copy the rule tables (B8) verbatim.** Do not rephrase, reorder or "improve" any label, verdict or route rule. If something looks wrong or contradictory, stop and ask (B13).
5. Schemas use **JSON Schema draft 2020-12**. Validate with `jsonschema.Draft202012Validator`.
6. Do not add features not listed. No engine logic, no network calls, no API keys, no secrets.
7. Run tests after every phase. If something fails 3 times in a row, stop and report.
8. Commit after each phase (`feat:`, `test:`, `docs:`, `chore:`).
9. Never force-push. Never change repo visibility. Never commit `.venv`, `out/`, keys.

### B3. Folder structure (create exactly this)

```
evidence-gate/
├── pyproject.toml
├── README.md
├── AGENTS.md                      # rules for OpenAI-based assistants (T1/T2)
├── CLAUDE.md                      # same content as AGENTS.md
├── .gitignore  .editorconfig
├── contract/
│   ├── README.md                  # what the contract is, version 1.0.0, change rule
│   ├── task.schema.json
│   ├── adapter.schema.json
│   ├── policy.schema.json
│   ├── policy.default.yaml
│   ├── evidence.schema.json
│   ├── challenge.schema.json
│   ├── report.schema.json
│   ├── RULES.md
│   └── examples/
│       ├── SHOP-101.task.yaml
│       ├── SHOP-102.task.yaml
│       ├── api.adapter.yaml
│       ├── browser.adapter.yaml
│       ├── policy.example.yaml
│       ├── evidence.example.json
│       ├── challenge.example.json
│       └── report.example.json
├── src/evidence_gate/
│   ├── __init__.py                # __version__ = "0.1.0"
│   ├── cli.py                     # argparse stubs
│   ├── drivers/
│   │   ├── __init__.py
│   │   ├── base.py                # EXACT interface (B6)
│   │   ├── http.py                # empty stub, owner T2
│   │   └── browser.py             # empty stub, owner T1
├── tests/
│   ├── test_cli_stub.py
│   └── test_contract_examples.py
├── eval/                          # empty, with .gitkeep (T1/T2 add files; Anil adds CSV headers separately)
└── docs/
    └── PLAN.md                    # move ./PLAN.md here unchanged
```

Also move `Gate-Skeleton-and-Contract-Build-Instructions.md` to `docs/` in the last phase. Do **not** create `challenger/`, `reporters/`, `loader.py` or any other engine module.

### B4. Packaging (`pyproject.toml`)

- Build backend: setuptools (or hatchling), `src/` layout, package `evidence_gate`.
- `[project] name = "evidence-gate"`, version `0.1.0`, `requires-python = ">=3.11"`.
- Dependencies: `pyyaml`, `jsonschema`, `requests`, `jinja2`, `playwright`.
- Optional extras: `anthropic = ["anthropic"]`, `dev = ["pytest"]`.
- Console script: `evidence-gate = "evidence_gate.cli:main"`.
- Package data: include nothing from `contract/` yet (the contract stays a plain folder at repo root).
- Pin nothing in `pyproject.toml`; use lower bounds only.

### B5. CLI stubs (`cli.py`)

argparse, program name `evidence-gate`, subcommands exactly:

| Command | Arguments |
|---|---|
| `validate` | `--task PATH` |
| `adapter-test` | `--adapter NAME --action NAME --input-file PATH` |
| `challenge-prompt` | `--task PATH` |
| `check` | `--task PATH` `[--base main]` `[--challenger off\|saved\|live]` `[--challenge-file PATH]` `[--out out]` `[--no-tests]` |

Behaviour of every stub: print `evidence-gate <command>: not implemented yet` to stderr and return exit code **3** (GATE ERROR). `--help` and `<command> --help` must work and exit 0. Put the exit-code meaning in the top-level help text: `0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR`. `main()` returns an int and the console script exits with it.

### B6. Driver interface (`drivers/base.py`) — write EXACTLY this

```python
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
```

`drivers/http.py` and `drivers/browser.py`: only a module docstring ("Owner: T2/T1. Implement class HttpDriver/BrowserDriver(Driver) here. Do not edit base.py.") and nothing else.

### B7. Contract: schemas

All schemas: `"$schema": "https://json-schema.org/draft/2020-12/schema"`, a `$id`, `title`, `description`, `additionalProperties: false` on objects **except** where noted as open. Add a `description` to every property (beginners read these).

**task.schema.json**

| Field | Rule |
|---|---|
| `id` (string, e.g. `SHOP-102`), `type` (`new`\|`updated`), `title`, `request` | required |
| `previous_rule`, `revised_rule` | required **if** `type == "updated"` (use `if/then`) |
| `check_type` | enum `functional`\|`security`\|`performance`\|`accessibility`, default `functional` (v1 engine runs only `functional`) |
| `scope.paths` | optional array of glob strings |
| `criteria[]` | required, min 1. Each: `id` (pattern `^AC-[0-9]+$`), `priority`, `statement`, `examples[]` |
| `criteria[].priority` | enum `MUST`\|`SHOULD` |
| `criteria[].examples[]` | **required and min 1 when priority is MUST** (`if/then`). Each: `via` (pattern `^(api\|browser)\.[a-z_]+$`, i.e. `adapter.action`), `input` (object), `expect` (object, min 1 property) |
| `open_questions[]` | optional. Each: `id` (pattern `^Q-[0-9]+$`), `text`, `criterion` (AC id or null) |
| `waivers[]` | optional. Each: `criterion`, `who`, `why`, `when` (ISO date). All four required |
| `approved_scenarios[]` | optional. Each: `criterion`, `via`, `input`, `expect`, `approved_by` |

`criteria[].id` must be unique within a file: enforce in the test helper, since JSON Schema cannot do this cleanly for objects (use `uniqueItems` only if it works; otherwise a Python check in `test_contract_examples.py`).

**adapter.schema.json**

- Common: `type` (`http`\|`browser`) required; `base_url` required; `before_each` optional array; `actions` required (object, min 1; each key `^[a-z_]+$`); `safety` required with `allowed_hosts` (array, min 1) and optional `blocked_paths`, `blocked`, `max_requests_per_run` (int ≥ 1); `context.tests_command` optional string.
- `type: http`: optional `health` {`request`, `commit_field`}; each action requires `request` and `read` (object of name → JSONPath string); optional `defaults`, `body`. `before_each` items: `{request: "POST /path"}`.
- `type: browser`: optional `headless` (bool), `channel` (string or null), `timeout_ms` (int); each action requires `steps` (array, min 1) and `read` (object); optional `defaults`, `screenshot` (bool). Steps and `read` entries are **open** objects (the browser driver owner defines details). `before_each` items: `{http: "POST /path"}`.
- Use `if/then` on `type` for the above. Keep `additionalProperties: false` at top level.

**policy.schema.json** (and `policy.default.yaml` must validate)

`version` (const 1), `ready_when` (enum `all_must_verified_or_waived`), `should_failures` (enum `warn`\|`block`), `high_risk_paths` (array of globs), `ignore_paths` (array of globs), `routes` (array, min 1, each `{route, when}`; `route` enum: `back_to_developer`, `product_owner_decides`, `full_review`, `focused_review`, `light_review`; `when` enum: `verdict_blocked`, `verdict_needs_decision`, `touches_high_risk_paths`, `uncovered_changed_code`, `always`), `spot_check` {`sample_rate` 0–1, `pause_light_route_if_miss_rate_above` 0–1}.

**evidence.schema.json** (one JSON line of `out/evidence.jsonl`)

Required: `run_id`, `task`, `criterion` (string, or null for AI scenarios not tied to a criterion), `scenario`, `source` (enum `spec-example`\|`approved`\|`ai-proposed`), `confirmed` (bool), `commit`, `adapter`, `action`, `input` (object), `expected` (object), `actual` (object or null), `status` (enum `pass`\|`fail`\|`error`), `error` (string or null), `ts` (date-time string). Optional: `mismatches[]` ({`field`, `expected`, `actual`}), `artifacts` (object), `challenger` ({`mode` enum `off`\|`saved`\|`live`, `model`, `prompt_hash`}). Add `if/then`: `source == "ai-proposed"` ⇒ `confirmed` is `false`.

**challenge.schema.json** (what the Challenger AI returns)

Required: `task`, `commit`, `coverage[]` ({`file`, `criteria[]`}), `uncovered[]` ({`file`, `why`}), `questions[]` ({`id` `^Q-[0-9]+$`, `criterion` AC id or null, `text`}), `proposed_scenarios[]` (max 5; each {`criterion`, `input`, `expected_guess`, `why`}). Optional: `model`, `prompt_hash`. (The engine adds `model`/`prompt_hash`; the AI template does not ask for them.)

**report.schema.json** (`out/report.json`)

Required fields: `task`, `title`, `type`, `commit`, `base`, `run_id`, `timestamp`, `challenger` ({`mode`, `model`, `prompt_hash`}), `criteria[]` (each: `id`, `priority`, `statement`, `label`, `reason` (string or null), `scenarios` (array of scenario ids)), `questions[]`, `changed_files[]`, `uncovered_files[]`, `verdict` (enum `READY`\|`BLOCKED`\|`NEEDS DECISION`\|`GATE ERROR`), `exit_code` (enum 0,1,2,3), `route` (enum as in policy, or null when verdict is GATE ERROR), `route_reason`, `next_action`, `context` ({`tests_passed`, `tests_total`} or null), `warnings[]`, `contract_version` (const `"1.0"`).
`label` enum: `verified`, `verified_waived`, `not_verified`, `needs_human_review`. `reason` enum when `not_verified`: `failed`, `missing`, `could_not_run`, `unconfirmed`; required non-null when label is `not_verified` (`if/then`), null otherwise.
Add `if/then` linking verdict ↔ exit_code: READY→0, BLOCKED→1, NEEDS DECISION→2, GATE ERROR→3.

### B8. Contract: RULES.md (copy verbatim)

`contract/RULES.md` must contain exactly these sections and tables, with the **row IDs** added in the first column (so tests can point at them). Heading: "Evidence Gate — Fixed Rules (Contract v1.0)". Start with one paragraph: *"These rules are fixed and checked in order, first match wins. Labels, verdicts and routes are decided only by these rules, never by AI."*

**Label rules** (one label per criterion; first match wins)

| ID | Condition | Label |
|---|---|---|
| L1 | Criterion has a valid waiver (who, why, when) | Verified (waived) |
| L2 | No scenarios at all | Not verified: missing |
| L3 | Any confirmed scenario has status fail | Not verified: failed |
| L4 | Any confirmed scenario has status error (adapter error, server down, commit mismatch) | Not verified: could not run |
| L5 | An open question is linked to this criterion | Needs human review |
| L6 | At least one confirmed scenario passed on the current commit | Verified |
| L7 | Only unconfirmed (AI-proposed) scenarios exist | Not verified: unconfirmed |

Below the table: "Unconfirmed (AI-proposed) scenarios are run and shown as 'AI suggestions', but they never change a label from rules L3–L6. Questions not linked to a criterion appear as extra '(new)' rows with the label Needs human review."

**Verdict rules** (in order)

| ID | Condition | Verdict | Exit code |
|---|---|---|---|
| V1 | Engine error or invalid input file | GATE ERROR | 3 |
| V2 | Any MUST criterion is Not verified | BLOCKED | 1 |
| V3 | Any Needs-human-review item is open | NEEDS DECISION | 2 |
| V4 | Otherwise | READY | 0 |

Below: "SHOULD criteria that are Not verified produce a warning only (policy `should_failures: warn`)."

**Coverage rules**
- Changed files = `git diff --name-only main...HEAD`, minus `ignore_paths`.
- A file is covered if the Challenger maps it to a criterion. With AI off, it is covered if it matches the task's `scope.paths`.
- A file is high-risk if it matches `high_risk_paths` in the policy.

**Route rules** (first match wins)

| ID | When | Route | What the human does |
|---|---|---|---|
| R1 | Verdict is BLOCKED | Back to developer | Nothing yet. Fix first, rerun. |
| R2 | Verdict is NEEDS DECISION | Product owner decides | Answers the question; spec updated; rerun. |
| R3 | Change touches a high-risk path | Full review | Normal deep review, whatever the evidence says. |
| R4 | Changed code that no criterion covers | Focused review | Reviews only the uncovered files. |
| R5 | Everything else | Light review | Skims evidence and approves (~10 min). |

Below: "Full review is checked before focused review (correction from plan v3). Otherwise a high-risk change with uncovered code would wrongly get only a focused review."

**Also include these short sections** (copy wording):
- *Compare rule:* numbers are equal within ±0.005; text is equal after trimming spaces; only the fields listed in `expect` are compared.
- *Placeholders in adapter configs:* `"{subtotal}"` is replaced with the example's input value. If the whole value is exactly one placeholder, the number stays a number. `defaults:` fill inputs an example did not give.
- *Three trust rules:* (1) Expected results come from the spec, never from the code or the AI. (2) Verified needs executed proof on the exact commit; if the app runs a different commit than the branch, the result is "could not run". (3) AI proposes, rules decide.
- *Exit codes:* 0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR.
- *Scope:* v1 covers functional acceptance criteria only; `check_type` lets other kinds plug in later.

### B9. Contract: examples

Create these files **exactly** (they are the examples the whole team copies).

**`examples/SHOP-102.task.yaml`**
```yaml
id: SHOP-102
type: updated
title: Raise free-shipping threshold
request: Raise the free-shipping threshold from $50 to $75.
previous_rule: Orders of $50 or more ship free.
revised_rule: Orders of $75 or more ship free.
check_type: functional
scope:
  paths: ["app/config.py", "app/pricing/**"]
criteria:
  - id: AC-1
    priority: MUST
    statement: An order of exactly $75.00 ships free.
    examples:
      - { via: api.quote_order, input: { subtotal: 75.00 }, expect: { shipping: 0.00 } }
  - id: AC-2
    priority: MUST
    statement: An order of $74.99 pays standard shipping ($5.99).
    examples:
      - { via: api.quote_order, input: { subtotal: 74.99 }, expect: { shipping: 5.99 } }
  - id: AC-3
    priority: MUST
    statement: An order of $50.00 no longer ships free (old rule removed).
    examples:
      - { via: api.quote_order, input: { subtotal: 50.00 }, expect: { shipping: 5.99 } }
  - id: AC-4
    priority: MUST
    statement: The customer's receipt shows the correct shipping on both sides of $75.
    examples:
      - via: browser.checkout_and_read_receipt
        input: { customer: returning-customer-01, add: ["HOODIE-001", "BAG-001", "PEN-001"] }   # 74.99
        expect: { shipping: 5.99 }
      - via: browser.checkout_and_read_receipt
        input: { customer: returning-customer-01, add: ["HOODIE-001", "BAG-001", "NOTE-001"] }  # 78.50
        expect: { shipping: 0.00 }
```

**`examples/SHOP-101.task.yaml`**
```yaml
id: SHOP-101
type: new
title: First-order welcome discount
request: Give new customers 10% off their first order. The receipt must show "Welcome 10%".
check_type: functional
scope:
  paths: ["app/pricing/**", "app/static/**"]
criteria:
  - id: AC-1
    priority: MUST
    statement: A registered customer with no previous orders gets 10% off the subtotal.
    examples:
      - { via: api.quote_order, input: { customer: new-customer-01, subtotal: 40.00 }, expect: { discount: 4.00, discount_label: "Welcome 10%" } }
  - id: AC-2
    priority: MUST
    statement: A returning customer gets no welcome discount.
    examples:
      - { via: api.quote_order, input: { customer: returning-customer-01, subtotal: 40.00 }, expect: { discount: 0.00 } }
  - id: AC-3
    priority: MUST
    statement: The receipt shows the label "Welcome 10%" for a new customer's first order.
    examples:
      - via: browser.checkout_and_read_receipt
        input: { customer: new-customer-01, add: ["MUG-001"] }
        expect: { discount_label: "Welcome 10%", discount: 1.20 }
  - id: AC-4
    priority: SHOULD
    statement: The discount is rounded to the nearest cent.
    examples:
      - { via: api.quote_order, input: { customer: new-customer-01, subtotal: 33.35 }, expect: { discount: 3.34 } }
# Deliberately NOT defined (the Challenger should find these):
# - Does a guest count as a "new customer"?
# - Is the $50 free-shipping threshold checked before or after the discount?
open_questions: []   # fill these in only for Plan C (AI off) runs
```

**`examples/api.adapter.yaml`**
```yaml
type: http
base_url: http://127.0.0.1:8080          # local test copy only, never production
health:
  request: GET /api/health
  commit_field: "$.commit"               # engine compares with git HEAD; mismatch = could not run
before_each:
  - request: POST /api/test/reset        # clean data before every scenario
actions:
  quote_order:
    request: POST /api/cart/quote
    defaults: { customer: returning-customer-01 }
    body:
      customer_id: "{customer}"
      items: [ { sku: "TEST-SKU", qty: 1, unit_price: "{subtotal}" } ]
    read:
      subtotal: "$.subtotal"
      shipping: "$.shipping"
      discount: "$.discount"
      discount_label: "$.discount_label"
      total: "$.total"
safety:
  allowed_hosts: ["127.0.0.1", "localhost"]
  blocked_paths: ["/api/payments/*"]
  max_requests_per_run: 200
context:
  tests_command: ".venv\\Scripts\\python -m pytest -q"   # existing tests: context only
```

**`examples/browser.adapter.yaml`**
```yaml
type: browser
base_url: http://127.0.0.1:8080
headless: true
channel: null                  # set to "msedge" if Playwright's Chromium is blocked
timeout_ms: 5000
before_each:
  - http: POST /api/test/reset
actions:
  checkout_and_read_receipt:
    defaults: { customer: returning-customer-01 }
    steps:
      - goto: "/?customer={customer}#/"
      - for_each: "{add}"                       # list of SKUs from the example input
        do:
          - click: "[data-testid=add-to-cart-{item}]"
      - click: "[data-testid=nav-cart]"
      - wait_for: "[data-testid=cart-total]"
      - click: "[data-testid=place-order]"
      - wait_for: "[data-testid=receipt-total]"
    read:                                       # a missing element reads as null (or the 'missing' value), not an error
      subtotal: { number: "[data-testid=receipt-subtotal]" }
      discount: { number: "[data-testid=receipt-discount]", missing: 0.00 }
      discount_label: { text: "[data-testid=receipt-discount-label]" }
      shipping: { number: "[data-testid=receipt-shipping]" }
      total: { number: "[data-testid=receipt-total]" }
    screenshot: true                            # saved to out/screens/<scenario>.png and linked from the HTML report
safety:
  allowed_hosts: ["127.0.0.1", "localhost"]
```

**`policy.default.yaml`** (in `contract/`) **and `examples/policy.example.yaml`** (identical content)
```yaml
version: 1
ready_when: all_must_verified_or_waived
should_failures: warn
high_risk_paths: ["app/payments/**", "app/customers/**"]
ignore_paths: ["tests/**", "requirements/**", "prompts/**", "docs/**", "*.md", ".evidence-gate/**"]
routes:                       # top to bottom, first match wins
  - { route: back_to_developer, when: verdict_blocked }
  - { route: product_owner_decides, when: verdict_needs_decision }
  - { route: full_review, when: touches_high_risk_paths }
  - { route: focused_review, when: uncovered_changed_code }
  - { route: light_review, when: always }
spot_check:
  sample_rate: 0.10
  pause_light_route_if_miss_rate_above: 0.02
```

**`examples/evidence.example.json`** — one record (the handbook's SHOP-102 AC-3 failure):
```json
{"run_id":"r-20261105-101403","task":"SHOP-102","criterion":"AC-3","scenario":"S-AC-3-1",
 "source":"spec-example","confirmed":true,"commit":"a41c9e2","adapter":"api","action":"quote_order",
 "input":{"subtotal":50.00},"expected":{"shipping":5.99},"actual":{"shipping":0.00},
 "status":"fail","error":null,"mismatches":[{"field":"shipping","expected":5.99,"actual":0.00}],
 "challenger":{"mode":"saved","model":"claude (chat)","prompt_hash":"9b1f3c"},"ts":"2026-11-05T10:14:03Z"}
```

**`examples/challenge.example.json`**
```json
{ "task": "SHOP-102", "commit": "a41c9e2", "model": "claude", "prompt_hash": "9b1f3c",
  "coverage": [ { "file": "app/pricing/shipping.py", "criteria": ["AC-1","AC-2","AC-3"] } ],
  "uncovered": [ { "file": "app/catalog/products.py", "why": "Price changed; no criterion asks for this." } ],
  "questions": [ { "id": "Q-1", "criterion": null, "text": "Is the threshold checked before or after discounts?" } ],
  "proposed_scenarios": [ { "criterion": "AC-2", "input": { "subtotal": 74.995 },
                            "expected_guess": { "shipping": 5.99 }, "why": "Rounding at the boundary" } ] }
```

**`examples/report.example.json`** — the SHOP-102 BLOCKED story, valid against `report.schema.json`: task `SHOP-102`, title `Raise free-shipping threshold`, type `updated`, commit `a41c9e2`, base `main`, run_id `r-20261105-101403`, timestamp `2026-11-05T10:14:05Z`, challenger {mode `saved`, model `claude (chat)`, prompt_hash `9b1f3c`}; criteria: AC-1 `verified`; AC-2 and AC-3 `not_verified` / reason `failed`; AC-4 `not_verified` / reason `failed` (each with plausible scenario ids like `S-AC-2-1`); questions: the Q-1 above; changed_files `["app/config.py","app/pricing/shipping.py"]`; uncovered_files `[]`; verdict `BLOCKED`; exit_code 1; route `back_to_developer`; route_reason "Verdict is BLOCKED"; next_action "The old $50 rule is still active. Fix it, then rerun `evidence-gate check`."; context {tests_passed 42, tests_total 42}; warnings `[]`; contract_version `"1.0"`.

### B10. Tests

`tests/test_contract_examples.py` (pytest, parametrized; resolve paths from the repo root via `Path(__file__)`):

1. Every `contract/*.schema.json` loads and passes `Draft202012Validator.check_schema`.
2. Each example validates against its schema: `*.task.yaml`→task, `*.adapter.yaml`→adapter, `policy.example.yaml` and `contract/policy.default.yaml`→policy, `evidence.example.json`→evidence, `challenge.example.json`→challenge, `report.example.json`→report. Failure messages must name the file and the field path.
3. `criteria[].id` unique in each task example.
4. **Negative tests** (each must be rejected): a MUST criterion with no examples; `type: updated` without `previous_rule`; priority `MAYBE`; a route `when: sometimes`; an `ai-proposed` evidence record with `confirmed: true`; a report with verdict BLOCKED but exit_code 0; a `not_verified` criterion without `reason`; an adapter of type `ftp`.
5. `RULES.md` contains the row IDs L1–L7, V1–V4, R1–R5 (guards against accidental deletion).

`tests/test_cli_stub.py`: `evidence-gate --help` exits 0 and lists the four commands; each command, run with valid dummy arguments, exits 3 and prints "not implemented yet". Use `subprocess` with `sys.executable -m evidence_gate.cli` (add `if __name__ == "__main__": sys.exit(main())`).

### B11. Repository docs

- **README.md** (beginner, Windows first): what it is (3 lines); install (`python -m venv .venv`, `.venv\Scripts\python -m pip install -e .[dev]`); run tests (`.venv\Scripts\python -m pytest`); how shop-demo uses it (`cd ..\shop-demo`, `.venv\Scripts\python -m pip install -e ..\evidence-gate`, `evidence-gate --help`); repo map; the contract change rule; Git workflow (branch → push → PR; never commit to main directly).
- **AGENTS.md** and **CLAUDE.md** (identical): (1) `contract/` is frozen at v1.0; never edit it unless Anil says so. (2) Labels, verdicts and routes come only from `contract/RULES.md`; first match wins; one unit test per rule row. (3) Drivers never decide pass/fail; they only report what they saw. (4) Expected values come from task specs, never from code or AI. (5) Do not edit files outside your area (T1: `drivers/browser.py`; T2: `drivers/http.py`; Anil: everything else). (6) No secrets, no keys, no `out/`, no `.venv` in git. (7) Run `pytest` before committing; add tests with every behaviour change. (8) Simple, commented code.
- **contract/README.md**: version `1.0.0`, list of files, "Any change after the freeze needs Anil's approval and a version bump."
- **`.gitignore`**: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `out/`, `.env`, `*.egg-info/`, `build/`, `dist/`, `*.log`.

### B12. Build phases (in order; check and commit after each)

| Phase | Work | Check before commit |
|---|---|---|
| 0 | Work in the folder containing this file (no nested folder). `git init -b main`; `.gitignore`, `.editorconfig`; create `.venv`; move `PLAN.md` → `docs/PLAN.md` | `git status` shows only intended files |
| 1 | `pyproject.toml`, package, `cli.py` stubs, `drivers/*`, empty `eval/.gitkeep`; `pip install -e .[dev]` | `.venv\Scripts\evidence-gate --help` lists validate, adapter-test, challenge-prompt, check |
| 2 | `test_cli_stub.py` | `pytest tests/test_cli_stub.py` green |
| 3 | All six schemas + `policy.default.yaml` | each schema passes `check_schema` |
| 4 | `RULES.md` (B8, verbatim) + examples (B9) | files exist; YAML parses |
| 5 | `test_contract_examples.py` (incl. negative tests) | full `pytest` green |
| 6 | README, AGENTS.md, CLAUDE.md, contract/README.md; move this instruction file to `docs/` | read-through: every README command works |
| 7 | Final: full `pytest`; `git status` clean | all green |
| 8 | Push (see below) | `git ls-remote --tags origin` shows `contract-v1.0` |

**Push (phase 8):** ask Anil to confirm the repo is **Private**. `git remote add origin <URL>`; `git push -u origin main`. If `main` is protected and the push is refused: `git switch -c feat/skeleton-contract`, push that branch, tell Anil to open and merge the PR (he can bypass protection), then wait for him to say "merged", `git switch main && git pull`. After `main` contains the work: `git tag -a contract-v1.0 -m "Contract frozen" ; git push origin contract-v1.0`.

**Final report to Anil** (print at the end): what was built (one paragraph); tests passed; commit SHA, tag, repo URL; exact commands to install and test; **every place you deviated from or filled a gap in this spec, with reason** (e.g. field names invented for `waivers`/`approved_scenarios`/`open_questions`); anything that did not work.

### B13. When to stop and ask Anil

- Before the first push: confirm the repo is Private.
- Authentication problems on push, or `main` protected (see above).
- Python < 3.11 or Git missing.
- Anything in this spec seems contradictory, or a rule table seems wrong.
- Before editing any rule row (don't).

### B14. Must NOT build

Loader, validator logic beyond the tests, runner, compare, labeller, verdict, router, challenger, reporters, drivers' real code, CI pipeline, HTML templates, `eval/*.csv` files, anything in `shop-demo`.

---

## PART C — Anil's acceptance checklist

- [ ] GitHub `evidence-gate` shows `main` with `contract/`, `src/`, `tests/`, `docs/PLAN.md`, **Private** badge, and tag `contract-v1.0`.
- [ ] Fresh clone check:
  ```powershell
  cd $env:TEMP
  git clone <repo URL> eg-check ; cd eg-check
  python -m venv .venv
  .venv\Scripts\python -m pip install -e .[dev]
  .venv\Scripts\python -m pytest
  ```
- [ ] Integration with the shop (Task 3 "done when"):
  ```powershell
  cd C:\Users\anikumar\Desktop\HackathonProjects\shop-demo
  .venv\Scripts\python -m pip install -e ..\evidence-gate
  .venv\Scripts\evidence-gate --help     # lists validate, adapter-test, challenge-prompt, check
  ```
- [ ] **You read `contract/RULES.md` yourself** against Handbook section 7: 7 label rows, 4 verdict rows, 5 route rows, full review before focused review. Nothing paraphrased.
- [ ] `drivers/base.py` matches the Role Guide interface word for word.
- [ ] `contract/examples/SHOP-102.task.yaml` expected values match the business rule ($75 free; $74.99 → 5.99; $50 → 5.99).
- [ ] Tell T1/T2 the contract is frozen at v1.0 (kickoff, 09:30 on 4 Nov).
