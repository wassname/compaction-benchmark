from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("name")
    parser.add_argument("--data-dir", type=Path, default=Path("data/source"))
    args = parser.parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    destination = args.data_dir / f"{args.name}.jsonl"
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, destination)
    print(destination.resolve())


if __name__ == "__main__":
    main()
