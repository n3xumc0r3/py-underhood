#!/usr/bin/env python3
r"""Перенумерация разделов книги по сложности — один скриптовый проход.

Карта частей (старая -> новая):
    XIII (байт-код)      -> XV      13-bytecode-vm.md     -> 15-bytecode-vm.md
    XIV (реализации)     -> XVII    14-implementations.md -> 17-implementations.md
    XV  (тестирование)   -> XIII    15-testing.md         -> 13-testing.md
    XVI (импорт)         -> XVI     без изменений
    XVII (C API)         -> XVIII   17-c-api.md           -> 18-c-api.md
    XVIII (упаковка)     -> XIV     18-packaging.md       -> 14-packaging.md

Внутри Части XI: zoneinfo (11.32) переставляется после datetime (11.17),
становится 11.18; старые 11.18..11.31 сдвигаются на +1 (-> 11.19..11.32);
якорь бенчмарков главы #11.31-benchmarki -> #11.32-benchmarki (по карте).

Правила:
  - single-pass замены (без каскада);
  - в код-блоках: секции маппятся (ссылки в комментариях), римские и имена файлов — нет;
  - границы (?<![\w.])KEY(?![\w]|\.\d): не трогают 'GCC 13.2.0', 'v1.13.2';
  - текстовые 'см. 15.4', '(XVII)', 'части X и XV' маппятся.

Скрипт меняет ТОЛЬКО содержимое. git mv делается отдельно (см. renumber_mv.sh).
"""
import re
import sys
from pathlib import Path

ROOT = Path('/home/z/my-project/py-underhood')
BOOK = ROOT / 'book'
LOG_PATH = ROOT / 'scripts' / 'renumber_log.txt'

FILE_MAP = {
    '13-bytecode-vm.md': '15-bytecode-vm.md',
    '14-implementations.md': '17-implementations.md',
    '15-testing.md': '13-testing.md',
    '17-c-api.md': '18-c-api.md',
    '18-packaging.md': '14-packaging.md',
}
FILE_MAP_REV = {v: k for k, v in FILE_MAP.items()}

SECTION_MAP = {}
for k in range(1, 6):
    SECTION_MAP[f'13.{k}'] = f'15.{k}'
for k in range(1, 5):
    SECTION_MAP[f'14.{k}'] = f'17.{k}'
for k in range(1, 12):
    SECTION_MAP[f'15.{k}'] = f'13.{k}'
for k in range(1, 12):
    SECTION_MAP[f'17.{k}'] = f'18.{k}'
for k in range(1, 12):
    SECTION_MAP[f'18.{k}'] = f'14.{k}'
for k in range(18, 32):
    SECTION_MAP[f'11.{k}'] = f'11.{k + 1}'
SECTION_MAP['11.32'] = '11.18'

PART_MAP = {'XIII': 'XV', 'XIV': 'XVII', 'XV': 'XIII', 'XVII': 'XVIII', 'XVIII': 'XIV'}

NEW_ORDER = [
    '01-basics.md', '02-context-managers.md', '03-generators.md', '04-async.md',
    '05-classes.md', '06-descriptors.md', '07-metaprogramming.md',
    '08-cpython-internals.md', '09-encodings.md', '10-introspection.md',
    '11-stdlib.md', '12-linters.md', '13-testing.md', '14-packaging.md',
    '15-bytecode-vm.md', '16-import.md', '17-implementations.md', '18-c-api.md',
]
ROMAN_VALUE = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8,
    'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18,
}

LOG = []


def log(msg):
    LOG.append(msg)


_sec_alt = '|'.join(re.escape(k) for k in sorted(SECTION_MAP, key=len, reverse=True))
SEC_RE = re.compile(r'(?<![\w.])(' + _sec_alt + r')(?![\w]|\.\d)')

_rom_alt = '|'.join(sorted(PART_MAP, key=len, reverse=True))
ROM_RE = re.compile(r'\b(' + _rom_alt + r')\b')

_file_names = {k[:-3]: v for k, v in FILE_MAP.items()}   # ключи без '.md'
_file_alt = '|'.join(re.escape(k) for k in sorted(_file_names, key=len, reverse=True))
FILE_RE = re.compile(r'(?<![\w-])(' + _file_alt + r')\.md')

FENCE_TOGGLE = re.compile(r'^\s*```')


def sub_sections(line, tag):
    def cb(m):
        old = m.group(0)
        new = SECTION_MAP[old]
        ctx = line[max(0, m.start() - 28):m.end() + 18].strip()
        log(f'SEC  [{tag}] {old} -> {new}  |{ctx}|')
        return new
    return SEC_RE.sub(cb, line)


def sub_romans(line, tag):
    def cb(m):
        old = m.group(0)
        new = PART_MAP[old]
        ctx = line[max(0, m.start() - 32):m.end() + 18].strip()
        log(f'ROM  [{tag}] {old} -> {new}  |{ctx}|')
        return new
    return ROM_RE.sub(cb, line)


def sub_files(line, tag):
    def cb(m):
        new = FILE_MAP[m.group(1) + '.md']
        ctx = line[max(0, m.start() - 30):m.end() + 18].strip()
        log(f'FILE [{tag}] {m.group(1)}.md -> {new}  |{ctx}|')
        return new
    return FILE_RE.sub(cb, line)


def split_fences(lines):
    """[(kind, [lines])], kind in {'text','fence'}; fence включает ```-строки."""
    segs, cur, kind = [], [], 'text'
    for ln in lines:
        if FENCE_TOGGLE.match(ln):
            if kind == 'text':
                if cur:
                    segs.append(('text', cur))
                cur, kind = [ln], 'fence'
            else:
                cur.append(ln)
                segs.append(('fence', cur))
                cur, kind = [], 'text'
        else:
            cur.append(ln)
    if cur:
        segs.append((kind, cur))
    return segs


def process_file(path):
    tag = path.name
    lines = path.read_text().split('\n')
    out = []
    for kind, seg in split_fences(lines):
        if kind == 'text':
            for ln in seg:
                ln = sub_sections(ln, tag)
                ln = sub_romans(ln, tag)
                ln = sub_files(ln, tag)
                out.append(ln)
        else:
            for ln in seg:
                out.append(sub_sections(ln, tag))
    path.write_text('\n'.join(out))


# --- 1. перенос zoneinfo -----------------------------------------------------

def move_zoneinfo():
    p = BOOK / '11-stdlib.md'
    lines = p.read_text().split('\n')
    zi = next(i for i, ln in enumerate(lines) if ln.startswith('## 11.32. '))
    bm = next(i for i, ln in enumerate(lines)
              if ln.startswith('### Бенчмарки к Части XI'))
    assert zi < bm, 'zoneinfo должна идти перед бенчмарками главы'
    block = lines[zi:bm]
    assert block[0].startswith('## 11.32.'), block[0]
    assert block[-1] == '', 'перед бенчмарками должна быть пустая строка'
    assert lines[zi - 1] == '', 'перед zoneinfo должна быть пустая строка'
    core = block[:-1]
    del lines[zi:bm]
    tgt = next(i for i, ln in enumerate(lines) if ln.startswith('## 11.18. '))
    assert lines[tgt - 1] == '', 'перед 11.18 должна быть пустая строка'
    lines[tgt:tgt] = core + ['']
    p.write_text('\n'.join(lines))
    log(f'MOVE zoneinfo: {len(core)} строк перенесено после 11.17 (перед "## 11.18.")')


# --- 2. index.md: структура + TOC --------------------------------------------

def rebuild_index():
    p = BOOK / 'index.md'
    lines = p.read_text().split('\n')

    i_struct = next(i for i, ln in enumerate(lines)
                    if ln.strip() == '## Структура по сложности')
    i_end_s = next(i for i in range(i_struct + 1, len(lines))
                   if lines[i].strip() == '---')
    struct_entry_re = re.compile(r'^\[Часть ([IVX]+)\]\(([^)]+)\) — (.*)$')
    appendix_re = re.compile(r'^\[Приложение ')
    entries, appendix_lines = {}, []
    j = i_struct + 1
    while j < i_end_s:
        m = struct_entry_re.match(lines[j])
        if m:
            entries[m.group(1)] = lines[j]
            j += 1
        elif appendix_re.match(lines[j]):
            appendix_lines.append(lines[j])
            j += 1
        elif lines[j].strip() == '':
            j += 1
        else:
            raise AssertionError(f'структура: неожиданная строка {lines[j]!r}')
    assert len(entries) == 18, f'структурных строк {len(entries)}, ждём 18'
    new_struct = ['']
    for rom in sorted(entries, key=lambda r: ROMAN_VALUE[r]):
        new_struct.append(entries[rom])
        new_struct.append('')
    for ln in appendix_lines:
        new_struct.append(ln)
        new_struct.append('')
    lines[i_struct + 1:i_end_s] = new_struct

    i_toc = next(i for i, ln in enumerate(lines) if ln.strip() == '## Содержание')
    i_end_t = next(i for i in range(i_toc + 1, len(lines))
                   if lines[i].strip() == '---')
    region = lines[i_toc + 1:i_end_t]
    blocks, cur, pre = [], None, []
    for ln in region:
        if ln.startswith('### '):
            cur = [ln]
            blocks.append(cur)
        elif cur is None:
            pre.append(ln)
        else:
            cur.append(ln)
    open_re = re.compile(r'\[Открыть часть →\]\(([^)]+)\)')
    keyed, app_block = {}, None
    for b in blocks:
        if b[0].startswith('### Приложения'):
            app_block = b
            continue
        m = open_re.search('\n'.join(b))
        assert m, f'нет "Открыть часть" в блоке {b[0]!r}'
        fname = m.group(1)
        assert fname in NEW_ORDER, f'неожиданный файл TOC: {fname}'
        keyed[fname] = b
    assert len(keyed) == 18 and app_block is not None

    def strip_tail(b):
        while b and b[-1].strip() == '':
            b.pop()
        return b

    new_region = list(pre)
    for f in NEW_ORDER:
        b = strip_tail(keyed[f])
        new_region.extend(b)
        new_region.append('')
    new_region.extend(strip_tail(app_block))
    new_region.append('')
    lines[i_toc + 1:i_end_t] = new_region
    p.write_text('\n'.join(lines))
    log('INDEX: структура + TOC переставлены')


# --- 3. README ----------------------------------------------------------------

def rebuild_readme():
    p = ROOT / 'README.md'
    lines = p.read_text().split('\n')
    row_re = re.compile(r'^\| ([IVX]+) \| \[[^\]]+\]\(book/([^)]+)\)')
    rows, idxs = {}, []
    for i, ln in enumerate(lines):
        m = row_re.match(ln)
        if m:
            rows[m.group(2)] = ln
            idxs.append(i)
    assert len(idxs) == 18, f'строк таблицы README {len(idxs)}, ждём 18'
    ordered = [rows[f] for f in NEW_ORDER]  # README уже прошёл FILE-проход
    for i, ln in zip(idxs, ordered):
        lines[i] = ln
    p.write_text('\n'.join(lines))
    log('README: таблица частей переставлена')


# --- 4. mkdocs.yml: nav --------------------------------------------------------

def rebuild_nav():
    p = ROOT / 'mkdocs.yml'
    lines = p.read_text().split('\n')
    part_re = re.compile(r"^  - '(Часть [IVX]+\..+)': (\S+\.md)$")
    entries, idxs = {}, []
    for i, ln in enumerate(lines):
        m = part_re.match(ln)
        if m:
            fname = FILE_MAP.get(m.group(2), m.group(2))
            rom_old = re.match(r'Часть ([IVX]+)\.', m.group(1)).group(1)
            rom_new = PART_MAP.get(rom_old, rom_old)
            title = re.sub(r'^Часть [IVX]+\.', f'Часть {rom_new}.', m.group(1))
            entries[fname] = f"  - '{title}': {fname}"
            idxs.append(i)
    assert len(idxs) == 18, f'nav-строк частей {len(idxs)}, ждём 18'
    ordered = [entries[f] for f in NEW_ORDER]
    for i, ln in zip(idxs, ordered):
        lines[i] = ln
    p.write_text('\n'.join(lines))
    log('MKDOCS: nav переставлен')


# --- 5. верификация ------------------------------------------------------------

KNOWN_ANCHOR_DUPS = {'chtenie', 'chto'}


def collect_anchors():
    anchors = {}
    part_files = {}
    for f in sorted(BOOK.glob('*.md')):
        if f.name == 'index.md':
            continue
        body = f.read_text()
        a = re.findall(r'\{\s*#([A-Za-z0-9._\-]+)\s*\}', body)
        anchors[f.name] = set(a)
        h1 = next((ln for ln in body.split('\n') if ln.startswith('# Часть')), '')
        m = re.search(r'Часть ([IVX]+)\.', h1)
        if m:
            part_files[ROMAN_VALUE[m.group(1)]] = f.name
    return anchors, part_files


def verify():
    problems = []
    golf = (BOOK / 'appendix-c-code-golf.md').read_text()
    if 'r(1546)' not in golf:
        problems.append('r(1546) исчез из appendix-c')
    intro = (BOOK / '10-introspection.md').read_text()
    if 'GCC 13.2.0' not in intro:
        problems.append('GCC 13.2.0 исчез из 10-introspection')
    if '14.4' in re.sub(r'17\.4', '', intro) and '(см. 14.4)' in intro:
        problems.append('в 10-introspection осталась старая ссылка (см. 14.4)')

    anchors, part_files = collect_anchors()

    for f in sorted(BOOK.glob('*.md')):
        if f.name == 'index.md' or f.name.startswith('appendix'):
            continue
        nums = [int(m.group(1)) for m in
                re.finditer(r'^## \d+\.(\d+)\.', f.read_text(), re.M)]
        if nums != list(range(1, len(nums) + 1)):
            problems.append(f'{f.name}: H2-нумерация не последовательна: {nums}')
        a = re.findall(r'\{\s*#([A-Za-z0-9._\-]+)\s*\}', f.read_text())
        dup = {x for x in a if a.count(x) > 1} - KNOWN_ANCHOR_DUPS
        if dup:
            problems.append(f'дубликаты якорей в {f.name}: {dup}')

    counts = {n: len(re.findall(rf'^## {n}\.(\d+)\.', (BOOK / fn).read_text(), re.M))
              for n, fn in part_files.items()}
    ref_re = re.compile(r'(?<![\w.])(\d{1,2})\.(\d{1,2})(?![\w]|\.\d)')
    unresolved = []
    for f in sorted(BOOK.glob('*.md')):
        if f.name == 'index.md':
            continue
        fence = False
        for i, ln in enumerate(f.read_text().split('\n'), 1):
            if FENCE_TOGGLE.match(ln):
                fence = not fence
                continue
            for m in ref_re.finditer(ln):
                n, mm = int(m.group(1)), int(m.group(2))
                # проверяем только перенумерованные зоны: секции 11.18+ и части 13-18
                if not (13 <= n <= 18 or (n == 11 and 18 <= mm <= 32)):
                    continue
                if mm < 1 or mm > counts.get(n, 0):
                    continue  # версии/десятичные (24.0, 15.0, ...)
                if fence:
                    pre = ln[:m.start()]
                    if not (pre.endswith('(') or pre.endswith('из ')
                            or pre.endswith('см. ')):
                        continue  # в коде это просто числа, не ссылки
                target = part_files.get(n)
                if target and f'{n}.{mm}' not in anchors[target] and \
                   not any(a.startswith(f'{n}.{mm}-') for a in anchors[target]):
                    unresolved.append(f'{f.name}:{i}: {m.group(0)}')
    if unresolved:
        problems.append('неразрешённые ссылки N.N: ' + '; '.join(unresolved[:25]))

    for fname, pat, expected in [
        ('11-stdlib.md', '## 11.18. `zoneinfo`', True),
        ('11-stdlib.md', '## 11.32. `venv`', True),
        ('11-stdlib.md', '{ #11.32-benchmarki }', True),
        ('11-stdlib.md', '{ #11.18-baza }', True),
        ('11-stdlib.md', '{ #11.32-fold }', False),
        ('13-testing.md', '# Часть XIII. Тестирование', True),
        ('13-testing.md', '{ #13.11-benchmarki }', True),
        ('13-testing.md', '{ #15.1 }', False),
        ('14-packaging.md', '# Часть XIV. Упаковка', True),
        ('14-packaging.md', '{ #14.11-benchmarki }', True),
        ('14-packaging.md', 'Части XVIII', False),
        ('15-bytecode-vm.md', '# Часть XV. От .py к байт-коду', True),
        ('15-bytecode-vm.md', '{ #15.5-benchmarki }', True),
        ('15-bytecode-vm.md', '{ #13.2 }', False),
        ('16-import.md', '{ #16.11-benchmarki }', True),
        ('16-import.md', '(XVII)', False),
        ('17-implementations.md', '# Часть XVII. Не только CPython', True),
        ('17-implementations.md', '{ #17.4-benchmarki }', True),
        ('18-c-api.md', '# Часть XVIII. C-расширения', True),
        ('18-c-api.md', '{ #18.11-benchmarki }', True),
        ('18-c-api.md', 'Части XIII', False),
        ('07-metaprogramming.md', 'части X и XV', False),
        ('07-metaprogramming.md', 'части X и XIII', True),
    ]:
        fpath = BOOK / fname
        if not fpath.exists():
            fpath = BOOK / FILE_MAP_REV.get(fname, fname)
        if not fpath.exists():
            problems.append(f'файла {fname} нет на диске')
            continue
        got = pat in fpath.read_text()
        if got != expected:
            problems.append(f'{fname}: {pat!r} присутствие={got}, ожидалось={expected}')

    idx = (BOOK / 'index.md').read_text()
    n11 = idx.count('](11-stdlib.md#11.')
    if n11 != 32:
        problems.append(f'в index.md ссылок 11.x: {n11}, ждём 32')
    for pat, expected in [
        ('### Часть XIII. Тестирование', True),
        ('### Часть XIV. Упаковка', True),
        ('### Часть XV. От .py к байт-коду', True),
        ('### Часть XVII. Не только CPython', True),
        ('### Часть XVIII. C-расширения', True),
        ('### Часть XVI. Механика импорта', True),
        ('(13-testing.md)', True),
        ('(18-packaging.md)', False),
        ('(15-testing.md)', False),
    ]:
        got = pat in idx
        if got != expected:
            problems.append(f'index.md: {pat!r} присутствие={got}, ожидалось={expected}')
    toc_links = re.findall(r'\]\(([^)#]+\.md)(?:#([^)]+))?\)', idx)
    for fname, anc in toc_links:
        if '://' in fname:
            continue
        real = fname if fname in anchors else FILE_MAP_REV.get(fname, fname)
        if real not in anchors:
            problems.append(f'index.md -> битый файл {fname}')
            continue
        if anc and not any(a == anc or a.startswith(anc + '-') for a in anchors[real]):
            problems.append(f'index.md -> битый якорь {fname}#{anc}')

    rme = (ROOT / 'README.md').read_text()
    for fname in NEW_ORDER:
        if f'(book/{fname})' not in rme:
            problems.append(f'README: нет ссылки на book/{fname}')
    for old in FILE_MAP:
        if f'(book/{old})' in rme:
            problems.append(f'README: осталась старая ссылка book/{old}')

    nav = (ROOT / 'mkdocs.yml').read_text()
    nav_re = re.compile(r"^  - 'Часть [IVX]+\.[^']*': (\S+\.md)$", re.M)
    nav_files = [FILE_MAP.get(x, x) for x in nav_re.findall(nav)]
    if nav_files != NEW_ORDER:
        problems.append(f'mkdocs nav порядок/имена неверны: {nav_files}')
    return problems


def main():
    try:
        move_zoneinfo()
        for f in sorted(BOOK.glob('*.md')):
            process_file(f)
        process_file(ROOT / 'README.md')
        rebuild_index()
        rebuild_readme()
        rebuild_nav()
        problems = verify()
    finally:
        LOG_PATH.write_text('\n'.join(LOG) + '\n')
    print(f'замен: {len(LOG)}; лог: {LOG_PATH}')
    if problems:
        print('\nПРОБЛЕМЫ:')
        for pr in problems:
            print(' -', pr)
        sys.exit(1)
    print('ВЕРИФИКАЦИЯ ПРОЙДЕНА')


if __name__ == '__main__':
    main()
