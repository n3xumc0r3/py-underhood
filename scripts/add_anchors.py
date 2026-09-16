#!/usr/bin/env python3
"""
Add explicit anchor IDs {#N.M} to all H2/H3 headings in book/*.md.

Rules:
- H2 "## 3.8. `itertools.pairwise`, `batched` (Python 3.10+/3.12+)"
  →  "## 3.8. ... { #3.8 }"
- H2 "## 3.9. `collections` — Counter, defaultdict, ..."
  →  "## 3.9. ... { #3.9 }"
- H3 "### `defaultdict` — словарь с дефолт-фабрикой"
  →  "### `defaultdict` — словарь с дефолт-фабрикой { #3.9-defaultdict }"
  (parent section prefix to avoid clashes between chapters)
- H3 "### `send(value)` — отправить значение в генератор" (under 3.4)
  →  "### ... { #3.4-send }"

For H2: use only the numeric prefix "N.M" as the anchor.
For H3: derive from parent section + first word, but ONLY if a parent H2 was seen
        before. If H3 appears before any H2, anchor = first word slugified.

Skips:
- Lines that already contain "{ #... }" (idempotent)
- H1 (chapter title, no anchor needed — MkDocs uses filename)
- Lines that are inside code blocks (``` ... ```)
"""
from __future__ import annotations
import re
from pathlib import Path

BOOK_DIR = Path("/home/z/my-project/py-underhood-work/book")

# Matches: "## 1.1. Title" or "## 1.1 Title" — capture the numeric prefix
H2_NUM_RE = re.compile(r"^(##)\s+(\d+\.\d+)\.?\s+(.+?)\s*$")
# H3 doesn't have a number; we'll derive anchor from parent
H3_RE = re.compile(r"^(###)\s+(.+?)\s*$")
# Detect existing attr_list anchor
HAS_ANCHOR_RE = re.compile(r"\{\s*#[\w\-]+\s*\}\s*$")


def slugify(text: str) -> str:
    """Simple slugify for Russian/English mix."""
    # Remove backticks and parentheses content
    s = re.sub(r"`([^`]+)`", r"\1", text)
    s = re.sub(r"\([^)]*\)", "", s)
    # Transliterate common Cyrillic — keep ASCII letters, digits, dashes
    s = s.lower()
    # Cyrillic → Latin (basic, only what's needed for typical headings)
    cyr_to_lat = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    s = "".join(cyr_to_lat.get(c, c) for c in s)
    # Keep only ASCII letters, digits, dashes, spaces
    s = re.sub(r"[^a-z0-9\- ]", "", s)
    # Take first word only (avoids super long anchors)
    s = s.strip().split()[0] if s.strip().split() else "section"
    return s or "section"


def process_file(path: Path) -> tuple[int, int]:
    """Process one markdown file. Returns (h2_count, h3_count)."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)
    in_code_block = False
    current_h2_num: str | None = None  # e.g. "3.4"
    h2_count = 0
    h3_count = 0

    for i, line in enumerate(lines):
        # Toggle code block state
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Skip if already has an anchor
        if HAS_ANCHOR_RE.search(line):
            continue

        # H2 with numeric prefix: ## 3.8. Title
        m2 = H2_NUM_RE.match(line)
        if m2:
            _, num, title = m2.groups()
            current_h2_num = num
            h2_count += 1
            lines[i] = f"## {num}. {title} {{ #{num} }}"
            continue

        # H3 without number: ### Title
        m3 = H3_RE.match(line)
        if m3:
            title = m3.group(2)
            h3_count += 1
            slug = slugify(title)
            if current_h2_num:
                anchor = f"{current_h2_num}-{slug}"
            else:
                anchor = slug
            lines[i] = f"### {title} {{ #{anchor} }}"
            continue

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return h2_count, h3_count


def main() -> None:
    total_h2 = 0
    total_h3 = 0
    for md in sorted(BOOK_DIR.glob("*.md")):
        if md.name == "index.md":
            continue
        h2, h3 = process_file(md)
        total_h2 += h2
        total_h3 += h3
        print(f"  {md.name:35s}  H2: {h2:4d}  H3: {h3:4d}")
    print(f"\nTotal: H2={total_h2}, H3={total_h3}")


if __name__ == "__main__":
    main()
