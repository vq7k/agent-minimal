from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stats:
    chars: int
    words: int
    lines: int


def count(text: str) -> Stats:
    if not text:
        return Stats(chars=0, words=0, lines=0)
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    return Stats(chars=len(text), words=len(text.split()), lines=lines)
