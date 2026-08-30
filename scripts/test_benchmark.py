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

    def test_detects_tool_calls_and_results(self) -> None:
        self.assertTrue(benchmark.entry_uses_tool({"message": {"role": "assistant", "content": [{"type": "toolCall"}]}}))
        self.assertTrue(benchmark.entry_uses_tool({"message": {"role": "toolResult", "content": []}}))
        self.assertFalse(benchmark.entry_uses_tool({"message": {"role": "assistant", "content": [{"type": "text"}]}}))

    def test_panel_requires_numbered_citations_and_a_majority(self) -> None:
        fixture = benchmark.Fixture("panel", Path("."), Path("source.jsonl"), {}, [], "", 0)
        gold = {"facts": [{"id": f"fact-{i:02d}"} for i in range(1, 21)]}
        answer = "\n".join(f"{i}. answer {i}" for i in range(1, 21))
        facts = [
            {"id": f"fact-{i:02d}", "grade": "retained", "candidate_lines": str(i), "reason": "same"}
            for i in range(1, 21)
        ]
        judgment = {"facts": facts, "invented_claims": [], "judge_note": ""}
        benchmark.validate_judgment(fixture, gold, answer, judgment)
        judgments = {f"judge-{i}": judgment for i in range(5)}
        result = benchmark.aggregate_judgments(fixture, gold, judgments)
        self.assertEqual(result["counts"], {"retained": 20, "distorted": 0, "missing": 0, "disputed": 0, "invented": 0})
        facts[0] = {"id": "fact-01", "grade": "retained", "candidate_lines": "2", "reason": "same"}
        with self.assertRaisesRegex(benchmark.BenchmarkError, "numbered answer item"):
            benchmark.validate_judgment(fixture, gold, answer, judgment)

    def test_panel_rejects_malformed_facts_and_deduplicates_invention_votes(self) -> None:
        fixture = benchmark.Fixture("panel", Path("."), Path("source.jsonl"), {}, [], "", 0)
        gold = {"facts": [{"id": f"fact-{i:02d}"} for i in range(1, 21)]}
        with self.assertRaisesRegex(benchmark.BenchmarkError, "fact objects"):
            benchmark.validate_judgment(fixture, gold, "", {"facts": [None] * 20})
        facts = [
            {"id": f"fact-{i:02d}", "grade": "missing", "candidate_lines": "", "candidate_quote": "", "reason": "absent"}
            for i in range(1, 21)
        ]
        judgments = {
            "one": {"facts": facts, "invented_claims": [{"candidate_item": 1, "candidate_quote": "1. false"}] * 3, "judge_note": ""},
            **{str(i): {"facts": facts, "invented_claims": [], "judge_note": ""} for i in range(2, 6)},
        }
        result = benchmark.aggregate_judgments(fixture, gold, judgments)
        self.assertEqual(result["counts"]["invented"], 0)

    def test_panel_marks_two_two_one_vote_disputed(self) -> None:
        fixture = benchmark.Fixture("panel", Path("."), Path("source.jsonl"), {}, [], "", 0)
        gold = {"facts": [{"id": f"fact-{i:02d}"} for i in range(1, 21)]}
        judgments = {}
        labels = ["retained", "retained", "distorted", "distorted", "missing"]
        for seat, label in enumerate(labels):
            facts = [
                {"id": f"fact-{i:02d}", "grade": label if i == 1 else "retained"}
                for i in range(1, 21)
            ]
            judgments[str(seat)] = {"facts": facts, "invented_claims": [], "judge_note": ""}
        result = benchmark.aggregate_judgments(fixture, gold, judgments)
        self.assertEqual(result["facts"][0]["grade"], "disputed")
        self.assertEqual(result["counts"]["disputed"], 1)
        self.assertEqual(result["counts"]["retained"], 19)

    def test_judge_uses_fresh_session_and_model_output_override(self) -> None:
        fixture = benchmark.Fixture.load("lucid-aug20")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "session.jsonl"
            benchmark.write_fresh_evaluator_session(fixture, session)
            self.assertEqual(len(session.read_text().splitlines()), 1)
            benchmark.write_json(
                root / "models-store.json",
                {"openrouter": {"models": [{"id": "judge", "maxTokens": 100000}]}},
            )
            benchmark.cap_model_output(root, "openrouter", "judge", 8192)
            override = json.loads((root / "models.json").read_text())
            self.assertEqual(override["providers"]["openrouter"]["modelOverrides"]["judge"]["maxTokens"], 8192)

    def test_method_manifest_and_extension_command_are_pinned(self) -> None:
        methods = benchmark.load_methods()
        self.assertEqual(methods["pi-context"]["classification"], "agent-driven-incomparable")
        command = benchmark.pi_command(Path("session.jsonl"), extension="pi-cc-compact@0.1.0")
        self.assertEqual(command[-2:], ["-e", "npm:pi-cc-compact@0.1.0"])
        with tempfile.TemporaryDirectory() as directory:
            stderr = Path(directory) / "stderr.log"
            stderr.write_text("")
            fixture = benchmark.Fixture("fixture", Path("."), Path("source.jsonl"), {}, [], "", 0)
            benchmark.validate_compaction_handler(
                fixture,
                "pi-default",
                methods["pi-default"],
                {"details": {"readFiles": [], "modifiedFiles": []}},
                stderr,
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
