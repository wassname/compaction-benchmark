#!/usr/bin/env python3
"""Run only missing OpenAI-native benchmark cells after the one-fixture checks pass."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data" / "openai-native" / "runs"
FIXTURES = ("jsteer-publication", "lucid3-first")
METHODS = ("pi-default-text", "openai-native-v2")

for method in METHODS:
    for fixture in FIXTURES:
        for trial in (1, 2, 3):
            grade = RUNS / fixture / method / f"trial-{trial:02d}" / "grade.json"
            if grade.is_file():
                continue
            subprocess.run(
                [
                    "uv", "run", "python", "scripts/07_openai_native_benchmark.py",
                    "run-method", fixture, "--trial", str(trial), "--method", method,
                ],
                cwd=ROOT,
                check=True,
            )
