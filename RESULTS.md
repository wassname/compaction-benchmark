# DeepSeek compaction results

All answers use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.
`pre` is the ten facts before Pi's cut. `tail` is the ten facts kept after the cut. The table sorts by mean `pre`.

| method | n | retained /20 | pre /10 | tail /10 | missing or fallback |
|---|---:|---:|---:|---:|---|
| `baseline — no compaction` | 3/3 | 18.7±2.3 | 9.0±1.7 | 9.7±0.6 |  |
| `pi-smart-compact` | 3/9 | 19.0±0.0 | 9.0±0.0 | 10.0±0.0 | 6 missing grade(s); see below |
| `pi-default` | 9/9 | 15.0±2.6 | 6.2±1.9 | 8.8±1.2 |  |
| `pi-cc-compact` | 8/9 | 15.5±2.4 | 6.1±2.5 | 9.4±0.5 | 1 missing grade(s); see below |
| `pi-custom-lab-report` | 9/9 | 14.6±3.2 | 5.2±2.3 | 9.3±1.1 |  |
| `pi-custom-handoff` | 8/9 | 13.5±2.9 | 4.9±1.8 | 8.6±1.3 | 1 missing grade(s); see below |
| `pi-blackhole` | 9/9 | 13.0±3.1 | 3.2±3.1 | 9.8±0.4 |  |
| `context-fold` | 9/9 | 11.3±3.9 | 3.1±2.8 | 8.2±1.6 |  |

`n` is graded runs / intended runs. Values are mean±sample SD. A missing grade is not included in a mean.

## Missing grades

- `data/runs/jsteer-publication/pi-smart-compact/trial-01/grade.json`: jsteer-publication/pi-smart-compact: unexpected compaction owner
- `data/runs/jsteer-publication/pi-smart-compact/trial-02/grade.json`: jsteer-publication/pi-smart-compact: unexpected compaction owner
- `data/runs/jsteer-publication/pi-smart-compact/trial-03/grade.json`: jsteer-publication/pi-smart-compact: unexpected compaction owner
- `data/runs/lucid-aug20/pi-smart-compact/trial-01/grade.json`: lucid-aug20/pi-smart-compact: unexpected compaction owner
- `data/runs/lucid-aug20/pi-smart-compact/trial-02/grade.json`: lucid-aug20/pi-smart-compact: unexpected compaction owner
- `data/runs/lucid-aug20/pi-smart-compact/trial-03/grade.json`: lucid-aug20/pi-smart-compact: unexpected compaction owner
- `data/runs/lucid-aug20/pi-cc-compact/trial-03/grade.json`: lucid-aug20: only 0 judge seats succeeded
- `data/runs/jsteer-publication/pi-custom-handoff/trial-03/grade.json`: jsteer-publication: only 0 judge seats succeeded

## Other compaction designs

| method | protocol | reason outside headline ranking |
|---|---|---|
| `pi-async-compaction` | early scheduling | uses Pi's native summary; changes timing, not summary method |
| `pi-session-handover` / Agenticoding handoff | new-session or task-only handoff | does not retain the same compacted context |
| provider-native compaction | provider protocol | needs its own run and grading path |
| retrieval/memory systems | retrieval | recall tools are disabled in this benchmark |
