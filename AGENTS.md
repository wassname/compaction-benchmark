# AGENTS.md

This repository tests real Pi session continuity after compaction.

- Do not modify a source session in place.
- Build gold facts outside the target session, before the compaction run.
- Run each compactor in a separate `PI_CODING_AGENT_DIR` so extension state cannot leak between methods.
- Store raw sessions and model transcripts in ignored `data/` and `outputs/`.
- A recall answer is evidence only when its source session was compacted and then resumed for a follow-up turn.
