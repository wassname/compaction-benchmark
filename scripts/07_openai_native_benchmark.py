#!/usr/bin/env python3
"""Run the OpenAI Responses compaction comparison without mixing its artifacts with the DeepSeek benchmark."""
from __future__ import annotations

from pathlib import Path

import benchmark

ROOT = Path(__file__).resolve().parents[1]

benchmark.RUNS = ROOT / "data" / "openai-native" / "runs"
benchmark.OUTPUTS = ROOT / "outputs" / "openai-native"
benchmark.METHODS_PATH = ROOT / "methods.openai-native.json"
benchmark.MODEL_PROVIDER = "openai-codex"
benchmark.MODEL_ID = "gpt-5.6-terra"
benchmark.THINKING_LEVEL = "high"

if __name__ == "__main__":
    benchmark.main()
