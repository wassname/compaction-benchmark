#!/usr/bin/env python3
"""Record per-cell launch and replay provenance for the OpenAI-native table."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHODS = json.loads((ROOT / "methods.openai-native.json").read_text())
RUNS = ROOT / "data" / "openai-native" / "runs"
OUTPUT = ROOT / "outputs" / "openai-native" / "provenance.json"
FIXTURES = ("jsteer-publication", "lucid3-first")
METHOD_NAMES = ("pi-default-text", "openai-native-v2")
TRIALS = (1, 2, 3)


def main() -> None:
    model = METHODS["model"]
    cells = []
    for fixture in FIXTURES:
        for method in METHOD_NAMES:
            for trial in TRIALS:
                work = RUNS / fixture / method / f"trial-{trial:02d}"
                run = json.loads((ROOT / "outputs" / "openai-native" / fixture / method / f"trial-{trial:02d}" / "run.json").read_text())
                compact = json.loads((work / "compaction.json").read_text())
                provider_events = []
                artifacts = work / "answer-home" / ".pi" / "agent" / "artifacts" / "pi-better-compaction"
                for path in artifacts.glob("sessions/*/provider-requests/*.json"):
                    provider_events.append(json.loads(path.read_text())["data"].get("event"))
                compact_agent_dir = work / "compact-agent"
                answer_agent_dir = work / "answer-agent"
                cells.append(
                    {
                        "fixture": fixture,
                        "method": method,
                        "trial": trial,
                        "pi_coding_agent_dirs": {
                            "compact": str(compact_agent_dir),
                            "answer": str(answer_agent_dir),
                            "distinct": compact_agent_dir != answer_agent_dir,
                            "compact_settings_exists": (compact_agent_dir / "settings.json").is_file(),
                            "answer_settings_exists": (answer_agent_dir / "settings.json").is_file(),
                        },
                        "model": model,
                        "methods_sha256": run["methods_sha256"],
                        "method_spec_sha256": run["method_spec_sha256"],
                        "extension_config_sha256": run["extension_config_sha256"],
                        "pi_version": run["measured_pi_version"],
                        "compaction_strategy": compact["entry"].get("details", {}).get("strategy", "pi-text-summary"),
                        "answer_provider_events": provider_events,
                    }
                )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"model": model, "cells": cells}, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
