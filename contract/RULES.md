# Evidence Gate — Fixed Rules (Contract v1.0)

These rules are fixed and checked in order, first match wins. Labels, verdicts and routes are decided only by these rules, never by AI.

## Label rules (one label per criterion; first match wins)

| ID | Condition | Label |
|----|-----------|-------|
| L1 | Criterion has a valid waiver (who, why, when) | Verified (waived) |
| L2 | No scenarios at all | Not verified: missing |
| L3 | Any confirmed scenario has status fail | Not verified: failed |
| L4 | Any confirmed scenario has status error (adapter error, server down, commit mismatch) | Not verified: could not run |
| L5 | An open question is linked to this criterion | Needs human review |
| L6 | At least one confirmed scenario passed on the current commit | Verified |
| L7 | Only unconfirmed (AI-proposed) scenarios exist | Not verified: unconfirmed |

Unconfirmed (AI-proposed) scenarios are run and shown as 'AI suggestions', but they never change a label from rules L3–L6. Questions not linked to a criterion appear as extra '(new)' rows with the label Needs human review.

## Verdict rules (in order)

| ID | Condition | Verdict | Exit code |
|----|-----------|---------|-----------|
| V1 | Engine error or invalid input file | GATE ERROR | 3 |
| V2 | Any MUST criterion is Not verified | BLOCKED | 1 |
| V3 | Any Needs-human-review item is open | NEEDS DECISION | 2 |
| V4 | Otherwise | READY | 0 |

SHOULD criteria that are Not verified produce a warning only (policy `should_failures: warn`).

## Coverage rules

- Changed files = `git diff --name-only main...HEAD`, minus `ignore_paths`.
- A file is covered if the Challenger maps it to a criterion. With AI off, it is covered if it matches the task's `scope.paths`.
- A file is high-risk if it matches `high_risk_paths` in the policy.

## Route rules (first match wins)

| ID | When | Route | What the human does |
|----|------|-------|---------------------|
| R1 | Verdict is BLOCKED | Back to developer | Nothing yet. Fix first, rerun. |
| R2 | Verdict is NEEDS DECISION | Product owner decides | Answers the question; spec updated; rerun. |
| R3 | Change touches a high-risk path | Full review | Normal deep review, whatever the evidence says. |
| R4 | Changed code that no criterion covers | Focused review | Reviews only the uncovered files. |
| R5 | Everything else | Light review | Skims evidence and approves (~10 min). |

Full review is checked before focused review (correction from plan v3). Otherwise a high-risk change with uncovered code would wrongly get only a focused review.

## Compare rule

Numbers are equal within ±0.005; text is equal after trimming spaces; only the fields listed in `expect` are compared.

## Placeholders in adapter configs

`"{subtotal}"` is replaced with the example's input value. If the whole value is exactly one placeholder, the number stays a number. `defaults:` fill inputs an example did not give.

## Three trust rules

1. Expected results come from the spec, never from the code or the AI.
2. Verified needs executed proof on the exact commit; if the app runs a different commit than the branch, the result is "could not run".
3. AI proposes, rules decide.

## Exit codes

0 READY, 1 BLOCKED, 2 NEEDS DECISION, 3 GATE ERROR.

## Scope

v1 covers functional acceptance criteria only; `check_type` lets other kinds plug in later.
