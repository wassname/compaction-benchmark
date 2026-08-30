# Research journal

## 2026-08-30 -- Paused during judge calibration

This entry records the compaction benchmark state for the next agent.

The benchmark compares factual recall after Pi compacts and resumes three real sessions. The active plan is `.pi/plan/01a05036-efe8-72e8-b229-c1c06d947df8-v1.md`. Commit `c458f2a` contains the isolated runner and judge panel. The next handover checkpoint adds the split judge passes and this state record.

### Completed evidence

Goal 1 is signed off. Its machine-generated validation records the uncompacted baseline counts as follows:

> `jsteer-publication`: `"retained": 20`  
> `lucid-aug20`: `"retained": 19`  
> `lucid3-first`: `"retained": 19`

Source: `outputs/benchmark/validation/goal1-validation.json:10-12,29-31,48-50`. Each fixture has twenty evidence-backed gold facts, split into ten pre-compaction facts and ten retained-tail controls. The plan contains the accepted goal evidence and sign-off.

Goal 2 is active and is not signed off. The latest local unit-test run says:

> `Ran 15 tests in 0.089s`  
> `OK`

Source: `outputs/benchmark/validation/handover-tests.log:18-20`.

The final smoke artifacts for native Pi and `pi-cc-compact@0.1.0` both pass the current `validate-run` command. Both records bind to methods manifest hash `96619a1f5390d235ced96b8fd2bab24889a613b507955cb0a1c664d48c59d7d2`. Native Pi reports `from_hook: false` and an estimated post-compaction size of 21,734 tokens. `pi-cc-compact` reports `from_hook: true`, source `pi-cc-compact`, and an estimated post-compaction size of 24,406 tokens. Source: `outputs/benchmark/validation/handover-run-validation.log:1-44`.

### Blocking evidence

Judge calibration version three rejected every judge seat:

> `benchmark error: lucid-aug20: only 0 judges passed calibration`

Source: `outputs/benchmark/validation/judge-calibration-v3-lucid-aug20.log:1`. The detailed line shows missed invented claims, incorrect retained or distorted labels, invalid citations, and malformed fact counts across the five seats.

A fresh reviewer reported five priority-one blocking findings and concluded:

> `Merge verdict: BLOCK`

The five findings are:

1. Grades do not record the exact calibrated judge subset.
2. A compaction extension can mutate the original session prefix without detection.
3. Stale or cross-trial artifacts can pass validation because embedded fixture, method, trial, and commands are not checked.
4. The runner disables `pi-blackhole` cold-load memory during recall, so the declared full method and measured method differ.
5. The harness asserts the Pi version and npm integrity values instead of measuring them at runtime.

Source: `outputs/benchmark/validation/goal2-review.log:2495-2505`.

### Split judge checkpoint

`scripts/benchmark.py` now separates judge work into two prompts. The first prompt compares each candidate answer with its gold answer and assigns retained, distorted, or missing. The second prompt compares the candidate with the full source and reports unsupported claims. Both prompts run as separate turns in the same fresh judge session. The local unit tests pass, but no live calibration has tested this split design.

The tracked working tree is clean at the handover checkpoint. `.pi/judge/` and `.vscode/` remain untracked and must not be committed. There are no running benchmark processes.

### Next

First add focused tests and fix the five reviewer findings. Then rerun judge calibration on `lucid-aug20`. Accept a judge seat only when it passes every calibration answer, and require at least four eligible seats as specified by the plan. If the split prompt still fails, inspect the separate fact and invention artifacts before changing the rubric.

My read: the isolated compaction runner is probably sound enough to continue from, but method rankings are not yet credible because calibration and provenance validation still fail. Do not start the full method matrix until Goal 2 receives sign-off.

The immediate task is to make Goal 2 evidence trustworthy before spending model calls on the full benchmark.

_Written by Claude for wassname to review._
