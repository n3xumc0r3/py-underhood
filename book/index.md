# Python под капотом

> **От синтаксических трюков до internals CPython.**
> Книга о редко используемых, скрытых и продвинутых возможностях Python и интерпретатора CPython — от базовых трюков до глубоких internals. В приложениях — системы проверки кода и взаимодействие с ними.

**Структура по сложности:**

[Часть I](01-basics.md) (базовые трюки) → [Часть II](02-context-managers.md) (контекстные менеджеры) → [Часть III](03-generators.md)–[Часть IV](04-async.md) (генераторы, асинхронность) → [Часть V](05-classes.md)–[Часть VI](06-descriptors.md) (классы, дескрипторы) → [Часть VII](07-metaprogramming.md)–[Часть VIII](08-cpython-internals.md) (метапрограммирование, internals CPython) → [Часть IX](09-encodings.md)–[Часть XII](12-linters.md) (кодировки, окружение, stdlib, линтеры) → [Приложение A](appendix-a-plagiarism.md) (системы обнаружения плагиата), [Приложение B](appendix-b-code-checkers.md) (взаимодействие с ними), [Приложение C](appendix-c-code-golf.md) (code golf), [Приложение D](appendix-d-references.md) (справочная литература).

---

## Содержание

### Часть I. Базовые скрытые особенности языка

[Открыть часть →](01-basics.md)

Подразделы: `1.1` числовые литералы · `1.2` строковые префиксы · `1.3` неявное склеивание · `1.4` f-строки · `1.5` `slice` · `1.6` эллипсис · `1.7` `else` у циклов · `1.8` тернарный · `1.9` моржовый `:=` · `1.10` `match/case` · `1.11` цепочки сравнений · `1.12` распаковка · `1.13` `as` · `1.14` `iter(callable, sentinel)` · `1.15` `assert` и `-O` · `1.16` `breakpoint()` · `1.17` `_` · `1.18` slice assignment · `1.19` списочные без приравнивания · `1.20` PEP 8 нарушается · `1.21` `try/except/else/finally` · `1.22` exception chaining · `1.23` скрытые параметры builtins · `1.24` `__future__` · `1.25` пасхалки.

### Часть II. Контекстные менеджеры

[Открыть часть →](02-context-managers.md)

Подразделы: `2.1` `with` internals · `2.2` свой менеджер через класс · `2.3` `@contextmanager` · `2.4` `suppress`/`ExitStack` · `2.5` несколько менеджеров · `2.6` подавление ошибок · `2.7` `redirect_stdout` · `2.8` `closing`/`aclosing`.

### Часть III. Генераторы и итераторы

[Открыть часть →](03-generators.md)

Подразделы: `3.1` `yield`/`next`/`StopIteration` · `3.2` genexpr vs listcomp · `3.3` `yield from` · `3.4` `send()`/`throw()`/`close()` · `3.5` бесконечные генераторы · `3.6` `itertools` рецепты · `3.7` экономия памяти · `3.8` `pairwise`/`batched` · `3.9` `collections`.

### Часть IV. Асинхронность

[Открыть часть →](04-async.md)

Подразделы: `4.1` event loop · `4.2` `async def`/`await` · `4.3` `asyncio.run` · `4.4` `gather` · `4.5` `create_task` · `4.6` `wait` · `4.7` `Queue`/`Lock`/`Semaphore` · `4.8` async generators · `4.9` async context managers · `4.10` конкурентность vs параллелизм · `4.11` threads vs asyncio vs multiprocessing · `4.12` `as_completed` · `4.13` `TaskGroup` · `4.14` `timeout`/`shield` · `4.15` `CancelledError` · `4.16` advanced.

### Часть V. Классы и интерфейсы

[Открыть часть →](05-classes.md)

Подразделы: `5.1` `dataclasses` · `5.2` `abc.ABC` · `5.3` `Protocol` · `5.4` MRO/C3 · `5.5` mixins · `5.6` `__init_subclass__` · `5.7` `super()` · `5.8` `__slots__` · `5.9` `classmethod` vs `staticmethod` · `5.10` `enum` · `5.11` dataclasses advanced · `5.12` typing advanced · `5.13` dataclasses advanced2 · `5.14` typing для async · `5.15` `TYPE_CHECKING` · `5.16` `ExceptionGroup` · `5.17` dunder-методы.

### Часть VI. Дескрипторы и property

[Открыть часть →](06-descriptors.md)

Подразделы: `6.1` `__get__`/`__set__`/`__delete__` · `6.2` data vs non-data · `6.3` `__set_name__` · `6.4` `@property` под капотом · `6.5` `__getattr__` vs `__getattribute__` vs `__setattr__`.

### Часть VII. Метапрограммирование

[Открыть часть →](07-metaprogramming.md)

Подразделы: `7.1` аннотации как данные · `7.2` `setattr`/`getattr`/`delattr` · `7.3` декораторы · `7.4` `functools.wraps` · `7.5` `type()` · `7.6` `types.FunctionType`/`CodeType` · `7.7` `compile`/`exec`/`eval` · `7.8` `locals()`/`globals()` · `7.9` `sys.modules` · `7.10` `builtins` · `7.11` `inspect` · `7.12` `importlib` · `7.13` `ast` · `7.14` `dir()`.

### Часть VIII. Внутренности CPython

[Открыть часть →](08-cpython-internals.md)

Подразделы: `8.1` интернация строк · `8.2` кэш малых чисел · `8.3` замыкания · `8.4` `sys._getframe` · `8.5` `sys.getrefcount` · `8.6` GC через `gc` · `8.7` `__code__` · `8.8` смена `__class__` · `8.9` `dis` · `8.10` recursion limit · `8.11` `contextvars` · `8.12` `pathlib` · `8.13` `types` · `8.14` `weakref` · `8.15` `sys.unraisablehook`.

### Часть IX. Кодировки и кодеки

[Открыть часть →](09-encodings.md)

Подразделы: `9.1` PEP 263 · `9.2` `rot_13` и `SyntaxError` · `9.3` кодировки для исходника · `9.4` проверка всех кодировок · `9.5` свой кодек · `9.6` `search_function`.

### Часть X. Интроспекция окружения

[Открыть часть →](10-introspection.md)

Подразделы: `10.1` `sys.flags` · `10.2` `sys._xoptions` · `10.3` `os.environ`/`PYTHON*` · `10.4` `sys.implementation`/`platform` · `10.5` `resource.getrlimit` · `10.6` `/proc/self/` · `10.7` audit hooks · `10.8` faulthandler · `10.9` универсальный комбайн.

### Часть XI. Полезные модули stdlib

[Открыть часть →](11-stdlib.md)

Подразделы: `11.1`–`11.31` — `functools` (`lru_cache`/`partial`/`reduce`/`singledispatch`/`cached_property`/`total_ordering`), `weakref`, `copy`, `warnings`, `__all__`, `pickle`, `tracemalloc`, `operator`, `queue`, `reprlib`, `os.scandir`, `logging`, `signal`/`atexit`, `datetime`, `bisect`/`heapq`, `csv`/`json`/`urllib.parse`, `mmap`, `shutil`/`tempfile`, `decimal`/`fractions`, `re`, `unicodedata`, `struct`/`memoryview`, `hashlib`/`hmac`/`secrets`, `math`/`statistics`, `random`, `argparse`/`configparser`/`subprocess`, `timeit`/`bdb`/`profile`/`cProfile`/`code`, `venv`/`pip`/`site`.

### Часть XII. Линтеры и директивы в комментариях

[Открыть часть →](12-linters.md)

Подразделы: `12.1` `# -*- coding: ... -*-` · `12.2` `# type: int` · `12.3` `# noqa` · `12.4` `# doctest: +ELLIPSIS` · `12.5` коды flake8/pylint · `12.6` `pyproject.toml`.

### Приложение A. Системы обнаружения плагиата

[Открыть приложение →](appendix-a-plagiarism.md)

Подразделы: `A.1` Winnowing · `A.2` MOSS/JPlag/Dolos/Codequiry · `A.3` метрики Хальстеда · `A.4` цикломатическая сложность · `A.5` AST-нормализация · `A.6` стилометрия · `A.7` динамический анализ · `A.8` constant folding.

### Приложение B. Взаимодействие с системами проверки кода

[Открыть приложение →](appendix-b-code-checkers.md)

Подразделы: `B.1` косметические приёмы · `B.2` архитектурные · `B.3` перехват через фреймы/ctypes · `B.4` интроспекция окружения · `B.5` песочницы и `__subclasses__()`.

### Приложение C. Code golf — Python на минималках

[Открыть приложение →](appendix-c-code-golf.md)

Подразделы: `C.1`–`C.22` — базовые приёмы сжатия, `bool` как `int`, тернарный vs индексация, unpack в `print`, срезы, short-circuit, `walrus`, `__import__`, битовые операции, `lambda`, `__builtins__`, строки vs регулярки, большие числа, `exit()` vs `sys.exit()`, антипаттерны, числовые константы, продвинутые приёмы, шпаргалка, канонические задачи, разбор реального онелинера, ссылки.

### Приложение D. Где почитать

[Открыть приложение →](appendix-d-references.md)

Библиография: PEP-ы, книги по CPython internals (Anthony Shaw, Luciano Ramalho, Brett Slatkin, David Beazley), исходники CPython, статьи по системам обнаружения плагиата (Winnowing, MOSS, JPlag, Dolos).

---

## Лицензия

- **Проза** (тексты в `book/`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **Код в сниппетах**: [MIT](https://github.com/n3xumc0r3/py-underhood/blob/main/CODE_LICENSE)

Подробнее — в [LICENSE](https://github.com/n3xumc0r3/py-underhood/blob/main/LICENSE) и [CONTRIBUTING.md](https://github.com/n3xumc0r3/py-underhood/blob/main/CONTRIBUTING.md).

## Контрибьют

PRs приветствуются — особенно bug fixes, опечатки, фактические ошибки. Большие новые секции — сначала откройте issue.
