# Часть XII. Линтеры и директивы в комментариях

## 12.1. `# -*- coding: ... -*-` (PEP 263) { #12.1 }

> **→ см. также:** Часть IX (9.1–9.6) — полный разбор работы с кодировками исходных файлов и собственными кодеками.

Жёсткая директива для парсера CPython — указывает кодировку исходного файла. Подробно в Части IX.

```python
# -*- coding: utf-8 -*-
# coding: cp1251
# coding=iso-8859-1
```

## 12.2. `# type: int` (PEP 484) { #12.2 }

Type comments — до того как в Python появились полноценные аннотации через двоеточие (`x: int = 5`), типы писали в комментариях. CPython до сих пор парсит их в специальный флаг AST `type_ignores`:

```python
x = 10  # type: int

def f(x):  # type: (int) -> str
    return str(x)

# Для коллекций
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
- `+NUMBER` — численные сравнения с допуском.

## 12.5. Коды flake8/pylint { #12.5 }

В больших проектах линтеры настраиваются в `pyproject.toml` или `.flake8` через `ignore = ["E501", "F401"]`. Если в учебной системе такого файла нет — точечное `# noqa: [код]` в строке.

### Группа F (Pyflakes) — логические аномалии { #12.5-gruppa }

- **F401 — Module imported but unused**:
  ```python
  import os, math, sys, json  # noqa: F401
  ```
- **F841 — Local variable is assigned to but never used**:
  ```python
  unused_hash_buffer = (x * 42) // 3  # noqa: F841
  ```
- **F811 — Redefinition of unused name** — повторное определение, которое перекрывает предыдущее.
- **F541 — f-string without placeholders** — `f"hello"` без `{}`.
- **F821 — Undefined name** — использование неопределённой переменной.
- **F811 — Redefinition of unused name**.

### Группа E и W (pycodestyle / PEP 8) { #12.5-gruppa }

- **E501 — Line too long (>79 characters)** — самое знаменитое правило PEP 8.
- **E203 — Whitespace before `:`**:
  ```python
  a[x : y]   # вместо a[x:y]
  ```
- **E302, E303, E305** — правила пустых строк:
  - E302: между импортами и функцией должно быть 2 пустые строки.
  - E303: внутри функции не больше 1 пустой строки подряд.
  - E305: между концом функции и `if __name__` — 2 пустые строки.
- **E711, E712** — сравнение с `None` через `==` (надо `is None`), с `True`/`False` через `==` (надо `if x:`).
- **E722** — голый `except:` без указания типа исключения.
- **W291, W293** — trailing whitespace и whitespace на пустых строках.

### Группа PL (Pylint) — архитектурные грехи { #12.5-gruppa }

- **`pylint: disable=broad-except` (W0703)** — перехват всех ошибок через `except Exception:`.
- **`pylint: disable=too-many-arguments` (R0913)** — слишком много аргументов (>5).
- **`pylint: disable=missing-docstring` (C0111)** — нет docstring.
- **`pylint: disable=eval-used` (W0122)** — использование `eval`.
- **`pylint: disable=too-few-public-methods` (R0903)** — слишком мало публичных методов.
- **`pylint: disable=import-outside-toplevel` (C0415)** — импорт вне верхнего уровня.

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

Аналогично для flake8 (через `[tool.flake8]` или отдельный `.flake8`):

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

---

### Бенчмарки к Части XII { #12.6-benchmarki }

**1. `ruff` vs `flake8` vs `pylint` — скорость проверки.**
```bash
# На репозитории ~500 .py файлов, ~100K строк:
# flake8:    ≈ 8.5 с
# pylint:    ≈ 45.0 с
# ruff:      ≈ 0.06 с  (140× быстрее flake8, 750× быстрее pylint)
# ruff --fix:≈ 0.12 с (с применением автофиксов)
```
`ruff` написан на Rust, парсит через `rustpython-parser`, без Python-импортов.
На CI для проекта среднего размера экономит **минуты на каждом пуше**.
Pylint медленнее, но ловит больше семантических проблем (напр. неиспользуемые
импорты в условных ветках, недостижимый код).

**2. `mypy --strict` vs `mypy` (по умолчанию) — цена строгости.**
```bash
# На ~500 файлов:
# mypy:                  ≈ 12 с
# mypy --strict:         ≈ 14 с   (+17%)
# mypy --strict --fast:  ≈ 13 с
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
doctest **быстрее** unit-тестов (~3× на тест) — нет фикстур, setup/teardown.
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
- `per-file-ignores` — для категорических исключений (напр. `tests/*: S101`
  разрешает `assert` во всех тестах).
- `# pylint: disable` — для pylint-специфичных правил, которых нет в ruff.

