# Полный конспект по скрытым и продвинутым возможностям Python

> Тема: редко используемые, скрытые и продвинутые возможности языка Python и интерпретатора CPython — от базовых трюков до глубоких internals. В приложении — системы проверки кода и взаимодействие с ними (как контекст, а не как основной фокус).

**Структура по сложности:** Часть I (базовые трюки) → II (контекстные менеджеры) → III-IV (генераторы, асинхронность — отдельные большие разделы) → V-VI (классы, дескрипторы) → VII-VIII (метапрограммирование, internals CPython) → IX-XII (кодировки, окружение, stdlib, линтеры) → Приложения A (системы проверки кода), B (взаимодействие с ними), C (code golf), D (справочная литература — в самом конце).

---

## Оглавление

### Часть I. Базовые скрытые особенности языка
_→ см. также: II (контекстные менеджеры для ресурсов из 1.22 — exception chaining), III (генераторы и `iter(callable, sentinel)` из 1.14), VII (аннотации как данные и AST-анализ трюков)_
1.1. Числовые литералы: `.9`, `1.`, underscores, hex/oct/bin, экспонента `1e3`, комплексные `1j`
1.2. Строковые префиксы: `r`, `b`, `u`, `f`, `t`
1.3. Неявное склеивание строковых литералов
1.4. f-строки: `=`, `:`, `!r`/`!s`/`!a`, даты, заполнители
1.5. `slice` как полноценный объект
1.6. Эллипсис `...`
1.7. `else` у циклов `for`/`while`
1.8. Тернарный оператор
1.9. Моржовый оператор `:=`
1.10. `match/case` — структурное сопоставление
1.11. Цепочки сравнений
1.12. Множественное присвоение и распаковка
1.13. `as` — все способы применения
1.14. `iter(callable, sentinel)` и `zip(strict=True)` _(расширенно — в Части III, раздел 3.5–3.6)_
1.15. `assert` и флаг `-O`
1.16. `breakpoint()` и `PYTHONBREAKPOINT`
1.17. `_` — переменная-«мусорник» и последний результат в REPL
1.18. Slice assignment — `a[:] = ...`, extended slices
1.19. Списочные выражения без приравнивания — `[print(i) for i in range(10)]`
1.20. Стиль: trailing comma, optional whitespace, когда нарушать PEP 8
1.21. `try/except/else/finally` — полный скелет и re-raise
1.22. Exception chaining — `raise X from Y`, `__cause__`, `__context__`
1.23. Скрытые параметры встроенных функций
1.24. `__future__` imports — включение фич из будущих версий
1.25. Пасхалки — культурный слой Python

### Часть II. Контекстные менеджеры
_→ см. также: I (exception chaining `from` из 1.22 — для `__exit__`), IV (async context managers `__aenter__`/`__aexit__` — асинхронный аналог), VIII (contextvars для контекстно-зависимых переменных)_
2.1. `with` — внутренности (`__enter__`/`__exit__`)
2.2. Свой менеджер через класс
2.3. `@contextmanager` — без класса
2.4. `contextlib.suppress` и `contextlib.ExitStack`
2.5. Несколько менеджеров в одном `with`
2.6. Подавление ошибок через `__exit__`
2.7. `contextlib.redirect_stdout`/`redirect_stderr`
2.8. `contextlib.closing` и `aclosing`

### Часть III. Генераторы и итераторы
_→ см. также: IV (async generators — асинхронный аналог `yield`), VII (`inspect` для интроспекции генераторов, `ast` для анализа), XI (itertools подробно, functools.partial для частичного применения)_
3.1. `yield`, `next`, `StopIteration`
3.2. Generator expressions vs list comprehensions
3.3. `yield from` — делегирование
3.4. `send()`, `throw()`, `close()` — корутины на генераторах
3.5. Бесконечные генераторы
3.6. `itertools` — избранные рецепты
3.7. Экономия памяти через ленивые вычисления
3.8. `itertools.pairwise`, `batched` (Python 3.10+/3.12+)
3.9. `collections` — Counter, defaultdict, deque, ChainMap, OrderedDict, namedtuple

### Часть IV. Асинхронность
_→ см. также: II (async context managers), III (корутины на генераторах через `send()` — историческая основа), V (`typing` для async, ExceptionGroup + `except*` для TaskGroup), XI (concurrent.futures как альтернатива asyncio)_
4.1. Что такое event loop
4.2. `async def`, `await` — синтаксис и семантика
4.3. `asyncio.run` — точка входа
4.4. `asyncio.gather` — конкурентный запуск
4.5. `asyncio.create_task` — фоновые задачи
4.6. `asyncio.wait` — ожидание с таймаутом
4.7. `asyncio.Queue`, `Lock`, `Semaphore`
4.8. Async generators (`yield` в `async def`)
4.9. Async context managers (`__aenter__`/`__aexit__`)
4.10. Конкурентность vs параллелизм
4.11. Threads vs asyncio vs multiprocessing — когда что
4.12. `asyncio.as_completed` — по мере завершения
4.13. `asyncio.TaskGroup` (Python 3.11+) — структурированная конкурентность
4.14. `asyncio.timeout` (Python 3.11+) и `asyncio.shield`
4.15. `asyncio.CancelledError` — корректная отмена
4.16. `asyncio.current_task`, `all_tasks`, `run_coroutine_threadsafe`, `to_thread`, `Runner`, `eager_task_factory`

### Часть V. Классы и интерфейсы
_→ см. также: VI (`@property` — что под капотом dataclass-field, дескрипторы), VII (`type()` для динамического создания классов, `__init_subclass__`), VIII (`__slots__` и internals объекта), XI (dataclasses + functools.total_ordering)_
5.1. `dataclasses` — современные data class builders
5.2. `abc.ABC` и `@abstractmethod`
5.3. `Protocol` (PEP 544) — структурная типизация
5.4. MRO и C3-линеаризация
5.5. Mixins и множественное наследование
5.6. `__init_subclass__` — хук при наследовании
5.7. `super()` — подробно
5.8. `__slots__` — оптимизация памяти
5.9. `@classmethod` vs `@staticmethod`
5.10. `enum` — Enum, IntEnum, IntFlag, auto
5.11. `dataclasses` advanced: `asdict`, `fields`, `replace`, `KW_ONLY`
5.12. `typing` advanced: TypeVar, Generic, cast, overload, Literal, final, TypedDict, NamedTuple
5.13. `dataclasses` advanced2: `InitVar`, `__post_init__`, sentinel-поля, `order`, `match_args`
5.14. `typing` для async, IO, collections.abc
5.15. `typing.TYPE_CHECKING`
5.16. `ExceptionGroup` и `except*`
5.17. Dunder-методы: полный обзор

### Часть VI. Дескрипторы и property
_→ см. также: V (`__slots__`, `@property` как sugar над дескрипторами), VII (`functools.cached_property`, декораторы классов), VIII (`__getattr__` через `__dict__` и internals attribute lookup)_
6.1. `__get__`/`__set__`/`__delete__` — протокол дескрипторов
6.2. Data vs non-data descriptors
6.3. `__set_name__` — автоматическая инициализация
6.4. `@property` — что под капотом
6.5. `__getattr__` vs `__getattribute__` vs `__setattr__`

### Часть VII. Метапрограммирование
_→ см. также: V (`type()` и метапрограммирование классов), VIII (`__code__`, `dis`, байт-код как объект), XI (functools.wraps/lru_cache/singledispatch как готовые декораторы), XII (AST-анализ — основа линтеров)_
7.1. Аннотации как данные (`__annotations__`)
7.2. `setattr`/`getattr`/`delattr`
7.3. Декораторы (параметризованные, классовые)
7.4. `functools.wraps` — зачем нужен
7.5. `type()` — динамическое создание классов
7.6. `types.FunctionType` и `types.CodeType`
7.7. `compile`/`exec`/`eval`
7.8. `locals()` и `globals()`
7.9. `sys.modules` и `__import__`
7.10. `builtins` — переопределение и интроспекция
7.11. `inspect` — интроспекция всего
7.12. `importlib` — программный импорт
7.13. `ast` — разбор исходного кода в AST
7.14. `dir()` — самый быстрый способ исследования API

### Часть VIII. Внутренности CPython
_→ см. также: V (`__slots__` — связь с объектной моделью), VII (`__code__`, `inspect`, `sys._getframe` — общий фундамент интроспекции), XI (weakref, contextvars, pathlib — отдельные stdlib-модули internals)_
8.1. Интернация строк и `sys.intern`
8.2. Кэш малых чисел (-5..256)
8.3. Замыкания и `__closure__`/cell objects
8.4. `sys._getframe` и фреймы
8.5. `sys.getrefcount` и счётчик ссылок
8.6. Управление GC через `gc` модуль
8.7. Интроспекция функций через `__code__`
8.8. Динамическая смена `__class__`
8.9. Доступ к байт-коду через `dis`
8.10. Recursion limit и `RecursionError`
8.11. `contextvars` — контекстно-зависимые переменные
8.12. `pathlib` — объектно-ориентированные пути
8.13. `types` — продвинутые типы
8.14. `weakref` — продвинутое
8.15. `sys.unraisablehook` и `sys._current_frames`

### Часть IX. Кодировки и кодеки
_→ см. также: I (строковые префиксы `r`/`b`/`u`/`f`/`t`), X (`sys.flags.utf8_mode`, `PYTHONUTF8`), XII (`# -*- coding: ... -*-` как директива и PEP 263)_
9.1. PEP 263: `# -*- coding: ... -*-`
9.2. Почему `rot_13` падает с `SyntaxError`
9.3. Какие кодировки подходят для исходного файла
9.4. Скрипт для проверки всех кодировок
9.5. Свой кодек через `codecs.register()`
9.6. Механика `search_function` в `encodings/__init__.py`

### Часть X. Интроспекция окружения
_→ см. также: VII (`sys.modules`, `inspect` для интроспекции), VIII (`sys._getframe`, `_current_frames`, `unraisablehook`), XII (`-O`, `--remove`-флаги и `# noqa` для контроля окружения)_
10.1. `sys.flags` — флаги командной строки Python
10.2. `sys._xoptions` — `-X` опции
10.3. `os.environ` и `PYTHON*` переменные
10.4. `sys.implementation`, `platform.*`
10.5. `resource.getrlimit` — лимиты ресурсов
10.6. `/proc/self/` — Linux-специфичная разведка
10.7. Audit hooks (PEP 578)
10.8. Faulthandler — дамп стеков
10.9. Универсальный «комбайн» для одной попытки

### Часть XI. Полезные модули стандартной библиотеки
_→ см. также: III (itertools подробно, generator expressions), V (`functools.cached_property`, `total_ordering`, `dataclasses`), VII (`functools.wraps`, `lru_cache`, `singledispatch` — метапрограммирование функций), VIII (weakref, contextvars, tracemalloc — internals)_
11.1. `functools.lru_cache`, `functools.cache`
11.2. `functools.partial`
11.3. `functools.reduce`
11.4. `weakref`
11.5. `copy`/`deepcopy`
11.6. `warnings`
11.7. `__all__`
11.8. `pickle` и его опасности
11.9. `tracemalloc`
11.10. `operator` модуль
11.11. `functools.singledispatch`, `cached_property`, `total_ordering`
11.12. `queue` — Queue, LifoQueue, PriorityQueue, SimpleQueue
11.13. `reprlib` — ограничение repr для больших структур
11.14. `os.scandir`, `os.fwalk` — продвинутое обход файловой системы
11.15. `logging` — стандартная библиотека логирования
11.16. `signal` и `atexit`
11.17. `datetime`, `timedelta`, `timezone`
11.18. `bisect` и `heapq` — быстрые операции на отсортированных данных
11.19. `csv`, `json`, `urllib.parse`
11.20. `mmap` — memory-mapped files
11.21. `shutil` и `tempfile`
11.22. `decimal` и `fractions`
11.23. `re` — регулярные выражения
11.24. `unicodedata` — нормализация Unicode
11.25. `struct`, `memoryview` — бинарные данные
11.26. `hashlib`, `hmac`, `secrets` — криптография
11.27. `math` — матфункции и `statistics`
11.28. `random` — псевдослучайные числа
11.29. `argparse`, `configparser`, `subprocess` — CLI, конфиги, процессы
11.30. `timeit`, `bdb`, `profile`/`cProfile`, `code`/`codeop` — профилирование, отладка и REPL-движки
11.31. `venv`, `pip`, `site` — виртуальные окружения, пакеты и site-packages

### Часть XII. Линтеры и директивы в комментариях
_→ см. также: I (`# -*- coding: ... -*-` как литерал + PEP 263), VII (AST-анализ — основа всех линтеров), XI (`pyproject.toml` и конфиги stdlib-модулей), X (`-X` опции и флаги командной строки как часть конфигурации окружения)_
12.1. `# -*- coding: ... -*-` (PEP 263)
12.2. `# type: int` (PEP 484)
12.3. `# noqa` — директива линтеров
12.4. `# doctest: +ELLIPSIS` — директивы doctest
12.5. Коды flake8/pylint
12.6. `pyproject.toml`

### Приложение A. Системы обнаружения плагиата
A.1. Winnowing (хеш-винновинг)
A.2. MOSS, JPlag, Dolos, Codequiry
A.3. Метрики Хальстеда
A.4. Цикломатическая сложность (McCabe)
A.5. AST-нормализация (canonicalization)
A.6. Стилометрия и детекторы AI-кода
A.7. Динамический анализ (рантайм)
A.8. Constant folding, propagation, dead code elimination

### Приложение B. Взаимодействие с системами проверки кода (контекст)
B.1. Косметические приёмы
B.2. Архитектурные приёмы (рантайм)
B.3. Перехват аргументов через фреймы и ctypes
B.4. Интроспекция окружения тестирующих систем
B.5. Песочницы и обход через `__subclasses__()`

### Приложение C. Code golf — Python на минималках
C.1. Базовые приёмы сжатия (включая 1-пробельную индентацию)
C.2. «Комментарии» в одну строку через `""`
C.3. Использование `bool` как `int`
C.4. Тернарный оператор vs индексация по `bool` (+ умножение строки на условие)
C.5. `unpack` в `print` и в `*args` (+ чтение stdin через `open(0)`, `print(file=f)`)
C.6. Срезы вместо вызовов
C.7. Short-circuit evaluation вместо `if`
C.8. `walrus` (`:=`) для экономии повторов
C.9. `__import__` вместо `import`
C.10. Битовые операции вместо арифметики (+ `~-n`/`-~n`, `pow(a,b,m)`, `n&~-n<1`)
C.11. `lambda` вместо `def` для коротких функций
C.12. `__builtins__`-трюки (включая таблицу окупаемости алиасов)
C.13. Строковые методы vs регулярки
C.14. Целые числа произвольной длины — бесплатно (→ см. также C.17)
C.15. `exit()` vs `sys.exit()` vs `raise SystemExit`
C.16. Антипаттерны code golf — что НЕ переносить в продакшен
C.17. Числовые константы — сжатие больших чисел (hex vs dec, `1e999`, `[*b'...']`, `int(...,36)`)
C.18. Продвинутые приёмы — I/O, матрицы, исключения, eval
C.19. Сводная шпаргалка по code golf
C.20. Канонические задачи — эталонные решения (FizzBuzz, простота, Фибоначчи, НОД, квайн, Паскаль, Цезарь, RLE)
C.21. Сложный реальный пример — разбор онелинера (`*T` в lambda, `chr(x+48+7*(x>9))`, инлайнинг, `m(gen)` без default)
C.22. Полезные ссылки

### Приложение D. Где почитать

---

