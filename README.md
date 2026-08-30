# compaction-benchmark

This repository tests whether a compaction method lets a resumed Pi session recover durable facts from a real research conversation.

The input for an experiment is the prefix of a historical session that ends immediately before its first compaction entry. It is a long live transcript that has never been compacted. Each compaction method receives a separate copy of that exact input.

## What is measured

The main score is a set of 10 to 20 facts that the resumed model can state after compaction. Each fact has source evidence in the untouched fixture.

| Result | Meaning |
| --- | --- |
| retained | The response states the fact and does not change its meaning. |
| distorted | The response states a related claim but changes a material detail. |
| missing | The response does not state the fact. |
| invented | The response adds a material claim with no fixture evidence. |

Latency, compaction size, and output tokens are recorded. They are diagnostics, not the quality score.

## Protocol

1. Find candidate sessions from user messages that contain `architecture`, `archetecture`, `arxiv.org`, `predict`, or `plot`.
2. Copy one source session into `data/source/`.
3. Slice it at the first compaction entry. The fixture is only the preceding entries.
4. In a separate evaluator session, read the fixture and write the 10 to 20 evidence-backed recall facts in `gold.json`.
5. Copy `source.jsonl` once per compaction method.
6. Start Pi on one copy with only the method under test loaded. Trigger `/compact`.
7. In the resumed session, ask the fixed recall questions. Save the answer and score it against `gold.json`.

The target session must not receive the gold facts before compaction. A pre-compaction request for facts would create a recent message that may be preserved verbatim and inflate recall.

## Candidate sessions

The first two fixtures are selected from local sessions:

| Name | Session | First compaction input |
| --- | --- | ---: |
| `jsteer-publication` | J-steer publication session, 213 user turns and 74 user mentions of `plot` | 422 entries, 205,950 tokens |
| `lucid3-first` | LUCID3 research session | 83 entries, 203,778 tokens |
| `lucid-aug20` | LUCID research session with architecture and prediction discussion | 319 entries, 67,799 tokens |

## Build fixtures

```sh
just candidates
just copy-source ~/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/2026-08-27T01-23-11-091Z_01a040d0-5873-7fb3-9e57-13b7a96fd8bb.jsonl jsteer-publication
just slice-before-first data/source/jsteer-publication.jsonl jsteer-publication
```

`data/` and `outputs/` are ignored because they contain private session content.

## Run one method temporarily

Pi can disable discovered extensions and load only an explicit extension. This prevents blackhole, custom compaction, and the tested extension from competing for the same `session_before_compact` event.

```sh
# Pi default compaction only
pi --no-extensions --session data/runs/pi-default/session.jsonl

# One temporary extension. It is loaded for this process only.
pi --no-extensions \
  -e npm:@lll9p/pi-better-compaction \
  --session data/runs/better-compaction/session.jsonl
```

Inside each interactive run, enter `/compact`, wait for it to complete, then submit the fixed recall prompt. The resulting session file and response are the evidence for that row.

The temporary extension still reads its normal config file. Record that file with the result. Do not change an extension configuration between rows without recording the change.

## Next implementation

- `scripts/04_make_run_copy.py`: create a run directory and copy a fixture session.
- `scripts/05_validate_run.py`: verify that a run contains one new compaction and one later recall response.
- `scripts/06_score_recall.py`: compare a response with the fact list and emit a review table.

<!-- Drafted by Claude for wassname to review. -->
