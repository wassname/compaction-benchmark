#!/usr/bin/env python3
"""Generate the public result table from saved grades. (PI[openai-codex])"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
OUTPUTS = ROOT / "outputs" / "benchmark"
README = ROOT / "README.md"
METHODS = json.loads((ROOT / "methods.json").read_text())["methods"]
FIXTURES = sorted(path.name for path in (ROOT / "data" / "fixtures").iterdir() if (path / "gold.json").is_file())

LABELS = {
    "uncompacted-baseline": "baseline, no compaction",
    "pi-default": "Pi default",
    "pi-smart-compact": "[Smart Compact](https://github.com/alpertarhan/pi-smart-compact)",
    "pi-cc-compact": "[CC Compact](https://github.com/pinion05/pi-cc-compact)",
    "pi-custom-lab-report": "[Lab report](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-custom-handoff": "[Handoff](https://github.com/nicobailon/pi-custom-compaction)",
    "pi-blackhole": "[Blackhole](https://github.com/k0valik/pi-blackhole)",
    "context-fold": "[Context Fold](https://github.com/Middlewatch/context-fold)",
}


def values(path: Path) -> tuple[int, int, int]:
    facts = json.loads(path.read_text())["facts"]
    retained = sum(fact["grade"] == "retained" for fact in facts)
    pre = sum(fact["grade"] == "retained" and fact["id"] <= "fact-10" for fact in facts)
    tail = sum(fact["grade"] == "retained" and fact["id"] > "fact-10" for fact in facts)
    return retained, pre, tail


def mean_sd(items: list[int]) -> str:
    return f"{statistics.mean(items):.1f}±{statistics.stdev(items) if len(items) > 1 else 0.0:.1f}"


def grade_paths(method: str) -> list[Path]:
    trials = (1,) if method == "uncompacted-baseline" else (1, 2, 3)
    return [RUNS / fixture / method / f"trial-{trial:02d}" / "grade.json" for fixture in FIXTURES for trial in trials]


def row(method: str) -> tuple[float, str]:
    paths = grade_paths(method)
    scored = [values(path) for path in paths if path.is_file()]
    intended = len(paths)
    retained, pre, tail = zip(*scored)
    missing = intended - len(scored)
    if method == "pi-smart-compact":
        compact = RUNS / "lucid3-first" / method / "trial-01" / "compaction.json"
        kept = round(json.loads(compact.read_text())["response"]["estimatedTokensAfter"] / 1000)
        note = f"one session; six native fallbacks; kept {kept}k tokens"
    elif missing:
        note = f"{missing} grade missing"
    elif method == "pi-blackhole":
        note = "`tailBehavior=pi-default`"
    else:
        note = ""
    return statistics.mean(pre), f"| {LABELS[method]} | {len(scored)}/{intended} | {mean_sd(list(retained))} | {mean_sd(list(pre))} | {mean_sd(list(tail))} | {note} |"


def main() -> None:
    methods = ["uncompacted-baseline", *[name for name, spec in METHODS.items() if spec["classification"].startswith("comparable")]]
    rows = [row(method) for method in methods]
    baseline, compared = rows[0], sorted(rows[1:], key=lambda item: item[0], reverse=True)
    README.write_text("\n".join([
        "# Pi compaction benchmark",
        "",
        "Pi default and [CC Compact](https://github.com/pinion05/pi-cc-compact) are tied for the best complete result. They retain about 6 of 10 facts from before compaction. [Smart Compact](https://github.com/alpertarhan/pi-smart-compact) scored 9 of 10, but only ran on one of three sessions and kept about 93k tokens. It is not a fair winner yet.",
        "",
        "This benchmark starts with a real Pi session. A method replaces old messages with a summary. The resumed model then answers 20 questions. `pre` is 10 facts from before the summary. `tail` is 10 facts Pi kept after the cut. The table sorts by `pre`.",
        "",
        "All answer calls use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.",
        "",
        "| method | n | retained /20 | pre /10 | tail /10 | note |",
        "|---|---:|---:|---:|---:|---|",
        baseline[1],
        *[item[1] for item in compared],
        "",
        "`n` is graded runs / intended runs. Values are mean±sample SD. Missing grades are excluded from means.",
        "",
        "<!-- PI[openai-codex] -->",
        "",
    ]))
    print(README)


if __name__ == "__main__":
    main()
