# Python под капотом

> **От синтаксических трюков до internals CPython.**
> Книга о редко используемых, скрытых и продвинутых возможностях Python и интерпретатора CPython — от базовых трюков до глубоких internals.

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/prose-CC%20BY--NC--SA%204.0-blue.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Code: MIT](https://img.shields.io/badge/code-MIT-green.svg)](CODE_LICENSE)
[![MkDocs Material](https://img.shields.io/badge/docs-mkdocs--material-526CFE.svg)](https://squidfunk.github.io/mkdocs-material/)

## Что внутри

Книга охватывает темы на стыке трёх областей: Python-трюки и идиомы, internals CPython, и взаимодействие с системами проверки кода (как контекст, а не основной фокус). Материал организован по нарастающей сложности — от простых синтаксических трюков до разбора байт-кода и фреймовых структур CPython.

### Структура

| # | Раздел | Содержание |
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
| A | [Системы обнаружения плагиата](book/appendix-a-plagiarism.md) | MOSS, JPlag, Dolos, Winnowing, fingerprinting |
| B | [Взаимодействие с системами проверки кода](book/appendix-b-code-checkers.md) | как работают, что видят, как писать «прозрачно» |
| C | [Code golf](book/appendix-c-code-golf.md) | Python на минималках — приёмы, алиасы, трюки для коротких решений |
| D | [Где почитать](book/appendix-d-references.md) | библиография: PEP-ы, книги, статьи |

## Где читать

- **Сайт (MkDocs Material):** автоматически деплоится на GitHub Pages при пуше в `main` — URL появится после первого деплоя.
- **Прямо в GitHub:** любой файл из `book/` открывается как страница с оглавлением справа.
- **Leanpub (планируется):** книга будет опубликована на Leanpub с тем же контентом, что и в репозитории.

## Лицензия

Двойная лицензия — это осознанное решение, чтобы и сообщество могло контрибьютить, и автор сохранял коммерческие права:

- **Проза** (тексты в `book/`, `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, и другие документационные `.md`): [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Любой может ремиксить с указанием авторства, в некоммерческих целях, производные произведения — под той же лицензией.
- **Код в сниппетах** (блоки кода внутри markdown, файлы в `scripts/`, любые `.py`): [MIT](CODE_LICENSE). Код свободно используется в любых проектах, включая коммерческие.

Полный текст обеих лицензий — в [`LICENSE`](LICENSE) и [`CODE_LICENSE`](CODE_LICENSE).

## Контрибьют

PRs приветствуются — особенно bug fixes, опечатки, фактические ошибки. Большие новые секции — сначала откройте issue для обсуждения.

Перед отправкой PR обязательно прочитайте [CONTRIBUTING.md](CONTRIBUTING.md) — там описаны требования к формату, стилю и юридические моменты (CLA не нужен, но контрибьютор подтверждает, что вклад оригинальный и лицензируется под те же условия).

## Контакты

- GitHub: [@n3xumc0r3](https://github.com/n3xumc0r3)
- Telegram-канал (планируется): `@py_underhood`
- Хабр-блог (планируется): «Python под капотом»
- Хештег: `#pyunderhood` / `#pythonподкапотом`

## Статус проекта

Книга в активной разработке. Контент книги (~17 800 строк) уже вычитан и структурирован, но возможны неточности, устаревшие ссылки и опечатки. Если нашли — открывайте issue или PR.
