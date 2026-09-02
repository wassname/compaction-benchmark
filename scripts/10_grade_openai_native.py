#!/usr/bin/env python3
"""Verify native replay evidence, grade every OpenAI-native cell, then render the table."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "openai-native" / "runs"
FIXTURES = ("jsteer-publication", "lucid3-first")
TRIALS = (1, 2, 3)

for fixture in FIXTURES:
    for trial in TRIALS:
        work = RUNS / fixture / "openai-native-v2" / f"trial-{trial:02d}"
        compact = json.loads((work / "compaction.json").read_text())
        if compact["entry"]["details"].get("strategy") != "openai-native-compact-v2":
            raise RuntimeError(f"{fixture} trial {trial}: native V2 compaction is absent")
        provider_request_paths = (work / "answer-home" / ".pi" / "agent" / "artifacts" / "pi-better-compaction").glob("sessions/*/provider-requests/*.json")
        events = [json.loads(path.read_text())["data"].get("event") for path in provider_request_paths]
        if "before_provider_request.native-rewrite" not in events:
            raise RuntimeError(f"{fixture} trial {trial}: native replay evidence is absent: {events}")

for method in ("pi-default-text", "openai-native-v2"):
    for fixture in FIXTURES:
        for trial in TRIALS:
            subprocess.run(
                [
                    "uv", "run", "python", "scripts/07_openai_native_benchmark.py",
                    "grade-method", fixture, "--trial", str(trial), "--method", method, "--skip-inventions",
                ],
                cwd=ROOT,
                check=True,
            )

subprocess.run(["uv", "run", "python", "scripts/08_openai_native_results.py"], cwd=ROOT, check=True)
