# Pi compaction benchmark

Pi default and [CC Compact](https://github.com/pinion05/pi-cc-compact) are tied for the best complete result. They retain about 6 of 10 facts from before compaction.

This benchmark starts with a real Pi session. A method replaces old messages with a summary. The resumed model then answers 20 questions. `pre` is 10 facts from before the summary. The table sorts by `pre`.

All answer calls use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.

| method | pre /10 | tokens after | n | retained /20 | note |
|---|---:|---:|---:|---:|---|
| baseline, no compaction | 9.0±1.7 | 159.2±79.1k | 3/3 | 18.7±2.3 |  |
| Pi default | 6.2±1.9 | 21.3±2.3k | 9/9 | 15.0±2.6 |  |
| [CC Compact](https://github.com/pinion05/pi-cc-compact) | 6.1±2.5 | 21.7±2.6k | 8/9 | 15.5±2.4 | 1 grade missing |
| [Lab report](https://github.com/nicobailon/pi-custom-compaction) | 5.2±2.3 | 20.7±2.1k | 9/9 | 14.6±3.2 |  |
| [Handoff](https://github.com/nicobailon/pi-custom-compaction) | 4.9±1.8 | 20.3±2.2k | 8/9 | 13.5±2.9 | 1 grade missing |
| [Blackhole](https://github.com/k0valik/pi-blackhole) | 3.2±3.1 | 23.1±5.7k | 9/9 | 13.0±3.1 | `tailBehavior=pi-default` |
| [Context Fold](https://github.com/Middlewatch/context-fold) | 3.1±2.8 | 21.3±2.0k | 9/9 | 11.3±3.9 |  |
| [Smart Compact](https://github.com/alpertarhan/pi-smart-compact) | 1.7±0.6 | 18.2±0.0k | 3/9 | 11.7±0.6 | 6 command failures |

`tokens after` is estimated session context after compaction. `n` is graded runs / intended runs. Values are mean±sample SD. Missing grades are excluded from means.

[Smart Compact](https://github.com/alpertarhan/pi-smart-compact) uses its manual `fast` command. It reached 18k tokens on one fixture but failed to create a compaction in six runs.

<!-- PI[openai-codex] -->
