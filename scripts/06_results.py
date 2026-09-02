#!/usr/bin/env python3
"""Generate the public result table from saved grades. (PI[openai-codex])"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
README = ROOT / "README.md"
METHODS = json.loads((ROOT / "methods.json").read_text())["methods"]
FIXTURES = sorted(path.name for path in (ROOT / "data" / "fixtures").iterdir() if (path / "gold.json").is_file())

LABELS = {
    "uncompacted-baseline": "baseline, no compaction",
    "pi-default": "Pi default",
    "pi-smart-compact": "[Smart Compact](https://github.com/alpertarhan/pi-smart-compact)",
    "pi-cc-compact": "[CC Compact](https://github.com/pinion05/pi-cc-compact)",
    "pi-custom-lab-report": "[Lab report](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-custom-lab-report-kimi-k3-high": "[Lab report + Kimi K3 high](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-custom-lab-report-deepseek-high": "[Lab report + DeepSeek high](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-custom-handoff": "[Handoff](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-blackhole": "[Blackhole](https://github.com/k0valik/pi-blackhole)",
    "context-fold": "[Context Fold](https://github.com/Middlewatch/context-fold)",
}


def values(path: Path) -> tuple[int, int]:
    facts = json.loads(path.read_text())["facts"]
    retained = sum(fact["grade"] == "retained" for fact in facts)
    pre = sum(fact["grade"] == "retained" and fact["id"] <= "fact-10" for fact in facts)
    return retained, pre


def mean_sd(items: list[int], scale: float = 1) -> str:
    return f"{statistics.mean(items) / scale:.1f}±{(statistics.stdev(items) if len(items) > 1 else 0.0) / scale:.1f}"


def grade_paths(method: str) -> list[Path]:
    trials = (1,) if method == "uncompacted-baseline" else (1, 2, 3)
    return [RUNS / fixture / method / f"trial-{trial:02d}" / "grade.json" for fixture in FIXTURES for trial in trials]


def tokens_after(method: str, grade_files: list[Path]) -> list[int]:
    if method == "uncompacted-baseline":
        return [
            json.loads((ROOT / "data" / "fixtures" / fixture / "manifest.json").read_text())["first_compaction"]["tokens_before"]
            for fixture in FIXTURES
        ]
    return [
        json.loads(path.with_name("compaction.json").read_text())["response"]["estimatedTokensAfter"]
        for path in grade_files
    ]


def row(method: str) -> tuple[float, str]:
    paths = grade_paths(method)
    grade_files = [path for path in paths if path.is_file()]
    retained, pre = zip(*(values(path) for path in grade_files))
    missing = len(paths) - len(grade_files)
    if method == "pi-smart-compact" and missing:
        note = f"{missing} command failures"
    elif missing:
        note = f"{missing} grade missing"
    elif method == "pi-blackhole":
        note = "`tailBehavior=pi-default`"
    else:
        note = ""
    tokens = tokens_after(method, grade_files)
    return statistics.mean(pre), f"| {LABELS[method]} | {mean_sd(list(pre))} | {mean_sd(tokens, 1000)}k | {len(grade_files)}/{len(paths)} | {mean_sd(list(retained))} | {note} |"


def main() -> None:
    methods = [
        "uncompacted-baseline",
        *[
            name
            for name, spec in METHODS.items()
            if spec["classification"].startswith("comparable")
        ],
    ]
    rows = [row(method) for method in methods]
    baseline, compared = rows[0], sorted(rows[1:], key=lambda item: item[0], reverse=True)
    README.write_text("\n".join([
        "# Pi compaction benchmark",
        "",
        "Pi default and [CC Compact](https://github.com/pinion05/pi-cc-compact) are tied for the best complete result. The Kimi K3 and DeepSeek high rows are pending.",
        "",
        "This benchmark starts with a real Pi session. A method replaces old messages with a summary. The resumed model then answers 20 questions. `pre` is 10 facts from before the summary. The table sorts by `pre`.",
        "",
        "All answer calls use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.",
        "",
        "| method | pre /10 | tokens after | n | retained /20 | note |",
        "|---|---:|---:|---:|---:|---|",
        baseline[1],
        *[item[1] for item in compared],
        "",
        "`tokens after` is estimated session context after compaction. `n` is graded runs / intended runs. Values are mean±sample SD. Missing grades are excluded from means.",
        "",
        "[Smart Compact](https://github.com/alpertarhan/pi-smart-compact) uses its manual `fast` command. It reached 18k tokens on one fixture but failed to create a compaction in six runs.",
        "",
        "<!-- PI[openai-codex] -->",
        "",
    ]))
    print(README)


if __name__ == "__main__":
    main()
