#!/usr/bin/env python3
"""
Fix markdown lists not separated from preceding paragraph by a blank line.

Problem: in source markdown, this pattern:
    Some text:
    - item 1
    - item 2

Renders as a single <p> with literal "- " in HTML, because Python-Markdown
requires a blank line before a list to recognize it as a list.

Fix: insert a blank line between a non-blank, non-list line and a following
line that starts with "- " or "* " or "1. " etc.

ALSO fixes the reverse: a list ending immediately followed by a non-list
line without blank line (less common but still valid markdown issue).

Idempotent: if a blank line is already present, no change.
Skips lines inside ``` code blocks.
"""
from __future__ import annotations
import re
from pathlib import Path

BOOK_DIR = Path("/home/z/my-project/py-underhood-work/book")

# Matches start of a list item: "- ", "* ", "+ ", "1. ", "2. ", etc.
LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+\S")

# Matches start of a blockquote: "> "
BLOCKQUOTE_RE = re.compile(r"^\s*>\s")

# Matches heading: "#", "##", etc.
HEADING_RE = re.compile(r"^#{1,6}\s")

# Matches horizontal rule: "---", "***", "___" on a line by itself
HR_RE = re.compile(r"^(\s*)(-{3,}|\*{3,}|_{3,})(\s*)$")

# Matches fence: ```
FENCE_RE = re.compile(r"^\s*```")

# A line is "list-starting" if it matches LIST_ITEM_RE
def is_list_start(line: str) -> bool:
    return bool(LIST_ITEM_RE.match(line))

def is_blockquote(line: str) -> bool:
    return bool(BLOCKQUOTE_RE.match(line))

def is_heading(line: str) -> bool:
    return bool(HEADING_RE.match(line))

def is_hr(line: str) -> bool:
    return bool(HR_RE.match(line))

def is_fence(line: str) -> bool:
    return bool(FENCE_RE.match(line))

def is_blank(line: str) -> bool:
    return line.strip() == ""


def process_file(path: Path) -> int:
    """Return number of blank lines inserted."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    out: list[str] = []
    in_code_block = False
    inserted = 0

    for i, line in enumerate(lines):
        # Toggle code block state
        if is_fence(line):
            in_code_block = not in_code_block
            out.append(line)
            continue
        if in_code_block:
            out.append(line)
            continue

        # Check: does this line start a list?
        if is_list_start(line):
            # Look at previous emitted line
            if out:
                prev = out[-1]
                # If prev is non-blank and NOT itself a list item / heading /
                # blockquote / hr / fence, then we need a blank line between.
                if (
                    not is_blank(prev)
                    and not is_list_start(prev)
                    and not is_heading(prev)
                    and not is_blockquote(prev)
                    and not is_hr(prev)
                    and not is_fence(prev)
                ):
                    out.append("")
                    inserted += 1
        out.append(line)

    if inserted:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return inserted


def main() -> None:
    total = 0
    for md in sorted(BOOK_DIR.glob("*.md")):
        n = process_file(md)
        if n:
            print(f"  {md.name:35s}  +{n} blank lines")
        total += n
    print(f"\nTotal blank lines inserted: {total}")


if __name__ == "__main__":
    main()
