#!/usr/bin/env python3
"""
Join list item continuation lines into the parent item line.

Problem: in source markdown like
    - `per-file-ignores` — для ... (напр. `tests/*: S101`
      разрешает `assert` во всех тестах).
the second line is a "continuation" of the first list item. When followed
by a blank line + next list item, this creates a "loose list" where each
<li> is wrapped in <p>, adding unwanted vertical spacing.

Fix: join continuation lines (indented, no list marker) to the preceding
list item line, so the whole item is on one line.

Rules:
- If line[i] is a list item ("- foo bar") and line[i+1] is an indented
  continuation ("  more bar") with no list marker, join them with a space.
- Continuation may span multiple lines — keep joining until next blank,
  next list item, or next non-indented line.
- Skip lines inside ``` code blocks.

Idempotent (after first run, no continuation lines remain).
"""
from __future__ import annotations
import re
from pathlib import Path

BOOK_DIR = Path("/home/z/my-project/py-underhood-work/book")

LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+\S")
FENCE_RE = re.compile(r"^\s*```")


def is_list_item(line: str) -> bool:
    return bool(LIST_ITEM_RE.match(line))


def is_continuation(line: str) -> bool:
    """A continuation line: indented (starts with space/tab), non-blank, not a list item."""
    if not line:
        return False
    if not (line.startswith(" ") or line.startswith("\t")):
        return False
    if line.strip() == "":
        return False
    if is_list_item(line.lstrip()):  # nested list — don't merge
        return False
    return True


def process_file(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    out: list[str] = []
    in_code_block = False
    joined = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
            out.append(line)
            i += 1
            continue
        if in_code_block:
            out.append(line)
            i += 1
            continue

        if is_list_item(line):
            # Look ahead for continuation lines
            merged = line.rstrip()
            j = i + 1
            while j < len(lines) and is_continuation(lines[j]):
                merged += " " + lines[j].strip()
                j += 1
                joined += 1
            out.append(merged)
            i = j
            continue

        out.append(line)
        i += 1

    if joined:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return joined


def main() -> None:
    total = 0
    for md in sorted(BOOK_DIR.glob("*.md")):
        n = process_file(md)
        if n:
            print(f"  {md.name:35s}  joined {n} continuation lines")
        total += n
    print(f"\nTotal continuation lines joined: {total}")


if __name__ == "__main__":
    main()
