# Eval answer key and case list
- `cases.csv` is filled by T1 (one row per branch/commit to test); `expected.csv` is filled by T2 (the answer key).
- `defect_origin` allowed values: `none, natural, planted, induced`.
- Label codes for `expected.csv`: `verified, failed, missing, could_not_run, unconfirmed, needs_human_review, n/a`.
- `expected.csv` is written before the Gate is run; never edited to match results.
- Both files are header-only on purpose: no example rows, so the answer key stays independent.
