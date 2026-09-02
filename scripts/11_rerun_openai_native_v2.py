#!/usr/bin/env python3
"""Replace all OpenAI native V2 cells after a local replay-path fix."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for fixture in ("jsteer-publication", "lucid3-first"):
    for trial in (1, 2, 3):
        subprocess.run(
            [
                "uv", "run", "python", "scripts/07_openai_native_benchmark.py",
                "run-method", fixture, "--trial", str(trial), "--method", "openai-native-v2",
            ],
            cwd=ROOT,
            check=True,
        )
