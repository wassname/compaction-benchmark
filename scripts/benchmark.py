#!/usr/bin/env python3
"""Create source-evidenced Pi recall gold facts and score uncompressed baselines. (worker)

The source fixtures are immutable. Every Pi process operates on a fresh copied session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "fixtures"
RUNS = ROOT / "data" / "runs"
EVALUATORS = ROOT / "data" / "evaluators"
OUTPUTS = ROOT / "outputs" / "benchmark"
HOST_AGENT_DIR = Path.home() / ".pi" / "agent"
MODEL_PROVIDER = "openai-codex"
MODEL_ID = "gpt-5.6-terra"
THINKING_LEVEL = "high"
FACTS_PER_FIXTURE = 20
TRIALS = (1, 2, 3)


class BenchmarkError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def text_content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            part.get("text", "")
            for part in value
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


def answer_values_are_evidenced(answer: str, quote: str) -> bool:
    """Require every explicit numeric value in a gold answer to occur in its quote. (worker)"""
    return all(value in quote for value in re.findall(r"\d+(?:\.\d+)?", answer))


def exact_whitespace_variant(source: str, candidate: str) -> str | None:
    """Restore source line wrapping without accepting changed words. (claude)"""
    collapsed: list[str] = []
    offsets: list[int] = []
    in_whitespace = False
    for index, character in enumerate(source):
        if character.isspace():
            if not in_whitespace:
                collapsed.append(" ")
                offsets.append(index)
            in_whitespace = True
        else:
            collapsed.append(character)
            offsets.append(index)
            in_whitespace = False
    normalized_source = "".join(collapsed)
    normalized_candidate = " ".join(candidate.split())
    positions = [match.start() for match in re.finditer(re.escape(normalized_candidate), normalized_source)]
    if len(positions) != 1:
        return None
    start = positions[0]
    end = start + len(normalized_candidate)
    return source[offsets[start] : offsets[end - 1] + 1]


def entry_text(entry: dict[str, Any]) -> str:
    """Text that a source-session reader could see, excluding opaque signatures. (worker)"""
    message = entry.get("message")
    if isinstance(message, dict):
        content = text_content(message.get("content"))
        if content:
            return content
    for key in ("summary", "content"):
        content = text_content(entry.get(key))
        if content:
            return content
    return ""


@dataclass(frozen=True)
class Fixture:
    name: str
    directory: Path
    source: Path
    manifest: dict[str, Any]
    entries: list[dict[str, Any]]
    source_hash: str
    tail_start_index: int

    @classmethod
    def load(cls, name: str) -> "Fixture":
        directory = FIXTURES / name
        source = directory / "source.jsonl"
        manifest = json.loads((directory / "manifest.json").read_text())
        entries = [json.loads(line) for line in source.read_text().splitlines()]
        # worker: manifest.source_sha256 names the full historical source before slicing.
        # worker: this immutable fixture slice hash identifies every benchmark artifact.
        source_hash = sha256(source)
        tail_id = manifest["first_compaction"]["first_kept_entry_id"]
        try:
            tail_start_index = next(i for i, entry in enumerate(entries) if entry["id"] == tail_id)
        except StopIteration as error:
            raise BenchmarkError(f"{name}: first kept entry {tail_id} is absent") from error
        return cls(name, directory, source, manifest, entries, source_hash, tail_start_index)

    def assert_unchanged(self) -> None:
        current = sha256(self.source)
        if current != self.source_hash:
            raise BenchmarkError(f"{self.name}: fixture source changed during run: {current}")

    def source_matches(self, quote: str) -> list[tuple[int, dict[str, Any]]]:
        return [(index, entry) for index, entry in enumerate(self.entries) if quote in entry_text(entry)]

    def locate_evidence(self, entry_id: str, quote: str, required_region: str) -> tuple[int, dict[str, Any], str]:
        """Check a quote against its cited immutable source entry. (worker)"""
        try:
            index, entry = next(
                (index, entry) for index, entry in enumerate(self.entries) if entry["id"] == entry_id
            )
        except StopIteration as error:
            raise BenchmarkError(f"{self.name}: unknown source entry {entry_id}") from error
        source_text = entry_text(entry)
        evidence = quote if quote in source_text else exact_whitespace_variant(source_text, quote)
        if evidence is None:
            raise BenchmarkError(f"{self.name}: evidence_quote changes source words in entry {entry_id}")
        matches = self.source_matches(evidence)
        if not any(entry["id"] == entry_id for _, entry in matches):
            raise BenchmarkError(f"{self.name}: evidence_quote is absent from the cited source entry")
        if required_region == "pre_first_kept" and any(self.region(match_index) == "retained_tail_control" for match_index, _ in matches):
            raise BenchmarkError(f"{self.name}: pre-boundary evidence_quote is repeated in the retained tail")
        if self.region(index) != required_region:
            raise BenchmarkError(f"{self.name}: evidence_quote is in the wrong source region")
        return index, entry, evidence

    def region(self, index: int) -> str:
        return "retained_tail_control" if index >= self.tail_start_index else "pre_first_kept"


class RpcProcess:
    """Strict LF-delimited JSONL client. Logs all stdout and stderr before parsing. (worker)"""

    def __init__(self, command: list[str], env: dict[str, str], artifact_dir: Path) -> None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        self.argv = command
        self.artifact_dir = artifact_dir
        self.events_path = artifact_dir / "rpc.jsonl"
        self.stderr_path = artifact_dir / "stderr.log"
        self.events_file = self.events_path.open("w")
        self.stderr_file = self.stderr_path.open("w")
        self.queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=ROOT,
            env=env,
        )
        for stream_name, stream in (("stdout", self.process.stdout), ("stderr", self.process.stderr)):
            assert stream is not None
            threading.Thread(target=self._read_stream, args=(stream_name, stream), daemon=True).start()

    def _read_stream(self, stream_name: str, stream: Any) -> None:
        for line in stream:
            self.queue.put((stream_name, line.rstrip("\n")))
        self.queue.put((stream_name, None))

    def _next(self, timeout: float) -> dict[str, Any] | None:
        try:
            stream_name, line = self.queue.get(timeout=timeout)
        except queue.Empty as error:
            raise BenchmarkError(f"Pi RPC timed out after {timeout:.0f}s") from error
        if line is None:
            if stream_name == "stdout" and self.process.poll() is not None:
                raise BenchmarkError(f"Pi RPC exited {self.process.returncode}; see {self.stderr_path}")
            return None
        if stream_name == "stderr":
            self.stderr_file.write(line + "\n")
            self.stderr_file.flush()
            return None
        self.events_file.write(line + "\n")
        self.events_file.flush()
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise BenchmarkError(f"Pi RPC emitted invalid JSON: {line[:200]!r}") from error
        if event.get("type") == "extension_error":
            raise BenchmarkError(f"Pi extension error: {event.get('error')}")
        return event

    def command(self, kind: str, timeout: float = 300.0, **fields: Any) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        command = {"id": request_id, "type": kind, **fields}
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            event = self._next(max(0.1, deadline - time.monotonic()))
            if event is None:
                continue
            if event.get("type") == "response" and event.get("id") == request_id:
                if not event.get("success"):
                    raise BenchmarkError(f"Pi RPC {kind} failed: {event.get('error')}")
                return event

    def wait_settled(self, timeout: float = 1800.0) -> None:
        deadline = time.monotonic() + timeout
        while True:
            event = self._next(max(0.1, deadline - time.monotonic()))
            if event is None:
                continue
            if event.get("type") == "agent_settled":
                return
            if event.get("type") == "auto_retry_end" and not event.get("success"):
                raise BenchmarkError(f"Pi retry failed: {event.get('finalError')}")
            if event.get("type") == "compaction_end" and event.get("result") is None:
                raise BenchmarkError(f"Unexpected failed compaction: {event.get('errorMessage')}")

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.events_file.close()
        self.stderr_file.close()


def isolated_agent_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    # worker: credentials are copied, never shared or modified; model metadata supports OAuth catalogs.
    for name in ("auth.json", "models.json", "models-store.json"):
        source = HOST_AGENT_DIR / name
        if source.is_file():
            shutil.copy2(source, path / name)
    if not (path / "auth.json").is_file():
        raise BenchmarkError(f"Missing {HOST_AGENT_DIR / 'auth.json'} needed for isolated Pi run")
    return path


def copy_source(fixture: Fixture, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    shutil.copy2(fixture.source, path)
    if sha256(path) != fixture.source_hash:
        raise BenchmarkError(f"{fixture.name}: copied session hash does not match source")


def pi_command(session: Path) -> list[str]:
    return [
        "pi",
        "--mode",
        "rpc",
        "--session",
        str(session),
        "--model",
        f"{MODEL_PROVIDER}/{MODEL_ID}",
        "--thinking",
        THINKING_LEVEL,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--no-builtin-tools",
        "--no-approve",
    ]


def start_pi(session: Path, agent_dir: Path, artifacts: Path) -> RpcProcess:
    env = os.environ.copy()
    env["PI_CODING_AGENT_DIR"] = str(agent_dir)
    env["PI_SKIP_VERSION_CHECK"] = "1"
    env["PI_TELEMETRY"] = "0"
    rpc = RpcProcess(pi_command(session), env, artifacts)
    state = rpc.command("get_state")
    data = state.get("data", {})
    model = data.get("model") or {}
    if model.get("provider") != MODEL_PROVIDER or model.get("id") != MODEL_ID:
        rpc.close()
        raise BenchmarkError(f"Pi model mismatch: {model!r}")
    if data.get("thinkingLevel") != THINKING_LEVEL:
        rpc.close()
        raise BenchmarkError(f"Pi thinking mismatch: {data.get('thinkingLevel')!r}")
    rpc.command("set_auto_compaction", enabled=False)
    state = rpc.command("get_state")["data"]
    if state.get("autoCompactionEnabled") is not False:
        rpc.close()
        raise BenchmarkError("Pi did not disable auto compaction")
    return rpc


def gold_prompt(region: str) -> str:
    role = "before the retained tail" if region == "pre_first_kept" else "the retained tail continuity control"
    return f"""You are an evaluator, not the session under test. This evaluator has only one bounded source stratum: {role}. Create exactly 10 durable factual recall items from the loaded history.

Return JSON only, with this shape:
{{"facts":[{{"question":"...","gold_answer":"...","source_entry_id":"8 hex characters shown in the source marker","evidence_quote":"exact source phrase"}}]}}

Rules:
- Each question must ask one durable fact that remains useful after resuming work. Do not ask about this request, generic agent behavior, or transient token counts.
- Every material clause in gold_answer must be asked by question and supported by evidence_quote.
- Each loaded source item starts with `[SOURCE_ENTRY_ID=...]`. Copy that ID into source_entry_id, but do not include the marker in evidence_quote.
- evidence_quote must be an exact, self-contained consecutive sentence or complete table block copied verbatim from that cited source entry. Do not use fragments or paraphrases.
- Do not use tools. Do not mention this evaluation protocol in any item.
"""


def parse_json(text: str, context: str) -> dict[str, Any]:
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0] in {"```", "```json"} and lines[-1] == "```":
        stripped = "\n".join(lines[1:-1])
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise BenchmarkError(f"{context}: model did not return JSON: {text[:500]!r}") from error
    if not isinstance(value, dict):
        raise BenchmarkError(f"{context}: expected JSON object")
    return value


def validate_gold(fixture: Fixture, proposed: dict[str, Any], required_region: str) -> list[dict[str, Any]]:
    facts = proposed.get("facts")
    if not isinstance(facts, list) or len(facts) != 10:
        raise BenchmarkError(f"{fixture.name}: expected exactly 10 {required_region} facts")
    validated = []
    questions: set[str] = set()
    for number, fact in enumerate(facts, 1):
        if not isinstance(fact, dict):
            raise BenchmarkError(f"{fixture.name}: fact {number} is not an object")
        question = fact.get("question")
        answer = fact.get("gold_answer")
        entry_id = fact.get("source_entry_id")
        quote = fact.get("evidence_quote")
        if not all(isinstance(value, str) and value.strip() for value in (question, answer, entry_id, quote)):
            raise BenchmarkError(f"{fixture.name}: fact {number} has empty question, answer, source entry, or evidence")
        if len(" ".join(quote.split())) < 24:
            raise BenchmarkError(f"{fixture.name}: fact {number} evidence is shorter than 24 characters")
        key = " ".join(question.lower().split())
        if key in questions:
            raise BenchmarkError(f"{fixture.name}: duplicate question {number}")
        questions.add(key)
        index, entry, evidence = fixture.locate_evidence(entry_id, quote, required_region)
        if not answer_values_are_evidenced(answer, evidence):
            raise BenchmarkError(f"{fixture.name}: fact {number} evidence omits a numeric gold-answer value")
        region = fixture.region(index)
        validated_fact = {
            "id": f"{required_region}-{number:02d}",
            "question": question.strip(),
            "gold_answer": answer.strip(),
            "source_entry_id": entry["id"],
            "source_entry_index": index,
            "evidence_quote": evidence,
            "model_evidence_candidate": quote,
            "source_region": region,
        }
        if "manual_review" in fact:
            validated_fact["manual_review"] = fact["manual_review"]
        validated.append(validated_fact)
    return validated


def annotate_entry(entry: dict[str, Any]) -> None:
    marker = f"[SOURCE_ENTRY_ID={entry['id']}]\n"
    message = entry.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = marker + content
        elif isinstance(content, list):
            content.insert(0, {"type": "text", "text": marker})
        return
    for key in ("summary", "content"):
        if isinstance(entry.get(key), str):
            entry[key] = marker + entry[key]
            return


def write_stratum_session(fixture: Fixture, region: str, path: Path) -> None:
    """Make a re-rooted, source-ID-annotated evaluator stratum. (worker)"""
    start = 1 if region == "pre_first_kept" else fixture.tail_start_index
    end = fixture.tail_start_index if region == "pre_first_kept" else len(fixture.entries)
    selected = [json.loads(json.dumps(entry)) for entry in fixture.entries[start:end]]
    if not selected:
        raise BenchmarkError(f"{fixture.name}: empty {region} evaluator stratum")
    selected_ids = {entry["id"] for entry in selected}
    previous_id: str | None = None
    for entry in selected:
        annotate_entry(entry)
        if previous_id is None:
            entry["parentId"] = None
        elif entry.get("parentId") not in selected_ids:
            entry["parentId"] = previous_id
        previous_id = entry["id"]
    header = json.loads(json.dumps(fixture.entries[0]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(entry, ensure_ascii=False) for entry in [header, *selected]) + "\n")


def generate_gold_stratum(fixture: Fixture, region: str) -> list[dict[str, Any]]:
    work = EVALUATORS / fixture.name / "gold" / region
    session = work / "session.jsonl"
    write_stratum_session(fixture, region, session)
    artifacts = OUTPUTS / fixture.name / "gold" / region
    curated = artifacts / "curated-answer.json"
    if curated.is_file():
        return validate_gold(fixture, json.loads(curated.read_text()), region)

    agent_dir = isolated_agent_dir(work / "agent")
    write_json(artifacts / "run.json", {"fixture": fixture.name, "region": region, "source_sha256": fixture.source_hash, "command": pi_command(session)})
    rpc = start_pi(session, agent_dir, artifacts)
    try:
        rpc.command("prompt", message=gold_prompt(region), timeout=60)
        rpc.wait_settled()
        text = rpc.command("get_last_assistant_text")["data"]["text"]
        if not isinstance(text, str):
            raise BenchmarkError(f"{fixture.name}: {region} gold generator returned no assistant text")
        (artifacts / "raw-answer.json").write_text(text + "\n")
    finally:
        rpc.close()
    return validate_gold(fixture, parse_json(text, f"{fixture.name} {region} gold"), region)


def generate_gold(fixture: Fixture) -> Path:
    fixture.assert_unchanged()
    pre = generate_gold_stratum(fixture, "pre_first_kept")
    tail = generate_gold_stratum(fixture, "retained_tail_control")
    facts = [*pre, *tail]
    for number, fact in enumerate(facts, 1):
        fact["id"] = f"fact-{number:02d}"
    gold = {
        "schema_version": 2,
        "fixture": fixture.name,
        "source_sha256": fixture.source_hash,
        "historical_source_sha256": fixture.manifest["source_sha256"],
        "first_kept_entry_id": fixture.manifest["first_compaction"]["first_kept_entry_id"],
        "first_kept_entry_index": fixture.tail_start_index,
        "regions": {"pre_first_kept": 10, "retained_tail_control": 10},
        "facts": facts,
    }
    destination = fixture.directory / "gold.json"
    write_json(destination, gold)
    fixture.assert_unchanged()
    return destination


def recall_prompt(gold: dict[str, Any]) -> str:
    lines = [
        "Answer every numbered question from this already-loaded session.",
        "Give exactly one concise factual answer per number. Do not use tools. Do not mention uncertainty unless the session lacks the fact.",
    ]
    lines.extend(f"{number}. {fact['question']}" for number, fact in enumerate(gold["facts"], 1))
    return "\n".join(lines)


def load_gold(fixture: Fixture) -> dict[str, Any]:
    path = fixture.directory / "gold.json"
    if not path.is_file():
        raise BenchmarkError(f"{fixture.name}: generate gold first: {path}")
    gold = json.loads(path.read_text())
    if gold.get("source_sha256") != fixture.source_hash:
        raise BenchmarkError(f"{fixture.name}: gold does not match fixture source hash")
    facts = gold.get("facts", [])
    if len(facts) != FACTS_PER_FIXTURE:
        raise BenchmarkError(f"{fixture.name}: gold does not contain {FACTS_PER_FIXTURE} facts")
    if gold.get("first_kept_entry_index") != fixture.tail_start_index:
        raise BenchmarkError(f"{fixture.name}: gold first_kept_entry_index does not match the fixture")
    if {region: sum(fact.get("source_region") == region for fact in facts) for region in ("pre_first_kept", "retained_tail_control")} != {"pre_first_kept": 10, "retained_tail_control": 10}:
        raise BenchmarkError(f"{fixture.name}: gold is not the required 10 pre-boundary facts and 10 tail controls")
    ids = {entry["id"]: (index, entry) for index, entry in enumerate(fixture.entries)}
    for fact in facts:
        entry_id = fact.get("source_entry_id")
        evidence = fact.get("evidence_quote")
        if entry_id not in ids or not isinstance(evidence, str):
            raise BenchmarkError(f"{fixture.name}: gold evidence has no valid source entry")
        index, entry = ids[entry_id]
        if fact.get("source_entry_index") != index:
            raise BenchmarkError(f"{fixture.name}: gold source_entry_index does not match its entry ID")
        if evidence not in entry_text(entry) or fact.get("source_region") != fixture.region(index):
            raise BenchmarkError(f"{fixture.name}: gold evidence does not match its labeled source entry")
        if not answer_values_are_evidenced(fact.get("gold_answer", ""), evidence):
            raise BenchmarkError(f"{fixture.name}: gold evidence omits a numeric gold-answer value")
        review = fact.get("manual_review")
        expected_leakage = "not_restated_in_retained_tail" if fact.get("source_region") == "pre_first_kept" else "not_applicable_tail_control"
        if not isinstance(review, dict) or review.get("reviewer") != "claude" or review.get("evidence_supports_gold") is not True or review.get("question_matches_gold") is not True or review.get("tail_leakage_review") != expected_leakage:
            raise BenchmarkError(f"{fixture.name}: gold fact lacks required semantic and tail-leakage review")
    return gold


def run_baseline(fixture: Fixture, trial: int) -> Path:
    fixture.assert_unchanged()
    gold = load_gold(fixture)
    work = RUNS / fixture.name / "uncompacted-baseline" / f"trial-{trial:02d}"
    session = work / "session.jsonl"
    copy_source(fixture, session)
    agent_dir = isolated_agent_dir(work / "agent")
    artifacts = OUTPUTS / fixture.name / "uncompacted-baseline" / f"trial-{trial:02d}"
    write_json(artifacts / "run.json", {"fixture": fixture.name, "trial": trial, "source_sha256": fixture.source_hash, "command": pi_command(session), "gold_sha256": sha256(fixture.directory / "gold.json")})
    rpc = start_pi(session, agent_dir, artifacts)
    try:
        rpc.command("prompt", message=recall_prompt(gold), timeout=60)
        rpc.wait_settled()
        answer = rpc.command("get_last_assistant_text")["data"]["text"]
        stats = rpc.command("get_session_stats")["data"]
        entries = rpc.command("get_entries")["data"]["entries"]
    finally:
        rpc.close()
    if not isinstance(answer, str):
        raise BenchmarkError(f"{fixture.name}: baseline returned no assistant text")
    if any(entry.get("type") == "compaction" for entry in entries):
        raise BenchmarkError(f"{fixture.name}: uncompressed baseline unexpectedly compacted")
    answer_path = work / "answer.json"
    write_json(answer_path, {"fixture": fixture.name, "trial": trial, "source_sha256": fixture.source_hash, "answer": answer, "session_stats": stats})
    fixture.assert_unchanged()
    return answer_path


def grade_prompt(gold: dict[str, Any], answer: str) -> str:
    items = []
    for number, fact in enumerate(gold["facts"], 1):
        items.append({"id": fact["id"], "question": fact["question"], "gold_answer": fact["gold_answer"]})
    return json.dumps(
        {
            "instruction": "Blind grade the candidate answer against the numbered gold items. The method and fixture are hidden. For every fact emit retained, distorted, or missing. retained requires materially the same meaning; distorted is a related answer with a material error; missing means no answer. Count each material unsupported claim in the candidate as invented. Return JSON only.",
            "facts": items,
            "candidate_answer": answer,
            "required_schema": {"facts": [{"id": "fact-01", "grade": "retained|distorted|missing", "reason": "short"}], "invented_claims": ["claim"]},
        },
        ensure_ascii=False,
    )


def grade_baseline(fixture: Fixture, trial: int) -> Path:
    gold = load_gold(fixture)
    answer_path = RUNS / fixture.name / "uncompacted-baseline" / f"trial-{trial:02d}" / "answer.json"
    if not answer_path.is_file():
        raise BenchmarkError(f"{fixture.name}: run baseline first")
    answer = json.loads(answer_path.read_text())["answer"]
    work = EVALUATORS / fixture.name / "baseline-grade" / f"trial-{trial:02d}"
    session = work / "session.jsonl"
    # worker: a source-loaded evaluator identifies claims unsupported by the fixture.
    # worker: the prompt hides the target method and fixture name.
    copy_source(fixture, session)
    grader_source_hash = sha256(session)
    agent_dir = isolated_agent_dir(work / "agent")
    artifacts = OUTPUTS / fixture.name / "baseline-grade" / f"trial-{trial:02d}"
    rpc = start_pi(session, agent_dir, artifacts)
    try:
        rpc.command("prompt", message=grade_prompt(gold, answer), timeout=60)
        rpc.wait_settled()
        text = rpc.command("get_last_assistant_text")["data"]["text"]
    finally:
        rpc.close()
    grade = parse_json(text, f"{fixture.name} grade")
    facts = grade.get("facts")
    if not isinstance(facts, list) or len(facts) != FACTS_PER_FIXTURE:
        raise BenchmarkError(f"{fixture.name}: grader did not grade all {FACTS_PER_FIXTURE} facts")
    expected = {fact["id"] for fact in gold["facts"]}
    received = {fact.get("id") for fact in facts if isinstance(fact, dict)}
    if received != expected or any(fact.get("grade") not in {"retained", "distorted", "missing"} for fact in facts):
        raise BenchmarkError(f"{fixture.name}: invalid blind-grade result")
    counts = {grade_name: sum(fact["grade"] == grade_name for fact in facts) for grade_name in ("retained", "distorted", "missing")}
    counts["invented"] = len(grade.get("invented_claims", [])) if isinstance(grade.get("invented_claims", []), list) else 0
    result = {"fixture": fixture.name, "trial": trial, "source_sha256": fixture.source_hash, "grader_source_sha256": grader_source_hash, "counts": counts, "facts": facts, "invented_claims": grade.get("invented_claims", [])}
    result_path = RUNS / fixture.name / "uncompacted-baseline" / f"trial-{trial:02d}" / "grade.json"
    write_json(result_path, result)
    if counts["retained"] <= FACTS_PER_FIXTURE * 0.9:
        raise BenchmarkError(f"{fixture.name}: baseline retained {counts['retained']}/{FACTS_PER_FIXTURE}, not above 90%")
    return result_path


def fixture_names() -> list[str]:
    return sorted(path.name for path in FIXTURES.iterdir() if (path / "manifest.json").is_file())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("gold", "baseline", "grade", "goal1"))
    parser.add_argument("fixtures", nargs="*", help="fixture names; default: all")
    parser.add_argument("--trial", type=int, choices=TRIALS, help="run one trial instead of all three")
    args = parser.parse_args()
    names = args.fixtures or fixture_names()
    for name in names:
        if name not in fixture_names():
            raise BenchmarkError(f"unknown fixture {name!r}")
    fixtures = [Fixture.load(name) for name in names]
    if args.command in {"gold", "goal1"}:
        for fixture in fixtures:
            print(generate_gold(fixture))
    if args.command in {"baseline", "goal1"}:
        for trial in (args.trial,) if args.trial else TRIALS:
            for fixture in fixtures:
                print(run_baseline(fixture, trial))
    if args.command in {"grade", "goal1"}:
        for trial in (args.trial,) if args.trial else TRIALS:
            for fixture in fixtures:
                print(grade_baseline(fixture, trial))


if __name__ == "__main__":
    try:
        main()
    except BenchmarkError as error:
        print(f"benchmark error: {error}", file=sys.stderr)
        raise SystemExit(2)
