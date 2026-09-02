#!/usr/bin/env python3
"""Generate the separate OpenAI Responses native-compaction result table."""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "openai-native" / "runs"
RESULTS = ROOT / "OPENAI_NATIVE_RESULTS.md"
FIXTURES = ("jsteer-publication", "lucid3-first")
TRIALS = (1, 2, 3)
METHODS = (
    ("pi-default-text", "Pi default text summary"),
    ("openai-native-v2", "OpenAI native V2 (local endpoint/replay patch)"),
)


def grade_counts(path: Path) -> tuple[int, int]:
    facts = json.loads(path.read_text())["facts"]
    retained = sum(fact["grade"] == "retained" for fact in facts)
    pre = sum(fact["grade"] == "retained" and fact["id"] <= "fact-10" for fact in facts)
    return pre, retained


def mean_sd(values: list[int]) -> str:
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0
    return f"{mean:.1f}±{sd:.1f}"


def debug_events(work: Path) -> list[dict[str, Any]]:
    root = work / "answer-home" / ".pi" / "agent" / "artifacts" / "pi-better-compaction" / "sessions"
    if not root.is_dir():
        return []
    events = []
    for path in root.glob("*/provider-requests/*.json"):
        events.append(json.loads(path.read_text()))
    return events


def native_status(work: Path) -> tuple[bool, bool]:
    compact = json.loads((work / "compaction.json").read_text())
    details = compact["entry"].get("details", {})
    native_v2 = details.get("strategy") == "openai-native-compact-v2"
    replayed = any(event.get("data", {}).get("event") == "before_provider_request.native-rewrite" for event in debug_events(work))
    return native_v2, replayed


def row(method: str, label: str) -> str:
    pre: list[int] = []
    retained: list[int] = []
    native_v2 = 0
    replayed = 0
    expected = len(FIXTURES) * len(TRIALS)
    for fixture in FIXTURES:
        for trial in TRIALS:
            work = RUNS / fixture / method / f"trial-{trial:02d}"
            grade = work / "grade.json"
            if not grade.is_file():
                continue
            cell_pre, cell_retained = grade_counts(grade)
            pre.append(cell_pre)
            retained.append(cell_retained)
            if method == "openai-native-v2":
                cell_native, cell_replayed = native_status(work)
                native_v2 += cell_native
                replayed += cell_replayed
    if not pre:
        return f"| {label} | — | — | 0/{expected} | — | — |"
    state = "text summary" if method == "pi-default-text" else f"V2 native {native_v2}/{len(pre)}"
    replay = "not applicable" if method == "pi-default-text" else f"native replay {replayed}/{len(pre)}"
    return f"| {label} | {mean_sd(pre)} | {mean_sd(retained)} | {len(pre)}/{expected} | {state} | {replay} |"


def main() -> None:
    rows = [row(method, label) for method, label in METHODS]
    RESULTS.write_text(
        "# OpenAI native compaction\n\n"
        "This table is separate from the DeepSeek benchmark. Both rows compact and answer with "
        "`openai-codex/gpt-5.6-terra`, `openai-codex-responses`, high thinking.\n\n"
        "| method | pre /10 | retained /20 | n | compaction state | resumed-request evidence |\n"
        "|---|---:|---:|---:|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
        "`pre` counts the ten facts before the historical compaction boundary. Values are mean±sample SD. "
        "OpenAI V2 state is encrypted and opaque, so this table does not present it as a text-summary token count. "
        "The native row uses a local endpoint/replay patch; stock V2 returned `Store must be set to false` in this setup. "
        "`native replay` counts answer requests whose extension artifact recorded `before_provider_request.native-rewrite`. "
        "These rows grade fact recall only; invented-claim checks remain in judge calibration but are skipped for this large-source recall table.\n"
    )
    print(RESULTS)


if __name__ == "__main__":
    main()
