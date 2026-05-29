from __future__ import annotations

import argparse
import sys
from pathlib import Path

from word_count.core import count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="word-count",
        description="Count chars/words/lines in a text file.",
    )
    parser.add_argument("path", help="Path to a text file, or '-' for stdin.")
    args = parser.parse_args(argv)

    text = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
    stats = count(text)
    print(f"chars={stats.chars} words={stats.words} lines={stats.lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
