#!/usr/bin/env python3
"""
Split python_conspect (15).md into 17 files under py-underhood/book/.

Layout (1-indexed line ranges from the source file):
  index.md                       1 -   252  (cover + TOC)
  01-basics.md                 253 -  5101  (Part I)
  02-context-managers.md       5102 -  5516  (Part II)
  03-generators.md             5517 -  6223  (Part III)
  04-async.md                  6224 -  7156  (Part IV)
  05-classes.md                7157 -  9489  (Part V)
  06-descriptors.md            9490 -  9879  (Part VI)
  07-metaprogramming.md        9880 - 11107  (Part VII)
  08-cpython-internals.md     11108 - 12128  (Part VIII)
  09-encodings.md             12129 - 12402  (Part IX)
  10-introspection.md         12403 - 12818  (Part X)
  11-stdlib.md                12819 - 15511  (Part XI)
  12-linters.md               15512 - 15736  (Part XII)
  appendix-a-plagiarism.md    15737 - 15844  (Appendix A)
  appendix-b-code-checkers.md 15845 - 16439  (Appendix B)
  appendix-c-code-golf.md     16440 - 17718  (Appendix C)
  appendix-d-references.md    17719 - 17890  (Appendix D)
"""
from pathlib import Path

SRC = Path("/home/z/my-project/upload/python_conspect (15).md")
DST = Path("/home/z/my-project/py-underhood/book")

# (filename, start_line, end_line) — 1-indexed, inclusive
SLICES = [
    ("index.md",                       1,    252),
    ("01-basics.md",                 253,   5101),
    ("02-context-managers.md",      5102,   5516),
    ("03-generators.md",            5517,   6223),
    ("04-async.md",                 6224,   7156),
    ("05-classes.md",               7157,   9489),
    ("06-descriptors.md",          9490,    9879),
    ("07-metaprogramming.md",       9880,  11107),
    ("08-cpython-internals.md",    11108,  12128),
    ("09-encodings.md",            12129,  12402),
    ("10-introspection.md",        12403,  12818),
    ("11-stdlib.md",               12819,  15511),
    ("12-linters.md",              15512,  15736),
    ("appendix-a-plagiarism.md",   15737,  15844),
    ("appendix-b-code-checkers.md",15845,  16439),
    ("appendix-c-code-golf.md",    16440,  17718),
    ("appendix-d-references.md",   17719,  17890),
]


def main() -> None:
    lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(lines)
    print(f"Source: {SRC} ({total} lines)")

    # Sanity check: each slice end must not exceed total
    for name, start, end in SLICES:
        assert end <= total, f"{name}: end {end} > total {total}"
        assert start >= 1, f"{name}: start {start} < 1"

    # Verify slice boundaries align with section headers
    headers = {
        253: "# Часть I",
        5102: "# Часть II",
        5517: "# Часть III",
        6224: "# Часть IV",
        7157: "# Часть V",
        9490: "# Часть VI",
        9880: "# Часть VII",
        11108: "# Часть VIII",
        12129: "# Часть IX",
        12403: "# Часть X",
        12819: "# Часть XI",
        15512: "# Часть XII",
        15737: "# Приложение A",
        15845: "# Приложение B",
        16440: "# Приложение C",
        17719: "# Приложение D",
    }
    for line_no, expected_prefix in headers.items():
        actual = lines[line_no - 1]
        assert actual.startswith(expected_prefix), (
            f"Line {line_no}: expected '{expected_prefix}', got: {actual[:80]!r}"
        )
    print("Boundary check: OK")

    DST.mkdir(parents=True, exist_ok=True)
    summary = []
    for name, start, end in SLICES:
        chunk = "".join(lines[start - 1 : end])
        out = DST / name
        # Ensure file ends with exactly one newline
        if not chunk.endswith("\n"):
            chunk += "\n"
        out.write_text(chunk, encoding="utf-8")
        n_lines = end - start + 1
        n_bytes = len(chunk.encode("utf-8"))
        summary.append((name, n_lines, n_bytes))
        print(f"  wrote {name:35s}  {n_lines:6d} lines  {n_bytes:8d} bytes")

    print(f"\nTotal files: {len(SLICES)}")
    print(f"Total lines: {sum(s[1] for s in summary)}")
    print(f"Total bytes: {sum(s[2] for s in summary)}")


if __name__ == "__main__":
    main()
