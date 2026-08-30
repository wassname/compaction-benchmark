from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import benchmark  # noqa: E402


class FixtureTests(unittest.TestCase):
    def test_manifest_tail_boundaries_are_in_the_fixture(self) -> None:
        expected = {
            "jsteer-publication": 380,
            "lucid3-first": 61,
            "lucid-aug20": 207,
        }
        for name, tail_index in expected.items():
            fixture = benchmark.Fixture.load(name)
            self.assertEqual(fixture.tail_start_index, tail_index)
            self.assertEqual(fixture.region(tail_index - 1), "pre_first_kept")
            self.assertEqual(fixture.region(tail_index), "retained_tail_control")

    def test_gold_requires_exactly_twenty_items(self) -> None:
        fixture = benchmark.Fixture.load("lucid-aug20")
        with self.assertRaisesRegex(benchmark.BenchmarkError, "exactly 10"):
            benchmark.validate_gold(fixture, {"facts": []}, "pre_first_kept")

    def test_copy_source_hash_matches_fixture(self) -> None:
        fixture = benchmark.Fixture.load("lucid3-first")
        self.assertEqual(benchmark.sha256(fixture.source), fixture.source_hash)

    def test_strata_retain_original_ids_and_reroot_only_evaluators(self) -> None:
        fixture = benchmark.Fixture.load("lucid-aug20")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tail.jsonl"
            benchmark.write_stratum_session(fixture, "retained_tail_control", path)
            entries = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(entries[1]["id"], fixture.entries[fixture.tail_start_index]["id"])
        self.assertIsNone(entries[1]["parentId"])
        self.assertEqual(benchmark.sha256(fixture.source), fixture.source_hash)

    def test_parses_one_json_code_fence(self) -> None:
        self.assertEqual(
            benchmark.parse_json('```json\n{"facts": []}\n```', "test"),
            {"facts": []},
        )

    def test_restores_only_source_whitespace(self) -> None:
        source = "one line wraps\nhere exactly"
        self.assertEqual(
            benchmark.exact_whitespace_variant(source, "line wraps here"),
            "line wraps\nhere",
        )
        self.assertIsNone(benchmark.exact_whitespace_variant(source, "line changed here"))

    def test_accepts_repeated_evidence_when_all_copies_precede_the_boundary(self) -> None:
        fixture = benchmark.Fixture(
            name="duplicate-pre",
            directory=Path("."),
            source=Path("source.jsonl"),
            manifest={},
            entries=[
                {"id": "one", "message": {"content": "same complete evidence sentence"}},
                {"id": "two", "message": {"content": "same complete evidence sentence"}},
            ],
            source_hash="",
            tail_start_index=2,
        )
        fixture.locate_evidence("one", "same complete evidence sentence", "pre_first_kept")

    def test_rejects_pre_boundary_evidence_repeated_in_the_tail(self) -> None:
        fixture = benchmark.Fixture(
            name="duplicate-tail",
            directory=Path("."),
            source=Path("source.jsonl"),
            manifest={},
            entries=[
                {"id": "one", "message": {"content": "same complete evidence sentence"}},
                {"id": "two", "message": {"content": "same complete evidence sentence"}},
            ],
            source_hash="",
            tail_start_index=1,
        )
        with self.assertRaisesRegex(benchmark.BenchmarkError, "repeated in the retained tail"):
            fixture.locate_evidence("one", "same complete evidence sentence", "pre_first_kept")

    def test_rejects_observed_partial_evidence_windows(self) -> None:
        self.assertFalse(
            benchmark.answer_values_are_evidenced(
                "At r=64, oracle KL was 1.832 (0.242× copy); at r=2048 it was 0.001119.",
                "4957 0.020\\n2048 0.001119",
            )
        )
        self.assertFalse(
            benchmark.answer_values_are_evidenced(
                "One checkpoint, temperature 0, with baseline, +z, -z, and placebo generations.",
                "? If 45\\nfinished, run the four-arm demo on its checkpoint",
            )
        )


if __name__ == "__main__":
    unittest.main()
