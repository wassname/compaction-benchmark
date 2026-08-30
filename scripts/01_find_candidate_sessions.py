from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

TERMS = ("architecture", "archetecture", "arxiv.org", "predict", "plot")


@dataclass
class SessionScore:
    path: Path
    bytes: int
    user_turns: int
    user_chars: int
    largest_user_turn_chars: int
    term_hits: dict[str, int]

    @property
    def total_hits(self) -> int:
        return sum(self.term_hits.values())


def message_text(entry: dict) -> str:
    message = entry.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return ""
    return "".join(
        part["text"]
        for part in message.get("content", [])
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def score_session(path: Path) -> SessionScore:
    user_messages = []
    for line in path.open(errors="replace"):
        entry = json.loads(line)
        text = message_text(entry)
        if text:
            user_messages.append(text)
    all_text = "\n".join(user_messages).lower()
    return SessionScore(
        path=path,
        bytes=path.stat().st_size,
        user_turns=len(user_messages),
        user_chars=sum(map(len, user_messages)),
        largest_user_turn_chars=max(map(len, user_messages)),
        term_hits={term: all_text.count(term) for term in TERMS},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".pi/agent/sessions")
    parser.add_argument("--min-bytes", type=int, default=1_000_000)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    candidates = []
    for path in args.sessions.rglob("*.jsonl"):
        if "/forks/" in str(path) or "/subagent-artifacts/" in str(path):
            continue
        if path.stat().st_size < args.min_bytes:
            continue
        score = score_session(path)
        if score.total_hits:
            candidates.append(score)

    candidates.sort(
        key=lambda score: (score.total_hits, score.user_turns, score.user_chars), reverse=True
    )
    rows = [
        {
            "path": str(score.path),
            "bytes": score.bytes,
            "user_turns": score.user_turns,
            "user_chars": score.user_chars,
            "largest_user_turn_chars": score.largest_user_turn_chars,
            **score.term_hits,
            "term_hits": score.total_hits,
        }
        for score in candidates[: args.limit]
    ]
    fields = list(rows[0]) if rows else ["path"]
    writer = csv.DictWriter(__import__("sys").stdout, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
