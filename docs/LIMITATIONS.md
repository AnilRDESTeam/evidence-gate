# Limitations

What the Gate did in the evaluation, where it fell short, and what it does not try to do. Numbers come from `eval/results.csv` (5 cases, 5 runs each, in each of two modes) and can be reproduced with `python eval/run_eval.py`.

## What was measured

| | Challenger off | Challenger saved |
|---|---|---|
| Defective changes missed (expected BLOCKED, got READY) | 0 of 2 (E2, E4) | 0 of 2 |
| Defective changes routed to light review | 0 | 0 |
| Correct changes wrongly BLOCKED | 0 | 0 |
| Correct changes held up by questions (expected READY, got NEEDS DECISION) | 0 of 2 (E1, E5) | **2 of 2** (E1, E5) |
| Results identical across 5 runs | 100% in every case | 100% in every case |
| Runs routed to light review | 20% (5 of 25; E1) | 0% |
| E3 (open questions expected) | READY, focused review: **missed the questions** | NEEDS DECISION, as expected |

Both planted defects were caught and named the right criterion in both modes: E2 (old $50 rule kept) failed AC-2, AC-3 and AC-4; E4 (returning customer discounted) failed AC-2.

## Where it fell short

- **The Challenger raised many questions on correct changes.** In saved mode it asked 6 to 9 questions on every change, including the correct E1 and E5. Open questions send a change to the product owner (NEEDS DECISION) ahead of any review route, so two correct changes were held up, and none was routed to light review in saved mode. This is a false alarm against the answer key (`question_expected: no`). Most of its questions were reasonable ("is the threshold checked before or after discounts?") but the spec did not need them answered for these changes. A stricter Challenger prompt, or a rule that only questions the spec could answer count, would be the next step. It was not tuned here, on purpose, so the result stays honest.
- **Questions turn Verified into Needs human review.** When the Challenger links a question to a criterion, that criterion is labelled "Needs human review" even though its examples passed (for example E1 AC-1 and AC-4). The rules say so, but it makes the report look less certain than the evidence is.
- **E3 is only caught with the Challenger.** With the Challenger off, the Gate cannot know the spec leaves "does a guest count as a new customer?" open, and reports READY (focused review). Putting the question in the spec's `open_questions` fixes it, but then a person has to have thought of it.
- **The extra change in E5 is flagged, not judged.** In both modes the unrequested price change to `app/data/products.json` shows up as "changed, covered by no criterion". With the Challenger off this gives the expected focused review. In saved mode the question volume hides it behind NEEDS DECISION. The Gate does not decide whether the extra change is wrong, only that nobody asked for it.

## How far the evidence goes

- **Five cases, three kinds of defect.** E1 and E3 are correct changes. E2 and E4 are **planted** defects (one commit each, written by the person or assistant building the evaluation, not by a coding AI trying to be correct). E5 is an **induced** one: the coding prompt itself asked for the extra price change. This shows the Gate catches these defects. It does not show how often real AI code has them.
- **The Challenger was saved, not live.** Its answers were produced once by separate AI agents that saw only the prompt, and then replayed. **Variation between live Challenger runs was not measured.** The "100% identical across 5 runs" figure therefore only shows that the engine, the shop and the browser checks are deterministic. It says nothing about AI variation.
- **Same model family throughout.** The Challenger answers, the code for E3, and the engine were all produced by Claude models. Different families would be a stronger test of independence.
- **The answer key was written before the first run**, by one person. It has not been reviewed by anyone else.
- **E2's planted commit left one of the shop's own tests failing** (57 of 58 pass), so E2 is not a pure "tests adjusted to match" case. E4 is: all 58 pass while the defect is present.
- **Spot checks of light-routed cases are not done yet.** E1 is the only change routed to light review (see `eval/spotchecks.csv`); a person still has to confirm it by hand.

## What the Gate does not do

- **Security, performance, accessibility and visual layout** are out of scope. It checks behaviour against written examples.
- **It only proves what the spec's examples cover.** A defect in a situation no example reaches is invisible to it. The examples must sit on both sides of each boundary and include a negative case, or a bug can pass.
- **Expected values are only as good as the spec.** If the spec is wrong, the evidence is wrong. The Gate moves the review effort to that one short document; it does not remove the need for it to be right.
- **Browser checks depend on stable `data-testid`s.** If a team renames them, the receipt check says "could not run" until the adapter is updated. It never guesses.
- **The app must report its git commit** (a health endpoint) and be restarted on each branch. Otherwise results are "could not run", by design.
- **The "existing tests" line is context only** and depends on pytest printing its summary line. A `-q` in both the command and the project's `pytest.ini` hides it; the Gate then warns instead of guessing.
- **It decides how much review a change needs. It never removes human review**, and a READY verdict is not a merge approval.
