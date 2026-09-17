# Приложение D. Где почитать

> Единой книги, которая покрывает **все** обсуждаемые приёмы, не существует — материал на стыке трёх разных областей: (1) systems for plagiarism detection, (2) Python/C Python internals, (3) security-oriented coding / obfuscation.

## D.1. По системам обнаружения плагиата

1. **Saul Schleimer, Daniel S. Wilkerson, Alex Aiken.** *Winnowing: Local Algorithms for Document Fingerprinting.* ACM SIGMOD 2003. PDF: https://theory.stanford.edu/~aiken/publications/papers/sigmod03.pdf · ACM DL: https://dl.acm.org/doi/10.1145/872757.872770
2. **Alex Aiken.** *MOSS: Measure of Software Similarity.* https://theory.stanford.edu/~aiken/moss/
3. **Maurice H. Halstead.** *Elements of Software Science.* North-Holland, 1977.
4. **Thomas J. McCabe.** *A Complexity Measure.* IEEE TSE, 1976.
5. **Lutz Prechelt, Guido Malpohl, Michael Philippsen.** *Finding Plagiarisms among a Set of Programs with JPlag.* JUCS 2002. https://www.jucs.org/jucs_8_11/finding_plagiarisms_among_a
6. **Maertens et al.** *Dolos: Language-agnostic Plagiarism Detection in Source Code.* 2022. https://dolos.ugent.be/
7. **Codequiry**: https://codequiry.com/ — документация, блог про AI-code detection.
8. **Patrick Juola.** *Authorship Attribution.* Foundations and Trends in Information Retrieval, 2008.

## D.2. По Python internals (CPython, байт-код, фреймы, интернация)

9. **Anthony Shaw.** *CPython Internals: Your Guide to the Python 3 Interpreter.* (2021) — лучшая современная книга по CPython.
10. **Philip Guo.** *Python Tutor* — визуализатор выполнения Python. https://pythontutor.com/
11. **PEP 263** — *Defining Python Source Code Encodings*. https://peps.python.org/pep-0263/
12. **PEP 484** — *Type Hints*. https://peps.python.org/pep-0484/
13. **PEP 526** — *Syntax for Variable Annotations*. https://peps.python.org/pep-0526/
14. **PEP 544** — *Protocols: Structural subtyping*. https://peps.python.org/pep-0544/
15. **PEP 557** — *Data Classes*. https://peps.python.org/pep-0557/
16. **PEP 563** — *Postponed Evaluation of Annotations*. https://peps.python.org/pep-0563/
17. **PEP 578** — *Python Runtime Audit Hooks*. https://peps.python.org/pep-0578/
18. **PEP 634** — *Structural Pattern Matching*. https://peps.python.org/pep-0634/
19. **PEP 750** — *Template Strings (t-strings)*. Python 3.14+. https://peps.python.org/pep-0750/
20. **PEP 8** — *Style Guide for Python Code*. https://peps.python.org/pep-0008/
21. **Brett Slatkin.** *Effective Python: 90 Specific Ways to Write Better Python.* 2-е изд., 2019.
22. **Luciano Ramalho.** *Fluent Python.* 2-е изд., 2022.
23. **David Beazley, Brian K. Jones.** *Python Cookbook* (3-е изд.).
24. **Исходники CPython** на GitHub: https://github.com/python/cpython
    - `Python/ceval.c` — главный цикл интерпретатора
    - `Objects/unicodeobject.c` — интернация строк
    - `Objects/longobject.c` — кэш малых чисел
    - `Objects/object.c` — реализация `__eq__`/`__hash__`/`__repr__` для `object` — база для понимания дескрипторов и `__class__` lookup (Часть VI)
    - `Objects/descrobject.c` — реализация дескрипторов (`property`, `classmethod`, `staticmethod`)
    - `Objects/funcobject.c` — `function.__get__`: почему методы привязываются (6.9)
    - `Python/bltinmodule.c` — `globals`, `locals`, `__import__`
    - `Python/frame.c` — реализация `PyFrame_LocalsToFast`
25. **PEP 448** — *Additional Unpacking Generalizations* (`[*a, *b]`, `{**d1, **d2}`). https://peps.python.org/pep-0448/
26. **PEP 465** — *A dedicated infix operator for matrix multiplication* (`@`). https://peps.python.org/pep-0465/
27. **PEP 570** — *Python Positional-Only Parameters* (`/`). https://peps.python.org/pep-0570/
28. **PEP 584** — *Add Union Operators To dict* (`dict |`, `dict |=`). https://peps.python.org/pep-0584/
29. **PEP 585** — *Type Hinting Generics In Standard Collections* (`list[int]` вместо `List[int]`). https://peps.python.org/pep-0585/
30. **PEP 649** — *Deferred Evaluation of Annotations* (lazy annotations в 3.14+). https://peps.python.org/pep-0649/
31. **PEP 742** — *Narrowing types with TypeIs*. https://peps.python.org/pep-0742/
32. **Dan Bader.** *Python Tricks: A Buffet of Awesome Python Features.* 2017.
33. **Patrick Viafore.** *Robust Python: Type Checking with Mypy.* 2021.
34. **PEP 257** — *Docstring Conventions*. https://peps.python.org/pep-0257/
35. **PEP 20** — *The Zen of Python*. https://peps.python.org/pep-0020/
36. **PEP 401** — *Barry's FLUFL* (April Fools). https://peps.python.org/pep-0401/

## D.3. По метапрограммированию и обфускации Python

37. **Naomi Ceder.** *The Quick Python Book* (3-е изд.).
38. **Doug Hellmann.** *The Python 3 Standard Library by Example*.
39. **Документация Python → `codecs`**: https://docs.python.org/3/library/codecs.html
40. **Документация Python → `sys`**: https://docs.python.org/3/library/sys.html
41. **Документация Python → `types`**: https://docs.python.org/3/library/types.html
42. **Документация Python → `ast`**: https://docs.python.org/3/library/ast.html
43. **Документация Python → `dis`**: https://docs.python.org/3/library/dis.html
44. **Документация Python → `asyncio`**: https://docs.python.org/3/library/asyncio.html
45. **Документация Python → `dataclasses`**: https://docs.python.org/3/library/dataclasses.html
46. **Документация Python → `typing`**: https://docs.python.org/3/library/typing.html
47. **Документация Python → `functools`**: https://docs.python.org/3/library/functools.html
48. **Документация Python → `weakref`**: https://docs.python.org/3/library/weakref.html
49. **Документация Python → `importlib.metadata`**: https://docs.python.org/3/library/importlib.metadata.html
50. **Документация Python → Command line**: https://docs.python.org/3/using/cmdline.html
51. **Документация Python → `mmap`**: https://docs.python.org/3/library/mmap.html
52. **Документация Python → `multiprocessing.shared_memory`**: https://docs.python.org/3/library/multiprocessing.shared_memory.html
53. **Документация Python → `signal`**: https://docs.python.org/3/library/signal.html
54. **Документация Python → `atexit`**: https://docs.python.org/3/library/atexit.html
55. **Документация Python → `subprocess`**: https://docs.python.org/3/library/subprocess.html
56. **Документация Python → `timeit`**: https://docs.python.org/3/library/timeit.html
57. **Документация Python → `cProfile`**: https://docs.python.org/3/library/profile.html
58. **Документация Python → `code`**: https://docs.python.org/3/library/code.html
59. **Документация Python → `bdb`**: https://docs.python.org/3/library/bdb.html
60. **Документация Python → `hashlib`**: https://docs.python.org/3/library/hashlib.html
61. **Документация Python → `secrets`**: https://docs.python.org/3/library/secrets.html
62. **Документация Python → `string.Template`**: https://docs.python.org/3/library/string.html#template-strings
63. **Документация Python → `__future__`**: https://docs.python.org/3/library/__future__.html

## D.4. По обходу фильтров и security (общий контекст)

64. **OWASP Cheat Sheet — Code Obfuscation**.
65. **Christian Collberg, Clark Thomborson, Douglas Low.** *A Taxonomy of Obfuscating Transformations.* 1997.
66. **Репозиторий pyminifier**: https://github.com/liftoff/pyminifier — подмена идентификаторов на случайные строки (`--obfuscate`), компрессия через `zlib`/`bz2`.
67. **Документация flake8**: https://flake8.pycqa.org/
68. **Документация ruff**: https://docs.astral.sh/ruff/
69. **Документация Pylint**: https://pylint.readthedocs.io/
70. **Документация mypy**: https://mypy.readthedocs.io/
71. **OWASP — Command Injection** (про `shell=True` в subprocess): https://owasp.org/www-community/attacks/Command_Injection
72. **Документация pre-commit**: https://pre-commit.com/ — конфиг и хуки из 12.10.

## D.5. По асинхронности и структурированной конкурентности

73. **Nathaniel Smith.** *Notes on structured concurrency, or: go statement considered harmful* (2018) — статья-первоисточник концепции nursery: https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/
74. **trio** — фреймворк, где nursery придуман и доведён до предела: https://github.com/python-trio/trio
75. **curio** — предшественник trio, первый фреймворк со строгими правилами отмены: https://github.com/dabeaz/curio
76. **anyio** — единый API поверх asyncio и trio; на нём стоят Starlette и FastAPI: https://github.com/agronholm/anyio

## D.6. Code golf: платформы и диалекты

77. **code.golf** — активный сайт с таблицей лидеров и разборами решений на Python 3: https://code.golf/
78. **Tips for golfing in Python** — коллективный тред-шпаргалка на codegolf.SE (аналог C.19, но живой и с обсуждением): https://codegolf.stackexchange.com/questions/54/tips-for-golfing-in-python
79. **Pyth** — отдельный язык, компилируемый в Python, специально для гольфа: https://github.com/isaacg1/pyth

## D.7. Pyjails и демо песочниц

80. **Ned Batchelder.** *Tarpit* (PyCon 2012) — каноническая демонстрация того, что «песочница» на CPython невозможна в принципе; 10 минут, делающие Приложение B этически осмысленным: http://nedbatchelder.com/blog/201211/tarpit_at_pycon_2012.html
81. **Сборник pyjails** — репозитории с разборами побегов из python-песочниц (активное CTF-направление; по запросу «pyjail» на GitHub — десятки таких): https://github.com/saladandonionfries/pyjails

## D.8. Блоги для регулярного чтения

82. **realpython.com** — крупные туториалы с реальной глубиной, часто с бенчмарками.
83. **snarky.ca** — Brett Cannon, бывший core-dev CPython: разборы PEP и internals по первоисточникам.
84. **treyhunner.com** — Trey Hunner: итераторы, генераторы, comprehensions — идеальный фон к Части III.
85. **hynek.me** — Hynek Schlawack: async, attrs, структурная обработка данных, production-практики.
86. **bitecode.dev** — серия «Python tricks you didn't know about» — ближе всего по формату к Части I этого конспекта.

## D.9. Что закрывает каждую тему

| Тема | Что почитать |
|------|--------------|
| Winnowing, MOSS | Schleimer et al. 2003 (№1), MOSS homepage (№2) |
| Halstead / McCabe | Halstead 1977 (№3), McCabe 1976 (№4) |
| JPlag, Dolos | Prechelt et al. 2002 (№5), Maertens et al. 2022 (№6) |
| AST-нормализация | Maertens et al. 2022 (№6), docs `ast` (№42) |
| Стилометрия / AI-code | Codequiry (№7), Juola 2008 (№8) |
| `compile`/`exec`/`eval`, байт-код | CPython Internals (№9), Fluent Python (№22), `dis` (№43) |
| `types.FunctionType`, `types.CodeType` | docs `types` (№41), CPython source (№24) |
| `operator`, `type()`, декораторы | Fluent Python (№22), Python Cookbook (№23) |
| `__annotations__` | PEP 526 (№13), Effective Python (№21) |
| `setattr`/`getattr`/`builtins` | Python Cookbook (№23) |
| `sys.modules`, `__import__` | docs `sys` (№40), Doug Hellmann (№38) |
| `sys._getframe`, `f_locals`, `f_code` | docs `sys` (№40), CPython Internals (№9) |
| `ctypes.pythonapi.PyFrame_LocalsToFast` | docs `ctypes`, CPython source `Python/frame.c` (№24) |
| Интернация строк, кэш чисел | CPython Internals (№9), Effective Python (№21) |
| `is` vs `==`, truthiness, `hash()` | Effective Python (№21), Fluent Python (№22), docs `sys` (№40) |
| `hash()`, `PYTHONHASHSEED` | docs `sys` (№40), CPython Internals (№9) |
| `id()`, `vars()`, `dir()` | docs `builtins`, docs `sys` (№40) |
| Кодировки, `# -*- coding: ... -*-`, rot_13, кастомные кодеки | PEP 263 (№11), docs `codecs` (№39) |
| `# noqa`, `# type: ignore`, `pylint: disable` | docs flake8/ruff/pylint (№67, 68, 69) |
| Коды F401/F841/E501/E203 | PEP 8 (№20), docs flake8/ruff |
| `sys.flags`, `-X` опции, `sys._xoptions` | docs `sys` (№40), Python docs → Command line (№50) |
| Audit hooks (PEP 578) | PEP 578 (№17) |
| Faulthandler | docs [faulthandler](https://docs.python.org/3/library/faulthandler.html) |
| `/proc/self/` (Linux) | man proc(5), Linux Kernel docs |
| `match/case` (вкл. OR, **rest, class patterns) | PEP 634 (№18), Fluent Python (№22) |
| `t`-строки | PEP 750 (№19) |
| `__future__` imports, `annotations`, `barry_as_FLUFL` | docs `__future__` (№63), PEP 563 (№16), PEP 401 (№36) |
| Пасхалки (`import this`, `antigravity`, `braces`) | PEP 20 (№35), PEP 401 (№36), docs Python |
| Генераторы, `yield`, `yield from` | Fluent Python (№22), Python Cookbook (№23) |
| Асинхронность, asyncio | docs `asyncio` (№44), Fluent Python (№22) |
| Контекстные менеджеры | docs `contextlib`, Fluent Python (№22) |
| `slice`, `iter(callable, sentinel)`, `__getitem__`-итерация | docs `builtins`, Python Cookbook (№23) |
| `slice.indices()`, `range` slicing | docs `builtins` |
| `reversed()`, `__reversed__` | docs `builtins` |
| `__slots__` + множественное наследование | Fluent Python (№22), Effective Python (№21) |
| `zip(strict=True)`, цепочки сравнений | docs Python (what's new in 3.10) |
| `dataclasses` (вкл. frozen, slots, InitVar) | PEP 557 (№15), docs `dataclasses` (№45) |
| `abc.ABC`, `Protocol`, `TypeIs` | docs `typing` (№46), PEP 544 (№14), PEP 742 (№31) |
| MRO, mixins, `__init_subclass__`, `super()` | Fluent Python (№22), Effective Python (№21) |
| Дескрипторы, `@property`, `__getattr__` | Fluent Python (№22), Effective Python (№21) |
| Dunder-методы (`__call__`, `__str__`/`__repr__`, `__bool__`, `__len__`, `__iter__`/`__next__`, `__contains__`, `__missing__`, `__del__`, `__index__`) | Fluent Python (№22), docs Python → Data model |
| `functools.lru_cache`, `partial`, `reduce`, `singledispatch` | docs `functools` (№47) |
| `weakref`, `weakref.finalize` | docs `weakref` (№48) |
| `copy`/`deepcopy`, `pickle`, `warnings`, `__all__`, `tracemalloc` | docs соответствующих модулей |
| `mmap`, `MAP_SHARED`, `multiprocessing.shared_memory` | docs `mmap` (№51), docs `shared_memory` (№52) |
| `signal`, `atexit`, graceful shutdown | docs `signal` (№53), docs `atexit` (№54) |
| `subprocess`, `shell=True` опасности | docs `subprocess` (№55), OWASP Command Injection (№71) |
| `timeit`, `cProfile`, `bdb`, `code`/`codeop` | docs `timeit` (№56), `cProfile` (№57), `code` (№58), `bdb` (№59) |
| AST-трансформации (`NodeTransformer`, instrumentation) | docs `ast` (№42) |
| Числовые литералы, `int.bit_count()`, `int.from_bytes` | docs Python → Lexical analysis, docs `int` |
| `hash()`, `math.isclose()`, `pow(x,y,mod)`, `round()` (banker's) | docs `math`, docs `builtins` |
| `bytes.fromhex()`/`.hex()` | docs `bytes` |
| Строковые методы: `casefold`, `partition`, `translate`/`maketrans`, `splitlines`, `.is*()` | docs `str` |
| `dict |` (PEP 584), `dict.fromkeys`, `get`/`setdefault`/`pop` | PEP 584 (№28), docs `dict` |
| `str.format()`, `%` formatting, `string.Template`, `format()` | docs `string` (№62), PEP 3101 |
| `lambda`, `map`/`filter` | docs `builtins`, Fluent Python (№22) |
| `del` оператор, `help()`/`__doc__`/docstrings | docs `builtins`, PEP 257 (№34) |
| `or`/`and` как values, тернарный, `walrus` (`:=`) | docs Python → Expressions, PEP 572 |
| `try/except/else/finally`, bare `raise`, `except (tuple)` | docs Python → Errors, Fluent Python (№22) |
| `python -i` (REPL после падения) | docs Python → Command line (№50) |
| `__matmul__` (`@` оператор) | PEP 465 (№26) |
| `*`/`**` в литералах (PEP 448) | PEP 448 (№25) |
| Positional-only `/` (PEP 570) | PEP 570 (№27) |
| Подписные generics `list[int]` (PEP 585) | PEP 585 (№29) |
| `__future__ import annotations` (PEP 563/649) | PEP 563 (№16), PEP 649 (№30) |
| `venv`, `pip`, `site`, `.pth`, `sitecustomize` | docs `venv`, docs `pip`, docs `site`, PEP 405 |
| `python -m`, флаги запуска (`-S`, `-s`, `-E`, `-B`, `-u`) | docs Python → Command line (№50) |
| Интроспекция окружения тестирующих систем | нет единого источника; разрозненные статьи на Habr, medium |

## D.10. Если выбирать одну книгу

- **Anthony Shaw, *CPython Internals*** (№9) — лучшее по internals: интернация, кэш чисел, фреймы, байт-код, `compile`, AST, объектная модель. Обфускацию и системы плагиата не покрывает.
- **Effective Python** Бретта Слаткина (№21) — практический взгляд «грабли + антипаттерны». Многие «грабли», которые превращены в оружие, у него разобраны как «что не надо делать».
- **Fluent Python** Лючиано Рамальо (№22) — для современного Python (3.10+ — `match/case`, `zip(strict=True)`, t-строки, протоколы, дескрипторы, метаклассы).
- **Python Tricks** Дэна Бейдера (№32) — сборник «вау, не знал, что так можно» — близок по духу к этому конспекту, но легче и без internals/обфускации.
- **Robust Python** Патрика Виафоре (№33) — про type hints, mypy, типобезопасность на уровне production. Хорошее продолжение после Части V (typing) и Части XII (линтеры).
