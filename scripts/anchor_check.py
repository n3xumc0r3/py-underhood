#!/usr/bin/env python3
"""Проверка якорей и ссылок книги.

1. Дубликаты {#...} внутри одного файла (кроме известных легаси-дуплей).
2. Каждый H2/H3 имеет якорь (предупреждение, не ошибка).
3. Ссылки index.md и README.md: файл существует, якорь существует.
4. Текстовые ссылки N.N вне код-блоков на перенумерованные зоны (11.18+, 13-18)
   резолвятся в якоря соответствующей части.
"""
import re
import sys
from pathlib import Path

ROOT = Path('/home/z/my-project/py-underhood')
BOOK = ROOT / 'book'
KNOWN_DUPS = {'chtenie', 'chto'}
FENCE = re.compile(r'^\s*```')
ANCHOR_RE = re.compile(r'\{\s*#([A-Za-z0-9._\-]+)\s*\}')


def main():
    problems, warnings = [], []
    anchors, h2nums = {}, {}
    for f in sorted(BOOK.glob('*.md')):
        body = f.read_text()
        a = ANCHOR_RE.findall(body)
        anchors[f.name] = set(a)
        dup = {x for x in a if a.count(x) > 1} - KNOWN_DUPS
        if dup:
            problems.append(f'{f.name}: дубликаты якорей: {sorted(dup)}')
        if f.name != 'index.md' and not f.name.startswith('appendix'):
            nums = [int(m.group(1)) for m in re.finditer(r'^## \d+\.(\d+)\.', body, re.M)]
            h2nums[f.name] = nums
            if nums and nums != list(range(1, len(nums) + 1)):
                problems.append(f'{f.name}: H2-нумерация не последовательна: {nums}')

    # ссылки в index.md
    idx = (BOOK / 'index.md').read_text()
    for fname, anc in re.findall(r'\]\(([^)#]+\.md)(?:#([^)]+))?\)', idx):
        if '://' in fname:
            continue
        if fname not in anchors:
            problems.append(f'index.md -> нет файла {fname}')
            continue
        if anc and anc not in anchors[fname] and \
           not any(a.startswith(anc + '-') for a in anchors[fname]):
            problems.append(f'index.md -> нет якоря {fname}#{anc}')

    # ссылки в README.md
    readme = (ROOT / 'README.md').read_text()
    for target, anc in re.findall(r'\]\((book/[^)#]+\.md)(?:#([^)]+))?\)', readme):
        fname = target[5:]
        if fname not in anchors:
            problems.append(f'README.md -> нет файла {fname}')
            continue
        if anc and anc not in anchors[fname] and \
           not any(a.startswith(anc + '-') for a in anchors[fname]):
            problems.append(f'README.md -> нет якоря {fname}#{anc}')

    # текстовые ссылки N.N в перенумерованных зонах
    part_by_num = {}
    for f in sorted(BOOK.glob('*.md')):
        if f.name == 'index.md':
            continue
        h1 = next((ln for ln in f.read_text().split('\n') if ln.startswith('# Часть')), '')
        m = re.search(r'Часть ([IVX]+)\.', h1)
        if m:
            val = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
                   'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
                   'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18}[m.group(1)]
            part_by_num[val] = f.name
    ref_re = re.compile(r'(?<![\w.])(\d{1,2})\.(\d{1,2})(?![\w]|\.\d)')
    for f in sorted(BOOK.glob('*.md')):
        if f.name == 'index.md':
            continue
        fence = False
        for i, ln in enumerate(f.read_text().split('\n'), 1):
            if FENCE.match(ln):
                fence = not fence
                continue
            for m in ref_re.finditer(ln):
                n, mm = int(m.group(1)), int(m.group(2))
                if not (13 <= n <= 18 or (n == 11 and 18 <= mm <= 32)):
                    continue
                if mm < 1 or mm > len([x for x in h2nums.get(part_by_num.get(n, ''), [])]):
                    continue
                if fence:
                    pre = ln[:m.start()]
                    if not (pre.endswith('(') or pre.endswith('из ') or pre.endswith('см. ')):
                        continue
                tgt = part_by_num.get(n)
                if tgt and f'{n}.{mm}' not in anchors[tgt] and \
                   not any(a.startswith(f'{n}.{mm}-') for a in anchors[tgt]):
                    problems.append(f'{f.name}:{i}: ссылка {m.group(0)} без якоря в {tgt}')

    total = sum(len(v) for v in anchors.values())
    print(f'якорей: {total} в {len(anchors)} файлах')
    for w in warnings:
        print('W:', w)
    if problems:
        print('\nПРОБЛЕМЫ:')
        for p in problems:
            print(' -', p)
        sys.exit(1)
    print('ЯКОРЯ И ССЫЛКИ ОК')


if __name__ == '__main__':
    main()
