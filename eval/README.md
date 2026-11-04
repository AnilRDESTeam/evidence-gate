# Evaluation

Five test changes (E1 to E5) on branches of the shop, an answer key, and a script that runs the Gate on each and compares.

| File | What it is |
|---|---|
| `cases.csv` | One row per branch/commit to test. `defect_origin` is one of `none, natural, planted, induced`. |
| `expected.csv` | The answer key. Written **before** the Gate was run; never edited to match results. Label codes: `verified, failed, missing, could_not_run, unconfirmed, needs_human_review, n/a`. |
| `challenges/<case>.json` | The saved Challenger AI answer for each case (used with `--mode saved`). Each is valid for one commit only. |
| `adapters/` | The Gate's adapter config for the shop. The runner lays these over every branch, so a coding AI's branch never controls how it is checked. |
| `run_eval.py` | Runs the cases and prints the comparison. |
| `results.csv` | One row per run: case, run number, mode, verdict, route, labels. |
| `spotchecks.csv` | Light-routed changes that a person must confirm by hand. |
| `last-run-off.txt`, `last-run-saved.txt` | The printed output of the last full run in each mode. |

## Run it

The shop needs its own `.venv` and the branches `eval/*` (see the repo README). Nothing else may be listening on port 8080; the script starts and stops its own shop for each branch and puts the shop back on `main` at the end.

```powershell
python eval/run_eval.py --mode off --runs 5           # Challenger off (no AI)
python eval/run_eval.py --mode saved --runs 5         # saved Challenger answers
python eval/run_eval.py --cases E2,E4 --runs 1        # a quick try
python eval/run_eval.py --compare-only --mode saved   # summarise results.csv again, run nothing
```

It prints misses (expected BLOCKED, got READY), false alarms (expected READY, got BLOCKED), correct changes held up by questions, defective changes routed to light review, label stability and the share routed to light review. Exit code 0 means none of those problems occurred.

## Rules

- The answer key is written first and never edited to match a result.
- If a saved Challenger answer is for another commit than the branch, the Gate refuses it (GATE ERROR). Regenerate it with `evidence-gate challenge-prompt`.
- What the results do and do not show is in [../docs/LIMITATIONS.md](../docs/LIMITATIONS.md).
