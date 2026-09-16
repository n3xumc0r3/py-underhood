#!/usr/bin/env python3
"""
Tighten markdown lists: remove blank lines BETWEEN consecutive list items
that belong to the same list.

A "loose" list (with blank lines between items) renders each <li> wrapped
in <p>, which adds unwanted vertical spacing. A "tight" list (no blank
lines between items) renders <li> as bare text.

Rules:
- If line[i] is a list item ("- foo") and line[i+1] is blank and line[i+2]
  is ALSO a list item with the SAME marker type ("- "), remove line[i+1].
- Continuation lines (indented, no marker) that follow a list item are part
  of that item — keep them attached, don't insert blank before them.
- Skip lines inside ``` code blocks.

Idempotent.
"""
from __future__ import annotations
import re
from pathlib import Path

BOOK_DIR = Path("/home/z/my-project/py-underhood-work/book")

LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+\S")
FENCE_RE = re.compile(r"^\s*```")


def get_marker(line: str) -> str | None:
    """Return the list marker ('-', '*', '+', '1.') or None."""
    m = LIST_ITEM_RE.match(line)
    if not m:
        return None
    return m.group(2)


def process_file(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    out: list[str] = []
    in_code_block = False
    removed = 0

    # Track: was the last non-blank emitted line a list item (or its continuation)?
    # We remember the marker of the current open list item.
    last_list_marker: str | None = None  # marker of the most recent list item
    last_emitted_non_blank_is_list_continuation = False

    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
            out.append(line)
            last_list_marker = None  # fence breaks list
            last_emitted_non_blank_is_list_continuation = False
            continue
        if in_code_block:
            out.append(line)
            continue

        if line.strip() == "":
            # Peek ahead to find next non-blank line
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and last_list_marker is not None:
                nxt = lines[j]
                nxt_marker = get_marker(nxt)
                # If next non-blank is a list item with SAME marker AND
                # the last non-blank line was a list item (not a continuation),
                # then this blank is between two items of same list → tighten.
                if (
                    nxt_marker == last_list_marker
                    and not last_emitted_non_blank_is_list_continuation
                ):
                    removed += 1
                    continue  # drop the blank line
            out.append(line)
            continue

        # Non-blank line
        marker = get_marker(line)
        if marker is not None:
            last_list_marker = marker
            last_emitted_non_blank_is_list_continuation = False
        else:
            # Is this a continuation of the current list item? (indented, no marker)
            if line.startswith(" ") or line.startswith("\t"):
                # Continuation — keep last_list_marker as-is
                last_emitted_non_blank_is_list_continuation = True
            else:
                # Non-list, non-continuation — break the list
                last_list_marker = None
                last_emitted_non_blank_is_list_continuation = False

        out.append(line)

    if removed:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return removed


def main() -> None:
    total = 0
    for md in sorted(BOOK_DIR.glob("*.md")):
        n = process_file(md)
        if n:
            print(f"  {md.name:35s}  -{n} blank lines (tightened)")
        total += n
    print(f"\nTotal blank lines removed: {total}")


if __name__ == "__main__":
    main()
