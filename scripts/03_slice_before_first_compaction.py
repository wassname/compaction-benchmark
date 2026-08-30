from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("name")
    parser.add_argument("--fixture-dir", type=Path, default=Path("data/fixtures"))
    args = parser.parse_args()

    lines = args.source.read_text().splitlines(keepends=True)
    entries = [json.loads(line) for line in lines]
    try:
        compact_index, first_compaction = next(
            (index, entry)
            for index, entry in enumerate(entries)
            if entry.get("type") == "compaction"
        )
    except StopIteration as error:
        raise ValueError(f"No compaction entry in {args.source}") from error
    if compact_index == 0:
        raise ValueError("The first entry is already a compaction")

    fixture_dir = args.fixture_dir / args.name
    fixture_dir.mkdir(parents=True, exist_ok=False)
    session_path = fixture_dir / "source.jsonl"
    session_path.write_text("".join(lines[:compact_index]))
    manifest = {
        "source": str(args.source.resolve()),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "slice": "entries strictly before the first compaction entry",
        "entries": compact_index,
        "first_compaction": {
            "id": first_compaction["id"],
            "timestamp": first_compaction["timestamp"],
            "tokens_before": first_compaction["tokensBefore"],
            "first_kept_entry_id": first_compaction["firstKeptEntryId"],
        },
    }
    (fixture_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(session_path.resolve())


if __name__ == "__main__":
    main()
