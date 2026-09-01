# Research journal

## 2026-09-01 — DeepSeek result

The public result table is generated into `README.md` by `just results` from ignored `data/runs/*/grade.json` files.

The benchmark runs a forced Pi compaction, resumes the session, then asks 20 fixed questions. Ten questions have evidence before the cut (`pre`). Ten have evidence after the cut (`tail`). `pre` is the ranking measure. `tail` checks that the kept session suffix survived.

The three source sessions and all run transcripts are ignored. The tracked `data/fixtures/*/gold.json` files contain the 20 source-derived questions and evidence quotes for each fixture.

Smart Compact has 3/9 grades, all from `lucid3-first`. Its valid runs retained about 93k tokens, compared with 17–20k for the other methods on that fixture. Do not compare its mean with the complete rows.

The named missing grades are saved in ignored `outputs/benchmark/*/failure.json`. They are excluded from means.

## 2026-08-30 — Historical checkpoint

Judge calibration and provenance checks were being repaired before the full method matrix. The final runner, prompt variants, and DeepSeek result replaced this checkpoint. Commit history contains the earlier implementation details.
