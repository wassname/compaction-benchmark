set shell := ["bash", "-euo", "pipefail", "-c"]

candidates:
    mkdir -p outputs
    uv run scripts/01_find_candidate_sessions.py --out outputs/candidate-sessions.csv

copy-source source name:
    uv run scripts/02_copy_source_session.py {{source}} {{name}}

slice-before-first source name:
    uv run scripts/03_slice_before_first_compaction.py {{source}} {{name}}

fast-dev-run:
    mkdir -p /tmp/empty-sessions
    uv run scripts/01_find_candidate_sessions.py --sessions /tmp/empty-sessions --limit 1

run:
    uv run python scripts/benchmark.py run-missing

results:
    uv run python scripts/06_results.py
