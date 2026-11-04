# Demo script (5 minutes)

Before you go on stage: run `python scripts/demo.py` once so you know it works on this machine. It opens an **overview PDF** (every case and its status on page one, then one page per case) plus a PDF for each case: keep those open as a backup. The committed `eval/overview/overview-off.pdf` and `overview-saved.pdf` (all five cases, 5 runs each) make good handouts. Nothing else needs to be running; the demo starts and stops its own shop.

## The story in one breath

"AI writes the code now. Reviewers can't read every diff, and **the AI also wrote the tests**, so green tests prove little. Evidence Gate checks the change against examples a *person* wrote in the spec, on the real running app, and tells the reviewer how much human attention is still needed."

## 1. Show the problem (1 minute)

Use E4. Say: "The coding AI was asked to give new customers 10% off their first order. It gave the discount to **every** registered customer, returning ones too, and adjusted the tests to match. The shop's own test run says **58 of 58 passed**."

(E2 is the same trick with free shipping: the AI kept the old $50 rule and edited the tests. There 57 of 58 pass, because one test was left failing, so E4 is the cleaner example.)

## 2. Run the Gate on the bad changes (1 minute)

Run `python scripts/demo.py` and wait for the E4 and E2 lines, or open their `report.html` files.

Point at E4: **BLOCKED**, "AC-2 failed: returning-customer-01 got a $4.00 discount, expected $0.00". For E2: "AC-2 failed: $74.99 → shipping 0.00, expected 5.99". Say: "The expected value came from the spec, not from the code or an AI. The Gate also says *which* criterion failed, and it routes the change back to the developer."

## 3. Run it on the good change (1 minute)

Open E1's report: **READY, light review**. Say: "Every written example passed on this exact commit, API and browser. A person now skims the evidence for about ten minutes instead of reading the diff."

Point at the screenshot and the footer: "The footer records the commit, so nobody can mistake evidence from another version."

## 4. What the second AI adds (1 minute)

Run `python scripts/demo.py --all --mode saved`, or open the E5 and E3 reports.

- **E5** (the AI also changed a product price nobody asked for): the Challenger flags `app/data/products.json` as covered by no criterion.
- **E3** (the spec leaves "does a guest count?" open): the Challenger raises the question and the verdict is **NEEDS DECISION**, routed to the product owner.

Say: "The second AI can ask questions and point at files. It can never change a result. Labels come from fixed rules."

## 5. Be upfront about limits (1 minute)

Read from [LIMITATIONS.md](LIMITATIONS.md). The honest points: a small set of five cases with planted defects; the Challenger answers were saved, not live; every result depends on the spec's examples being right; and the Challenger sometimes asks more questions than the answer key expects (a false alarm in the evaluation).

## Likely questions

| Question | Answer |
|---|---|
| "Why not just trust the tests?" | The AI wrote them. E4 shows tests edited to match a defect, with all 58 passing. |
| "Why not have an AI judge the code?" | An AI can be wrong and cannot show proof. The Gate only reports what was executed, and fixed rules turn that into a label. |
| "What if the spec is wrong?" | Then the evidence is wrong. The Gate makes the spec the single source of truth, so the review effort moves to checking that one short document. |
| "Does it replace code review?" | No. It decides how much review is needed: light, focused, full, back to the developer, or a decision from the product owner. |
| "Can I use it on my project?" | Yes: [ADOPTION.md](ADOPTION.md), about an hour. |
