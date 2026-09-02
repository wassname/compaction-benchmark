# OpenAI native compaction

This table is separate from the DeepSeek benchmark. Both rows compact and answer with `openai-codex/gpt-5.6-terra`, `openai-codex-responses`, high thinking.

| method | pre /10 | retained /20 | n | compaction state | resumed-request evidence |
|---|---:|---:|---:|---|---|
| Pi default text summary | 5.7±2.6 | 14.5±1.5 | 6/6 | text summary | not applicable |
| OpenAI native V2 (local endpoint/replay patch) | 6.0±3.2 | 13.2±2.0 | 6/6 | V2 native 6/6 | native replay 6/6 |

`pre` counts the ten facts before the historical compaction boundary. Values are mean±sample SD. OpenAI V2 state is encrypted and opaque, so this table does not present it as a text-summary token count. The native row uses a local endpoint/replay patch; stock V2 returned `Store must be set to false` in this setup. `native replay` counts answer requests whose extension artifact recorded `before_provider_request.native-rewrite`. These rows grade fact recall only; invented-claim checks remain in judge calibration but are skipped for this large-source recall table.
