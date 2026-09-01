#!/usr/bin/env python3
"""Generate the DeepSeek compaction results table from saved panel grades. (claude)"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "runs"
OUTPUTS = ROOT / "outputs" / "benchmark"
RESULTS = ROOT / "RESULTS.md"
METHODS = json.loads((ROOT / "methods.json").read_text())["methods"]
FIXTURES = sorted(path.name for path in (ROOT / "data" / "fixtures").iterdir() if (path / "gold.json").is_file())


def grade_values(path: Path) -> tuple[int, int, int]:
    grade = json.loads(path.read_text())
    facts = grade["facts"]
    retained = sum(fact["grade"] == "retained" for fact in facts)
    pre = sum(fact["grade"] == "retained" and fact["id"] <= "fact-10" for fact in facts)
    tail = sum(fact["grade"] == "retained" and fact["id"] > "fact-10" for fact in facts)
    return retained, pre, tail


def mean_sd(values: list[int]) -> str:
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{mean:.1f}±{sd:.1f}"


def row(method: str, label: str, intended: int) -> tuple[float, str, list[str]]:
    values: list[tuple[int, int, int]] = []
    missing: list[str] = []
    for fixture in FIXTURES:
        trials = (1,) if method == "uncompacted-baseline" else (1, 2, 3)
        for trial in trials:
            grade = RUNS / fixture / method / f"trial-{trial:02d}" / "grade.json"
            if grade.is_file():
                values.append(grade_values(grade))
                continue
            failure = OUTPUTS / fixture / method / f"trial-{trial:02d}" / "failure.json"
            error = json.loads(failure.read_text())["error"] if failure.is_file() else "no grade.json"
            missing.append(f"`data/runs/{fixture}/{method}/trial-{trial:02d}/grade.json`: {error}")
    note = f"{len(missing)} missing grade(s); see below" if missing else ""
    if not values:
        return -1.0, f"| `{label}` | 0/{intended} | — | — | — | {note} |", missing
    retained, pre, tail = zip(*values)
    return statistics.mean(pre), f"| `{label}` | {len(values)}/{intended} | {mean_sd(list(retained))} | {mean_sd(list(pre))} | {mean_sd(list(tail))} | {note} |", missing


def main() -> None:
    rows = [row("uncompacted-baseline", "baseline — no compaction", len(FIXTURES))]
    for name, method in METHODS.items():
        if method["classification"].startswith("comparable"):
            rows.append((name, *row(name, name, len(FIXTURES) * 3)))
    baseline = rows[:1]
    ranked = sorted(rows[1:], key=lambda item: item[1], reverse=True)
    lines = [
        "# DeepSeek compaction results",
        "",
        "All answers use `openrouter/deepseek/deepseek-v4-flash-0731:fp8` at `medium`.",
        "`pre` is the ten facts before Pi's cut. `tail` is the ten facts kept after the cut. The table sorts by mean `pre`.",
        "",
        "| method | n | retained /20 | pre /10 | tail /10 | missing or fallback |",
        "|---|---:|---:|---:|---:|---|",
        baseline[0][1],
        *[item[2] for item in ranked],
        "",
        "`n` is graded runs / intended runs. Values are mean±sample SD. A missing grade is not included in a mean.",
        "",
        "## Missing grades",
        "",
        *[f"- {missing}" for item in baseline for missing in item[2]],
        *[f"- {missing}" for item in ranked for missing in item[3]],
        "",
        "## Other compaction designs",
        "",
        "| method | protocol | reason outside headline ranking |",
        "|---|---|---|",
        "| `pi-async-compaction` | early scheduling | uses Pi's native summary; changes timing, not summary method |",
        "| `pi-session-handover` / Agenticoding handoff | new-session or task-only handoff | does not retain the same compacted context |",
        "| provider-native compaction | provider protocol | needs its own run and grading path |",
        "| retrieval/memory systems | retrieval | recall tools are disabled in this benchmark |",
    ]
    RESULTS.write_text("\n".join(lines) + "\n")
    print(RESULTS)


if __name__ == "__main__":
    main()
