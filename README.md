# Python под капотом

> **От синтаксических трюков до internals CPython.**
> Книга о редко используемых, скрытых и продвинутых возможностях Python и интерпретатора CPython — от базовых трюков до глубоких internals.

[![Site](https://img.shields.io/badge/site-live-10b981?style=flat&logo=github&labelColor=000)](https://n3xumc0r3.github.io/py-underhood/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/prose-CC%20BY--NC--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](CODE_LICENSE)
[![MkDocs Material](https://img.shields.io/badge/docs-mkdocs--material-526CFE.svg)](https://squidfunk.github.io/mkdocs-material/)

## Где читать

| Источник | URL | Что это |
|----------|-----|---------|
| **Сайт** | https://n3xumc0r3.github.io/py-underhood/ | MkDocs Material, светлая/тёмная тема, поиск, навигация «книжкой» |
| **В GitHub** | [book/](book/) | Markdown-исходники, открываются прямо в репо |
| **Leanpub** | _запланировано_ | Платная beta с тем же контентом |

Сайт автоматически пересобирается при пуше в `main` через [GitHub Actions](.github/workflows/deploy-mkdocs.yml) — изменений видно через 1-2 минуты после мержа.

## Что внутри

Книга охватывает темы на стыке трёх областей: Python-трюки и идиомы, internals CPython, и взаимодействие с системами проверки кода (как контекст, а не основной фокус). Материал организован по нарастающей сложности — от простых синтаксических трюков до разбора байт-кода и фреймовых структур CPython.

### Структура

| # | Раздел | Что покрывает |
|---|--------|-----------|
| I | [Базовые скрытые особенности](book/01-basics.md) | числовые/строковые литералы, f-строки, `match/case`, моржовый оператор, `try/except/else/finally`, exception chaining |
| II | [Контекстные менеджеры](book/02-context-managers.md) | `with`, `@contextmanager`, `ExitStack`, `suppress`, `redirect_stdout` |
| III | [Генераторы и итераторы](book/03-generators.md) | `yield`, `yield from`, `send()`/`throw()`/`close()`, `itertools`, `collections` |
| IV | [Асинхронность](book/04-async.md) | event loop, `asyncio.gather`, `TaskGroup`, async generators, async context managers |
| V | [Классы и интерфейсы](book/05-classes.md) | `dataclasses`, `Protocol`, MRO, `__init_subclass__`, `super()`, `__slots__`, `enum`, `typing` |
| VI | [Дескрипторы и property](book/06-descriptors.md) | `__get__`/`__set__`/`__delete__`, `@property`, data/non-data descriptors |
| VII | [Метапрограммирование](book/07-metaprogramming.md) | `type()`, метаклассы, `__init_subclass__`, `ast`, `inspect`, аннотации как данные |
| VIII | [Внутренности CPython](book/08-cpython-internals.md) | байт-код, фреймы, интернация строк, кэш малых чисел, GIL, цикл сборки мусора |
| IX | [Кодировки и кодеки](book/09-encodings.md) | UTF-8/16, `codecs`, `sys.getdefaultencoding`, BOM, normalization |
| X | [Интроспекция окружения](book/10-introspection.md) | `sys`, `inspect`, `builtins`, `__import__`, `importlib` |
| XI | [Полезные модули stdlib](book/11-stdlib.md) | `itertools`, `functools`, `collections`, `pathlib`, `subprocess`, `concurrent.futures` |
| XII | [Линтеры и директивы](book/12-linters.md) | `# noqa`, `# type: ignore`, `# pylint: disable`, изолирование ложных срабатываний |
| A | [Приложение A. Системы обнаружения плагиата](book/appendix-a-plagiarism.md) | MOSS, JPlag, Dolos, Winnowing, fingerprinting |
| B | [Приложение B. Взаимодействие с системами проверки кода](book/appendix-b-code-checkers.md) | как работают, что видят, как писать «прозрачно» |
| C | [Приложение C. Code golf](book/appendix-c-code-golf.md) | Python на минималках — приёмы, алиасы, трюки для коротких решений |
| D | [Приложение D. Где почитать](book/appendix-d-references.md) | библиография: PEP-ы, книги, статьи |

## Структура репозитория

```
py-underhood/
├── book/                       # Исходники глав (docs_dir для mkdocs)
│   ├── index.md                # Главная: кликабельное оглавление по всем 161 разделу
│   ├── 01-basics.md            # Часть I
│   ├── 02-context-managers.md  # Часть II
│   ├── ...
│   ├── 12-linters.md           # Часть XII
│   ├── appendix-a-plagiarism.md
│   ├── appendix-b-code-checkers.md
│   ├── appendix-c-code-golf.md
│   ├── appendix-d-references.md
│   ├── yandex_4b729843aad89a3d.html  # Yandex Webmaster verification
│   ├── google6c18515b3f63e728.html   # Google Search Console verification
│   ├── stylesheets/
│   │   └── extra.css           # Кастомный CSS: monochrome + electric green, IBM Plex
│   └── javascripts/
│       └── extra.js            # Runtime: ⚠️ жёлтая подсветка callout'ов
├── overrides/                  # Material theme overrides (пока пусто, на будущее)
├── scripts/                    # Утилиты для поддержки контента
│   ├── split_book.py           # Разбивка исходного markdown на 17 файлов
│   ├── add_anchors.py          # Якоря {#N.M} ко всем H2/H3
│   ├── fix_list_separation.py  # Пустая строка между абзацем и списком
│   ├── join_list_continuations.py  # Склейка continuation-строк в list items
│   └── tighten_lists.py        # Tight lists (без <p> обёртки)
├── .github/
│   ├── ISSUE_TEMPLATE/         # Шаблоны: bug_report, feature_proposal
│   ├── workflows/
│   │   └── deploy-mkdocs.yml   # GitHub Actions: авто-деплой на Pages
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

## Фичи сайта

- **Книжная навигация** — внизу каждой страницы «← предыдущая / следующая →», без бесконечного sidebar.
- **Якоря `#N.M`** — каждый раздел имеет короткий читаемый якорь: `/#3.8` вместо `/#38-itertoolspairwise-batched-python-310312`. Все 161 раздел кликабельны с главной.
- **⚠️ жёлтая подсветка** — блоки с предупреждениями (blockquote, list items, paragraphs с ⚠️) автоматически подсвечиваются мягким жёлтым.
- **Поиск по全文у** — с подсветкой и подсказками, работает по 17 000+ строк.
- **Light/Dark тема** — monochrome база + electric green акцент (`#10b981`), шрифты IBM Plex Sans / IBM Plex Mono.
- **Скруглённые углы** — кнопки, поля, карточки, table rows — всё со скруглением (radius-pill для кнопок, radius-md для карточек).
- **Кнопка «копировать»** — у каждого блока кода.
- **Адаптивная ширина** — контент растянут до 90rem (1800px), не узкая колонка.

## Лицензия

Двойная лицензия — осознанное решение, чтобы и сообщество могло контрибьютить, и автор сохранял коммерческие права:

- **Проза** (тексты в `book/`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, и другие документационные `.md`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Любой может ремиксить с указанием авторства, в некоммерческих целях, производные произведения — под той же лицензией.
- **Код в сниппетах** (блоки кода внутри markdown, файлы в `scripts/`, любые `.py`): [MIT](CODE_LICENSE). Код свободно используется в любых проектах, включая коммерческие.

Полный текст обеих лицензий — в [`LICENSE`](LICENSE) и [`CODE_LICENSE`](CODE_LICENSE).

## Контрибьют

PRs приветствуются — особенно bug fixes, опечатки, фактические ошибки. Большие новые секции — сначала откройте issue для обсуждения.

Перед отправкой PR обязательно прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) — там описаны требования к формату, стилю и юридические моменты (CLA не нужен, но контрибьютор подтверждает, что вклад оригинальный и лицензируется под те же условия).

Шаблоны issue: [баг в книге](.github/ISSUE_TEMPLATE/bug_report.md) · [предложение нового раздела](.github/ISSUE_TEMPLATE/feature_proposal.md).

## Контакты

- GitHub: [@n3xumc0r3](https://github.com/n3xumc0r3)
- Telegram-канал (планируется): `@py_underhood`
- Хабр-блог (планируется): «Python под капотом»
- Хештег: `#pyunderhood` / `#pythonподкапотом`

## Статус проекта

Книга задеплоена и читается на https://n3xumc0r3.github.io/py-underhood/. Контент (~17 800 строк) вычитан и структурирован, но возможны неточности, устаревшие ссылки и опечатки. Если нашли — открывайте issue или PR.
