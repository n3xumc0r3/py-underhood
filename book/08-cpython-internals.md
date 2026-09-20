# Часть VIII. Внутренности CPython

Первый этаж internals — то, что можно потрогать из чистого Python, не заходя в C: интернация строк (8.1), кэш малых чисел (8.2), фреймы и ячейки (8.3–8.4), счётчик ссылок (8.5), сборщик мусора (8.6), `__code__` и `dis` (8.7–8.9). Почти каждая находка этой части используется дальше — от контекстных переменных (8.11) до байт-кода Части XV и импорта Части XVI.

## 8.1. Интернация строк и `sys.intern` { #8.1 }

CPython **автоматически** интернирует строки, которые выглядят как валидные идентификаторы (только латиница, цифры, `_`) — но только те, что появляются в исходном коде как литералы или формируются компилятором. **Runtime-конкатенация** (`"a" + "b"`) интернирования не делает — для неё нужно явное `sys.intern()`:

```python
a = "hello_world"   # валидный идентификатор
b = "hello_world"
print(a is b)   # True — один ID в памяти

c = "hello world"   # пробел — не валидный идентификатор
d = "hello world"
print(c is d)   # False в REPL на отдельных строках; в скрипте — True (один код-объект дедуплицирует литералы)

# А вот runtime-конкатенация — НЕ интернируется автоматически:
# ⚠️ ВАЖНО: "hello" + "_" + "world" — это НЕ рантайм-конкатенация!
# Компилятор сворачивает литералы (Constant Folding) в одну константу "hello_world",
# которая интернируется. Результат: a is e → True (не False!)
# Для честной рантайм-конкатенации нужна переменная:
prefix = "hello"
e = prefix + "_world"
print(a is e)   # False — e создан в рантайме, это новый объект
import sys
print(a is sys.intern(e))   # True — после явной интернации
```

**Принудительная интернация**:

```python
import sys

x = sys.intern("hello world 2026")
y = sys.intern("hello world 2026")
print(x is y)   # True
```

После `sys.intern` обе строки — это один и тот же объект в памяти. Сравнение через `is` (сравнение адресов) становится мгновенным вместо посимвольного.

**Применение**: для часто повторяющихся строк в больших объёмах данных — названия меток, ключи, имена. Особенно полезно в парсерах, где одна и та же строка встречается тысячи раз:

```python
import sys

def process_log(lines):
    # Без интернации: 100000 объектов "ERROR"
    # С интернацией: 1 объект "ERROR", остальные ссылки на него
    for line in lines:
        level = sys.intern(line.split()[0])
        # ...
```

⚠️ Интернированные строки **никогда** не удаляются из памяти до конца процесса — это leak. Не стоит интернировать динамически сгенерированные строки (UUID, пути).

## 8.2. Кэш малых чисел (-5..256) { #8.2 }

CPython при старте создаёт объекты для целых чисел **от -5 до 256** включительно и хранит их в единственном экземпляре:

```python
# Слитые значения из кэша:
x = 256
y = 256
print(x is y)   # True

# Вне кэша:
a = 257
b = 257
print(a is b)   # True! (скрипт: константы одного код-объекта дедуплицируются всегда)
```

⚠️ **Дедупликация констант**: если `a = 257` и `b = 257` компилируются в ОДНОМ кодовом объекте (функция, модуль или одна строка REPL), `a is b` — `True` всегда и гарантированно. `False` получите только при раздельной компиляции: две отдельные строки в REPL (`>>> a = 257`, `>>> b = 257`) или pickle-десериализация ниже.

**Проверка с разными путями создания (для гарантии разных объектов):**

```python
import pickle

a = pickle.loads(pickle.dumps(257))
b = pickle.loads(pickle.dumps(257))
print(a is b)   # False — разные объекты

a = pickle.loads(pickle.dumps(256))
b = pickle.loads(pickle.dumps(256))
print(a is b)   # True — из кэша
```

`-5` и `256` — границы кэша. Определены в исходниках CPython как `NSMALLNEGINTS = 5` и `NSMALLPOSINTS = 257` (256 + 1 для нуля). Ищите в `Objects/longobject.c` и `Include/internal/pycore_global_objects.h` (с 3.11 малые инты — глобальные immortal-объекты `_Py_small_ints`; в 3.8–3.10 жили в `pycore_interp.h`).

## 8.3. Замыкания и `__closure__`/cell objects { #8.3 }

Когда функция возвращает внутреннюю функцию, которая использует переменные внешней, CPython оборачивает эти переменные в **cell objects** — отдельные «ячейки», хранящиеся в `__closure__`:

```python
def outer_func(text):
    message = text

    def inner_func():
        print(message)

    return inner_func

my_closure = outer_func("Привет, CPython!")

# Доступ к пойманным переменным
print(my_closure.__closure__)
# (<cell at 0x...: str object at 0x...>,)

# Достаём значение из ячейки напрямую:
cell = my_closure.__closure__[0]
print(cell.cell_contents)   # "Привет, CPython!"
```

Переменные не удаляются сборщиком мусора после завершения `outer_func`, потому что на них держит ссылку скомпилированный байт-код `inner_func`.

**Подмена содержимого ячейки** (позволяет модифицировать пойманные переменные снаружи):

```python
my_closure.__closure__[0].cell_contents = "Взломано"
my_closure()   # "Взломано"
```

**Свободные переменные** (`__code__.co_freevars`) и **переменные ячейки** (`__code__.co_cellvars`):

```python
def outer():
    x = 10
    def inner():
        return x
    return inner

print(outer.__code__.co_cellvars)    # ('x',) — x используется во вложенной
print(outer().__code__.co_freevars)   # ('x',) — x взят из внешней
```

## 8.4. `sys._getframe` и фреймы { #8.4 }

> **→ см. также:** Часть X (10.7) — Audit hooks (PEP 578) как более безопасный способ мониторинга вызовов; Часть VII (7.11) — `inspect.stack()` как высокоуровневая обёртка над фреймами.

⚠️ **`sys._getframe` — для отладки.** Для production-кода в Python 3.12+ предпочтительнее `sys.monitoring` (PEP 669) — низкооверхедный трейсинг, заменяющий `sys.settrace`/`sys.setprofile`. `sys.monitoring` не создаёт фреймы при каждом вызове, а регистрирует event-хуки для конкретных событий (CALL, PY_START, PY_RESUME, PY_RETURN, PY_UNWIND); накладные расходы при неиспользуемых событиях — на порядки ниже, чем у `settrace` (точную экономию меряйте на своём workload). `_getframe` остаётся полезным для отладки и интроспекции, но не для production-мониторинга.

`sys._getframe(depth=0)` возвращает фрейм стека. `depth=0` — текущий, `depth=1` — вызвавший, и т.д.

```python
import sys

def magic_function():
    caller_frame = sys._getframe(1)            # фрейм того, кто вызвал
    caller_name = caller_frame.f_code.co_name   # имя функции-родителя

    if caller_name == "test_one":
        return 100
    elif caller_name == "test_two":
        return 200
    return 0

def test_one():
    return magic_function()

def test_two():
    return magic_function()

print(test_one())   # 100
print(test_two())   # 200
```

Внутри `magic_function` нет аргументов, на вход ничего не подаётся, но функция **выдаёт разные результаты** в зависимости от того, кто её вызвал.

**Полезные атрибуты фрейма:**

| Атрибут | Что даёт |
|---------|---------|
| `f_code` | код-объект (`CodeType`) |
| `f_code.co_name` | имя функции |
| `f_code.co_filename` | путь к файлу |
| `f_code.co_firstlineno` | номер первой строки функции |
| `f_locals` | словарь локальных переменных |
| `f_globals` | словарь глобальных |
| `f_lineno` | текущая строка выполнения |
| `f_back` | предыдущий фрейм (можно блуждать по стеку) |

⚠️ **Часто менее инвазивный способ** — модуль `inspect`:

```python
import inspect

def f():
    frame = inspect.currentframe()
    caller = frame.f_back
    print(caller.f_code.co_name)
```

## 8.5. `sys.getrefcount` и счётчик ссылок { #8.5 }

CPython управляет памятью через **подсчёт ссылок**. У каждого объекта есть счётчик. Когда становится 0 — объект удаляется.

```python
import sys

x = [1, 2, 3]
print(sys.getrefcount(x))   # 2 (x + временная ссылка при передаче в функцию)

y = x
print(sys.getrefcount(x))   # 3 (x, y, временная)

del y
print(sys.getrefcount(x))   # 2
```

⚠️ Число часто **больше**, чем вы ожидаете, потому что:

1. Аргумент, переданный в `getrefcount`, временно добавляет ссылку.
2. Строки и числа могут интернироваться / кэшироваться — общий счётчик.

```python
print(sys.getrefcount(1))   # 4294967295 на 3.12+ 64-bit (immortal objects, PEP 683); на 32-bit сборках 1073741823; ~300 на 3.11 и ниже
```

**Использование как флаг** — трюк, который выглядит заманчиво, но на практике **ненадёжен**:

```python
my_list = [1, 2, 3]
if sys.getrefcount(my_list) > 2:
    print("Интерпретатор держит объект (возможно, кто-то шпионит)")
else:
    print("Только мы держим объект")
```

⚠️ **Скрытые проблемы**: refcount зависит от множества факторов, которые от вас не зависят:

- **Временные ссылки** при вызове функций (`getrefcount(x)` сам добавляет +1 к ожидаемому числу).
- **Интернирование строк** и **кэш малых чисел** — для маленьких объектов refcount всегда аномально высок (`sys.getrefcount(1)` возвращает 4294967295 на Python 3.12+ из-за PEP 683 Immortal Objects — константа `_Py_IMMORTAL_REFCNT`, равная `UINT_MAX` на 64-битных сборках и `UINT_MAX >> 2` на 32-битных, поэтому число зависит от битности платформы; или ~300 на 3.11 и ниже).
- **Constant folding** компилятора держит литералы, которые вы считаете «вашими».
- **Оптимизации в разных версиях CPython** — на 3.11+ из-за адаптивной интерпретации и specializing interpreter счётчики могут вести себя иначе, чем на 3.9.
- **Слабые ссылки** не учитываются в refcount, но влияют на логику.

Как **детектор шпионажа** — не работает: слишком много ложных срабатываний и пропусков. Если задача — найти, кто держит ссылку на объект, используйте `gc.get_referrers(obj)` — он возвращает конкретные объекты-держатели, а не голое число.

## 8.6. Управление GC через `gc` модуль { #8.6 }

CPython использует **подсчёт ссылок** + **циклический GC** для борьбы с циклами (`a.b = c; c.a = a` — счётчики никогда не обнулятся, только GC найдёт).

```python
import gc

# Текущие пороги: как часто GC запускается для каждого поколения
print(gc.get_threshold())   # (700, 10, 10) — поколение 0/1/2

# Изменить пороги
gc.set_threshold(1000, 15, 15)

# Вручную запустить
gc.collect()              # все поколения
gc.collect(2)             # полная сборка (как и без аргумента; прогон: находит свежий цикл в старом поколении); только поколение 0 — gc.collect(0)

# Кто ссылается на объект
obj = [1, 2, 3]
referrers = gc.get_referrers(obj)
# Список всех объектов, которые держат ссылку на obj

# Объекты, на которые ссылается obj
referents = gc.get_referents(obj)

# Включить/выключить GC
gc.disable()
gc.enable()

# Получить статистику
print(gc.get_stats())   # [{"collections": ..., "collected": ..., "uncollectable": ...}, ...]
```

**Применения:**

- Отключение GC для performance-critical кода (если уверены, что циклов нет).
- Принудительный сбор перед замером памяти.
- Отладка утечек через `gc.get_referrers`.

## 8.7. Интроспекция функций через `__code__` { #8.7 }

У каждой функции есть `__code__` — код-объект с метаданными:

```python
def f(x, y):
    z = x + y
    return z

print(f.__code__.co_varnames)   # ('x', 'y', 'z') — все локальные и аргументы
print(f.__code__.co_consts)     # (None, ...) — все литералы внутри функции
print(f.__code__.co_code)      # b'...' — сырой байт-код для VM CPython
print(f.__code__.co_names)     # имена глобальных имён, к которым обращается функция
print(f.__code__.co_argcount)  # 2 — число позиционных аргументов
print(f.__code__.co_filename)  # путь к файлу с функцией
print(f.__code__.co_firstlineno)  # номер первой строки функции
```

Через `co_varnames` можно прочитать имена переменных, которые статический анализатор считал «спрятанными» в рантайме.

```python
def analyze(func):
    code = func.__code__
    return {
        'args': code.co_argcount,
        'locals': code.co_varnames,
        'constants': code.co_consts,
        'globals_used': code.co_names,
        'filename': code.co_filename,
        'lineno': code.co_firstlineno,
    }

print(analyze(f))
# {'args': 2, 'locals': ('x', 'y', 'z'), 'constants': (None,), 
#  'globals_used': (), 'filename': '<stdin>', 'lineno': 1}
```

## 8.8. Динамическая смена `__class__` { #8.8 }

В Python можно **сменить класс объекта в рантайме**:

```python
class Dog:
    def speak(self):
        return "Woof!"

class Cat:
    def speak(self):
        return "Meow!"

my_pet = Dog()
print(my_pet.speak())   # Woof!

my_pet.__class__ = Cat   # меняем класс в рантайме!
print(my_pet.speak())   # Meow!
```

⚠️ **Ограничения**:

- Новый класс должен иметь совместимую **memory layout** (те же `__slots__` или также с `__dict__`).
- Нельзя сменить на встроенный тип (`int`, `str`, ...).
- `isinstance(obj, NewClass)` после смены `__class__` вернёт `True` — даже если это «хакерская» смена, а не настоящее наследование. Это ломает рассуждения о типах.

**Применение** — конечные автоматы без `if/else`:

```python
class State:
    pass

class IdleState(State):
    def click(self):
        print("Click → Active")
        self.__class__ = ActiveState

class ActiveState(State):
    def click(self):
        print("Click → Idle")
        self.__class__ = IdleState

class Button:
    def __init__(self):
        self.__class__ = IdleState   # начальное состояние (хак)
    
    def click(self):
        pass

# Лучше через композицию, но __class__ работает
```

⚠️ **Скрытые проблемы с паттерном через `__class__`**:

- `isinstance(button, IdleState)` вернёт `True` после `__class__ = IdleState`, хотя `Button` не наследует `IdleState`. Это нарушает инварианты типов, mypy/pyright не знают об этом и могут дать неверные подсказки.
- Если `IdleState` и `ActiveState` имеют разные `__slots__` — смена `__class__` упадёт с `TypeError: __class__ assignment only supported for mutable types or ModuleType subclasses`; при несовпадении layout — `TypeError: __class__ assignment: 'ActiveState' object layout differs from 'IdleState'` (обе ошибки сняты на 3.12).
- `pickle`/`copy`/`repr` таких объектов могут вести себя неожиданно — они смотрят на `type(obj)`, который теперь `IdleState`, а `__init__` у `Button` ожидает другие аргументы.
- В реальном коде предпочитают **композицию** (`self.state = IdleState()` + `self.state.click(self)`) — она не ломает систему типов и работает с любым layout.

## 8.9. Доступ к байт-коду через `dis` { #8.9 }

`dis` модуль — дизассемблер Python-байт-кода:

```python
import dis

def f(x):
    return x * 2

dis.dis(f)
#  2           0 RESUME 0
#  3           2 LOAD_FAST 0 (x)
#              4 LOAD_CONST 1 (2)
#              6 BINARY_OP 5 (*)
#             10 RETURN_VALUE        ← offset 10: BINARY_OP несёт 1 CACHE-слово
```

Полезно, чтобы понять:

- **Почему `a, b = b, a` быстрее, чем `temp = a; a = b; b = temp`** — в функции `a, b = b, a` компилируется в `LOAD_FAST` + `LOAD_FAST` + `STORE_FAST` + `STORE_FAST` (порядок STORE переставлен; на уровне модуля — `LOAD_NAME` ×2 + `SWAP 2` + `STORE_NAME` ×2; `ROT_TWO` удалён в 3.11).
- **Почему `is` быстрее `==`** — `is` это `IS_OP` (сравнение указателей), а `==` вызывает `__eq__` через `COMPARE_OP`.
- **Что Python реально делает** с вашим кодом.

**Инструкция по методу**:

```python
# Дизассемблировать функцию
dis.dis(f)

# Дизассемблировать строку с кодом
dis.dis("x = 1; y = x + 2")

# Показать байт-код без красивого форматирования
print(f.__code__.co_code.hex())
# 97007c0064017a0500005300 — hex (RESUME; LOAD_FAST; LOAD_CONST; BINARY_OP с CACHE; RETURN_VALUE)

# Получить программно — список инструкций
for instr in dis.Bytecode(f):
    print(instr.opname, instr.argval)
# RESUME 0
# LOAD_FAST x
# LOAD_CONST 2
# BINARY_OP *
# RETURN_VALUE None
```

`dis.Bytecode(f)` возвращает итератор инструкций — удобно для программного анализа.

## 8.10. Recursion limit и `RecursionError` { #8.10 }

CPython по умолчанию ограничивает глубину рекурсии 1000 вызовов (для защиты от stack overflow):

```python
import sys

print(sys.getrecursionlimit())   # 1000

def rec(n):
    if n == 0:
        return
    rec(n - 1)

rec(990)   # OK
rec(2000)  # RecursionError: maximum recursion depth exceeded

# Поднять лимит
sys.setrecursionlimit(5000)
rec(4000)  # OK

# Слишком высокий лимит — segfault (стек кончится в C):
# sys.setrecursionlimit(1000000)  # НЕ ДЕЛАЙТЕ ЭТО
```

**Альтернативы рекурсии** — обычно лучше переделать в итерацию:

```python
# Рекурсивно (упадёт на больших n):
def fact_rec(n):
    return 1 if n == 0 else n * fact_rec(n - 1)

fact_rec(1500)   # RecursionError

# Итеративно:
def fact_iter(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

fact_iter(1500)   # OK (вернёт большое int)
```

**Хвостовая рекурсия** — Python **не** оптимизирует (в отличие от Scheme/Haskell). Любая хвостовая рекурсия в Python будет стеком. Если нужно — пишите итеративно или используйте `trampolining` через генераторы/исключения.

**Увеличение размера стека ОС** (Linux/macOS) — отдельно от recursion limit:

```python
import threading, sys

sys.setrecursionlimit(100_000)

# Поток с большим стеком — иначе segfault
threading.stack_size(256 * 1024 * 1024)   # 256 MB

def deep_rec(n):
    if n == 0:
        return
    deep_rec(n - 1)

t = threading.Thread(target=deep_rec, args=(50_000,))
t.start()
t.join()
```

⚠️ **Скрытые проблемы с `threading.stack_size`**:

- Значение должно быть **кратно размеру системной страницы памяти** (4 KB на x86/x64 Linux, 16 KB на некоторых ARM). Некратные значения могут округляться или падать с `ValueError`.
- На **Windows** максимальный размер стека ограничен (~1 GB обычно), и большие значения (> 256 MB) могут либо молча округляться вниз, либо приводить к `OverflowError`.
- На **macOS** основной поток имеет фиксированный размер стека (обычно 8 MB), который нельзя изменить через `threading.stack_size` — поэтому глубокая рекурсия **обязательно** должна идти в отдельном потоке (как в примере выше), а не в main thread.
- `setrecursionlimit(10**6)` + `stack_size(256 MB)` на CPython 3.11+ всё равно может **сегфолтнуть**, если C-стек потока (отличается от Python recursion limit) переполнится — особенно на архитектурах с большим frame size (debug builds, ASan/MSan). Лечится только ещё большим `stack_size` или отказом от рекурсии.

## 8.11. `contextvars` — контекстно-зависимые переменные { #8.11 }

`contextvars` (PEP 567, Python 3.7+) — переменные, значение которых **автоматически копируется** в новые async-задачи (`asyncio.create_task()`, `asyncio.to_thread()`). Главное применение — `request_id`, `user_id`, `trace_id` в логах без явной передачи через аргументы.

⚠️ **`threading.Thread` НЕ копирует контекст автоматически!** Новый поток ОС стартует с **чистым дефолтным контекстом**. Для проброса контекста в поток:
```python
ctx = contextvars.copy_context()
threading.Thread(target=ctx.run, args=(worker,)).start()  # ✅ теперь видит значения
```

```python
import contextvars

# Создаём переменную контекста
request_id: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='unknown')

def log(msg):
    print(f"[{request_id.get()}] {msg}")

# Установка в одном месте
request_id.set("req-123")
log("Start processing")   # [req-123] Start processing

# Доступ из любой функции ниже по стеку — без передачи через аргументы:
def helper():
    log("helper called")

helper()   # [req-123] helper called
```

**Главный кейс — `request_id` для async-задач:**

```python
import asyncio
import contextvars

request_id = contextvars.ContextVar('request_id', default='?')

async def handle_request(rid):
    token = request_id.set(rid)   # установить в этой задаче
    try:
        await asyncio.sleep(0.1)
        await helper()
    finally:
        request_id.reset(token)   # восстановить старое значение

async def helper():
    print(f"[{request_id.get()}] helper")   # видит свой request_id

async def main():
    # Запускаем две задачи параллельно — у каждой свой request_id
    await asyncio.gather(
        handle_request("req-A"),
        handle_request("req-B"),
    )
    # [req-A] helper
    # [req-B] helper

asyncio.run(main())
```

Каждая корутина получает **копию контекста** — `request_id` в одной не видит изменения другой.

⚠️ Без `contextvars` (через обычный `global` или атрибут класса) переменная будет **общей** для всех async-задач — нельзя разделить per-request.

**Свой Context для изоляции:**

```python
ctx = contextvars.copy_context()   # сделать копию текущего контекста
ctx.run(some_function, *args, **kwargs)   # выполнить функцию с этой копией (args распаковываются)
```

Это используется во всех современных async-фреймворках: FastAPI, Starlette, aiohttp — для проброса `request_id`/`user_id` без явных аргументов.

## 8.12. `pathlib` — объектно-ориентированные пути { #8.12 }

`pathlib` (Python 3.4+) — современная замена `os.path`. Пути как объекты с методами вместо строковых операций.

```python
from pathlib import Path

# Создание
p = Path('/home/user/docs/file.txt')
p = Path('docs') / 'file.txt'           # оператор /
p = Path.home() / 'docs'                # /home/user/docs (платформенно-зависимо)
p = Path.cwd()                          # текущий каталог
p = Path(__file__)                       # путь к этому скрипту
p = Path('/tmp') / 'sub' / 'file.txt'   # /tmp/sub/file.txt

# ⚠️ Выше p перезаписывался 6 раз — ниже разобран первый вариант:
p = Path('/home/user/docs/file.txt')

# Чтение
print(p.name)           # 'file.txt'
print(p.stem)            # 'file' — без расширения
print(p.suffix)          # '.txt'
print(p.suffixes)        # ['.txt'] — все расширения
print(p.parent)          # /home/user/docs
print(p.parents[0])      # /home/user/docs — Path, не строка
print(p.parents[1])      # /home/user
print(p.anchor)          # '/' (на Windows — 'C:\\')
print(p.parts)           # ('/', 'home', 'user', 'docs', 'file.txt') — кортеж

# Проверки
print(p.exists())        # True/False
print(p.is_file())       # True/False
print(p.is_dir())
print(p.is_absolute())

# Чтение/запись как файлы:
content = p.read_text(encoding='utf-8')
data = p.read_bytes()
p.write_text("hello")
p.write_bytes(b"hello")

# Открытие:
with p.open('r') as f:
    ...

# Итерация по каталогу
for child in Path('/tmp').iterdir():
    print(child)

# Glob
for py_file in Path('.').glob('**/*.py'):   # рекурсивно
    print(py_file)
for log in Path('/var/log').glob('*.log'):
    print(log)

# rglob — рекурсивный glob
for py_file in Path('.').rglob('*.py'):
    print(py_file)

# Создание/удаление
p.mkdir(parents=True, exist_ok=True)   # mkdir -p
p.rmdir()   # пустой каталог
p.unlink()  # файл

# rename, replace, resolve (абсолютный путь)
p2 = p.rename('/tmp/new_name.txt')
abs_path = p.resolve()   # все . и .. раскрыты, симлинки разыменованы

# Path.walk() (Python 3.12+) — заменяет os.walk(), возвращает Path-объекты:
for root, dirs, files in Path('src').walk():
    for f in files:
        file_path = root / f   # удобная склейка без os.path.join
```

⚠️ **Path Traversal через оператор `/`**: если правый операнд — абсолютный путь, он **полностью перетирает левую часть**:
```python
base = Path("/var/app/uploads")
user_input = "/etc/passwd"
target = base / user_input   # → /etc/passwd (не /var/app/uploads/etc/passwd)!
```
Защита через `is_relative_to()` (Python 3.9+):
```python
resolved = (base / user_input.lstrip('/')).resolve()
if not resolved.is_relative_to(base.resolve()):
    raise PermissionError("Path Traversal!")
```

**PurePath** — операции без файловой системы (для путей, которые не надо проверять):

```python
from pathlib import PurePath, PurePosixPath, PureWindowsPath

p = PurePosixPath('/usr/local/bin')
p2 = p / 'python3'   # PurePosixPath('/usr/local/bin/python3')

# Windows-пути на Linux:
wp = PureWindowsPath('C:\\Users\\Alice')
print(wp.drive)   # 'C:'
print(wp.root)    # '\\'
print(wp.parts)   # ('C:\\', 'Users', 'Alice')

# Сравнение
PurePosixPath('/a/b') == PurePosixPath('/a/b')   # True
PurePosixPath('/a/b') == PureWindowsPath('/a/b')  # False — разные ОС
```

**`Path` vs `os.path`** — в новом коде всегда `pathlib`. `os.path` — только в старом коде.

## 8.13. `types` — продвинутые типы { #8.13 }

`types` модуль содержит типы, которые обычно создаются автоматически, но могут быть полезны напрямую.

### `MethodType` — метод экземпляра { #8.13-methodtype }

```python
import types

class A:
    def method(self):
        return "hello"

a = A()
# a.method — bound method, объект типа MethodType
print(isinstance(a.method, types.MethodType))   # True

# Динамически добавить метод экземпляру
def new_method(self):
    return "world"

a.greet = types.MethodType(new_method, a)   # привязываем как метод a
print(a.greet())   # 'world'
```

⚠️ `a.greet = new_method` просто привяжет функцию как атрибут — вызов `a.greet()` упадёт с `TypeError: new_method() missing 1 required positional argument: 'self'` (функция не стала bound method, поэтому `self` не передан). Через `MethodType` — корректно привязывается.

### `SimpleNamespace` — простой объект с атрибутами { #8.13-simplenamespace }

```python
from types import SimpleNamespace

# Быстрый объект с произвольными атрибутами
config = SimpleNamespace(host="localhost", port=8080, debug=True)
print(config.host)        # 'localhost'
print(config.port)        # 8080

# Изменяемый
config.host = "example.com"
config.new_attr = "added"

# repr
print(config)   # namespace(host='example.com', port=8080, debug=True, new_attr='added')

# Заменяет простой dict, когда доступ через точку удобнее
```

⚠️ В отличие от `dataclass` — `SimpleNamespace` не имеет аннотаций, не валидируется, не имеет методов. Только для «quick and dirty» структур.

### `MappingProxyType` — immutable view на словарь { #8.13-mappingproxytype }

```python
from types import MappingProxyType

original = {'a': 1, 'b': 2}
proxy = MappingProxyType(original)
print(proxy['a'])   # 1

# proxy['c'] = 3   # TypeError: 'mappingproxy' object does not support item assignment

# Но изменения в original видны через proxy:
original['c'] = 3
print(proxy['c'])   # 3
```

Используется для возврата «только для чтения» словаря — клиент не может модифицировать, но вы (через original) можете.

```python
class Config:
    def __init__(self):
        self._data = {'debug': False, 'port': 8080}
    
    @property
    def data(self):
        return MappingProxyType(self._data)   # клиенты не могут изменять

c = Config()
print(c.data['debug'])   # False
# c.data['debug'] = True   # TypeError — protected
```

### `CellType` — тип cell (для замыканий) { #8.13-celltype }

```python
import types

# Cell — контейнер для переменных замыкания
cell = types.CellType()
cell.cell_contents = "hello"
print(cell.cell_contents)   # 'hello'

# Эквивалентно:
# def outer():
#     x = "hello"
#     def inner():
#         return x
#     return inner.__closure__[0]
```

Полезно для тестов замыканий и для ручного создания функций через `FunctionType` (где cellvars/freevars передаются явно).

### `GenericAlias` — тип `list[int]` { #8.13-genericalias }

```python
import types
from typing import List

# list[int] — это GenericAlias
print(isinstance(list[int], types.GenericAlias))   # True
print(isinstance(dict[str, int], types.GenericAlias))   # True

# typing.List[int] — это typing._GenericAlias, НЕ types.GenericAlias
print(isinstance(List[int], types.GenericAlias))   # False

# Получить args:
print(list[int].__args__)   # (<class 'int'>,)
print(dict[str, int].__args__)   # (<class 'str'>, <class 'int'>)
```

### `UnionType` — тип `int | str` (PEP 604, Python 3.10+) { #8.13-uniontype }

```python
import types

# int | str — это UnionType, не typing.Union
print(isinstance(int | str, types.UnionType))   # True

# typing.Union[int, str] — это typing._SpecialForm, НЕ types.UnionType
from typing import Union
print(isinstance(Union[int, str], types.UnionType))   # False

# __args__ — компоненты объединения
print((int | str | None).__args__)   # (<class 'int'>, <class 'str'>, <class 'NoneType'>)
```

⚠️ В современном коде предпочтительно `int | str` вместо `Union[int, str]` (Python 3.10+).

## 8.14. `weakref` — продвинутое { #8.14 }

(Базовые `weakref.ref`, `WeakValueDictionary`, `WeakKeyDictionary`, `finalize` — см. §11.4.)

### `WeakSet` — множество слабых ссылок { #8.14-weakset }

```python
import weakref

class Image:
    pass

images = [Image() for _ in range(100)]
cache = weakref.WeakSet()

for img in images:
    cache.add(img)

print(len(cache))   # 100

# Удаляем все сильные ссылки
images.clear()
del img   # ⚠️ переменная цикла держит последний Image — без del будет len(cache) == 1

import gc; gc.collect()
print(len(cache))   # 0 — все элементы удалены из cache автоматически
```

### `weakref.proxy` — прозрачный прокси { #8.14-weakrefproxy }

В отличие от `weakref.ref` (надо вызывать `ref()` чтобы получить объект), `proxy` ведёт себя как сам объект — обращение к атрибутам автоматически разыменовывает:

```python
import weakref

class Big:
    def __init__(self, name):
        self.name = name

obj = Big("huge")
p = weakref.proxy(obj)
print(p.name)   # 'huge' — обращение через прокси

del obj
# print(p.name)   # ReferenceError — объект удалён
```

⚠️ Прокси «прозрачный» для доступа к атрибутам и для `isinstance` — `isinstance(p, Big)` вернёт `True` (прокси делегирует `__class__` к целевому объекту). Но сам `type(p)` — это `<class 'weakref.ProxyType'>`, а не `Big`. Поэтому проверка через `type(p) is Big` или `type(p) == Big` уже **даст False**. Если объект удалён — любое обращение к прокси поднимет `ReferenceError`.

### `weakref.finalize` — детерминированный финализатор { #8.14-weakreffinalize }

В отличие от `__del__`, `finalize` не вызывает проблем с циклами GC:

```python
import weakref

class Resource:
    pass

def cleanup(file_path, lock_id):
    print(f"Cleaning up {file_path} (lock {lock_id})")

r = Resource()
finalizer = weakref.finalize(r, cleanup, '/tmp/data.bin', 42)

# Явный вызов ДО удаления:
finalizer()   # "Cleaning up /tmp/data.bin (lock 42)"

del r   # финализатор уже сработал — повторный вызов no-op
# Также finalizer.detach() — отключить, без вызова
# finalizer.peek() — посмотреть, что было бы вызвано
```

Полезно для освобождения ресурсов без `__del__` (который ломает GC в некоторых случаях).

## 8.15. `sys.unraisablehook` и `sys._current_frames` { #8.15 }

### `sys.unraisablehook` — обработка «unraisable» исключений { #8.15-sysunraisablehook }

Когда исключение происходит в `__del__` или в C-расширении (где его нельзя пробросить), Python вызывает `sys.unraisablehook`:

```python
import sys

def my_hook(args):
    # args — sys.UnraisableHookArgs с полями:
    #   err_msg, exc_type, exc_value, exc_traceback, object
    print(f"UNRAISABLE in {args.object}: {args.exc_type.__name__}: {args.exc_value}")

sys.unraisablehook = my_hook

class Buggy:
    def __del__(self):
        raise ValueError("ups")

Buggy()   # при уничтожении (по refcount — сразу на конце строки):
# "UNRAISABLE in <function Buggy.__del__ at 0x...>: ValueError: ups"
# (args.object — это bound __del__, не сам экземпляр)
```

Зачем: по умолчанию Python печатает такие исключения в stderr, что засоряет логи. Через hook можно их подавить, залогировать, или превратить в alert.

### `sys._current_frames` — стеки всех потоков { #8.15-syscurrentframes }

```python
import sys, threading, time

def worker():
    time.sleep(10)

threads = [threading.Thread(target=worker) for _ in range(3)]
for t in threads: t.start()

# Получить стеки всех потоков
for thread_id, frame in sys._current_frames().items():
    print(f"Thread {thread_id}:")
    print(frame.f_code.co_filename, frame.f_lineno)
```

Полезно для отладки deadlocks и зависших процессов. Аналогично для asyncio — `asyncio.all_tasks()`.

---

### Бенчмарки к Части VIII { #8.15-benchmarki }

**1. `sys.intern` — влияет ли на скорость lookup'а в dict по строковым ключам.**
```python
import sys, timeit
# 10 000 строк-ключей
keys = [f"key_{i}" for i in range(10_000)]
d = {k: i for i, k in enumerate(keys)}
d_intern = {sys.intern(k): i for i, k in enumerate(keys)}
# ⚠️ Честный тест: ключи для lookup — НОВЫЕ объекты с теми же значениями.
# Если lookup идёт по тем же объектам, что лежат в dict (как в наивном
# варианте бенчмарка), dict и так срабатывает по identity — intern ни при чём.
lookup_new = [(k + "!")[:-1] for k in keys]                    # новые равные строки
lookup_new_intern = [sys.intern((k + "!")[:-1]) for k in keys]

def lookup_plain():
    for k in lookup_new: _ = d[k]
def lookup_intern():
    for k in lookup_new_intern: _ = d_intern[k]
print(timeit.timeit(lookup_plain,  number=10))   # ≈ 0.0125 с (зависит от CPU)
print(timeit.timeit(lookup_intern, number=10))   # ≈ 0.0064 с — без выигрыша, даже чуть медленнее
```
На 3.12 честный замер показывает **нулевую или отрицательную разницу**:
intern не ускоряет dict-lookup — быстрый путь по hash/length уже встроен,
а identity-сравнение у dict и так первое. Реальные выгоды `sys.intern` —
память (дедупликация равных строк) и быстрые `is`-сравнения в вашем коде,
а не скорость словарей.

**2. Кэш малых чисел (-5..256) — реальные последствия.**
```python
a, b = 256, 256
print(a is b)   # True — оба из кэша
c, d = 257, 257
print(c is d)   # True в скрипте (константы одного код-объекта дедуплицируются);
# False — только на двух отдельных строках REPL
```
**На производительность это не влияет** — арифметика работает одинаково.
Влияет на **`is`-сравнения**: никогда не сравнивайте целые через `is`,
только через `==`. `is` для чисел — источник загадочных багов.

**3. `__slots__` — измерение памяти на 1M экземпляров.**
```python
import sys, tracemalloc
# Корректное сравнение:
class Plain:
    def __init__(self): self.x = self.y = 0
class Slotted:
    __slots__ = ("x", "y")
    def __init__(self): self.x = self.y = 0

# Размер одного экземпляра (честный подсчёт через sys.getsizeof):
p = Plain(); s = Slotted()
print(f"Plain:   {sys.getsizeof(p) + sys.getsizeof(p.__dict__)} bytes")  # 344 (48 obj + 296 __dict__)
print(f"Slotted: {sys.getsizeof(s)} bytes")                                # 48 (нет __dict__)

# 1M объектов (tracemalloc недооценивает __dict__, но порядок виден):
tracemalloc.start()
objs = [Plain() for _ in range(1_000_000)]
_, peak1 = tracemalloc.get_traced_memory()
del objs
objs = [Slotted() for _ in range(1_000_000)]
_, peak2 = tracemalloc.get_traced_memory()
print(f"Plain 1M:   {peak1 / 1e6:.1f} MB (tracemalloc)")   # ~88.5 MB — на 3.12 __dict__ не материализуется
print(f"Slotted 1M: {peak2 / 1e6:.1f} MB (tracemalloc)")   # ~88.5 MB — разницы tracemalloc не видит
# Честный per-instance через getsizeof: 344 vs 48 байт — ~7.2×
```
Экономия **~7×** на экземпляр по `sys.getsizeof` (344 байта → 48) — уходит `__dict__` (хеш-таблица ~296 байт). Нюанс 3.12: `tracemalloc` на реальном миллионе показывает одинаковые ~88.5 MB — instance-`__dict__` хранится inline (in-object values) и не материализуется, пока к нему не обратятся; честная per-instance картина — через `getsizeof(p) + getsizeof(p.__dict__)`, как выше.

**4. `weakref.WeakValueDictionary` vs обычный `dict` — цена слабых ссылок.**
```python
import weakref, timeit, gc
class Obj: pass
# Обычный dict: сильные ссылки, объекты не удаляются GC
strong = {}
# WeakValueDictionary: значения удаляются автоматически, когда на них нет сильных ссылок
weak = weakref.WeakValueDictionary()
o = Obj()
strong["k"] = o
weak["k"] = o
# Доступ
print(timeit.timeit(lambda: strong["k"], number=1_000_000))   # ≈ 0.06 с (зависит от CPU)
print(timeit.timeit(lambda: weak["k"],  number=1_000_000))   # ≈ 0.14 с
```
WeakValueDictionary **в ~2–3× медленнее** на доступ — каждый lookup проверяет,
жива ли ссылка, и dereference'ит её. Используйте только когда реально нужна
автоматическая очистка (кеш, observers).

**5. `OrderedDict.move_to_end` для LRU — скорость.**
```python
from collections import OrderedDict
import timeit
od = OrderedDict()
for i in range(10_000): od[i] = i
# Имитация LRU: 1M обращений, каждый раз move_to_end
def lru_access():
    for _ in range(1_000_000):
        k = 0  # всегда один и тот же ключ
        od.move_to_end(k)
# ≈ 0.05 с на 1M операций (зависит от CPU)
```
`OrderedDict`-based LRU — **~20M операций/сек** на одном потоке.
Для сравнения, `functools.lru_cache` (C-реализация) — того же порядка, но с готовой политикой вытеснения.
На горячих путях берите `lru_cache`; кастомный LRU через `OrderedDict` —
когда нужен кастомный eviction policy или ограничения не по размеру, а по памяти.

