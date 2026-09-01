# Pi compaction benchmark

Pi default and [CC Compact](https://github.com/pinion05/pi-cc-compact) are tied for the best complete result. They retain about 6 of 10 facts from before compaction. [Smart Compact](https://github.com/alpertarhan/pi-smart-compact) scored 9 of 10, but only ran on one of three sessions and kept about 93k tokens. It is not a fair winner yet.

This benchmark starts with a real Pi session. A method replaces old messages with a summary. The resumed model then answers 20 questions. `pre` is 10 facts from before the summary. `tail` is 10 facts Pi kept after the cut. The table sorts by `pre`.

All answer calls use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.

| method | n | retained /20 | pre /10 | tail /10 | note |
|---|---:|---:|---:|---:|---|
| baseline, no compaction | 3/3 | 18.7±2.3 | 9.0±1.7 | 9.7±0.6 |  |
| [Smart Compact](https://github.com/alpertarhan/pi-smart-compact) | 3/9 | 19.0±0.0 | 9.0±0.0 | 10.0±0.0 | one session; six native fallbacks; kept 93k tokens |
| Pi default | 9/9 | 15.0±2.6 | 6.2±1.9 | 8.8±1.2 |  |
| [CC Compact](https://github.com/pinion05/pi-cc-compact) | 8/9 | 15.5±2.4 | 6.1±2.5 | 9.4±0.5 | 1 grade missing |
| [Lab report](https://github.com/nicobailon/pi-custom-compaction) | 9/9 | 14.6±3.2 | 5.2±2.3 | 9.3±1.1 |  |
| [Handoff](https://github.com/nicobailon/pi-custom-compaction) | 8/9 | 13.5±2.9 | 4.9±1.8 | 8.6±1.3 | 1 grade missing |
| [Blackhole](https://github.com/k0valik/pi-blackhole) | 9/9 | 13.0±3.1 | 3.2±3.1 | 9.8±0.4 | `tailBehavior=pi-default` |
| [Context Fold](https://github.com/Middlewatch/context-fold) | 9/9 | 11.3±3.9 | 3.1±2.8 | 8.2±1.6 |  |

`n` is graded runs / intended runs. Values are mean±sample SD. Missing grades are excluded from means.

<!-- PI[openai-codex] -->
