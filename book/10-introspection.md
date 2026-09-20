# Часть X. Интроспекция окружения

Эта часть — про то, как узнать, **как именно** запущен интерпретатор и что происходит в процессе: `sys.flags` и `sys._xoptions` (10.1–10.2), `PYTHON*`-переменные (10.3), лимиты ресурсов и `/proc` (10.5–10.6), audit hooks (10.7) и faulthandler (10.8). Отсюда же растут CLI-темы 11.31 и диагностические режимы Части XV.

## 10.1. `sys.flags` — флаги командной строки Python { #10.1 }

`sys.flags` — именованный кортеж с полным набором флагов `python`. Самый точный способ узнать, **как именно Python был запущен**:

```python
import sys
print(sys.flags)
# sys.flags(debug=0, inspect=0, interactive=0, optimize=0,
#   dont_write_bytecode=1, no_user_site=0, no_site=0, ignore_environment=0,
#   verbose=0, bytes_warning=0, quiet=0, hash_randomization=1,
#   isolated=0, dev_mode=False, utf8_mode=0, warn_default_encoding=0,
#   safe_path=False, int_max_str_digits=4300)
```

Полная таблица флагов:

| Поле `sys.flags` | Флаг CLI | Что значит |
|------------------|---------|-----------|
| `optimize` | `-O`, `-OO` | 0/1/2. При 1+ — `__debug__ = False`, `assert` удалён из байт-кода. |
| `dont_write_bytecode` | `-B` | Не писать `.pyc` файлы. |
| `no_user_site` | `-s` | Не добавлять `~/.local/lib/pythonX.Y/site-packages` в путь. |
| `no_site` | `-S` | Не импортировать `site` при запуске. |
| `ignore_environment` | `-E` | Игнорировать переменные окружения `PYTHON*`. |
| `isolated` | `-I` | `-E + -s + no user site`. Максимальная изоляция. |
| `verbose` | `-v` | Подробный лог импорта каждого модуля в stderr. |
| `debug` | `-d` | Отладочный вывод парсера. С PEG-парсером (3.9+) практически ничего не печатает — legacy-поле. |
| `inspect` / `interactive` | `-i` | Оба поля взводятся флагом `-i`: интерактивная сессия после выполнения скрипта/stdin (проверено: даже когда stdin — пайп). |
| `quiet` | `-q` | REPL без баннера (версия/копирайт). |
| `bytes_warning` | `-b`, `-bb` | Предупреждение/ошибка при сравнении `bytes` и `str`. |
| `hash_randomization` | `-R` | Рандомизация `PYTHONHASHSEED`. По умолчанию 1. |
| `dev_mode` | `-X dev` | Python Development Mode. |
| `utf8_mode` | `-X utf8` | UTF-8 Mode (PEP 540). |
| `safe_path` | `-P` | Не добавлять `sys.path[0]` — каталог скрипта (Python 3.11+). |
| `int_max_str_digits` | `-X int_max_str_digits` | Лимит на длину строки при `int(str)` (Python 3.11+). |

Слить в stderr/stdout:

```python
import sys, json
flags_dict = {k: getattr(sys.flags, k) for k in dir(sys.flags) if not k.startswith('_')}
# ⚠️ dir() содержит методы count/index — без default=str json.dumps упадёт
# с TypeError: Object of type builtin_function_or_method is not JSON serializable
raise RuntimeError(f"FLAGS_DUMP: {json.dumps(flags_dict, default=str)}")
```

## 10.2. `sys._xoptions` — `-X` опции { #10.2 }

Некоторые флаги не имеют поля в `sys.flags` — они передаются через `-X` (расширенные опции), доступны в `sys._xoptions` (словарь):

```python
import sys
print(sys._xoptions)
# {} если ничего не передано
# {'dev': True} при python -X dev
# {'faulthandler': True} при python -X faulthandler
# {'importtime': True} при python -X importtime
# {'utf8': '1'} при python -X utf8=1 (значения строковые; флаг без = → True)
# {'tracemalloc': '10'} при python -X tracemalloc=10
# {'frozen_modules': 'off'} при python -X frozen_modules=off
```

Известные `-X` опции (CPython 3.12+):

- `-X dev` — Development Mode
- `-X faulthandler` — включить `faulthandler` сразу при старте
- `-X importtime` — логировать время каждого импорта в stderr
- `-X tracemalloc=N` — включить tracemalloc с лимитом N кадров
- `-X int_max_str_digits=N` — лимит на длину int-строки
- `-X utf8` / `-X utf8=1` — UTF-8 Mode
- `-X frozen_modules=on/off` — использовать ли замороженные модули
- `-X pycache_prefix=PATH` — альтернативный корень `__pycache__` (эквивалент `PYTHONPYCACHEPREFIX`)
- `-X no_debug_ranges` — вырезать точные позиции (колонки/концы) из traceback — короче сообщения (эквивалент `PYTHONNODEBUGRANGES`)
- `-X warn_default_encoding` — `EncodingWarning` на каждый `open()` без явного `encoding` (PEP 597, эквивалент `PYTHONWARNDEFAULTENCODING`)
- `-X perf` — поддержка Linux perf-профайлера (3.12+, `PYTHONPERFSUPPORT`)
- `-X perf_jit` — то же + DWARF-аннотации, чтобы perf показывал Python-вызовы через JIT (3.13+, `PYTHON_PERF_JIT_SUPPORT`)
- `-X importtime=2` — дополнительно помечать уже загруженные модули словом `cached` в логе импортов (3.13+)
- `-X cpu_count=N` — подменить `os.cpu_count()` / `os.process_cpu_count()` / `multiprocessing.cpu_count()` (3.13+, эквивалент `PYTHON_CPU_COUNT`)
- `-X gil=0/1` — принудительно включить/выключить GIL в free-threaded сборках (3.13+; env `PYTHON_GIL`)
- `-X presite=package.module` — импортировать модуль до `site` и до появления `__main__` (3.13+, env `PYTHON_PRESITE`)
- `-X showrefcount` — печатать суммарный refcount и число блоков памяти при выходе; только debug-сборки (`--with-pydebug`)
- `-X disable_remote_debug` — выключить remote-отладку PEP 768 (подключение кода к работающему процессу) (3.14+, env `PYTHON_DISABLE_REMOTE_DEBUG`)
- 3.14+: `-X thread_inherit_context=0/1`, `-X context_aware_warnings=0/1`, `-X tlbc=0/1` — наследование contextvars в потоках, предупреждения с учётом контекста, счётчики tier-2 байт-кода (экспериментальные)
- историческое: `-X showalloccount` удалена в 3.9, `-X oldparser` — в 3.10 (сейчас просто игнорируются)
- неизвестные `-X` игнорируются молча (`-X path` не существует — просто попадёт в `sys._xoptions`)

## 10.3. `os.environ` и `PYTHON*` переменные { #10.3 }

⚠️ **Переменные `PYTHON*` читаются ТОЛЬКО при старте CPython.** Изменение `os.environ['PYTHONUNBUFFERED'] = '1'` внутри работающего скрипта **не повлияет на текущий процесс** — только на дочерние процессы (запущенные через `subprocess`). Все `PYTHON*` должны быть выставлены **до** запуска `python`.

Многие аспекты поведения CPython настраиваются через переменные окружения, начинающиеся с `PYTHON*`:

```python
import os
interesting = {k: v for k, v in os.environ.items()
               if k.startswith('PYTHON') or k.startswith('UV_') or k in ('VIRTUAL_ENV',)}
print(interesting)
# {
#   'PYTHONUNBUFFERED': '1',         # буферизация вывода выключена
#   'PYTHONDONTWRITEBYTECODE': '1',  # эквивалент флага -B
#   'PYTHONHASHSEED': '0',           # детерминированный hash()
#   'PYTHONPATH': '/srv/libs',
#   'PYTHONSTARTUP': '/home/user/.pythonrc',
#   'PYTHONBREAKPOINT': 'IPython.terminal.debugger.set_trace',
#   'PYTHONOPTIMIZE': '1',           # эквивалент флага -O
#   'PYTHONFAULTHANDLER': '1',        # включить faulthandler при старте
#   'PYTHONTRACEMALLOC': '10',       # включить tracemalloc с 10 кадрами
#   'PYTHONMALLOC': 'debug',         # настройки аллокатора
#   'PYTHONWARNINGS': 'ignore::DeprecationWarning',
#   'PYTHONIOENCODING': 'utf-8',
#   'PYTHONNODEBUGRANGES': '1',      # отключить debug ranges в traceback
#   'UV_PYTHON': '3.12',
#   'VIRTUAL_ENV': '/srv/venv',
# }
```

Основные переменные (полный список — [Python docs → Command line and environment](https://docs.python.org/3/using/cmdline.html#environment-variables)):

- `PYTHONHOME` — альтернативный каталог установки Python.
- `PYTHONPATH` — дополнительные пути для `sys.path`.
- `PYTHONSTARTUP` — файл, исполняемый перед REPL.
- `PYTHONINSPECT` — эквивалент флага `-i`.
- `PYTHONBREAKPOINT` — переопределяет `breakpoint()`.
- `PYTHONDEBUG` — эквивалент `-d`.
- `PYTHONOPTIMIZE` — эквивалент `-O`. Если установлена, `__debug__ = False`.
- `PYTHONUNBUFFERED` — эквивалент `-u`.
- `PYTHONFAULTHANDLER` — включает `faulthandler` при старте.
- `PYTHONTRACEMALLOC` — включает tracemalloc.
- `PYTHONMALLOC` — настройки аллокатора.
- `PYTHONDONTWRITEBYTECODE` — эквивалент `-B`.
- `PYTHONWARNINGS` — список предупреждений.
- `PYTHONHASHSEED` — seed для `hash()`.
- `PYTHONIOENCODING` — кодировка stdin/stdout/stderr.
- `PYTHONNODEBUGRANGES` — отключить отладочную инфу в Traceback.
- `PYTHONCOERCECLOCALE` — для UNIX локалей.
- `PYTHONUTF8` — эквивалент `-X utf8`.
- `PYTHONSAFEPATH` — эквивалент `-P` (не добавлять каталог скрипта в sys.path).
- `PYTHONPYCACHEPREFIX` — альтернативный корень для `__pycache__`.
- `PYTHONINTMAXSTRDIGITS` — лимит int↔str (эквивалент `-X int_max_str_digits`).
- `PYTHON_GIL` — 0/1 для free-threaded сборок (3.13+).
- `PYTHONPLATLIBDIR` — имя каталога платформенных библиотек.
- `PYTHONPROFILEIMPORTTIME` — эквивалент `-X importtime`.
- `PYTHONDEVMODE` — эквивалент `-X dev` (Development Mode).
- `PYTHON_FROZEN_MODULES` — эквивалент `-X frozen_modules=on/off`.
- `PYTHONMALLOCSTATS` — печатать статистику pymalloc в stderr при выходе (работает в паре с `PYTHONMALLOC`).
- `PYTHONWARNDEFAULTENCODING` — эквивалент `-X warn_default_encoding`: `EncodingWarning` на `open()` без явного `encoding` (PEP 597; см. 9.1).
- `PYTHONUSERBASE` — база user-site вместо `~/.local` (см. 11.10).
- `PYTHONPERFSUPPORT` / `PYTHON_PERF_JIT_SUPPORT` — эквиваленты `-X perf` / `-X perf_jit` (профилирование Linux perf).
- `PYTHONCASEOK` — только Windows: импортировать модули без учёта регистра имени файла (на POSIX регистр всегда значим).
- `PYTHONEXECUTABLE` — только macOS/framework-сборки: подменить значение `sys.executable` при старте.
- `PYTHONLEGACYWINDOWSFSENCODING` / `PYTHONLEGACYWINDOWSSTDIO` — вернуть legacy-кодировки Windows: mbcs для ФС и старый консольный I/O вместо UTF-8 (до 3.6 было так).
- `PYTHONDUMPREFS` / `PYTHONDUMPREFSFILE` — при выходе выгрузить все живые объекты с refcount (в stderr или файл); только debug-сборки (`--with-pydebug`).

**Только 3.13+/3.14+** (проверяйте `whatsnew` своего релиза):

- `PYTHON_CPU_COUNT` — эквивалент `-X cpu_count=N`: подмена `os.cpu_count()`.
- `PYTHON_HISTORY` — путь к файлу истории REPL (по умолчанию `~/.python_history`).
- `PYTHON_COLORS` — управление цветами сообщений/трейсбеков (авто/always/never).
- `PYTHON_BASIC_REPL` — `1` возвращает до-3.13 REPL без `_pyrepl` (см. 14.4).
- `PYTHON_PRESITE` — эквивалент `-X presite=package.module`.
- `PYTHON_JIT` — 0/1 для экспериментального JIT (работает только если интерпретатор собран с `--enable-experimental-jit`).
- `PYTHON_TLBC` — счётчики tier-2 байт-кода (микро-телеметрия специализированных инструкций, 3.14+).
- `PYTHON_THREAD_INHERIT_CONTEXT` — наследование `contextvars` в потоках (3.14+).
- `PYTHON_CONTEXT_AWARE_WARNINGS` — предупреждения с учётом contextvar-контекста (3.14+).
- `PYTHON_DISABLE_REMOTE_DEBUG` — эквивалент `-X disable_remote_debug` (PEP 768, 3.14+).

⚠️ **Все `PYTHON*` переменные игнорируются** при флаге `-E` или `-I`.

## 10.4. `sys.implementation`, `platform.*` { #10.4 }

```python
import sys, platform, os

# Реализация интерпретатора
print(sys.implementation.name)        # 'cpython', 'pypy', 'graalpy', 'ironpython'
print(sys.implementation.version)     # sys.version_info для этой реализации
print(sys.implementation.hexversion)  # версия в hex

# Платформа
print(platform.python_implementation())  # 'CPython', 'PyPy', 'GraalPy'
print(platform.python_compiler())        # 'Clang 22.1.3' или 'GCC 13.2.0'
print(platform.python_branch())          # Git branch (если есть)
print(platform.python_revision())        # Git revision
print(platform.system())                 # 'Linux', 'Windows', 'Darwin'
print(platform.machine())                # 'x86_64', 'arm64', 'aarch64'
print(platform.processor())              # часто пустая строка на Linux
print(platform.release())                # '6.5.0-44-generic'
print(platform.version())                # полная версия ОС

# Процесс
print(os.getpid())        # PID этого процесса
print(os.getppid())       # PID родителя — ключевой маркер сэндбокса!
print(os.getcwd())        # рабочий каталог
print(os.getuid(), os.getgid())  # Unix only

# Хост
import socket
print(socket.gethostname())   # имя хоста
print(socket.getfqdn())        # полное доменное имя
```

Если `os.getppid()` возвращает 1 — скорее всего, процесс запущен в Docker-контейнере (init PID=1). Если `os.getuid()` возвращает 0 — мы root (песочница слабая или её нет).

## 10.5. `resource.getrlimit` — лимиты ресурсов { #10.5 }

⚠️ **Модуль `resource` доступен только на POSIX/Unix (Linux, macOS).** На Windows — `ModuleNotFoundError`. Кроссплатформенный код: `try: import resource except ModuleNotFoundError: ...`.

⚠️ **`ru_maxrss` возвращает KB на Linux, но байты на macOS** — при кроссплатформенном переводе в MB:
```python
import resource, sys
usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform == "darwin":
    max_rss_mb = usage / (1024 * 1024)  # macOS: байты → MB
else:
    max_rss_mb = usage / 1024            # Linux: KB → MB
```

```python
import resource, sys, shutil

# Unix: soft/hard лимиты на ресурсы
print(resource.getrlimit(resource.RLIMIT_CPU))      # CPU time в секундах
print(resource.getrlimit(resource.RLIMIT_FSIZE))     # максимальный размер файла
print(resource.getrlimit(resource.RLIMIT_DATA))     # максимальный размер data
print(resource.getrlimit(resource.RLIMIT_AS))       # максимальный размер адресного пространства
print(resource.getrlimit(resource.RLIMIT_NPROC))    # максимальное число процессов
print(resource.getrlimit(resource.RLIMIT_NOFILE))   # максимальное число открытых файлов
print(resource.getrlimit(resource.RLIMIT_STACK))    # размер стека

# Внутренние лимиты Python
print(sys.getrecursionlimit())  # обычно 1000

# Свободное место на диске
print(shutil.disk_usage('/'))   # usage(total=..., used=..., free=...)
print(shutil.disk_usage('/tmp')) # для временных файлов

# Куда можно писать
import tempfile
print(tempfile.gettempdir())     # обычно /tmp
print(tempfile.gettempprefix())  # обычно 'tmp'
```

Если `RLIMIT_CPU` выставлен в 1 секунду — это песочница. Если `RLIMIT_AS` в 64 МБ — это классическая строгая сэндбокс-конфигурация для учебных тестирующих систем.

## 10.6. `/proc/self/` — Linux-специфичная разведка { #10.6 }

На Linux `/proc/self/` — это «магический» каталог, показывающий состояние текущего процесса:

```python
import os

# Кто нас запустил
with open('/proc/self/cmdline', 'rb') as f:
    cmdline = f.read().replace(b'\x00', b' ').decode()
print(f"CMDLINE: {cmdline}")

# Какой cwd
print(os.readlink('/proc/self/cwd'))

# Какие fd открыты (можно найти открытые файлы)
print(os.listdir('/proc/self/fd'))

# Куда смотрят std{in,out,err}
for fd in ('0', '1', '2'):
    print(f"fd {fd} →", os.readlink(f'/proc/self/fd/{fd}'))

# Состояние памяти
with open('/proc/self/status') as f:
    print(f.read())

# Окружение (полный словарь, без фильтрации)
with open('/proc/self/environ', 'rb') as f:
    env = f.read().replace(b'\x00', b'\n').decode()
print(env)

# Это Docker-контейнер?
try:
    with open('/proc/1/cgroup') as f:
        cgroup = f.read()
    if 'docker' in cgroup or 'containerd' in cgroup or 'kubepods' in cgroup:
        print("DOCKER/K8s СЭНДБОКС")
    else:
        print("host система")
except FileNotFoundError:
    pass

# Что в корне (часто бывает .dockerenv)
print(os.path.exists('/.dockerenv'))  # True для Docker
```

`/proc/self/environ` часто **полезнее**, чем `os.environ` — даёт вообще всё окружение, не отфильтрованное.

## 10.7. Audit hooks (PEP 578, Python 3.8+) { #10.7 }

`sys.addaudithook(hook)` ставит **глобальный перехватчик** для всех «интересных» событий: `import`, `exec` (порождается и `exec()`, и `eval()`), `open`, `socket.*`, `subprocess.Popen`, `compile`, `code.__new__`, и т.д. Полный список событий в [PEP 578](https://peps.python.org/pep-0578/).

```python
import sys

def my_hook(event, args):
    if event.startswith('import.') or event in ('exec', 'compile', 'open'):
        import sys as _s
        _s.stderr.write(f"AUDIT {event}: {args}\n")

sys.addaudithook(my_hook)

# Дальше все импорты, exec, open — будут залогированы
import json
exec('x = 1')
open('/tmp/x', 'w').close()
```

**Применение в разведке**: можно за одну попытку сдачи кода собрать полный лог того, что тестирующая система делает с вашим файлом — какие модули импортирует, какие файлы открывает, какие сокеты создаёт. Часто видно, что после `import solution` система пытается открыть базу эталонов, читать ответы, и т.д.

⚠️ Audit hooks **нельзя удалить** — `sys.addaudithook` односторонний. Любая установка нового хука сама порождает событие `sys.addaudithook`, которое видят уже установленные хуки: «дополнить наблюдателя» скрытно не получится.

Систематическая картина: какие события бывают, как из хука не только наблюдать, но и **блокировать**, и сколько это стоит.

**Основные события** (полный и актуальный список — в [PEP 578](https://peps.python.org/pep-0578/) и `sys.audit`-документации CPython):

| Событие | Когда срабатывает | args |
|---|---|---|
| `exec` | `exec(obj)` / `eval(obj)` | `(code_object,)` |
| `compile` | `compile(source, filename, ...)` | `(source, filename)` — по PEP 578, без mode |
| `import` | каждый оператор import | `(module, filename, sys.path, sys.meta_path, sys.path_hooks)` |
| `open` | `open(path, ...)` | `(path, mode, flags)` |
| `socket.connect` | исходящее соединение | `(socket, address)` |
| `socket.getaddrinfo` | DNS-резолв | `(host, port, family, type, protocol)` |
| `subprocess.Popen` | запуск дочернего процесса | `(executable, args, cwd, env)` |
| `os.system` | shell-команда | `(command,)` |
| `os.remove` / `os.rename` | удаление/переименование | `(path, dir_fd)` / `(src, dst, ...)` |
| `sys._getframe` | доступ к чужим фреймам | `(depth,)` |
| `pickle.load` | десериализация | `(file,)` |
| `sys.addaudithook` | установка нового хука | `(hook,)` |

Для задач из 10.7 («что делает тестирующая система с моим файлом») самый частотный набор — `open`, `import`, `exec`, `compile`, `socket.*`, `subprocess.Popen`.

**Обработчик «мониторинг + блокировка».** Исключение, поднятое из хука, распространяется **в место вызова аудируемой операции** и срабатывает до её выполнения — так хук превращается из журнала в запретитель:

```python
import sys, os

BLOCKED = {"os.system", "subprocess.Popen", "socket.connect"}
SUSPICIOUS = ("/etc/", "answers", "etalon", "tests/")

def guard(event, args):
    # 1) мониторинг: всё интересное — в лог
    if event in ("open", "exec", "compile", "import"):
        sys.stderr.write(f"[audit] {event}: {args!r}\n")
    # 2) блокировка: raise = отказ операции в месте вызова
    if event in BLOCKED:
        raise RuntimeError(f"операция запрещена политикой: {event}")
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = args[0] if isinstance(args[0], str) else args[0].decode(errors="replace")
        if any(s in path for s in SUSPICIOUS):
            raise PermissionError(f"доступ к {path!r} запрещён")

sys.addaudithook(guard)

os.system("ls")            # RuntimeError: операция запрещена политикой
open("/etc/passwd")        # PermissionError: доступ к '/etc/passwd' запрещён
```

Это ровно тот механизм, которым тестирующая система может защищать базу эталонов: хук ставится до загрузки решения, всё `open` мимо белого списка — с отказом. Обратная сторона: `try/except` вокруг операции **глотает** отказ хука, а сам хук ничего не знает о том, что его исключение поймали. Блокировка — не sandbox, а жёсткое правило с обходом через исключения.

**Замер накладных расходов.** Каждое событие — это построение кортежа args и вызов python-функции. Пустой хук на все события, замер на 200 000 `open('/dev/null', 'rb')` (CPython 3.12):

```bash
python bench.py            # без хуков:  2.72 мкс/вызов
python bench.py --hook     # с пустым хуком: 2.88 мкс/вызов  → +6%
```

На syscall-доминированной операции накладные почти незаметны; проигрывают операции, где событие частое, а сама операция дешёвая (импорт десятков модулей, чтение мелких файлов). Для «разведки на одной попытке» это несущественно; для продакшн-профайлинга — учитывать.

**Чего audit hooks не дают.** В тексте PEP 578 прямым текстом: хуки — **не** механизм безопасности и не песочница. Три дыры, о которых стоит помнить:

- события порождает **CPython API**: вызов `ctypes.CDLL("libc.so.6").open(...)` идёт мимо события `open`;
- код на других языках расширения (C-модули) порождает события только там, где автор модуля вызвал `PySys_Audit()`;
- хук работает в том же интерпретаторе, что и наблюдаемый код — у рантайма, скомпрометированного раньше установки хука, нет гарантий.

Для «поймать подозрительные вызовы в своём процессе» и «залогировать, что делает чужой модуль» — правильный инструмент. Для изоляции враждебного кода — нет: это задача ОС-уровня (контейнеры, seccomp).

→ **см. также:** 10.6 — `/proc/self/` как источник того же знания без хуков; Приложение B — как выглядит «оборона» тестирующей системы со стороны.

## 10.8. Faulthandler — дамп стеков { #10.8 }

```python
import faulthandler

# Включить — при SIGSEGV/SIGABRT/SIGFPE автоматически дампит стеки всех тредов
faulthandler.enable()

# Дампнуть стеки всех тредов вручную (например, в stderr)
faulthandler.dump_traceback()

# Дампнуть в файл
with open('/tmp/traceback.txt', 'w') as f:
    faulthandler.dump_traceback(file=f)

# Если есть долгий цикл — можно включить периодический dump
faulthandler.dump_traceback_later(timeout=5)  # один раз через 5 сек (для периодики — repeat=True)
```

В тестирующей системе с таймаутами (Task timed out) `dump_traceback_later` выведет в stderr стек всех тредов — видно, на чём зависла программа.

## 10.9. Универсальный «комбайн» для одной попытки { #10.9 }

Если есть только одна попытка, можно слить максимум инфы в stderr/stdout через один `raise`:

```python
# flake8: noqa
# ruff: noqa
import sys, os, platform, socket, json, traceback

info = {
    'sys_version': sys.version,
    'sys_flags': {k: getattr(sys.flags, k) for k in dir(sys.flags) if not k.startswith('_')},
    'sys_xoptions': dict(sys._xoptions),
    'implementation': sys.implementation.name,
    'platform': platform.platform(),
    'pid': os.getpid(),
    'ppid': os.getppid(),
    'cwd': os.getcwd(),
    'hostname': socket.gethostname(),
    'environ_PYTHON': {k: v for k, v in os.environ.items() if k.startswith('PYTHON')},
}

# Linux-only:
try:
    with open('/proc/self/cmdline', 'rb') as f:
        info['cmdline'] = f.read().replace(b'\x00', b' ').decode()
    with open('/proc/1/cgroup') as f:
        info['cgroup'] = f.read()[:500]
    info['dockerenv'] = os.path.exists('/.dockerenv')
except Exception:
    pass

# Поднимаем как RuntimeError — попадёт в stderr тестирующей системы
raise RuntimeError(f"RECON_DUMP: {json.dumps(info, default=str, indent=2)}")
```

В логе тестирующей системы появится JSON со всем, что удалось собрать. Это даёт максимум разведки за одну попытку.

---

### Бенчмарки к Части X { #10.9-benchmarki }

**1. `sys.flags` vs `os.environ["PYTHON..."]` — где искать флаги.**
```python
import sys, os, timeit
# sys.flags — именованный кортеж, доступ O(1)
print(timeit.timeit(lambda: sys.flags.optimize, number=1_000_000))   # ≈ 0.07 с (зависит от CPU)
# os.environ['PYTHONOPTIMIZE'] — словарный lookup + str compare
print(timeit.timeit(lambda: os.environ.get("PYTHONOPTIMIZE"), number=1_000_000))  # ≈ 0.71 с
```
`sys.flags` **в ~10× быстрее** и даёт уже распарсенные int/bool, а не строки.
Но `os.environ` содержит **больше** информации (произвольные `PYTHON*` переменные),
а `sys.flags` — только флаги командной строки `python`.

**2. Audit hooks (PEP 578) — цена перехвата всех событий.**
```python
import sys, timeit
# Без hook'а
def no_hook():
    for _ in range(100_000): exec("1+1", {})
print(timeit.timeit(no_hook, number=10))   # ≈ 4.8 с (зависит от CPU; exec сам по себе дорог)
# С простым hook'ом
calls = [0]
def hook(event, args):
    calls[0] += 1
sys.addaudithook(hook)
def with_hook():
    for _ in range(100_000): exec("1+1", {})
print(timeit.timeit(with_hook, number=10))   # ≈ 5.3 с (+11% overhead от простого счётчика)
# С hook'ом, который ещё и логирует
import logging
logging.basicConfig(level=logging.INFO)
def logging_hook(event, args):
    if event.startswith("exec"):
        logging.info(f"{event}: {args}")
sys.addaudithook(logging_hook)
# Замедление ещё в 3–5× (зависит от логирования)
```
Audit hook'и добавляют **~30%** к стоимости `exec`/`import`/`open`.
На горячих путях I/O — накладные расходы минимальны (событий меньше).
Используйте их только для аудита/безопасности, не для трассировки
производительности — берите `sys.settrace` или `cProfile`.

**3. `faulthandler.dump_traceback_later` — мониторинг зависаний.**
```python
import faulthandler, time
# Запустить таймер на 5 сек, повторять каждые 1 сек
faulthandler.dump_traceback_later(timeout=5, repeat=True)
# При зависании в stderr появится стек всех потоков
# Замер накладных расходов: dump_traceback_later использует отдельный поток
# под капотом, на основной код влияет только через GIL — практически не заметно.
```
Стоимость — **<0.1% CPU** (один фоновый `threading.Timer`-цикл).
Можно держать включённым в production-процессах как страховку.

**4. `/proc/self/` разведка vs `os.*` — точность и скорость.**
```python
import os, timeit
def via_proc():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
def via_resource():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(timeit.timeit(via_proc,      number=10_000))   # ≈ 0.11 с (зависит от CPU)
print(timeit.timeit(via_resource,  number=10_000))   # ≈ 0.006 с
```
`resource.getrusage` **в ~15–20× быстрее** — один syscall, без чтения файла.
Но `/proc/self/status` даёт **текущий** RSS, а `ru_maxrss` — **пиковый** за всё
время жизни процесса. Для мониторинга утечек берите `/proc`.

**5. `sys._current_frames()` vs `threading.enumerate()`.**
```python
import sys, threading, timeit
def via_frames():
    return list(sys._current_frames().keys())
def via_threading():
    return [t.ident for t in threading.enumerate()]
print(timeit.timeit(via_frames,    number=10_000))   # ≈ 0.005 с (зависит от CPU)
print(timeit.timeit(via_threading, number=10_000))   # ≈ 0.011 с
```
`_current_frames()` **в 2× быстрее** и даёт ещё и стек каждого потока —
бесценно для отладки дедлоков в production. Но он **не возвращает** имена
потоков и `daemon`-флаг, только идентификаторы. Для аудита — `threading.enumerate`,
для отладки зависаний — `_current_frames()`.

