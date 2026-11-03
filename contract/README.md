# Gate Contract

Version: **1.0.0**

The contract defines what a task spec, adapter config, policy, evidence record, challenge file and report must look like, plus the fixed rules that decide labels, verdicts and routes.

## Files

- `task.schema.json`: shape of a task spec
- `adapter.schema.json`: shape of an adapter config (http or browser)
- `policy.schema.json` and `policy.default.yaml`: team rules and the default policy
- `evidence.schema.json`: one evidence record per scenario run
- `challenge.schema.json`: what the Challenger AI returns
- `report.schema.json`: `out/report.json`
- `RULES.md`: the fixed label, verdict, coverage and route rules
- `examples/`: one valid example for each schema

Any change after the freeze needs Anil's approval and a version bump.
