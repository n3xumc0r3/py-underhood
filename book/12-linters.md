# Часть XII. Линтеры и директивы в комментариях

> Комментарий в Python — не всегда просто комментарий: некоторые строки парсер читает сам (`# -*- coding: utf-8 -*-`, PEP 263), некоторые обрабатывают линтеры и тайпчекеры (`# noqa`, `# type: ignore`), некоторые — doctest. Часть разбирает каждую директиву и инструменты, которые её потребляют: ruff (12.7), гранулярные подавления (12.8–12.9), pre-commit (12.10) и `pyproject.toml` (12.6).

## 12.1. `# -*- coding: ... -*-` (PEP 263) { #12.1 }

> **→ см. также:** Часть IX (9.1–9.6) — полный разбор работы с кодировками исходных файлов и собственными кодеками.

Жёсткая директива для парсера CPython — указывает кодировку исходного файла. Подробно в Части IX.

```python
# -*- coding: utf-8 -*-
# coding: cp1251
# coding=iso-8859-1
```

## 12.2. `# type: int` (PEP 484) { #12.2 }

Type comments — до того как в Python появились полноценные аннотации через двоеточие (`x: int = 5`), типы писали в комментариях. CPython до сих пор умеет их парсить — в поле AST `type_ignores` (заполняется только при `ast.parse(..., type_comments=True)` / флаге `PyCF_TYPE_COMMENTS`):

```python
x = 10  # type: int

def f(x):  # type: (int) -> str
    return str(x)

# Для коллекций (в эпоху type comments писали List[int] из typing; современный list[int] — PEP 585, 3.9+)
data = []  # type: list[int]
```

`mypy` и другие тайп-чекеры читают эти комментарии и проверяют типы. CPython сам ничего с ними не делает — только сохраняет в AST.

## 12.3. `# noqa` — директива линтеров { #12.3 }

`# noqa` — это **не** фича CPython, а директива **линтеров** (`flake8`, `ruff`, `pylint`), не интерпретатора. Линтеры работают до запуска кода: читают файл построчно, ищут нарушения. Если в конце строки стоит `# noqa`, линтер закрывает глаза на эту строку.

```python
import sys  # noqa: F401            # игнорировать конкретную ошибку
import os, sys, json  # noqa         # игнорировать все ошибки на строке
x = "очень длинная строка..."  # noqa: E501   # игнорировать длинную строку

# pylint: disable=line-too-long
result = "строка" + 42  # type: ignore   # для mypy — игнорировать type-ошибку
```

**Файл-уровневое отключение:**

```python
# flake8: noqa        — отключить все проверки flake8 в файле
# ruff: noqa          — то же для ruff
# pylint: skip-file   — то же для pylint
```

## 12.4. `# doctest: +ELLIPSIS` — директивы doctest { #12.4 }

`doctest` — модуль для запуска тестов из docstring'ов. Директивы модифицируют поведение теста:

```python
def sample():
    """
    >>> print(list(range(20)))  # doctest: +ELLIPSIS
    [0, 1, 2, ..., 19]
    
    >>> print('Hello   World')  # doctest: +NORMALIZE_WHITESPACE
    Hello World
    
    >>> expensive_call()  # doctest: +SKIP
    >>> 1/0  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    ZeroDivisionError: division by zero
    """
    pass
```

Распространённые директивы:

- `+ELLIPSIS` — `...` в выводе матчит любое количество любых значений.
- `+NORMALIZE_WHITESPACE` — пробелы в выводе игнорируются.
- `+SKIP` — пропустить тест.
- `+IGNORE_EXCEPTION_DETAIL` — не проверять детали исключения (только тип).
- `DONT_ACCEPT_BLANKLINE` — пустые строки в выводе не матчатся (`#` — заглушка пустой строки).

## 12.5. Коды flake8/pylint { #12.5 }

В больших проектах линтеры настраиваются в `pyproject.toml` или `.flake8` через `ignore = ["E501", "F401"]`. Если конфига нет — точечное `# noqa: [код]` в строке.

### Группа F (Pyflakes) — логические аномалии { #12.5-gruppa }

- **F401 — Module imported but unused**: `import os, math, sys, json  # noqa: F401`
- **F841 — Local variable is assigned to but never used**: `unused_hash_buffer = (x * 42) // 3  # noqa: F841`
- **F811 — Redefinition of unused name** — повторное определение, которое перекрывает предыдущее.
- **F541 — f-string without placeholders** — `f"hello"` без `{}`.
- **F821 — Undefined name** — использование неопределённой переменной.
- **F632 — use of `is` to compare str/bytes/int literals** — `s is "hello"` вместо `==`.

### Группа E и W (pycodestyle / PEP 8) { #12.5-gruppa-ew }

- **E501 — Line too long (>79 characters)** — самое знаменитое правило PEP 8.
- **E203 — Whitespace before `:`**: `a[x : y]  # вместо a[x:y]`
- **E302, E303, E305** — правила пустых строк:
  - E302: между импортами и функцией должно быть 2 пустые строки.
  - E303: срабатывает на 3+ пустых строках подряд (допустимо максимум 2).
  - E305: между концом функции и `if __name__` — 2 пустые строки.
- **E711, E712** — сравнение с `None` через `==` (надо `is None`), с `True`/`False` через `==` (надо `if x:`).
- **E722** — голый `except:` без указания типа исключения.
- **W291, W293** — trailing whitespace и whitespace на пустых строках.

### Группа PL (Pylint) — архитектурные грехи { #12.5-gruppa-pl }

- **`pylint: disable=broad-except` (W0703)** — перехват всех ошибок через `except Exception:`.
- **`pylint: disable=too-many-arguments` (R0913)** — слишком много аргументов (>5).
- **`pylint: disable=missing-module-docstring`/`-class-docstring`/`-function-docstring` (C0114/C0115/C0116)** — нет docstring (старый код C0111 был разделён на C0114/C0115/C0116 в pylint 2.6, август 2020).
- **`pylint: disable=eval-used` (W0122)** — использование `eval`.
- **`pylint: disable=too-few-public-methods` (R0903)** — слишком мало публичных методов.
- **`pylint: disable=import-outside-toplevel` (C0415)** — импорт вне верхнего уровня.

Выше — только ходовые коды, а не реестры. Полные списки: у flake8 — сводные таблицы кодов Pyflakes и pycodestyle, у pylint — сотни сообщений с поиском по группам, у ruff (см. 12.7) — все коды плагинов плюс собственные. Где искать:

- [коды flake8/Pyflakes/pycodestyle](https://flake8.pycqa.org/en/latest/user/error-codes.html)
- [коды pycodestyle (E/W)](https://pycodestyle.readthedocs.io/en/latest/intro.html)
- [все сообщения pylint](https://pylint.readthedocs.io/en/stable/user_guide/messages/messages_overview.html)
- [все правила ruff](https://docs.astral.sh/ruff/rules/)

## 12.6. `pyproject.toml` { #12.6 }

Современный способ настроить линтер — через `pyproject.toml` (PEP 518):

```toml
[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B"]
ignore = ["E501", "F401", "E203"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]   # разрешить неиспользуемые импорты в __init__
"tests/*" = ["S101"]       # разрешить assert в тестах

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Аналогично для flake8 (нативно `pyproject.toml` он НЕ читает — нужен плагин `flake8-pyproject` или отдельный `.flake8`/`setup.cfg`):

```ini
[flake8]
max-line-length = 120
extend-ignore = E501, F401, E203
exclude = .git, __pycache__, build, dist
per-file-ignores =
    __init__.py:F401
    tests/*:S101
```

В больших системах — основной способ. `# noqa` оставляют только для точечных исключений.

## 12.7. `ruff` — замена стека flake8 + isort + pyupgrade { #12.7 }

`ruff` — линтер на Rust, который к 2025 фактически вытеснил классическую связку flake8 + isort + pyupgrade: одна утилита, один конфиг, один кеш, на 1–2 порядка быстрее (на репозитории в 100K строк — единицы секунд вместо минут у pylint). Бонусом `ruff format` — drop-in замена black с тем же стилем вывода.

Принцип ruff: **проверки сторонних плагинов переизобретены внутри**, как правила с собственными префиксами. Старый стек из 4–5 инструментов сворачивается в одну таблицу:

| Правила ruff | Аналог из старого стека | Что покрывает |
|---|---|---|
| `E`, `W` | pycodestyle | стиль PEP 8: E501, W291, E711 |
| `F` | Pyflakes | логические аномалии: F401, F841, F811 |
| `I` | isort | сортировка импортов |
| `UP` | pyupgrade | синтаксис под целевую версию: UP007 → `X \| Y` |
| `B` | flake8-bugbear | реальные грабли: B006 mutable default |
| `N` | pep8-naming | соглашения об именах |
| `C4` | flake8-comprehensions | избыточные comprehensions |
| `SIM` | flake8-simplify | упрощаемые конструкции |
| `S` | flake8-bandit | security: S101 `assert`, S301 `pickle` |
| `D` | pydocstyle | docstring |
| `PL` | pylint | часть архитектурных правил (PLR, PLC, PLW) |
| `RUF` | — | собственные правила, в т.ч. RUF100 — мёртвый `# noqa` |

```bash
pip install ruff

ruff check .                  # линт (аналог flake8)
ruff check --fix .            # линт + автопочинка безопасных нарушений
ruff check --fix --unsafe-fixes .   # + агрессивные фиксы (перечитать diff!)
ruff check --statistics .     # сводка нарушений по кодам
ruff format .                 # форматирование (аналог black)
ruff format --check .         # CI-режим: только проверить
```

Конфигурация — в `pyproject.toml` (полный пример в 12.6). С версии 0.2.0 правила живут под `[tool.ruff.lint]` — плоские ключи `[tool.ruff]` устарели, но ruff молча их принимает, что регулярно путает в старых репозиториях:

```toml
[tool.ruff]                       # общие настройки
line-length = 120
target-version = "py312"          # какие UP-правила включать

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
extend-select = ["C4", "RUF"]     # добавить к select, не перечисляя заново
ignore = ["E501"]                 # длину строк контролирует форматтер

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]
```

`target-version = "py312"` — ключевой параметр для группы `UP`: при `py<3.10` может советовать `from __future__ import annotations` (UP037), при `py312+` — разрешает PEP 695 `type X = ...` и убирает ставшие ненужными `from __future__ import annotations`. Без этой настройки `UP` работает по консервативному минимуму.

**Что мигрирует болезненно:**

- **Кастомные flake8-плагины** — если в проекте свой плагин, ruff его не запустит (расширение через плагины ruff на Rust не появилось). Кастомные проверки выносят в отдельный скрипт или в pylint.
- **`# noqa` без кодов** — под ruff голый `# noqa` глушит все проверки строки; при включённом RUF100 он же станет источником предупреждений. См. 12.8.
- **Правила «в превью»** — свежие правила ruff лежат за флагом `[tool.ruff.lint] preview = true` и меняются между минорными версиями; в проде лучше не включать.

→ **см. также:** 12.6 — `pyproject.toml` для flake8 и ruff рядом; 12.8 — гранулярные подавления под ruff; 12.10 — ruff в pre-commit.

## 12.8. Гранулярные подавления: `# noqa: E501` vs `# noqa` vs `# ruff: noqa: E501` { #12.8 }

В 12.3 показан базовый `# noqa`. На практике у директивы три уровня действия и три разных синтаксиса под flake8/ruff/pylint — и разница между ними регулярно роняет CI.

**Уровень строки** — всё, что без префикса инструмента, действует на строку, где стоит:

```python
import sys  # noqa: F401         — только F401, остальное на строке проверяется
import os  # noqa                — глушит ВСЁ на строке (и ruff, и flake8)
x = ""  # type: ignore           — это для mypy, линтеры её не читают
```

**Уровень файла** — требует явного префикса инструмента. Голый `# noqa` в начале файла файловое отключение **не** даёт (для flake8/ruff это просто комментарий на первой строке):

```python
# ruff: noqa                    — отключить ruff во всём файле
# ruff: noqa: E501              — отключить только E501 во всём файле
# flake8: noqa                  — отключить flake8 во всём файле
# flake8: noqa: E501            — только E501 для всего файла (flake8 >= 4.0)
# pylint: skip-file             — отключить pylint во всём файле
```

`# ruff: noqa: E501` — синтаксис именно ruff: он действует **только** на ruff и не глушит flake8/pylint/mypy. Если файл проверяется двумя линтерами, для ruff-исключений используют его, чтобы не отключать правило и у остальных инструментов.

Сводная таблица:

| Директива | Уровень | flake8 | ruff | pylint |
|---|---|---|---|---|
| `# noqa` | строка | глушит всё | глушит всё | — |
| `# noqa: E501` | строка | глушит E501 | глушит E501 | — |
| `# ruff: noqa` | файл | — | глушит всё | — |
| `# ruff: noqa: E501` | файл | — | глушит E501 | — |
| `# flake8: noqa` | файл | глушит всё | — | — |
| `# flake8: noqa: E501` | файл (≥ 4.0) | глушит E501 | — | — |
| `# pylint: disable=X` | строка/блок | — | — | глушит X |
| `# pylint: skip-file` | файл | — | — | глушит всё |

**RUF100 — линтер самих `# noqa`.** Мёртвые директивы — главный мусор старых репозиториев: правило починили, а `# noqa` остался, и под ним уже спокойно живёт новое нарушение. RUF100 помечает `# noqa`, который ничего не глушит:

```python
import json  # noqa: F401   ← RUF100: F401 не срабатывает, импорт используется

# ruff check --extend-select RUF100 --fix .
# — за один проход удалит все мёртвые # noqa
```

⚠️ Два нюанса RUF100. Во-первых, он считает мёртвым и `# noqa: CODE`, где `CODE` неизвестен ruff (коды сторонних плагинов, которых нет в ruff) — такие коды надо перечислить в `external`:

```toml
[tool.ruff.lint]
external = ["V101"]   # коды внешнего плагина, RUF100 их не трогает
```

Во-вторых, RUF100 не видит, что `# noqa` глушит pylint-правило — ruff о pylint-директивах ничего не знает.

Практическое правило: в файле — `# ruff: noqa: CODE` с точным кодом, на строке — `# noqa: CODE` с точным кодом, голый `# noqa` — только как временная мера с комментарием, почему.

→ **см. также:** 12.3 — базовый `# noqa`; 12.6 — per-file-ignores; 12.9 — подавления для тайпчекеров (там своя система кодов).

## 12.9. Типовые игноры: `# type: ignore` vs `# type: ignore[code]` vs `# pyright: ignore` { #12.9 }

У тайпчекеров — собственная система подавлений, не связанная с `# noqa`. И у каждого чекера свой синтаксис со своими ловушками.

**mypy: голый vs точный игнор.**

```python
result = may_return_none()  # type: ignore          — глушит ВСЕ ошибки mypy на строке
result = may_return_none()  # type: ignore[union-attr]  — только ошибку с этим кодом
```

Код ошибки виден в выводе mypy в квадратных скобках (`--show-error-codes`; с версии 0.990 включён по умолчанию):

```bash
error: Item "None" of "str | None" has no attribute "upper"  [union-attr]
```

Список часто встречающихся кодов: `attr-defined` (атрибут неизвестен), `arg-type` / `assignment` (несовпадение типов), `union-attr` (доступ по Optional), `no-untyped-def` (нет аннотаций), `import-untyped` (пакет без типов).

⚠️ Голый `# type: ignore` — самый опасный вид подавления: он глушит не только ту ошибку, что вы видели, но и **будущие** — после рефакторинга строка может сломаться, а mypy промолчит. Лечение — `warn_unused_ignores`: точные `# type: ignore[code]` при изменении кода перестают срабатывать и подсвечиваются как неиспользуемые, голые — никогда:

```toml
[tool.mypy]
warn_unused_ignores = true
# точечно, без комментариев в коде:
disable_error_code = ["no-untyped-def"]

[[tool.mypy.overrides]]        # для модулей без аннотаций целиком
module = ["legacy.*"]
ignore_errors = true
```

**pyright — своя система кодов.** Директива pyright: `# pyright: ignore[код]`, коды длинные и говорящие: `reportAttributeAccessIssue`, `reportArgumentType`, `reportGeneralTypeIssues`, `reportOptionalMemberAccess`.

```python
result = may_return_none()  # pyright: ignore[reportOptionalMemberAccess]
```

Тонкое место — совместимость двух чекеров в одном проекте:

- mypy **не понимает** `# pyright: ignore` — для него это просто хвост комментария, ошибка mypy останется.
- pyright **понимает** `# type: ignore`, но **список кодов в квадратных скобках игнорирует**: `# type: ignore[union-attr]` для pyright эквивалентен голому игнору — подавятся все ошибки строки, не только `union-attr`.
- Если код проверяется обоими, на одной строке собирается зоопарк: `x  # type: ignore[union-attr]  # pyright: ignore[reportOptionalMemberAccess]`. Это некрасиво, но это честная цена двойного статического анализа — или аргумент выбрать один чекер.
- У pyright есть опция `enableTypeIgnoreComments` для управления почтением `# type: ignore`; для более гранулярных подавлений pyright предпочитает собственный синтаксис `# pyright: ignore[reportOptionalMemberAccess]`.

**ty (Astral, 2025).** Молодой тайпчекер от авторов ruff идёт тем же путём: `# ty: ignore[unresolved-attribute]` — подавление по имени правила; для совместимости понимает и `# type: ignore`. Экосистема кодов ещё нестабильна — в прод включать с осторожностью.

Сводная таблица:

| Директива | mypy | pyright | ty |
|---|---|---|---|
| `# type: ignore` | глушит всё | глушит всё | глушит всё |
| `# type: ignore[code]` | глушит только код | код игнорирует, глушит всё | частичная поддержка |
| `# pyright: ignore[код]` | не понимает | глушит только код | не понимает |
| `# ty: ignore[rule]` | не понимает | не понимает | глушит только правило |

Практическое правило: всегда игнорить **с кодом** — это самодокументация и страховка от молчаливой порчи при рефакторинге; голый игнор — последний ресурс, для строк, где ошибка чекера заведомо ложная и код будет переписан.

→ **см. также:** 12.2 — `# type: int` и история комментариев-типов; Часть VII (7.10) — аннотации как данные; «Бенчмарки» п. 3 — cast() vs type: ignore.

## 12.10. pre-commit: ruff + mypy в одном конвейере { #12.10 }

[pre-commit](https://pre-commit.com) — менеджер git-хуков: один файл `.pre-commit-config.yaml` описывает, что гонять перед каждым коммитом, у каждого хука — изолированное окружение и зафиксированная версия. Стандартный набор питон-проекта: ruff (линт + формат) и mypy.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4                # фиксируйте версию — хук живёт в своём окружении
    hooks:
      - id: ruff               # линт + автопочинка
        args: [--fix]
      - id: ruff-format        # форматирование (после линта)

  - repo: local                # mypy — локальным хуком, см. ниже
    hooks:
      - id: mypy
        name: mypy
        entry: .venv/bin/mypy
        language: system
        types: [python]
        files: ^(src|tests)/
```

Три правила, которые экономят часы отладки хуков:

**1. Порядок: линт → формат → типы.** Сначала `ruff --fix` правит содержимое, потом `ruff-format` выравнивает, и только затем mypy смотрит на финальный текст. В обратном порядке mypy будет ловить ошибки в строках, которые форматтер через секунду переставит.

**2. mypy — локальным хуком (`language: system`).** Официальный `mirrors-mypy` ставит mypy в изолированное окружение, где **нет** зависимостей вашего проекта — и mypy сыплет `import-untyped` на всё подряд. Локальный хук с `entry: .venv/bin/mypy` использует реальное окружение проекта со всеми stub-пакетами.

**3. Хуки ruff читают тот же `pyproject.toml`.** Отдельного конфига для pre-commit не нужно: `ruff-pre-commit` запускает ruff из корня репозитория, и `select`/`per-file-ignores` из 12.6–12.7 работают как обычно.

```bash
pip install pre-commit
pre-commit install            # повесить хуки на git commit
pre-commit run --all-files    # прогнать всё вручную (первый прогон долгий — качает окружения)
```

⚠️ `pre-commit` гоняет хуки **только на изменённых файлах** (в стадии `commit`). Разовый прогон по всему репо — `pre-commit run --all-files`; чтобы хуки не «протухали», его же ставят в CI:

```yaml
# .github/workflows/lint.yml — фрагмент
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
- run: pip install pre-commit && pre-commit run --all-files
```

Альтернатива без своего CI-шага — [pre-commit.ci](https://pre-commit.ci): сервис сам гоняет хуки на PR и сам обновляет `rev` хуков автоматически.

Что остаётся за кадром: pre-commit защищает **коммиты**, но не историю — хук можно обойти `git commit --no-verify`. Для гарантий CI-прогон обязателен: хуки ускоряют обратную связь, CI — единственный источник истины.

→ **см. также:** 12.7 — конфиг ruff; 12.9 — коды mypy; 12.6 — общий `pyproject.toml`.

---

### Бенчмарки к Части XII { #12.11-benchmarki }

**1. `ruff` vs `flake8` vs `pylint` — скорость проверки.**
```bash
# На репозитории ~500 .py файлов, ~100K строк:
# flake8:    ≈ 8.5 с
# pylint:    ≈ 45.0 с
# ruff:      ≈ 0.06 с  (140× быстрее flake8, 750× быстрее pylint)
# ruff --fix:≈ 0.12 с (с применением автофиксов)
```
`ruff` написан на Rust, парсит собственным парсером (`ruff_python_parser`; `rustpython-parser` использовался только в ранних версиях), без Python-импортов.
На CI для проекта среднего размера экономит **минуты на каждом пуше**.
Pylint медленнее, но ловит больше семантических проблем (напр. неиспользуемые
импорты в условных ветках, недостижимый код).

**2. `mypy --strict` vs `mypy` (по умолчанию) — цена строгости.**
```bash
# На ~500 файлов:
# mypy:                  ≈ 12 с
# mypy --strict:         ≈ 14 с   (+17%)
```
`--strict` добавляет ~15–20% к времени проверки, но ловит на ~30% больше
проблем на этапе разработки (а не в рантайме). На CI — обязательно.

**3. `# type: ignore` vs `# pyright: ignore` vs `cast()`.**
```python
from typing import cast
# 1. type: ignore — подавляет все ошибки на строке (нечётко)
x = json.loads(s)  # type: ignore
# 2. cast() — явно сообщаем тип, mypy проверяет остальное
x = cast(dict, json.loads(s))
# 3. pyright: ignore — специфично для pyright, с причиной
x = json.loads(s)  # pyright: ignore[reportUnknownArgumentType]
```
Производительности не касается — это про **точность статического анализа**.
Правило: `cast()` для явных сужений типа, `# type: ignore[code]` для
подавления конкретной ошибки, голый `# type: ignore` — последний ресурс.

**4. doctest — стоимость запуска.**
```bash
# На модуле со 100 doctest-тестами:
python -m doctest -v module.py                    # ≈ 0.3 с
python -m pytest --doctest-modules module.py      # ≈ 0.5 с (накладные pytest)
# Сравнение с обычным unit-тестом:
python -m pytest tests/   # 100 тестов            # ≈ 1.2 с
```
doctest **быстрее** unit-тестов (~4× на тест: 0.3 с / 100 = 0.003 с против 1.2 с / 100 = 0.012 с) — нет фикстур, setup/teardown.
Но он **не заменяет** полноценные тесты: нет параметризации, нет `setUp`/`tearDown`,
сложно тестировать исключения и побочные эффекты. Идеален для проверки
**примеров в docstring** — и только.

**5. `# noqa` vs `# pylint: disable` vs `per-file-ignores` — что выбирать.**
```python
# noqa — самый дешёвый: flake8/ruff читают комментарии построчно, O(1)
# pylint: disable — дороже: pylint строит AST и привязывает директивы к узлам
# per-file-ignores в pyproject.toml — самый быстрый: конфиг читается один раз
```
Производительность — не главное. Главное — **поддерживаемость**:

- `# noqa` — для точечных исключений (1 строка в 1 месте).
- `per-file-ignores` — для категорических исключений (напр. `tests/*: S101` разрешает `assert` во всех тестах).
- `# pylint: disable` — для pylint-специфичных правил, которых нет в ruff.

