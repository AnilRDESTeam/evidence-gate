# Adding Evidence Gate to a new repository (about an hour)

You need a web app that runs locally, a git repository, and someone who can write down what a change should do, with worked examples.

## 0. What your app must offer

The Gate drives your app from the outside, so it needs three small things:

| Need | Why | Example in the shop |
|---|---|---|
| A **health endpoint** that returns the git commit the app is running | So the Gate can refuse to trust results from a stale server ("commit mismatch" means "could not run") | `GET /api/health` returns `{"commit": "12a4eb8"}` |
| A way to **reset test data** (optional but recommended) | Each scenario starts clean | `POST /api/test/reset`, allowed only in test mode |
| Stable **`data-testid`** attributes on the UI parts the browser check reads (only if you want UI checks) | The browser driver finds elements by them | `data-testid="receipt-shipping"` |

The app must run on `127.0.0.1` (the safety rules only allow local hosts by default).

## 1. Copy the Gate's config folder

In your repo, create `.evidence-gate/` with two things:

```
.evidence-gate/
  policy.yaml          # copy contract/policy.default.yaml, then edit high_risk_paths
  adapters/
    api.yaml           # how to call your API
    browser.yaml       # how to click through your UI (optional)
```

Pick the policy: `high_risk_paths` lists the folders where a change always gets a full human review (payments, customer data, auth). `ignore_paths` lists files that are not "code" for coverage (tests, docs).

## 2. Write the API adapter

Start from `contract/examples/api.adapter.yaml` (a working copy for the shop is in `eval/adapters/api.yaml`). Change:

- `base_url`, and `health.request` / `health.commit_field` to match your health endpoint,
- one **action** per thing you want to check: the request, a `body` with `"{placeholders}"` for the inputs, and `read:` paths for the response fields,
- `safety.allowed_hosts` and `safety.blocked_paths` (for example anything that charges money).

Try an action by hand before going further:

```powershell
Set-Content in.json '{"subtotal": 50}'
evidence-gate adapter-test --adapter api --action quote_order --input-file in.json
```

If your tests command is not plain `pytest`, set `context.tests_command`. It is shown as context only and never changes a verdict. (If your `pytest.ini` already has `-q`, do not add another: two of them hide the summary line the Gate reads.)

## 3. Write one task spec

Put it in `requirements/<ID>.task.yaml`. Start from `contract/examples/SHOP-102.task.yaml`. The parts that matter:

- `criteria`: each one has a `priority` (MUST or SHOULD) and a plain `statement`,
- `examples`: concrete inputs with the **expected** result, written by a person from the business rule, never copied from the code or from an AI,
- `scope.paths`: the code you expect this task to touch,
- `open_questions`: anything the spec does not settle yet (each one asks a person to decide).

Include at least one example **on each side of every boundary** (for example $74.99 and $75.00), and one negative example ("a returning customer gets no discount"). The planted defects in the evaluation were all caught by exactly these.

## 4. Check, then run

```powershell
evidence-gate validate --task requirements\MY-1.task.yaml     # fix every problem it lists
# start your app on the branch under review (restart it after switching branch), then:
evidence-gate check --task requirements\MY-1.task.yaml
```

Read `out\report.html`. Exit code 0 means READY, 1 BLOCKED, 2 NEEDS DECISION, 3 the Gate itself could not finish.

## 5. Optional: the Challenger AI

`evidence-gate challenge-prompt --task ...` prints a prompt. Give it to a **different AI than the one that wrote the code**, save only its JSON answer, and run `check --challenger saved --challenge-file answer.json`. It adds questions, flags changed files no criterion covers, and proposes extra scenarios. None of that can change a label.

## Common problems

| Message | Meaning |
|---|---|
| `commit mismatch: shop runs X, branch is Y. Restart the shop.` | The app is serving old code. Restart it on the branch you are checking. |
| `shop not reachable` | The app is not running, or `base_url` is wrong. |
| `blocked by safety rule` | The adapter tried a host or path the safety rules forbid. |
| `adapter 'browser' was not found` | No `browser.yaml`; browser criteria stay "could not run". |
