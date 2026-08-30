# Handover: compaction benchmark

## Goal

Compare Pi compaction methods by factual recall after a real session is compacted and resumed.

## Completed

- Repository: `/workspace/2026/compaction-benchmark`
- Commit: `52b512e Set up pre-compaction recall benchmark`
- Three private fixtures are copied into ignored `data/fixtures/`.
- Each fixture contains only entries before its source session's first `compaction` entry.

| Fixture | Entries | Tokens before source compaction |
| --- | ---: | ---: |
| `jsteer-publication` | 422 | 205,950 |
| `lucid3-first` | 83 | 203,778 |
| `lucid-aug20` | 319 | 67,799 |

## Important rule

Do not ask for facts inside the session under test before compacting it. That request can stay in the recent tail and make recall look better than it is.

Generate a fact list with evidence in a separate evaluator session. Save it in the fixture directory as `gold.json`. Then copy the untouched `source.jsonl` into each method's run directory.

## Next actions

1. Create 10 to 20 durable, source-evidenced facts for each fixture.
2. Implement a script that copies a fixture into `data/runs/<fixture>/<method>/session.jsonl`.
3. Run each copy with `pi --no-extensions` plus only the compactor under test.
4. Compact, submit the fixed recall prompt, and save the follow-up answer.
5. Score retained, distorted, missing, and invented facts.

## Temporary extension pattern

```sh
pi --no-extensions \
  -e npm:@lll9p/pi-better-compaction \
  --session data/runs/<fixture>/better-compaction/session.jsonl
```

`--no-extensions` prevents other discovered compaction handlers from competing. The explicit `-e` extension still loads. The temporary package reads its normal configuration, so copy that configuration into the run output before executing.

## Source files

- `scripts/01_find_candidate_sessions.py`
- `scripts/02_copy_source_session.py`
- `scripts/03_slice_before_first_compaction.py`
- `README.md`

<!-- Drafted by Claude for wassname to review. -->
