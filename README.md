# Pi compaction benchmark

I wanted to know which compaction is the best for pi. So I evaluated this way

- find some complex pi sessions
- rewind to just before first compact
- ask "What are 10 critical facts" and record these as the ideal answers
- for N=3
  - for all pi compaction candidated,
    - copy the session and compact
    - ask them question about the facts,
    - judge: how many facts did they recall correctly?

So you can see below that the baseline is "don't compact at all" and that recalls 9/10 facts, while pi default recalls 6/10 facts (worse). But of course we do need to compact or we will get context rot, or hit the token limit.

Conclusions: pi's default compaction is good, as is the leaked claude code compaction.

All answer calls use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.

| method | pre /10 | context after | n | retained /20 | note |
|---|---:|---:|---:|---:|---|
| baseline, no compaction | 9.0±1.7 | 159.2±79.1k | 3/3 | 18.7±2.3 |  |
| Pi default | 6.2±1.9 | 21.3±2.3k | 9/9 | 15.0±2.6 |  |
| [CC Compact](https://github.com/pinion05/pi-cc-compact) | 6.1±2.5 | 21.7±2.6k | 8/9 | 15.5±2.4 | 1 grade missing |
| [Lab report + DeepSeek high](https://github.com/nicobailon/pi-custom-compaction) | 5.8±2.5 | 20.9±2.4k | 9/9 | 15.0±2.7 |  |
| [Pi prompt + Kimi K3 high](https://github.com/nicobailon/pi-custom-compaction) | 5.4±2.0 | 21.1±2.3k | 9/9 | 15.0±2.2 |  |
| [Lab report](https://github.com/nicobailon/pi-custom-compaction) | 5.2±2.3 | 20.7±2.1k | 9/9 | 14.6±3.2 |  |
| [MoA: Kimi, Gemini, DeepSeek → Luna](https://github.com/NousResearch/hermes-agent/blob/c83ea9bed7cac19a0e119c0e3832624f86979531/agent/moa_loop.py#L1330) | 5.2±2.2 | 21.0±2.3k | 9/9 | 13.2±1.5 |  |
| [Handoff](https://github.com/nicobailon/pi-custom-compaction) | 4.9±1.8 | 20.3±2.2k | 8/9 | 13.5±2.9 | 1 grade missing |
| [Lab report + Kimi K3 high](https://github.com/nicobailon/pi-custom-compaction) | 4.6±2.8 | 21.0±2.0k | 8/9 | 12.4±5.2 | 1 grade missing |
| [Blackhole](https://github.com/k0valik/pi-blackhole) | 3.2±3.1 | 23.1±5.7k | 9/9 | 13.0±3.1 | `tailBehavior=pi-default` |
| [Context Fold](https://github.com/Middlewatch/context-fold) | 3.1±2.8 | 21.3±2.0k | 9/9 | 11.3±3.9 |  |
| [Smart Compact](https://github.com/alpertarhan/pi-smart-compact) | 1.7±0.6 | 18.2±0.0k | 3/9 | 11.7±0.6 | 6 command failures |

`context after` is Pi's estimated retained raw context plus summary. `n` is graded runs / intended runs. Values are mean±sample SD. Missing grades are excluded from means.

[Smart Compact](https://github.com/alpertarhan/pi-smart-compact) uses its manual `fast` command. It reached 18k context on one fixture but failed to create a compaction in six runs.

## OpenAI native compaction

This separate check uses [pi-better-compaction](https://github.com/wassname/pi-better-compaction) with `openai-codex/gpt-5.6-terra`, the OpenAI Responses API, and high thinking. Native V2 compacted and replayed encrypted state in all six native runs.

| method | pre /10 | retained /20 | n | compaction state | resumed-request evidence |
|---|---:|---:|---:|---|---|
| Pi default text summary | 5.7±2.6 | 14.5±1.5 | 6/6 | text summary | not applicable |
| OpenAI native V2 (local endpoint/replay patch) | 6.0±3.2 | 13.2±2.0 | 6/6 | V2 native 6/6 | native replay 6/6 |

These are fact-recall grades only. The native row uses a local endpoint/replay patch.

<!-- PI[openai-codex]: OpenAI native table -->
<!-- PI[openai-codex] -->
