# Часть XIV. Упаковка: от исходников до PyPI

Части XI (11.32) и XVI уже дали базу: `venv`/`pip`/`site` как пользовательский инструмент и импорт-механику, которая эти пакеты потом загружает. Здесь — то, что происходит **между** этими двумя точками: как проект превращается в дистрибуцию, как устроены `dist-info` и wheel, что именно делает pip при установке (и что пишет на диск), как работает editable-режим, на каком языке говорят зависимости (PEP 508/440) и как пакет доезжает до PyPI. Каждый формат в этой части вскрыт реальными прогонами: мы собрали демо-пакет setuptools'ом, разобрали wheel по косточкам, поставили его тремя способами и сняли тайминги — бенчмарки в конце части сняты на машине с 2 ядрами, CPython 3.12.14.

## 14.1. Словарь упаковки и `importlib.metadata` { #14.1 }

Четыре слова, которые постоянно путают:

| Термин | Что это | Пример |
|---|---|---|
| **модуль** | один `.py`-файл (16.1) | `demo_hood/cli.py` |
| **пакет** | каталог с `__init__.py` (или namespace — 16.5) | каталог `demo_hood/` |
| **дистрибуция** | единица установки: то, что публикуется и ставится pip'ом | `demo-pkg-hood 0.1.0` |
| **wheel / sdist** | два формата артефактов дистрибуции (14.5) | `demo_pkg_hood-0.1.0-py3-none-any.whl` |

Заметьте несостыковку имён: дистрибуция `demo-pkg-hood` содержит пакет `demo_hood`. PyPI-имя живёт по правилам нормализации (PEP 503): `-`, `_`, `.` эквивалентны и сравниваются в нижнем регистре — `Demo_Pkg.Hood`, `demo-pkg-hood` и `DEMO_PKG_HOOD` для pip'а один и тот же проект.

Окно в установленные дистрибуции — `importlib.metadata` (с 3.8):

```python
import importlib.metadata as im

im.version("packaging")            # '26.0'
im.metadata("packaging")["Name"]   # 'packaging' (то же, что METADATA-файл)
im.requires("aiohttp")[:3]         # ['aiohappyeyeballs>=2.5.0', 'aiosignal>=1.4.0',
                                   #  'async-timeout<6.0,>=4.0; python_version < "3.11"']
im.files("packaging")[:2]          # ['packaging-26.0.dist-info/INSTALLER', ...]

im.version("no-such-pkg")          # PackageNotFoundError (наследник ModuleNotFoundError → ImportError)

# версия собственного пакета без ручного дублирования констант:
__version__ = im.version(__package__)   # внутри своего же модуля
```

| Вызов | Возвращает | Откуда читает |
|---|---|---|
| `version(name)` | строка версии | `METADATA` или `PKG-INFO` |
| `metadata(name)` | объект `email.message.Message` | тот же файл целиком |
| `requires(name)` | список строк-зависимостей (PEP 508, 14.9) | `Requires-Dist:` в METADATA |
| `files(name)` | список `PackagePath` | `RECORD` |
| `entry_points(group=...)` | `EntryPoints` | `entry_points.txt` (14.10) |
| `distribution(name)` | полный объект `Distribution` | каталог `*.dist-info` |

✅ Отсутствие пакета — это `PackageNotFoundError` (наследник `ModuleNotFoundError` — факт из MRO), а не пустая строка: различайте «пакет есть, но версии нет» и «пакета нет». А если метаданных нет вообще (модуль просто лежит на `sys.path` без установки) — любая попытка уронится: метаданные — атрибут **дистрибуции**, не модуля. Как именно находятся эти `dist-info`-каталоги — см. 14.2.

## 14.2. Анатомия `dist-info`: паспорт установленного пакета { #14.2 }

Всё, что pip «знает» об установленной дистрибуции, лежит в каталоге `<нормализованное_имя>-<версия>.dist-info` рядом с кодом в `site-packages` (11.32). Реальный пример из живого окружения — `packaging-26.0.dist-info`, собранный бэкендом flit и установленный uv:

```
packaging-26.0.dist-info/
├── INSTALLER      # 'uv' — кто ставил
├── METADATA       # паспорт: имя, версия, зависимости, описание
├── RECORD         # манифест: каждый файл + sha256 + размер
├── REQUESTED      # маркер «ставили явно, не как зависимость»
├── WHEEL          # метаданные wheel-артефакта
└── licenses/      # тексты лицензий
```

| Файл | Содержимое | Кто читает |
|---|---|---|
| `METADATA` | `Name:`, `Version:`, `Requires-Dist:`, `Requires-Python:`, описание | `importlib.metadata`, pip |
| `RECORD` | `путь,sha256=<b64>,<размер>` на каждый файл | pip uninstall, `files()` |
| `WHEEL` | `Wheel-Version`, `Generator: <бэкенд>`, `Tag:` | pip при установке |
| `INSTALLER` | имя инструмента установки: `pip`, `uv`, `conda`… | диагностика, pip (предупреждения) |
| `REQUESTED` | пустой маркер, ставился ли пакет явно | pip (resolution) |
| `direct_url.json` | откуда ставили: URL/архив + hash | pip (audit, freeze) |
| `entry_points.txt` | INI-секции групп точек входа | `entry_points()` (14.10) |
| `top_level.txt` | корневые импорт-имена | legacy-инструменты |

Формат `RECORD` — сердце безопасного удаления (внутри wheel того же демо, что соберём в 14.4):

```
demo_hood/__init__.py,sha256=kUR5RAFc7HCeiqdlX36dZOHkUI5wI6V_43RpEcD8b-0,22
demo_hood/cli.py,sha256=gJ8p_hHJMK3tzViREpbHEt3irQk7edKcuiEk_-7bOx0,80
demo_pkg_hood-0.1.0.dist-info/METADATA,sha256=vfOdQp-LLCTwp2kdY1ENhCxsUcg7XS5F1FZ19XRFBqY,171
demo_pkg_hood-0.1.0.dist-info/RECORD,,
```

Каждая строка — «путь, хеш, размер». Две детали, которые важно видеть: **сам RECORD записан с пустыми хешем и размером** (он не может хешировать сам себя), а пути у файлов вне `site-packages` — **относительные** (14.7 покажет `../../bin/demo-hood`). `pip uninstall` просто читает этот список и удаляет файлы построчно — потому удаление не трогает ничего, чего нет в RECORD.

`direct_url.json` — единственное место, где остаётся память об источнике установки:

```json
{"archive_info": {"hash": "sha256=67c376...", "hashes": {"sha256": "67c376..."}},
 "url": "file:///home/z/.../dist/demo_pkg_hood-0.1.0-py3-none-any.whl"}
```

Появляется при установке **не с индекса** (локальный путь, git, прямой URL) — оттуда `pip freeze` рисует `file://`-ссылки, а аудит-инструменты сверяют хеш.

### Что dist-info не содержит { #14.2-net }

Кода. Каталог с `dist-info` — только паспорт; сам код лежит рядом отдельными пакетными каталогами. Отсюда следствия: два пакета, затирающие один и тот же `__init__.py`, останутся «успешно установленными» (RECORD второго перезапишет хеши первого — pip не проверяет коллизии содержимого), а ручное удаление каталога пакета оставит осиротевший `dist-info`, о котором pip всё ещё будет знать. Лечится переустановкой: `pip install --force-reinstall --no-deps <pkg>`.

## 14.3. `pyproject.toml`: PEP 621 { #14.3 }

Один файл вместо ветки `setup.py`/`setup.cfg`/`MANIFEST.in`. Три обязательных смысла в нём: **что собираем** (`[project]`), **чем собираем** (`[build-system]`) и **настройки конкретного инструмента** (`[tool.*]` — ruff/pytest/mypy из Части XII живут здесь же).

```toml
[build-system]                       # ЧЕМ собирать (PEP 518)
requires = ["setuptools>=61"]        # зависимости сборки (ставятся в изолированное окружение)
build-backend = "setuptools.build_meta"

[project]                            # ЧТО собираем (PEP 621)
name = "demo-pkg-hood"
version = "0.1.0"
description = "Демо для Части XIV"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"                      # SPDX-выражение (PEP 639)
authors = [{name = "Author"}]
dependencies = [                     # runtime-зависимости (PEP 508, см. 14.9)
    "requests>=2.25",
    'pywin32==306; sys_platform == "win32"',
]

[project.optional-dependencies]      # extras: pip install demo-pkg-hood[dev]
dev = ["pytest", "ruff", "mypy"]
docs = ["sphinx"]

[project.scripts]                    # консольные команды (14.10)
demo-hood = "demo_hood.cli:main"

[project.entry-points."demo_hood.plugins"]   # своя группа точек входа
hello = "demo_hood.cli:hello"

[project.urls]
Homepage = "https://github.com/user/demo-pkg-hood"

[tool.setuptools.packages.find]      # настройки бэкенда: где искать пакеты
where = ["src"]
```

| Поле `[project]` | Тип | Примечание |
|---|---|---|
| `name` | str | PyPI-имя, нормализация PEP 503 |
| `version` | str | PEP 440 (14.9); можно вынести в `dynamic` |
| `requires-python` | спека | pip откажется ставить на неподходящий интерпретатор |
| `dependencies` | список | runtime-зависимости |
| `optional-dependencies` | таблица | extras; имя extra тоже нормализуется |
| `scripts` / `gui-scripts` | таблица | «команда = модуль:функция» |
| `entry-points` | таблица таблиц | произвольные группы |
| `dynamic` | список | поля, которые бэкенд вычислит сам: `["version", "readme"]` |

`dynamic` — способ не дублировать версию: в `[project]` пишется `dynamic = ["version"]`, а бэкенду говорят, откуда её брать:

```toml
[project]
dynamic = ["version"]
[tool.setuptools.dynamic]
version = {attr = "demo_hood.__version__"}        # читать атрибут (без импорта — AST'ом)
# или из файла: version = {file = "VERSION.txt"}
```

⚠️ `pyproject.toml` читает и pip (для `requires` из `[build-system]`), и бэкенд, и линтеры (Часть XII), но **не Python**: `import pyproject` невозможен, runtime-код не должен опираться на этот файл — версия живёт в метаданных (14.1), а не в исходниках.

## 14.4. Build-бэкенды и PEP 517 { #14.4 }

Сборка отделена от установки стандартом PEP 517: pip не умеет собирать пакеты — он **зовёт функции бэкенда** в subprocess'е:

```
pip install .
   │
   ├─ read [build-system] → создать ИЗОЛИРОВАННОЕ окружение сборки →
   │    pip install setuptools>=61  (только для сборки!)
   ├─ backend.get_requires_for_build_wheel()      → доустановить, если нужно
   ├─ backend.prepare_metadata_for_build_wheel()  → METADATA заранее (для резолвера)
   └─ backend.build_wheel(outdir)                 → *.whl на диск
   │
   └─ установка полученного wheel (14.7)
```

`[build-system] requires` — это не декорация: изолированное окружение сборки свежее, чем вы думаете. В нашем эксперименте `python3 -m venv` создал venv **без setuptools вообще** (с 3.12 ensurepip ставит только pip), и `pip install -e . --no-build-isolation` на таком venv падает, потому что вызывать `setuptools.build_meta` некому. С изоляцией тот же pip сам скачает setuptools с индекса — сборка работает везде, но требует сеть и занимает время (~1–2 с только на подготовку).

| Бэкенд | `build-backend` | Когда выбирать |
|---|---|---|
| `setuptools` | `setuptools.build_meta` | дефолт и максимум совместимости, legacy-пакеты |
| `hatchling` | `hatchling.build` | быстрый, строгие проверки, плагины |
| `flit-core` | `flit_core.buildapi` | чистый Python, минимум конфигурации |
| `pdm-backend` | `pdm.backend` | PDM-стек, динамические метаданные |
| `maturin` | `maturin` | Rust-расширения (PyO3) |
| `scikit-build-core` | `scikit_build_core.build` | C/C++ через CMake (17-я часть) |
| `uv_build` | `uv_build` | uv-стек, очень быстрый (2025+) |

```bash
# штатная сборка (PEP 517 CLI): и sdist, и wheel
pip install build
python -m build                     # → dist/*.tar.gz + dist/*.whl
python -m build --sdist             # только sdist

# pip умеет и сам: собрать wheel без установки
python -m pip wheel . --no-deps --no-build-isolation -w dist/
# → demo_pkg_hood-0.1.0-py3-none-any.whl (в нашем прогоне: 1.72 c, см. бенчмарки)
```

⚠️ `--no-build-isolation` — не «ускоритель», а способ использовать **уже установленный** setuptools (без сети). Требование `requires = ["setuptools>=61"]` при этом никем не проверяется: если в окружении старый setuptools — сборка сломается с невнятной ошибкой глубоко в бэкенде.

✅ Разделение «install-tool vs build-backend» делает сборку воспроизводимой: что бы ни было в вашем рабочем venv, пакет соберётся против зафиксированных `requires`. Платите изоляцией окружения и секундами на её наполнение (см. бенчмарки B3).

## 14.5. sdist и wheel: два формата артефактов { #14.5 }

Из бэкенда выходят два вида артефактов, и pip принимает оба:

**sdist** (source distribution) — tar.gz с исходниками (имя файла — по PEP 625: `name-1.0.tar.gz`). Вскрыли реальный `six-1.17.0.tar.gz`:

```
six-1.17.0/
├── PKG-INFO         # метаданные (предок METADATA — тот же формат email-заголовков)
├── setup.py         # код сборки (у legacy-пакетов вся конфигурация здесь)
├── setup.cfg
├── MANIFEST.in      # какие не-кодовые файлы включить
├── CHANGES, LICENSE, README.rst
└── documentation/   # …и вообще всё, что автор решил положить
```

**wheel** (`.whl`) — уже **готовый к установке** zip-архив (анатомия — 14.6). Ключевое отличие: wheel строит **автор пакета** (или CI), а пользователю остаётся только распаковать. Ставить wheel — это не «быстрее sdist», это качественно другой сценарий: не нужен компилятор C, не запускается чужой код сборки (14.7 о границах этого обещания), не нужна сеть для зависимостей сборки.

| | sdist | wheel |
|---|---|---|
| Формат | `.tar.gz` (PEP 625) | zip `.whl` со строгим именем (14.6) |
| Метаданные | `PKG-INFO` в корне | `*.dist-info/METADATA` внутри |
| Сборка у пользователя | нужна (PEP 517, изоляция, сеть) | **не нужна** |
| Код сборки исполняется | да, на машине пользователя | нет |
| Платформозависимость | без тегов | зашита в имя (теги) |
| C-расширения | собираются на месте | уже внутри `.so`/`.dll` (17-я часть) |
| Кто строит | пользователь (косвенно) | автор/CI один раз |

```bash
pip install six                          # предпочтёт wheel, если есть
pip install --no-binary :all: six        # заставить ставить из sdist (сборка на месте)
pip install --prefer-binary pkg          # старый wheel вместо новейшего sdist
pip download --no-deps --no-binary :all: six   # скачать sdist руками
```

✅ Практическое правило: sdist обязателен к публикации (некоторые упаковщики/линукс-дистрибутивы собирают только из него), но добрые пакеты публикуют и wheel для каждой платформы. Если пакет публикует **только** sdist с C-кодом — его установка потребует gcc у каждого пользователя (или см. 18.9 про stable ABI: один `cp312-abi3`-wheel покрывает 3.12+).

## 14.6. Анатомия wheel: имя как протокол { #14.6 }

Имя wheel-файла — не подпись, а **машинночитаемый протокол совместимости**:

```
demo_pkg_hood-0.1.0-py3-none-any.whl
└name─────┘ └ver.┘ └py┘ └abi┘ └platform┘
numpy-2.1.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
pywin32-306-cp312-cp312-win_amd64.whl
mypy-1.11.0-cp312-cp312-musllinux_1_1_x86_64.whl
```

| Поле | Примеры | Смысл |
|---|---|---|
| python-тег | `py3`, `py2.py3`, `cp312` | какой интерпретатор: `py3` — любой Python 3, `cp312` — только CPython 3.12 |
| abi-тег | `none`, `cp312`, `abi3` | `none` — чистый Python; `cp312` — своя ABI; `abi3` — stable ABI (18.9) |
| platform-тег | `any`, `manylinux_2_17_x86_64`, `win_amd64`, `macosx_11_0_arm64` | ОС/архитектура; `any` — везде |
| build-тег (опц.) | `1-` перед python-тегом | пересборка той же версии |

Теги читает `packaging.utils.parse_wheel_filename` — тот же код (в вендорнутой копии) живёт в pip'е: кандидаты, несовместимые с текущим интерпретатором, отсеиваются ещё на этапе разбора имени, до скачивания. Платформенные теги иерархичны: `manylinux2014` — псевдоним `manylinux_2_17`, а один wheel может носить несколько платформенных тегов сразу, перечисленных через точку — матчится любой из них, по порядку приоритета из `sys_tags()` (новейшая совместимая glibc — первой).

Как много вариантов «подходит» даже на одной машине:

```python
from packaging import tags
st = list(tags.sys_tags())      # порядок приоритета для ЭТОГО интерпретатора
len(st)                         # 1122 тега на CPython 3.12 / Linux x86_64 / glibc 2.41
st[:2]                          # cp312-cp312-manylinux_2_41_x86_64, ..._2_40...
st[-1]                          # py30-none-any — самый «древний» совместимый
```

Внутри wheel — zip с двумя частями: код и `dist-info` (всё это проверено на собранном демо):

```
demo_pkg_hood-0.1.0-py3-none-any.whl
├── demo_hood/__init__.py            # код — как будет лежать в site-packages
├── demo_hood/cli.py
└── demo_pkg_hood-0.1.0.dist-info/
    ├── METADATA                     # e-mail-заголовки PEP 621
    ├── WHEEL                        # Wheel-Version: 1.0; Generator: setuptools (82.0.1);
    │                                # Root-Is-Purelib: true; Tag: py3-none-any
    ├── entry_points.txt             # [console_scripts] / [demo_hood.plugins]
    ├── top_level.txt
    └── RECORD                       # хеши всех файлов архива; pyc здесь ещё нет!
```

Детали, которые иначе не увидеть:

- **`Root-Is-Purelib`** говорит, куда распаковывать: `true` — в `purelib` (site-packages), `false` — в `platlib` (у системного питона это разные каталоги; в venv совпадают). Platform-wheel'ы кладут `.so`-файлы рядом с кодом — вся платформенная специфика уже в имени.
- **`RECORD` внутри wheel не содержит `.pyc`** — они ещё не существуют! pip при установке компилирует байт-код (15.2) и дописывает строки `demo_hood/__pycache__/cli.cpython-312.pyc,,` (без хеша — pyc воспроизводим из исходника) в RECORD **установленной** копии.
- **`.data/`-каталог**: файлы, которые должны попасть НЕ в site-packages (скрипты, данные, заголовки), пакуются как `demo.data/scripts/run.sh` и раскладываются pip'ом по схемам установки.

⚠️ Wheel — не-installer: никаких скриптов постустановки. Всё, что делается при установке wheel'а — распаковка по схеме, компиляция pyc, генерация скриптов из `entry_points.txt` и запись dist-info. Если вы «установили пакет, а он требует ещё что-то скачать» — это делает импортируемый код, не wheel (и это основание не доверять таким пакетам, см. Приложение B).

## 14.7. pip изнутри: что происходит при `pip install` { #14.7 }

Соберём весь путь (и проверим его на реальном пакете):

```
pip install demo-pkg-hood
  1. RESOLVE   резолвер (resolvelib): собрать граф зависимостей,
               для каждого требования — список кандидатов с индекса,
               отсечь по тегам/Requires-Python/маркерам, выбрать версию
  2. DOWNLOAD  скачать wheel (или sdist) в HTTP-кэш ~/.cache/pip
  3. BUILD     если sdist — собрать wheel через PEP 517 (14.4); wheel кэшируется
  4. INSTALL   распаковка в site-packages → компиляция pyc (15.2) →
               генерация console-скриптов → запись dist-info (RECORD/INSTALLER/…)
```

Что реально оказывается на диске после `pip install demo_pkg_hood-0.1.0-py3-none-any.whl --target ...` (наш прогон):

```
demo_hood/__init__.py
demo_hood/__pycache__/__init__.cpython-312.pyc     ← скомпилировано при установке
demo_hood/cli.py
demo_hood/__pycache__/cli.cpython-312.pyc
bin/demo-hood                                      ← скрипт из [project.scripts]
demo_pkg_hood-0.1.0.dist-info/INSTALLER            ← 'pip'
demo_pkg_hood-0.1.0.dist-info/METADATA
demo_pkg_hood-0.1.0.dist-info/RECORD               ← теперь и с pyc, и с bin/-путём
demo_pkg_hood-0.1.0.dist-info/REQUESTED            ← ставили явно (не как зависимость)
demo_pkg_hood-0.1.0.dist-info/direct_url.json      ← ставили не с индекса
demo_pkg_hood-0.1.0.dist-info/WHEEL
demo_pkg_hood-0.1.0.dist-info/entry_points.txt
```

Сгенерированный `bin/demo-hood` — не копия чего-то из wheel, а **код, который pip написал сам**:

```python
#!/home/z/.venv/bin/python3          # абсолютный shebang — на интерпретатор этого venv
# -*- coding: utf-8 -*-
import re
import sys
from demo_hood.cli import main
if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    sys.exit(main())
```

Три следствия, объясняющие классические «а почему так»: (1) shebang абсолютный — скрипт, положенный в venv, останется работать только с ним; (2) пути в RECORD относительные (`../../bin/demo-hood`) — pip uninstall удалит скрипт даже из соседнего каталога; (3) `python -m pip` (11.32) надёжнее голого `pip` именно потому, что гарантирует «тот pip, что принадлежит этому интерпретатору», — `bin/pip` мог остаться от другого окружения.

Кэши и переменные:

| Механизм | Путь / переменная | Что кэширует |
|---|---|---|
| HTTP-кэш | `~/.cache/pip` (`PIP_CACHE_DIR`) | скачанные файлы + ответы индекса |
| wheel-кэш локальных сборок | там же | wheels, собранные из sdist ранее |
| `--find-links ./wheels/` | флаг | корпоративные каталоги без индекса |
| `--no-index` + `--find-links` | флаги | полностью офлайн-установка |

| Переменная (10.3) | Действие |
|---|---|
| `PIP_INDEX_URL` | зеркало/приватный индекс вместо pypi.org |
| `PIP_BREAK_SYSTEM_PACKAGES=1` | разрешить ломать системный Python (Debian блокирует pip по умолчанию) |
| `PIP_REQUIRE_VIRTUALENV=1` | запретить pip'у работать вне venv — защита от «sudo pip» |
| `PIP_DISABLE_PIP_VERSION_CHECK=1` | тише и быстрее на CI |
| `PIP_TARGET` | каталог по умолчанию для `--target` |

⚠️ **Установка из sdist исполняет код бэкенда** (а с legacy `setup.py` — и его) на вашей машине. Wheel безопаснее ровно в этом смысле. pip резолвер ставит wheel по умолчанию и предупреждает, когда вынужден собирать. Приложение B разбирает упаковку глазами нарушителя.

✅ Ошибка резолвера `Cannot install X because these package versions have conflicting dependencies` — это работа step 1: резолвер честно перебирает граф и не ставит «что-нибудь». Фиксация версий целиком (`pip freeze`) или constraints-файл (`pip install -c constraints.txt`) дают воспроизводимость, но не отменяют конфликтов на стороне pip — их решает только автор графа.

## 14.8. Editable-установка: `.pth` и finder { #14.8 }

`pip install -e .` не копирует код в site-packages — он делает так, чтобы `import` находил код **в исходниках проекта**. Механика не магическая и — что интереснее — у одного и того же setuptools их две; мы обе воспроизвели в чистом venv. Стандартизована editable-инсталляция в **PEP 660** (расширение PEP 517): бэкенд может предоставить hook `build_editable` рядом с `build_wheel`, и `pip` вызывает именно его для `pip install -e .`. До PEP 660 бэкенды решали задачу кто во что горазд — `setuptools` использовал `setup.py develop`, у других были свои трюки.

**Случай 1: src-layout** (код в `src/demo_hood/`) — простая `.pth`-ссылка:

```
site-packages/
├── __editable__.demo_pkg_hood-0.1.0.pth     # СОДЕРЖИМОЕ — просто путь:
│                                            # /home/z/.../demo-pkg/src
└── demo_pkg_hood-0.1.0.dist-info/           # паспорт всё равно пишется целиком
```

`site` (11.32) при старте читает `.pth` и добавляет путь в `sys.path` — дальше работает обычный PathFinder (16.3). Проверка подтверждает: `demo_hood.__file__` указывает в `.../demo-pkg/src/demo_hood/__init__.py`, правки в исходниках видны без переустановки.

**Случай 2: flat-layout** (пакет в корне проекта, рядом с `pyproject.toml`) — так просто нельзя: добавив корень проекта в `sys.path`, вы засорили бы его `pyproject.toml`-окрестностью, конфликтующими именами и самим пакетом (кстати, здесь же лежит каталог `tests/`). setuptools генерирует **метапатч-finder**:

```
site-packages/
├── __editable__.demo_flat-0.2.0.pth            # исполняемая строка:
│                                               # import __editable___demo_flat_0_2_0_finder; ...install()
└── __editable___demo_flat_0_2_0_finder.py      # код-генерат:
                                                # MAPPING = {'demo_flat': '/…/demo-flat/demo_flat'}
                                                # class _EditableFinder:  # MetaPathFinder
                                                #     def find_spec(cls, fullname, ...): ...
```

`.pth`-строка здесь **исполняет код при старте каждого Python** (вот и живое применение «`.pth` может выполнять arbitrary code» из 11.32) — finder встраивается в `sys.meta_path` (16.3) и отдаёт spec'и по явной карте `имя_пакета → каталог`. Импорты идут мимо обычного PathFinder, ровно и без побочных путей.

Что общего у обоих случаев — и что на удивление «настоящее»:

- **dist-info пишется полностью**: `importlib.metadata.version("demo-pkg-hood")` в editable-режиме возвращает `0.1.0`, `entry_points()` видит `[project.scripts]`, а `files()` честно перечисляет `.pth` и `bin/demo-hood` — то есть **console-скрипты в editable-режиме тоже создаются** (с тем же shebang).
- **`direct_url.json`** отмечает `dir_info: {"editable": true}` — `pip list` подсвечивает такие пакеты.
- **удаление** `pip uninstall demo-pkg-hood` снимет и `.pth`, и finder, и dist-info — по RECORD.

⚠️ Границы editable: версия в метаданных **не обновится**, если вы поменяли `version = "0.2.0"` в `pyproject.toml` (переустановите `-e .`); переименование пакетов/перенос файлов finder в src-layout отследит, а в flat — по MAPPING тоже, но кэш импортов (16.1) внутри одного процесса остаётся; и помните, что editable-пакет на проде — код, которого нет в целевой системе: в Docker-образы ставьте обычные wheels.

Бэкенды различаются деталями: hatchling и flit в editable-режиме всегда пишут простой `.pth` на каталог `src/` (у них stricter-модель, генерировать finder не требуется), setuptools — как разобрано выше. Поведение заметно, когда ловят «а почему мой модуль импортируется из корня проекта» — это у вас flat-layout + простой `.pth`-инструмент: добавьте `src/`.

**Именно поэтому современный стандарт де-факто — `src/`-layout**: он исключает случайный импорт локального неоттестированного каталога в обход сборки и метаданных — и попутно удешевляет editable-установку до простой `.pth`-строки без кода-finder'а.

## 14.9. Зависимости: PEP 508 и PEP 440 { #14.9 }

Строка зависимости — маленький DSL, который парсит `packaging.requirements.Requirement` (в pip'е — вендорнутая копия):

```
celery[redis]==5.3.0; python_version >= "3.7"
└─name─┘└extra┘└specifier┘└────marker────┘
```

Все три части проверены живыми прогонами; снаружи — это то, что лежит в `dependencies` (14.3) и `Requires-Dist:` в METADATA (14.2).

**Операторы версий** (PEP 440), поведение проверено:

| Оператор | Пример | `2.31.9`? | `2.32`? | `3.0`? | Примечание |
|---|---|---|---|---|---|
| `>=2.31` | нижняя граница | ✓ | ✓ | ✓ | |
| `<3.0` | верхняя граница | ✓ | ✓ | ✗ | |
| `==2.31.0` | точное | ✗ | ✗ | ✗ | |
| `==2.31.*` | wildcard | ✓ | ✓ | ✗ | wildcard допустим ТОЛЬКО с `==` |
| `!=2.32.*` | исключение | ✓ | ✗ | ✓ | `!=1.5*` без точки — InvalidSpecifier |
| `~=2.31` | «совместимая»: `>=2.31, ==2.*` | ✓ | ✓ | ✗ | `~=2.31.4` — уже `>=2.31.4, ==2.31.*` |
| `===1.0` | arbitrary equality | только `1.0` | | | строковое сравнение, для экзотики |

Версия — тоже не строка, а структурированный объект: `Version("1.1rc1.post2.dev3+local")` разбирается на `release=(1, 1)`, `pre=('rc', 1)`, `post=2`, `dev=3`, `local='local'`; `public` отсекает `+local`, `base_version` — ещё и `pre/post/dev`. Сортировка определена спецификацией (проверено):

```
1.0 < 1.0.1 < 1.1a1 < 1.1b2 < 1.1rc1 < 1.1 < 2.0.post1 < 2023.10.15
```

Заметьте: `1.1rc1 < 1.1` (пре-релизы идут **до** релиза), `1.0 == 1.0.0`, а CalVer (`2023.10.15`) — просто большой номер релиза.

**Пре-релизы pip по умолчанию не ставит** — но правило точнее, чем кажется: кандидат-пре-релиз рассматривается, если это единственный вариант, вы попросили `--pre`, или ваш собственный specifier сам называет пре-релиз: `Specifier(">=2.0rc1").prereleases == True` (проверено) — с такой границей pip спокойно поставит `2.0rc2`.

**Маркеры** (PEP 508) вычисляются на машине пользователя и решают, относится ли зависимость к окружению вообще:

```python
from packaging.markers import Marker
from packaging.requirements import Requirement

Marker('sys_platform == "win32"').evaluate()         # False на Linux
Marker('sys_platform == "win32"').evaluate({"sys_platform": "win32"})   # True
Marker('python_version >= "3.11"').evaluate()        # True на 3.12
Marker('extra == "dev"').evaluate()                  # False — extra активен только при [dev]
Requirement('pywin32==306; sys_platform == "win32"').marker.evaluate()  # False
```

Отсюда разделение труда: `pyproject.toml` — декларация (диапазоны, маркеры, extras), `requirements.txt` — снимок окружения (по традиции жёстко закреплённые `==` версии; хеши — для репродьюсибл-установки, см. 11.32). Между ними стоит **lock-файл**: `pip freeze > requirements.txt`, `pip-tools` (`pip-compile`: резолвит и фиксирует весь транзитивный граф), `uv lock` (быстрый резолвер + `uv.lock`). Все решают одну задачу — детерминированная установка того, что декларативно задано диапазонами.

⚠️ `python_version` в маркере — `major.minor` (`3.12`), а `python_full_version` — с патчем (`3.12.14`). Разница видна на equality-маркерах: `python_version == "3.9"` истинно для **любого** 3.9.x, а `python_full_version == "3.9"` — ложно для всех, кроме гипотетического релиза `3.9.0` без патча (PEP 440 такое не выпускает, но маркер его требует буквально). Для диапазонов `python_version < "3.10"` и `python_full_version < "3.10"` ведут себя одинаково (обе отсекают 3.10+ на любом патче), разница возникает только на `==`/`!=`. Учитывайте, что именно вы фиксируете.

## 14.10. entry points: console-скрипты и плагины { #14.10 }

`entry_points.txt` внутри dist-info — INI-секции с парами «имя = модуль:объект»:

```ini
[console_scripts]
demo-hood = demo_hood.cli:main

[demo_hood.plugins]
hello = demo_hood.cli:hello
```

Секция `console_scripts` обрабатывается pip'ом при установке особым образом: для каждой записи пишется исполняемый файл в `bin/` (код обёртки — в 14.7). Функция **не импортируется до запуска команды** — обёртка делает `from demo_hood.cli import main` в момент вызова. Поэтому `pip install` быстрый, а первая команда ещё платит за импорт пакета (16.11 покажет его цену через `-X importtime`).

Все остальные группы — универсальный **реестр плагинов**: любое приложение может объявить группу и в рантайме найти её в установленных пакетах:

```python
import importlib.metadata as im

im.entry_points(group="console_scripts")          # все консольные команды окружения
im.entry_points(group="console_scripts", name="pip")
# [EntryPoints(name='pip', value='pip._internal.cli.main:main', group='console_scripts')]
ep = im.entry_points(group="console_scripts", name="pip")[0]
ep.load()          # <function main at ...> — РЕАЛЬНЫЙ импорт цели

im.entry_points(group="demo_hood.plugins")   # наша группа из 14.3
# pytest ищет group='pytest11', ruff/flake8 — свои; ровно так строятся плагин-системы
```

`ep.load()` — это `importlib.import_module` по части до `:` плюс `getattr`. Отсюда практическое следствие: плагин, сломанный при импорте, роняет не установку, а **первый вызов `load()`** у приложения — на которые у зрелых фреймворков стоят try/except с предупреждением.

Цена вопроса измерена (бенчмарки B4): скан всех dist-info окружения занимает ~15 мс на 430 каталогах — поэтому зрелые приложения (pytest) кэшируют результат поиска плагинов на процесс, а горячие пути (каждый запрос, каждый вызов) не опрашивают entry points в принципе. Точечный запрос `im.version()` — ~0.3 мс: чтение одного маленького файла.

| Группа | Кто объявляет | Кто читает |
|---|---|---|
| `console_scripts` | `[project.scripts]` | pip (генерирует bin) |
| `pytest11` | плагины pytest | pytest при старте |
| `distutils.commands` | доп. команды сборки | setuptools |
| любая своя | `[project.entry-points."x.y"]` | ваш код через `entry_points(group="x.y")` |

## 14.11. Публикация: PyPI, twine и альтернативные формы { #14.11 }

Канонический путь на индекс:

```bash
pip install build twine
python -m build                         # dist/demo_pkg_hood-0.1.0.tar.gz + .whl
twine check dist/*                      # валидация метаданных (README-разметка и пр.)
twine upload --repository testpypi dist/*   # репетиция на test.pypi.org
twine upload dist/*                     # публикация
```

Аутентификация за последние годы сменила модель: API-токены с ограниченным скоупом вытеснили пароли, а **trusted publishing** (OIDC) убрал токены вовсе — CI-работа GitHub Actions публикует по короткоживущей подписи идентичности репозитория, никакие секреты не хранятся. Загруженные файлы **неизменяемы**: перезалить ту же версию нельзя — только выложить новую или **yank**нуть (открепить от новых резолвов, не удаляя: сломанный релиз перестаёт отдаваться свежим установкам, но старые `==`-пины продолжают работать).

Дистрибуция не всегда «в PyPI и только там»:

| Форма | Инструмент | Когда |
|---|---|---|
| Приватный индекс | `PIP_INDEX_URL`, devpi, Artifactory | корпоративные пакеты, закрытые зависимости |
| Каталог wheels без индекса | `pip install --no-index --find-links wheels/` | офлайн-инсталляции, air-gapped |
| Исполняемый zip | `python -m zipapp` → `.pyz` | скрипт-приложение одним файлом |
| Замороженный бинарник | PyInstaller, Nuitka | пользователям без Python |
| Контейнер | Docker + обычный pip install | сервисы |

`zipapp` — самый недооценённый: папка с кодом + `__main__.py` превращается в один `.pyz`, который запускается напрямую (исполняемый zip — это тот же механизм zipimport из 16.9, смонтированный на сам файл):

```bash
$ mkdir myapp/libdir
$ cat > myapp/libdir/tool.py <<'EOF'
name = 'tool-v1'
def run():
    print('pyz run:', name)
EOF
$ echo "from libdir import tool
print('pyz (A, __main__.py):', tool.name)" > myapp/__main__.py

$ python3 -m zipapp myapp -o myappA.pyz -p "/usr/bin/env python3"
$ ./myappA.pyz
pyz (A, __main__.py): tool-v1

# вариант Б: точка входа флагом -m вместо __main__.py
$ rm myapp/__main__.py
$ python3 -m zipapp myapp -o myappB.pyz -m libdir.tool:run -p "/usr/bin/env python3"
$ ./myappB.pyz
pyz run: tool-v1
```

Внутри `.pyz` — обычный zip с шебангом первой строкой; `-m` сгенерировал `__main__.py` из `модуль:функция`. Оба варианта взаимоисключающие — zipapp откажется: `ZipAppError: Cannot specify entry point if the source has __main__.py` (проверено). Зависимости можно вшить внутрь каталога (`pip install --target myapp/ requests`) — и `.pyz` станет самодостаточным, без venv.

⚠️ `.pyz` — не безопасность, а удобство: код читается как zip, подписи у него нет, «вирусный вектор» он ничем не лучше скрипта. Для распространения среди «своих» — идеально; в публичный доступ — только wheel.

PEP 723 (2024) — «inline script metadata»: шапка вида `# /// script` прямо в одном `.py`-файле, по которой `uv run`/`pipx` поднимают окружение с зависимостями. Тот же PEP 508-синтаксис, но носитель — сам скрипт. Идейно это zipapp наоборот: не «приложение без зависимостей», а «скрипт со своими».

### Бенчмарки к Части XIV { #14.11-benchmarki }

Машина: 2 ядра, CPython 3.12.14, pip 25.0.1, uv 0.12.15. Один и тот же пакет `requests` (2.34.2) у обоих инструментов; тёплый кэш у каждого своего.

**B1. Установка `requests` + 4 зависимостей, тёплый кэш:**

| Инструмент | Время | × |
|---|---:|---:|
| `pip install requests --target …` | 1.53 с | 1.0× |
| `uv pip install requests --target …` | 0.02 с | 67.5× |

Разрыв — не «питон медленный», а архитектура: uv (Rust) держит глобальный кэш распакованных wheels и связывает файлы в целевое окружение hardlink'ами — ни распаковки, ни компиляции pyc (uv, в отличие от pip, не компилирует байт-код по умолчанию); pip каждый раз распаковывает и компилирует. Для CI и Docker-слоёв перевод на uv — самые дешёвые минуты в жизни проекта.

**B2. Создание окружения:**

| Инструмент | Время |
|---|---:|
| `python3 -m venv .venv` | 2.11 с |
| `uv venv .venv` | 0.06 с (~35×) |

`python -m venv` грузит pip внутрь (ensurepip); uv venv создаёт только каталоги и симлинк на интерпретатор — pip туда приносит сами инструменты (`uv pip install`).

**B3. Сборка wheel демо-проекта** (`pip wheel . --no-build-isolation`, setuptools 82): 1.72 с. В изоляции добавляется скачивание setuptools в окружение сборки — на холодном кэше +2–4 с. Это цена, которую платит каждый пользователь, ставящий sdist без wheel'а: вот почему авторам стоит выкладывать wheels (14.5).

**B4. `importlib.metadata`:**

| Операция | Время |
|---|---:|
| `im.version("aiohttp")` | 299 мкс |
| `im.metadata("aiohttp")` | 299 мкс |
| `im.entry_points(group="console_scripts")` — скан 430 dist-info | 13.3 мс |

Вывод для плагинных систем: точечный запрос — микро-цена, полный скан — миллисекунды; кэшируйте `entry_points()` на процесс и не дёргайте его в горячих путях (14.10).

**B5. Бюрократия конвейера** (то же демо, те же прогоны): `pip install` из готового wheel — доли секунды, из sdist — секунды на сборку (B3). Резолвер и скачивание доминируют на малых пакетах; на больших (numpy/scipy) разница wheel/sdist — уже минуты и компилятор.

