# Rules for AI assistants working in this repo

1. `contract/` is frozen at v1.0. Never edit it unless Anil says so.
2. Labels, verdicts and routes come only from `contract/RULES.md`. First match wins. Write one unit test per rule row.
3. Drivers never decide pass/fail. They only report what they saw. The runner compares.
4. Expected values come from task specs, never from code or AI.
5. Do not edit files outside your area. T1: `drivers/browser.py`. T2: `drivers/http.py`. Anil: everything else.
6. No secrets, no keys, no `out/`, no `.venv` in git.
7. Run `pytest` before committing. Add tests with every behaviour change.
8. Keep code simple and commented (short comments explaining why).
