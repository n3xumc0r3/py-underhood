# Python под капотом

> **От синтаксических трюков до internals CPython.**
> Книга о редко используемых, скрытых и продвинутых возможностях Python и интерпретатора CPython — от базовых трюков до глубоких internals. В приложениях — системы проверки кода и взаимодействие с ними.

Эта книга — систематический разбор редко используемых, скрытых и продвинутых возможностей Python и интерпретатора CPython. От числовых литералов и f-строк до internals CPython, обхода песочниц и code golf. Материал организован по нарастающей сложности: первые главы доступны любому разработчику на Python, последние требуют готовности разбираться в байт-коде, фреймовых структурах и устройстве `dict` под капотом. Каждая тема снабжена работающими примерами, пояснениями «почему так» и ссылками на PEP-ы и исходники CPython.

## Для кого

Для разработчиков, которые уже пишут на Python и хотят понимать, что происходит под капотом. Не учебник для новичков — предполагается, что вы знаете базовый синтаксис, разбираетесь в классах и хотя бы раз запускали `asyncio`. Книга будет полезна тем, кто готовится к сложным собеседованиям, пишет библиотеки и фреймворки, занимается оптимизацией или просто хочет выйти за рамки «написал код — заработало». Часть VIII (internals CPython) и приложения A–B полезны преподавателям, ревьюерам и авторам проверяющих систем.

## Объём

~20 800 строк, ~1.1 МБ исходника. 15 частей и 4 приложения, 191 раздел с собственным якорем `#N.M`. Все примеры проверены на CPython 3.12+. Книга в активной доработке — возможны опечатки и неточности, если нашли — открывайте issue или PR. Сайт подключён к IndexNow для мгновенной индексации изменений в Bing и Yandex.

## Лицензия

Текст — [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), код в примерах — [MIT](https://github.com/n3xumc0r3/py-underhood/blob/main/CODE_LICENSE). Бесплатно для чтения и некоммерческого использования. Внести правку можно через PR — [создайте его прямо на GitHub](https://github.com/n3xumc0r3/py-underhood/pulls), открыв любой файл в `book/` и нажав «Edit».

## Структура по сложности

[Часть I](01-basics.md) — базовые трюки

[Часть II](02-context-managers.md) — контекстные менеджеры

[Часть III](03-generators.md) — генераторы, итераторы

[Часть IV](04-async.md) — асинхронность

[Часть V](05-classes.md) — классы, дескрипторы

[Часть VI](06-descriptors.md) — дескрипторы, property

[Часть VII](07-metaprogramming.md) — метапрограммирование

[Часть VIII](08-cpython-internals.md) — internals CPython

[Часть IX](09-encodings.md) — кодировки, кодеки

[Часть X](10-introspection.md) — интроспекция окружения

[Часть XI](11-stdlib.md) — полезные модули stdlib

[Часть XII](12-linters.md) — линтеры, директивы

[Часть XIII](13-bytecode-vm.md) — от .py к байт-коду: компиляция и виртуальная машина

[Часть XIV](14-implementations.md) — не только CPython: реализации и REPL-ы

[Часть XV](15-testing.md) — тестирование: assert, unittest, mock, doctest, pytest, coverage, sys.monitoring

[Приложение A](appendix-a-plagiarism.md) — системы обнаружения плагиата

[Приложение B](appendix-b-code-checkers.md) — взаимодействие с системами проверки кода

[Приложение C](appendix-c-code-golf.md) — code golf

[Приложение D](appendix-d-references.md) — справочная литература

---

## Содержание

### Часть I. Базовые скрытые особенности языка

[Открыть часть →](01-basics.md)

- [1.1. Числовые литералы](01-basics.md#1.1)
- [1.2. Строковые префиксы](01-basics.md#1.2)
- [1.3. Неявное склеивание строковых литералов](01-basics.md#1.3)
- [1.4. f-строки](01-basics.md#1.4)
- [1.5. `slice` как полноценный объект](01-basics.md#1.5)
- [1.6. Эллипсис `...`](01-basics.md#1.6)
- [1.7. `else` у циклов](01-basics.md#1.7)
- [1.8. Тернарный оператор](01-basics.md#1.8)
- [1.9. Моржовый оператор `:=`](01-basics.md#1.9)
- [1.10. `match/case`](01-basics.md#1.10)
- [1.11. Цепочки сравнений](01-basics.md#1.11)
- [1.12. Множественное присвоение и распаковка](01-basics.md#1.12)
- [1.13. `as` — все способы применения](01-basics.md#1.13)
- [1.14. `iter(callable, sentinel)`](01-basics.md#1.14)
- [1.15. `assert` и флаг `-O`](01-basics.md#1.15)
- [1.16. `breakpoint()` и `PYTHONBREAKPOINT`](01-basics.md#1.16)
- [1.17. `_` — переменная-«мусорник»](01-basics.md#1.17)
- [1.18. Slice assignment](01-basics.md#1.18)
- [1.19. Списочные выражения без приравнивания](01-basics.md#1.19)
- [1.20. Стиль: trailing comma, PEP 8](01-basics.md#1.20)
- [1.21. `try/except/else/finally`](01-basics.md#1.21)
- [1.22. Exception chaining](01-basics.md#1.22)
- [1.23. Скрытые параметры встроенных функций](01-basics.md#1.23)
- [1.24. `__future__` imports](01-basics.md#1.24)
- [1.25. Пасхалки](01-basics.md#1.25)

### Часть II. Контекстные менеджеры

[Открыть часть →](02-context-managers.md)

- [2.1. `with` — внутренности](02-context-managers.md#2.1)
- [2.2. Свой менеджер через класс](02-context-managers.md#2.2)
- [2.3. `@contextmanager`](02-context-managers.md#2.3)
- [2.4. `contextlib.suppress` и `ExitStack`](02-context-managers.md#2.4)
- [2.5. Несколько менеджеров в одном `with`](02-context-managers.md#2.5)
- [2.6. Подавление ошибок через `__exit__`](02-context-managers.md#2.6)
- [2.7. `redirect_stdout`/`redirect_stderr`](02-context-managers.md#2.7)
- [2.8. `closing` и `aclosing`](02-context-managers.md#2.8)

### Часть III. Генераторы и итераторы

[Открыть часть →](03-generators.md)

- [3.1. `yield`, `next`, `StopIteration`](03-generators.md#3.1)
- [3.2. Generator expressions vs list comprehensions](03-generators.md#3.2)
- [3.3. `yield from` — делегирование](03-generators.md#3.3)
- [3.4. `send()`, `throw()`, `close()`](03-generators.md#3.4)
- [3.5. Бесконечные генераторы](03-generators.md#3.5)
- [3.6. `itertools` — избранные рецепты](03-generators.md#3.6)
- [3.7. Экономия памяти через ленивые вычисления](03-generators.md#3.7)
- [3.8. `pairwise`, `batched` (Python 3.10+/3.12+)](03-generators.md#3.8)
- [3.9. `collections` — Counter, defaultdict, deque, ChainMap, OrderedDict, namedtuple](03-generators.md#3.9)
- [3.10. Мост в асинхронность: async-генераторы глазами Части III](03-generators.md#3.10)

### Часть IV. Асинхронность

[Открыть часть →](04-async.md)

- [4.1. Что такое event loop](04-async.md#4.1)
- [4.2. `async def`, `await`](04-async.md#4.2)
- [4.3. `asyncio.run`](04-async.md#4.3)
- [4.4. `asyncio.gather`](04-async.md#4.4)
- [4.5. `asyncio.create_task`](04-async.md#4.5)
- [4.6. `asyncio.wait`](04-async.md#4.6)
- [4.7. `asyncio.Queue`, `Lock`, `Semaphore`](04-async.md#4.7)
- [4.8. Async generators](04-async.md#4.8)
- [4.9. Async context managers](04-async.md#4.9)
- [4.10. Конкурентность vs параллелизм](04-async.md#4.10)
- [4.11. Threads vs asyncio vs multiprocessing](04-async.md#4.11)
- [4.12. `asyncio.as_completed`](04-async.md#4.12)
- [4.13. `asyncio.TaskGroup` (Python 3.11+)](04-async.md#4.13)
- [4.14. `asyncio.timeout` и `shield`](04-async.md#4.14)
- [4.15. `asyncio.CancelledError`](04-async.md#4.15)
- [4.16. Advanced: `current_task`, `to_thread`, `Runner`, `eager_task_factory`](04-async.md#4.16)

### Часть V. Классы и интерфейсы

[Открыть часть →](05-classes.md)

- [5.1. `dataclasses`](05-classes.md#5.1)
- [5.2. `abc.ABC` и `@abstractmethod`](05-classes.md#5.2)
- [5.3. `Protocol` (PEP 544)](05-classes.md#5.3)
- [5.4. MRO и C3-линеаризация](05-classes.md#5.4)
- [5.5. Mixins и множественное наследование](05-classes.md#5.5)
- [5.6. `__init_subclass__`](05-classes.md#5.6)
- [5.7. `super()` — подробно](05-classes.md#5.7)
- [5.8. `__slots__`](05-classes.md#5.8)
- [5.9. `@classmethod` vs `@staticmethod`](05-classes.md#5.9)
- [5.10. `enum`](05-classes.md#5.10)
- [5.11. dataclasses advanced](05-classes.md#5.11)
- [5.12. typing advanced](05-classes.md#5.12)
- [5.13. dataclasses advanced2](05-classes.md#5.13)
- [5.14. typing для async](05-classes.md#5.14)
- [5.15. `typing.TYPE_CHECKING`](05-classes.md#5.15)
- [5.16. `ExceptionGroup` и `except*`](05-classes.md#5.16)
- [5.17. Dunder-методы](05-classes.md#5.17)

### Часть VI. Дескрипторы и property

[Открыть часть →](06-descriptors.md)

- [6.1. `__get__`/`__set__`/`__delete__`](06-descriptors.md#6.1)
- [6.2. Data vs non-data descriptors](06-descriptors.md#6.2)
- [6.3. `__set_name__`](06-descriptors.md#6.3)
- [6.4. `@property` — что под капотом](06-descriptors.md#6.4)
- [6.5. `__getattr__` vs `__getattribute__` vs `__setattr__`](06-descriptors.md#6.5)
- [6.6. `functools.cached_property` vs `@property` + кэш в `__dict__`](06-descriptors.md#6.6)
- [6.7. `__set_name__` на практике: поле ORM](06-descriptors.md#6.7)
- [6.8. `__init_subclass__` + дескрипторы: декларативная регистрация](06-descriptors.md#6.8)
- [6.9. Функции — тоже дескрипторы](06-descriptors.md#6.9)
- [6.10. Дескрипторы и `__slots__`](06-descriptors.md#6.10)

### Часть VII. Метапрограммирование

[Открыть часть →](07-metaprogramming.md)

- [7.1. Аннотации как данные](07-metaprogramming.md#7.1)
- [7.2. `setattr`/`getattr`/`delattr`](07-metaprogramming.md#7.2)
- [7.3. Декораторы](07-metaprogramming.md#7.3)
- [7.4. `functools.wraps`](07-metaprogramming.md#7.4)
- [7.5. `type()` — динамическое создание классов](07-metaprogramming.md#7.5)
- [7.6. `types.FunctionType` и `CodeType`](07-metaprogramming.md#7.6)
- [7.7. `compile`/`exec`/`eval`](07-metaprogramming.md#7.7)
- [7.8. `locals()` и `globals()`](07-metaprogramming.md#7.8)
- [7.9. `sys.modules` и `__import__`](07-metaprogramming.md#7.9)
- [7.10. `builtins`](07-metaprogramming.md#7.10)
- [7.11. `inspect`](07-metaprogramming.md#7.11)
- [7.12. `importlib`](07-metaprogramming.md#7.12)
- [7.13. `ast`](07-metaprogramming.md#7.13)
- [7.14. `dir()`](07-metaprogramming.md#7.14)

### Часть VIII. Внутренности CPython

[Открыть часть →](08-cpython-internals.md)

- [8.1. Интернация строк](08-cpython-internals.md#8.1)
- [8.2. Кэш малых чисел (-5..256)](08-cpython-internals.md#8.2)
- [8.3. Замыкания и `__closure__`](08-cpython-internals.md#8.3)
- [8.4. `sys._getframe` и фреймы](08-cpython-internals.md#8.4)
- [8.5. `sys.getrefcount`](08-cpython-internals.md#8.5)
- [8.6. Управление GC через `gc`](08-cpython-internals.md#8.6)
- [8.7. `__code__`](08-cpython-internals.md#8.7)
- [8.8. Динамическая смена `__class__`](08-cpython-internals.md#8.8)
- [8.9. `dis` — байт-код](08-cpython-internals.md#8.9)
- [8.10. Recursion limit](08-cpython-internals.md#8.10)
- [8.11. `contextvars`](08-cpython-internals.md#8.11)
- [8.12. `pathlib`](08-cpython-internals.md#8.12)
- [8.13. `types`](08-cpython-internals.md#8.13)
- [8.14. `weakref`](08-cpython-internals.md#8.14)
- [8.15. `sys.unraisablehook`](08-cpython-internals.md#8.15)

### Часть IX. Кодировки и кодеки

[Открыть часть →](09-encodings.md)

- [9.1. PEP 263](09-encodings.md#9.1)
- [9.2. Почему `rot_13` падает с `SyntaxError`](09-encodings.md#9.2)
- [9.3. Какие кодировки подходят](09-encodings.md#9.3)
- [9.4. Скрипт для проверки всех кодировок](09-encodings.md#9.4)
- [9.5. Свой кодек через `codecs.register()`](09-encodings.md#9.5)
- [9.6. Механика `search_function`](09-encodings.md#9.6)

### Часть X. Интроспекция окружения

[Открыть часть →](10-introspection.md)

- [10.1. `sys.flags`](10-introspection.md#10.1)
- [10.2. `sys._xoptions`](10-introspection.md#10.2)
- [10.3. `os.environ` и `PYTHON*`](10-introspection.md#10.3)
- [10.4. `sys.implementation`, `platform.*`](10-introspection.md#10.4)
- [10.5. `resource.getrlimit`](10-introspection.md#10.5)
- [10.6. `/proc/self/`](10-introspection.md#10.6)
- [10.7. Audit hooks (PEP 578)](10-introspection.md#10.7)
- [10.8. Faulthandler](10-introspection.md#10.8)
- [10.9. Универсальный «комбайн»](10-introspection.md#10.9)

### Часть XI. Полезные модули stdlib

[Открыть часть →](11-stdlib.md)

- [11.1. `functools.lru_cache`, `functools.cache`](11-stdlib.md#11.1)
- [11.2. `functools.partial`](11-stdlib.md#11.2)
- [11.3. `functools.reduce`](11-stdlib.md#11.3)
- [11.4. `weakref`](11-stdlib.md#11.4)
- [11.5. `copy`/`deepcopy`](11-stdlib.md#11.5)
- [11.6. `warnings`](11-stdlib.md#11.6)
- [11.7. `__all__`](11-stdlib.md#11.7)
- [11.8. `pickle`](11-stdlib.md#11.8)
- [11.9. `tracemalloc`](11-stdlib.md#11.9)
- [11.10. `operator`](11-stdlib.md#11.10)
- [11.11. `singledispatch`, `cached_property`, `total_ordering`](11-stdlib.md#11.11)
- [11.12. `queue`](11-stdlib.md#11.12)
- [11.13. `reprlib`](11-stdlib.md#11.13)
- [11.14. `os.scandir`, `os.fwalk`](11-stdlib.md#11.14)
- [11.15. `logging`](11-stdlib.md#11.15)
- [11.16. `signal` и `atexit`](11-stdlib.md#11.16)
- [11.17. `datetime`, `timedelta`, `timezone`](11-stdlib.md#11.17)
- [11.18. `bisect` и `heapq`](11-stdlib.md#11.18)
- [11.19. `csv`, `json`, `urllib.parse`](11-stdlib.md#11.19)
- [11.20. `mmap`](11-stdlib.md#11.20)
- [11.21. `shutil` и `tempfile`](11-stdlib.md#11.21)
- [11.22. `decimal` и `fractions`](11-stdlib.md#11.22)
- [11.23. `re`](11-stdlib.md#11.23)
- [11.24. `unicodedata`](11-stdlib.md#11.24)
- [11.25. `struct`, `memoryview`](11-stdlib.md#11.25)
- [11.26. `hashlib`, `hmac`, `secrets`](11-stdlib.md#11.26)
- [11.27. `math`, `statistics`](11-stdlib.md#11.27)
- [11.28. `random`](11-stdlib.md#11.28)
- [11.29. `argparse`, `configparser`, `subprocess`](11-stdlib.md#11.29)
- [11.30. `timeit`, `bdb`, `profile`/`cProfile`, `code`/`codeop`](11-stdlib.md#11.30)
- [11.31. `venv`, `pip`, `site`](11-stdlib.md#11.31)

### Часть XII. Линтеры и директивы в комментариях

[Открыть часть →](12-linters.md)

- [12.1. `# -*- coding: ... -*-` (PEP 263)](12-linters.md#12.1)
- [12.2. `# type: int` (PEP 484)](12-linters.md#12.2)
- [12.3. `# noqa`](12-linters.md#12.3)
- [12.4. `# doctest: +ELLIPSIS`](12-linters.md#12.4)
- [12.5. Коды flake8/pylint](12-linters.md#12.5)
- [12.6. `pyproject.toml`](12-linters.md#12.6)
- [12.7. `ruff` — замена стека flake8 + isort + pyupgrade](12-linters.md#12.7)
- [12.8. Гранулярные подавления: `# noqa: E501` vs `# noqa` vs `# ruff: noqa: E501`](12-linters.md#12.8)
- [12.9. Типовые игноры: `# type: ignore` vs `# type: ignore[code]` vs `# pyright: ignore`](12-linters.md#12.9)
- [12.10. pre-commit: ruff + mypy в одном конвейере](12-linters.md#12.10)

### Часть XIII. От .py к байт-коду: компиляция и виртуальная машина

[Открыть часть →](13-bytecode-vm.md)

- [13.1. Почему Python и компилируется, и интерпретируется](13-bytecode-vm.md#13.1)
- [13.2. Импорт и .pyc: формат, кэширование, инвалидация](13-bytecode-vm.md#13.2)
- [13.3. Пайплайн компилятора: токены → PEG → AST → байт-код](13-bytecode-vm.md#13.3)
- [13.4. Стековая машина: как читается байт-код](13-bytecode-vm.md#13.4)
- [13.5. Виртуальная машина: eval loop, специализация, GIL, JIT](13-bytecode-vm.md#13.5)

### Часть XIV. Не только CPython: кто ещё исполняет Python

[Открыть часть →](14-implementations.md)

- [14.1. Язык против реализации: контракт Python](14-implementations.md#14.1)
- [14.2. Альтернативные реализации: кто, на чём, зачем](14-implementations.md#14.2)
- [14.3. Не реализации: Numba, Cython и граница «тот же язык»](14-implementations.md#14.3)
- [14.4. REPL поверх REPL: IPython, Jupyter и соседи](14-implementations.md#14.4)

### Часть XV. Тестирование: от assert до тестов самого CPython

[Открыть часть →](15-testing.md)

- [15.1. `assert` под капотом: байт-код, `-O` и тонкие локации ошибок](15-testing.md#15.1)
- [15.2. `unittest` изнутри: loader → suite → runner → result](15-testing.md#15.2)
- [15.3. `unittest.mock` изнутри: анатомия подмены](15-testing.md#15.3)
- [15.4. Подмена времени и окружения в тестах](15-testing.md#15.4)
- [15.5. `doctest` изнутри](15-testing.md#15.5)
- [15.6. `pytest` изнутри](15-testing.md#15.6)
- [15.7. `coverage.py`: измерение покрытия](15-testing.md#15.7)
- [15.8. `sys.settrace`/`sys.setprofile`: крючки отладчика и профайлера](15-testing.md#15.8)
- [15.9. `sys.monitoring` (PEP 669, 3.12+): один API для инструментов](15-testing.md#15.9)
- [15.10. Тесты самого CPython: `python -m test`](15-testing.md#15.10)
- [15.11. Тестовые режимы интерпретатора: шпаргалка](15-testing.md#15.11)

### Приложения

- [Приложение A. Системы обнаружения плагиата](appendix-a-plagiarism.md)
- [Приложение B. Взаимодействие с системами проверки кода](appendix-b-code-checkers.md)
- [Приложение C. Code golf — Python на минималках](appendix-c-code-golf.md)
- [Приложение D. Где почитать](appendix-d-references.md)

---

## Лицензия

- **Проза** (тексты в `book/`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **Код в сниппетах**: [MIT](https://github.com/n3xumc0r3/py-underhood/blob/main/CODE_LICENSE)

Подробнее — в [LICENSE](https://github.com/n3xumc0r3/py-underhood/blob/main/LICENSE) и [CONTRIBUTING.md](https://github.com/n3xumc0r3/py-underhood/blob/main/CONTRIBUTING.md).

## Контрибьют

PRs приветствуются — особенно bug fixes, опечатки, фактические ошибки. Большие новые секции — сначала откройте issue.
