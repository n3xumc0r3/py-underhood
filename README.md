# Python под капотом

> **Книга о редко используемых, скрытых и продвинутых возможностях Python и интерпретатора CPython — от синтаксических трюков до глубоких internals.**

[![Site](https://img.shields.io/badge/site-n3xumc0r3.github.io-10b981?style=flat&logo=github&labelColor=000)](https://n3xumc0r3.github.io/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/prose-CC%20BY--NC--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](CODE_LICENSE)
[![MkDocs Material](https://img.shields.io/badge/docs-mkdocs--material-526CFE.svg)](https://squidfunk.github.io/mkdocs-material/)

**Читать онлайн:** **<https://n3xumc0r3.github.io/>**

---

## Что это за книга

Систематический разбор того, что обычно остаётся за кадром в обычных учебниках по Python: редко используемые синтаксические трюки, internals интерпретатора CPython, метапрограммирование, дескрипторы, асинхронность под капотом, code golf. Материал подан по нарастающей — первые главы доступны любому разработчику на Python, последние требуют готовности разбираться в байт-коде, фреймовых структурах и устройстве `dict` под капотом.

Это **не** учебник для новичков. Предполагается, что вы уже пишете на Python, знаете базовый синтаксис, разбираетесь в классах и хотя бы раз запускали `asyncio`. Книга будет полезна тем, кто готовится к сложным собеседованиям, пишет библиотеки и фреймворки, занимается оптимизацией или просто хочет выйти за рамки «написал код — заработало».

## Что внутри

~22 600 строк, 17 глав и 4 приложения, 213 разделов с собственным коротким якорем `#N.M`. Все примеры проверены на CPython 3.12+.

### Краткое оглавление

| # | Раздел | Что покрывает |
|---|--------|-----------|
| I | [Базовые скрытые особенности](book/01-basics.md) | числовые/строковые литералы, f-строки, `match/case`, моржовый оператор, `try/except/else/finally`, exception chaining, truthiness |
| II | [Контекстные менеджеры](book/02-context-managers.md) | `with`, `@contextmanager`, `ExitStack`, `suppress`, `redirect_stdout` |
| III | [Генераторы и итераторы](book/03-generators.md) | `yield`, `yield from`, `send()`/`throw()`/`close()`, `itertools`, `collections`, мост в async-генераторы |
| IV | [Асинхронность](book/04-async.md) | event loop, `asyncio.gather`, `TaskGroup`, async generators, async context managers |
| V | [Классы и интерфейсы](book/05-classes.md) | `dataclasses`, `Protocol`, MRO/C3, `__init_subclass__`, `super()`, `__slots__`, `enum`, `typing` |
| VI | [Дескрипторы и property](book/06-descriptors.md) | `__get__`/`__set__`/`__delete__`, `@property`, data/non-data, `cached_property`, `__set_name__` на практике (ORM-поля), функции как дескрипторы |
| VII | [Метапрограммирование](book/07-metaprogramming.md) | `type()`, метаклассы, `ast`, `inspect`, `compile`/`exec`/`eval`, аннотации как данные |
| VIII | [Внутренности CPython](book/08-cpython-internals.md) | байт-код, фреймы, интернация строк, кэш малых чисел, GIL, цикл сборки мусора |
| IX | [Кодировки и кодеки](book/09-encodings.md) | UTF-8/16, `codecs`, BOM, свой кодек через `codecs.register()` |
| X | [Интроспекция окружения](book/10-introspection.md) | `sys.flags`, `os.environ`, `PYTHON*` переменные, audit hooks, faulthandler |
| XI | [Полезные модули stdlib](book/11-stdlib.md) | `itertools`, `functools`, `collections`, `pathlib`, `subprocess`, `concurrent.futures`, ещё 25+ модулей |
| XII | [Линтеры и директивы](book/12-linters.md) | `# noqa` (включая `# ruff: noqa` и RUF100), `# type: ignore[code]` vs `# pyright: ignore`, ruff, `pyproject.toml`, pre-commit |
| XIII | [От .py к байт-коду: компиляция и VM](book/13-bytecode-vm.md) | компиляция vs интерпретация, формат `.pyc` (PEP 552), PEG→AST→байт-код, стековая машина, специализирующий интерпретатор (PEP 659), GIL, JIT |
| XIV | [Не только CPython](book/14-implementations.md) | язык против реализации, PyPy/GraalPy/MicroPython/RustPython, Jython/IronPython/Stackless/Pyston, Numba/Cython, IPython и Jupyter |
| XV | [Тестирование](book/15-testing.md) | assert в байт-коде, unittest/mock изнутри, doctest, pytest (fixtures, assertion rewriting), coverage.py, sys.settrace и sys.monitoring (PEP 669), тесты самого CPython, диагностические режимы для CI |
| XVI | [Механика импорта](book/16-import.md) | IMPORT_NAME и sys.modules, анатомия sys.path и -P, finders/path hooks, ModuleSpec и loaders, namespace-пакеты (PEP 420), круговые импорты, PEP 562 и LazyLoader, reload, builtin/frozen/extension/zipimport, кастомные импорт-хуки, -X importtime + бенчмарки старта |
| XVII | [C-расширения и C API](book/17-c-api.md) | ctypes (структуры, колбэки, use_errno), cffi ABI/API, PyObject и owned/borrowed-ссылки, бессмертные объекты (PEP 683), свой модуль (METH_*), свой тип (static/heap), PyErr-протокол, GIL из C (Py_BEGIN_ALLOW_THREADS), stable ABI (abi3), сборки без GIL, встраивание интерпретатора, отладка + бенчмарки |
| A | [Прил. A. Системы обнаружения плагиата](book/appendix-a-plagiarism.md) | Winnowing, MOSS, JPlag, Dolos, метрики Хальстеда, McCabe |
| B | [Прил. B. Взаимодействие с системами проверки кода](book/appendix-b-code-checkers.md) | косметические и архитектурные приёмы, песочницы, обход через `__subclasses__()` |
| C | [Прил. C. Code golf](book/appendix-c-code-golf.md) | Python на минималках — сжатие, алиасы, канонические задачи, разбор онелинеров |
| D | [Прил. D. Где почитать](book/appendix-d-references.md) | библиография: PEP-ы, книги по CPython internals, статьи |

Полное кликабельное оглавление по всем 213 разделам — на сайте: **<https://n3xumc0r3.github.io/>**

## Как читать

Три способа, выбирайте удобный:

1. **На сайте** — <https://n3xumc0r3.github.io/>. MkDocs Material, светлая/тёмная тема, поиск по тексту, удобная навигация, якоря `#N.M` для прямой ссылки на любой раздел.
2. **В GitHub** — markdown-исходники в [book/](book/). Удобно, если хочется смотреть raw-версию или делать PR.
3. **Локально** — клонируйте репозиторий и поднимите MkDocs (или воспользуйтесь Obsidian):
   ```bash
   git clone https://github.com/n3xumc0r3/py-underhood.git
   cd py-underhood
   pip install -r requirements.txt
   mkdocs serve
   # открыть http://127.0.0.1:8000
   ```

## Как контрибьютить

PRs приветствуются — особенно bug fixes, опечатки, фактические ошибки. Большие новые секции — сначала откройте issue для обсуждения.

1. Прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) — там описаны требования к формату, стилю и юридические моменты.
2. Для багов в книге — откройте issue по шаблону [bug_report](.github/ISSUE_TEMPLATE/bug_report.md).
3. Для предложений новых разделов — [feature_proposal](.github/ISSUE_TEMPLATE/feature_proposal.md).
4. Перед PR запустите `mkdocs build --strict` локально — это поймает битые ссылки и ошибки в markdown.

## Лицензия

Двойная — осознанное решение, чтобы и сообщество могло контрибьютить, и автор сохранял коммерческие права:

- **Проза** (тексты в `book/`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, другие документационные `.md`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Любой может ремиксить с указанием авторства, в некоммерческих целях, производные произведения — под той же лицензией.
- **Код в сниппетах** (блоки кода внутри markdown, файлы в `scripts/`, любые `.py`): [MIT](CODE_LICENSE). Код свободно используется в любых проектах, включая коммерческие.

CLA не нужен — делая PR, вы неявно принимаете лицензию проекта (та же модель, что у [HackTricks](https://github.com/HackTricks-wiki/hacktricks)). Контрибьютор подтверждает, что вклад оригинальный и не скопирован из других источников.

Полный текст обеих лицензий — в [`LICENSE`](LICENSE) и [`CODE_LICENSE`](CODE_LICENSE).

## Структура репозитория

```
py-underhood/
├── book/                       # Исходники глав (docs_dir для mkdocs)
│   ├── index.md                # Главная сайта: кликабельное оглавление
│   ├── 01-basics.md            # Часть I
│   ├── 02-context-managers.md  # Часть II
│   ├── ...                     # Части III-XI
│   ├── 12-linters.md           # Часть XII
│   ├── appendix-a-plagiarism.md
│   ├── appendix-b-code-checkers.md
│   ├── appendix-c-code-golf.md
│   ├── appendix-d-references.md
│   ├── yandex_4b729843aad89a3d.html  # Yandex Webmaster verification
│   ├── google6c18515b3f63e728.html   # Google Search Console verification
│   ├── robots.txt              # для поисковых ботов
│   ├── stylesheets/
│   │   └── extra.css           # Кастомный CSS: monochrome + electric green, IBM Plex
│   └── javascripts/
│       └── extra.js            # Runtime: ⚠️ жёлтая подсветка callout'ов
├── overrides/
│   └── main.html               # OG tags + Twitter Card + JSON-LD для SEO
├── scripts/                    # Утилиты для поддержки контента
│   ├── split_book.py           # Разбивка исходного markdown на 17 файлов
│   ├── add_anchors.py          # Якоря {#N.M} ко всем H2/H3
│   ├── fix_list_separation.py  # Пустая строка между абзацем и списком
│   ├── join_list_continuations.py  # Склейка continuation-строк в list items
│   └── tighten_lists.py        # Tight lists (без <p> обёртки)
├── .github/
│   ├── ISSUE_TEMPLATE/         # Шаблоны: bug_report, feature_proposal
│   ├── workflows/
│   │   └── trigger-user-pages.yml  # Триггерит sync в n3xumc0r3.github.io репо
│   └── PULL_REQUEST_TEMPLATE.md
├── mkdocs.yml                  # Конфиг MkDocs Material
├── requirements.txt            # mkdocs + material + pymdown-extensions + Pygments
├── LICENSE                     # CC BY-NC-SA 4.0 (полный текст) — для прозы
├── CODE_LICENSE                # MIT — для кода в сниппетах
├── CONTRIBUTING.md             # Как контрибьютить
├── CODE_OF_CONDUCT.md          # Contributor Covenant 2.1
├── .gitignore
└── .gitattributes
```

## Как устроен деплой

Сайт хостится на **корневом URL** `https://n3xumc0r3.github.io/` (не на `/py-underhood/`). Это нужно для правильной индексации поисковиками и более удобной работы с ним. А ещё это более красиво.

Сборка и деплой идут через **два репозитория**:

1. **`n3xumc0r3/py-underhood`** (этот репо) — источник контента. При пуше в `main` запускается workflow `trigger-user-pages.yml`, который триггерит `repository_dispatch` на втором репо.
2. **`n3xumc0r3/n3xumc0r3.github.io`** (user-pages репо) — там хостится собранный сайт. Workflow `sync-from-py-underhood.yml` клонирует py-underhood, собирает `mkdocs build --strict`, копирует `site/` в корень и коммитит в `main`. GitHub Pages автоматически публикует изменения.

## Фичи сайта

- **Книжная навигация** — внизу каждой страницы «← предыдущая / следующая →», без бесконечного sidebar.
- **Якоря `#N.M`** — каждый раздел имеет короткий читаемый якорь: `/03-generators/#3.8` вместо `/03-generators/#38-itertoolspairwise-batched-python-310312`. Все разделы кликабельны с главной.
- **Поиск по тексту** — с подсветкой и подсказками и красивым выводом найденного. Разделитель токенов — любой не-буквенный символ, чтобы слова с прилипшей пунктуацией (`операторы,` и `операторы`) находились одинаково.
- **⚠️ жёлтая подсветка** — блоки с предупреждениями (blockquote, list items, paragraphs с ⚠️) автоматически подсвечиваются мягким жёлтым.
- **Light/Dark тема** — monochrome база + electric green акцент (`#10b981`), шрифты IBM Plex Sans / IBM Plex Mono.
- **Скруглённые углы** — кнопки, поля, карточки, table rows — всё со скруглением (radius-pill для кнопок, radius-md для карточек).
- **Кнопка «копировать»** — у каждого блока кода.
- **Адаптивная ширина** — контент растянут до 90rem (1800px), не узкая колонка.
- **Open Graph + JSON-LD** — превью при шаринге в Telegram/Twitter, structured data для Google rich results.

## Контакты

- GitHub: [@n3xumc0r3](https://github.com/n3xumc0r3)
- Telegram-канал (планируется): `@py_underhood`
- Хабр-блог (планируется): «Python под капотом»
- Хештег: `#pyunderhood` / `#pythonподкапотом`

## Статус проекта

Книга задеплоена и читается на **<https://n3xumc0r3.github.io/>**. Контент более-менее вычитан и структурирован, но возможны неточности, устаревшие ссылки и опечатки. Если нашли — открывайте issue или PR.
