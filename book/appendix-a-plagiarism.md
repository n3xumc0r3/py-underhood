# Приложение A. Системы обнаружения плагиата

> Это приложение — контекст для тех, кому интересно, как работают системы проверки кода. Основной фокус конспекта — на скрытых возможностях языка, а не на обходе антиплагиата.

## A.1. Winnowing (хеш-винновинг) { #A.1 }

Алгоритм для поиска плагиата в текстах и коде. Применяется в **Dolos** и **Codequiry**. **MOSS** (Stanford) использует похожий token-based fingerprinting, но точный алгоритм публично не описан. **JPlag** использует **Greedy String Tiling** (GST), а не Winnowing в чистом виде — хотя на токенизированном представлении. У **Noplag** и **Viper** точные алгоритмы варьируются, документация публично недоступна.

**4 шага алгоритма:**

1. **Нормализация** — удаляются пробелы, знаки препинания, всё приводится к нижнему регистру.
2. **K-граммы** — нарезка на перекрывающиеся цепочки длины `k`. Слово «привет» при `k=3` → `при`, `рив`, `иве`, `вет`.
3. **Хеширование** — каждый k-грамм превращается в число. Текст становится цепочкой чисел.
4. **Провеивание (winnowing)** — берётся «скользящее окно» (например, ширины 4), внутри каждого окна сохраняется только минимальный хеш.

Итог: 80–90% хешей отбрасывается, но оставшиеся «отпечатки» гарантированно покрывают весь документ. Защита от мелких правок (замена союза не разрушает околостоящие k-граммы). Миллисекундная проверка по миллионам документов.

Реализация всех четырёх шагов на чистом Python (~30 строк):

```python
import hashlib

def _kgram_hashes(text: str, k: int = 5):
    """Шаги 1–3: нормализация → k-граммы → хеши."""
    norm = ''.join(c.lower() for c in text if c.isalnum())      # шаг 1
    for i in range(len(norm) - k + 1):                          # шаг 2
        h = int(hashlib.md5(norm[i:i + k].encode()).hexdigest()[:8], 16)  # шаг 3
        yield i, h                                              # (позиция, хеш)

def winnow(text: str, k: int = 5, w: int = 4) -> list:
    """Шаг 4: окно ширины w, из каждого — минимальный хеш."""
    fingerprints, prev_pos, window = [], -1, []
    for pos, h in _kgram_hashes(text, k):
        window.append((h, pos))
        if len(window) == w:
            m = min(window)           # min по (хеш, позиция): при равенстве — левый
            if m[1] != prev_pos:      # тот же отпечаток дважды не сохраняем
                fingerprints.append(m)
                prev_pos = m[1]
            window.pop(0)
    return fingerprints

def similarity(a: str, b: str, k: int = 5, w: int = 4) -> float:
    """Коэффициент Жаккара по множествам отпечатков."""
    fa = {h for h, _ in winnow(a, k, w)}
    fb = {h for h, _ in winnow(b, k, w)}
    return len(fa & fb) / len(fa | fb) if fa | fb else 1.0
```

Проверка на трёх парах показывает и силу, и границу буквенного уровня (`renamed_everywhere` ниже — гипотетическая функция, переименовывающая все переменные; её механика — токенизация, см. A.2):

```python
similarity(src, src)                      # 1.0   — идентичный текст
similarity(src, src.replace('total += item', 'total = total + item'))
                                          # 0.92  — локальная правка почти не видна
similarity(src, renamed_everywhere(src))  # 0.03  — переименование уничтожает отпечаток
```

⚠️ Последняя строка — ключ к пониманию: на **буквах** переименование переменных разрушает k-граммы. Поэтому реальные системы (MOSS, Dolos — см. A.2) провеивают не буквы, а **токены**: `IDENTIFIER` — и переименование уже ничего не меняет. Реализация выше остаётся честной демонстрацией механики окна и минимальных хешей.

Оригинальная статья: **Saul Schleimer, Daniel S. Wilkerson, Alex Aiken.** *Winnowing: Local Algorithms for Document Fingerprinting.* ACM SIGMOD 2003. PDF: https://theory.stanford.edu/~aiken/publications/papers/sigmod03.pdf

## A.2. MOSS, JPlag, Dolos, Codequiry { #A.2 }

**MOSS** (Measure of Software Similarity, Stanford, Aiken) — для текста работает по классическому Winnowing. **Для кода** сначала превращает исходник в цепочку **токенов** (не букв). Поэтому `x = 10` и `my_super_variable = 10` для MOSS идентичны — оба имени становятся токеном `IDENTIFIER`. `0x3` и `3` — тоже одинаковый токен `NUMBER`.

**JPlag** (KIT) — главный аналог MOSS. Подробно разбирает токенизацию и AST-сравнение. Статья: Prechelt et al., *Finding Plagiarisms among a Set of Programs with JPlag.* JUCS 2002. https://www.jucs.org/jucs_8_11/finding_plagiarisms_among_a

**Dolos** (Ghent University / UGent) — современный инструмент, использует token + AST-гибрид. https://dolos.ugent.be/. Статья: Maertens et al., *Dolos: Language-agnostic Plagiarism Detection in Source Code.* 2022.

**Codequiry** — коммерческий MOSS-replacement, проверяет против GitHub и веба. Помимо плагиата — детектор AI-кода (см. A.6).

## A.3. Метрики Хальстеда { #A.3 }

«Математический паспорт кода». Считает уникальность, не имена.

- **η₁** — количество уникальных операторов (distinct operators).
- **η₂** — количество уникальных операндов (distinct operands).
- **N₁** — суммарное количество операторов.
- **N₂** — суммарное количество операндов.
- **Словарь (η)** = `η₁ + η₂` — число уникальных токенов.
- **Длина (N)** = `N₁ + N₂` — суммарное число токенов.
- **Объём (V)** = `N · log₂(η₁+η₂)` — бит для хранения.
- **Сложность (D)** = `(η₁/2) · (N₂/η₂)`.
- **Усилие (E)** = `V · D`.

Если просто переименовать переменные — `η₁` и `η₂` останутся теми же. Система увидит идентичный «паспорт» и поднимет тревогу.

Реализация через `ast` (~25 строк) — операторы и операнды классифицируются по типам узлов:

```python
import ast, math

_BIN = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
        ast.Mod: "%", ast.Pow: "**", ast.LShift: "<<", ast.RShift: ">>",
        ast.BitOr: "|", ast.BitAnd: "&", ast.BitXor: "^"}
_UNARY = {ast.USub: "-", ast.UAdd: "+", ast.Not: "not", ast.Invert: "~"}
_CMP = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">",
        ast.GtE: ">=", ast.In: "in", ast.NotIn: "not in", ast.Is: "is", ast.IsNot: "is not"}

def halstead(src: str) -> dict:
    operators, operands = [], []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.BinOp):    operators.append(_BIN[type(node.op)])
        elif isinstance(node, ast.UnaryOp): operators.append(_UNARY[type(node.op)])
        elif isinstance(node, ast.Compare):
            operators.extend(_CMP[type(op)] for op in node.ops)
        elif isinstance(node, ast.Assign):    operators.append("=")
        elif isinstance(node, ast.AugAssign): operators.append("+=")
        elif isinstance(node, ast.Call):      operators.append("()")
        elif isinstance(node, ast.Name):      operands.append(node.id)
        elif isinstance(node, ast.Constant):  operands.append(repr(node.value))
    n1, n2 = len(set(operators)), len(set(operands))   # уникальные
    N1, N2 = len(operators), len(operands)             # суммарные
    V = (N1 + N2) * math.log2(n1 + n2) if n1 + n2 else 0.0
    D = (n1 / 2) * (N2 / n2) if n2 else 0.0
    return {"V": round(V, 1), "D": round(D, 1), "E": round(V * D, 1)}
```

Демонстрация «паспорта» на двух переименованных версиях одного кода:

```python
src = '''
def process(data):
    total = 0
    for item in data:
        if item > 0:
            total += item
    return total
'''
renamed = src.replace("process", "handle").replace("data", "rows") \
             .replace("total", "sum_").replace("item", "row")

halstead(src)      # {'V': 33.7, 'D': 3.4, 'E': 113.7}
halstead(renamed)  # {'V': 33.7, 'D': 3.4, 'E': 113.7} — идентично
```

Оригинальная книга: **Maurice H. Halstead.** *Elements of Software Science.* North-Holland, 1977.

## A.4. Цикломатическая сложность (McCabe) { #A.4 }

Считается количество независимых путей выполнения через граф потока управления. Базовая формула McCabe: `M = E − N + 2P`, где `E` — рёбра, `N` — узлы, `P` — компоненты связности. Часто упрощают до `M = количество if + количество for/while + количество case + 1`.

Совпадение до третьего знака после запятой у двух работ — маркер искусственного изменения.

Подсчёт через `ast` (~15 строк) — каждый узел-ветвление добавляет независимый путь:

```python
import ast

_BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp,
             ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Assert)

def cyclomatic(src: str) -> int:
    m = 1                                            # базовый путь
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, _BRANCHES):
            m += 1
        elif isinstance(node, ast.BoolOp):           # a and b and c → +2 пути
            m += len(node.values) - 1
        elif isinstance(node, ast.Match):            # каждый case — ветка
            m += len(node.cases)
        elif isinstance(node, ast.comprehension):    # каждый for внутри [...]
            m += 1 + len(node.ifs)
    return m
```

Тернарник, comprehension с `if`, `except` — всё считает честно, потому что в AST это полноценные узлы. Замена `for` на list comprehension сложность **не меняет** (пути те же) — в отличие от AST-сравнения (A.5), где это разные узлы.

Оригинальная статья: **Thomas J. McCabe.** *A Complexity Measure.* IEEE Transactions on Software Engineering, 1976.

## A.5. AST-нормализация (canonicalization) { #A.5 }

Продвинутые аналоги MOSS (Dolos, JPlag) строят дерево синтаксиса и **нормализуют** его перед сравнением:

1. **Переименование идентификаторов** — все `Name`-узлы заменяются на каноническую форму (`var_1`, `var_2`, `var_3` в порядке первого появления). Поэтому `x = 10` и `my_super_variable = 10` после нормализации **идентичны**.
2. **Линеаризация дерева** — AST превращается в строку токенов (через pre-order обход), дальше применяется Winnowing или Greedy String Tiling.
3. **Удаление комментариев и пробелов** — всегда на этапе предобработки.

Нормализация идентификаторов в ~20 строк — сердце метода:

```python
import ast

def normalize(src: str) -> str:
    """Переименование идентификаторов в порядке первого появления."""
    names: dict[str, str] = {}

    class Norm(ast.NodeTransformer):
        def _canon(self, key: str) -> str:
            return names.setdefault(key, f"v{len(names) + 1}")

        def visit_FunctionDef(self, node):
            node.name = self._canon(node.name)   # имя функции — тоже идентификатор
            self.generic_visit(node)
            return node

        def visit_Name(self, node):
            return ast.copy_location(ast.Name(id=self._canon(node.id), ctx=node.ctx), node)

        def visit_arg(self, node):
            return ast.arg(arg=self._canon(node.arg), annotation=None)  # аннотации выкидываем

    return ast.dump(Norm().visit(ast.parse(src)), include_attributes=False)
```

Результат — два «разных» исходника дают одинаковый дамп:

```python
src = '''
def process(data):
    total = 0
    for item in data:
        if item > 0:
            total += item
    return total
'''
renamed = '''
def handle(rows):
    sum_ = 0
    for row in rows:
        if row > 0:
            sum_ += row
    return sum_
'''

normalize(src) == normalize(renamed)   # True — только структура имеет значение
```

Упрощения против промышленных реализаций: переименование глобальное (не по областям видимости — два локальных `x` в разных функциях получат один канонический номер), имена функций здесь канонизируются наравне с переменными, а аннотации типов отбрасываются. Настоящие системы делают переименование по областям видимости и линейизуют дерево в строку токенов для Winnowing/GST.

Подтверждено в статье про Dolos (Maertens et al., 2022): «Token renaming and syntax tree linearisation increase effectiveness at a cost of efficiency». И JPlag: «JPlag's tokenization step, as for most token-based detectors, is a form of lexical normalization» (Sağlam et al., 2024).

**Что это значит для атак:**

- Просто переименовать переменные — **не работает**.
- Заменить `for` на `while` — **работает**, потому что меняется тип узла.
- Атаки с переносом логики в рантайм (через `compile`/`globals`/`__annotations__`) — **работают**: AST-анализатор видит только вызов `compile()`, но не видит, что внутри.

## A.6. Стилометрия и детекторы AI-кода { #A.6 }

Классическая стилометрия (отдельная от плагиата задача «кто автор этого кода») в чистом виде применяется редко. Вместо этого «стиль» — маркер **«этот код сгенерирован AI»**.

**Codequiry** анализирует:

- **Code entropy** — насколько «однообразно» написано.
- **Comment patterns** — шаблоны комментариев.
- **Error handling consistency** — единообразие обработки ошибок.
- **Stylistic uniformity** — стилистическая однородность.
- **Style Incongruence Detection** — флаги, когда стиль кусков кода внутри одной работы не совпадает.

Эти маркеры нацелены на AI-код (который часто «ровнее», чем человек) и на копипасту с разных источников (где стилистика скачет от блока к блоку).

Часть сигналов воспроизводится вручную (~30 строк): код превращается в вектор признаков, близость текстов — косинус между векторами:

```python
import math, re

def style_vector(src: str) -> list[float]:
    lines = [l for l in src.splitlines() if l.strip()]
    n = max(len(lines), 1)
    indents = [len(l) - len(l.lstrip()) for l in lines]
    kw = ["for", "if", "while", "def", "lambda", "try", "except", "with", "import", "return"]
    counts = [len(re.findall(rf"\b{w}\b", src)) / n for w in kw]
    features = [
        sum(len(l.strip()) for l in lines) / n,      # средняя длина строки
        max(indents, default=0),                     # максимальная вложенность
        (src.count("\n") - len(lines)) / n,          # плотность пустых строк
        src.count("#") / n,                          # плотность комментариев
        *counts,                                     # частоты ключевых слов
    ]
    norm = math.sqrt(sum(f * f for f in features)) or 1.0
    return [f / norm for f in features]              # на единичную сферу

def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
```

Проверка на трёх парах:

```python
cosine(style_vector(compact), style_vector(same_style))       # 1.0  — стиль совпадает
cosine(style_vector(compact), style_vector(verbose_loops))    # 0.81 — стили разъехались
```

⚠️ На сниппетах в 10–20 строк ручная стилометрия даёт лишь грубый сигнал: реальные детекторы смотрят на файлы в сотни строк и сравнивают распределения по десяткам признаков (идиомы, выбор между comprehension и циклом, привычность сочетаний токенов — вплоть до n-грамм). Механизм тот же: текст → числовой вектор → метрика близости.

**Dolos** сам по себе стилометрию не делает — это token-based + Winnowing система. Стиль как отдельный сигнал — это скорее надстройка.

⚠️ **Практический вывод**: просто сменить стиль внутри одного файла **контрпродуктивно** — стиль скачет и триггерит Style Incongruence Detection. Лучше выбрать один стиль и держать его по всему файлу.

## A.7. Динамический анализ (рантайм) { #A.7 }

В отличие от статического MOSS, динамические системы смотрят на поведение программы в рантайме (в памяти процесса):

1. **Трейсинг инструкций** — сколько раз процессор выполнил сложение, прыгнул по веткам. Если у двух программ одинаковый «цифровой пульс» при одинаковых входных данных — плагиат.
2. **Граф вызовов (Call Graph)** — отслеживает syscall'ы. Замена `requests` на `httpx` бесполезна: обе библиотеки внутри дёргают одни и те же сокеты ОС.
3. **Heap & Stack анализ** — как растёт стек и как выделяется память.

На практике динамические системы **крайне редки** в академическом антиплагиате. Причина — для корректного сравнения двух программ по их runtime-следу нужно **идентичное окружение**: та же ОС, та же версия интерпретатора, тот же набор библиотек, тот же CPU. В реальном учебном процессе это обеспечить трудно. Поэтому динамический анализ в основном встречается в специализированных ИБ-соревнованиях (где окружение контролируется) и в коммерческих enterprise-продуктах.

В **MOSS**, **JPlag**, **Dolos**, **Codequiry** динамический анализ **не применяется** — это чисто статические системы. Столкнуться с динамическим анализом в учебном курсе можно только в специализированных ИБ-программах или при проверке capture-the-flag-решений.

## A.8. Constant folding, propagation, dead code elimination { #A.8 }

Современные аналоги MOSS перед проверкой запускают оптимизации:

- **Constant folding** — `1+1+1` и `0x3` превращаются в `3` ещё до анализа. Чистый классический MOSS этого не делает.
- **Constant propagation** — если `PI = 3.14` и ниже идёт `x = PI * 2`, то `x` заменяется на `6.28`.
- **Dead code elimination** — недостижимые ветки и неиспользуемые переменные вырезаются до сравнения.

---

