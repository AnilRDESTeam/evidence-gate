# Challenger hand-test

Try the Challenger prompt by hand in Claude chat (the approved tool). No model is called from code.

1. Fill the template with the sample kit:
   ```
   .venv\Scripts\python scripts\fill_challenge_prompt.py --task docs\challenger\sample\task.yaml --diff docs\challenger\sample\change.diff --files docs\challenger\sample\changed_files.txt --commit a41c9e2
   ```
2. Open `out\challenge-test-prompt.md`, copy everything, paste it into Claude chat.
3. Copy **only the JSON** answer into `out\challenge.json`.
4. Check it against the contract (expect `OK`):
   ```
   .venv\Scripts\python scripts\validate_json.py contract\challenge.schema.json out\challenge.json
   ```
5. Check by eye:
   - `app/data/products.json` appears under `uncovered`.
   - `coverage` maps `app/pricing/shipping.py` to AC ids.
   - There is at least one question, and at most 5 proposed scenarios.
   - No invented criteria.
6. Rules: never give the Challenger the coding prompt; never put keys in files or chat.

The sample diff is fake demo data (it includes a deliberate scope-creep change to a product price).
