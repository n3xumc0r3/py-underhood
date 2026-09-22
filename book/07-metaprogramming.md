# Часть VII. Метапрограммирование

Метапрограммирование — код, который оперирует кодом: аннотации как рантайм-данные (7.1), декораторы (7.3), динамическое создание классов через `type()` (7.5), `exec`/`compile` (7.7), программный импорт (7.12), разбор исходников в AST (7.13). Здесь же `inspect` (7.11) — швейцарский нож интроспекции, которым дальше пользуются части X и XIII.

## 7.1. Аннотации как данные (`__annotations__`) { #7.1 }

Аннотации типов — это **данные**, доступные в рантайме:

```python
class Config:
    x: 10           # без присваивания — это аннотация, не переменная

print(Config.__annotations__)    # {'x': 10}
print(Config.__annotations__['x'])  # 10
```

В функциях — то же самое, но с сюрпризом: **следующий код упадёт с `KeyError: 'result'`** — это демонстрация ловушки, а не рабочий пример:

```python
def calculate_something():
    result: 42       # аннотация без присваивания — и она НЕ СОХРАНЯЕТСЯ (PEP 526)
    my_number = calculate_something.__annotations__['result']
    return my_number

print(calculate_something())   # KeyError: 'result' — а не 42!

# Локальные аннотации переменных внутри функции интерпретатор только проверяет
# синтаксически и выбрасывает: в func.__annotations__ их нет. В func.__annotations__
# живут только аннотации параметров и return. Аннотации переменных сохраняются
# лишь на уровне модуля/класса (как в примере выше) — в mod.__annotations__ / cls.__annotations__.
```

Что видит интерпретатор:

- `result: 42` → `[IDENTIFIER, COLON, NUMBER]` — нет оператора присваивания `=`.
- `result = 42` → `[IDENTIFIER, ASSIGN, NUMBER]`.

`.__annotations__['result']` → `[IDENTIFIER, DOT, IDENTIFIER, LBRACKET, STRING, RBRACKET]` — выглядит как обычное чтение словаря.

⚠️ **Получение аннотаций**: `typing.get_type_hints(func)` (доступна с Python 3.5) делает правильный резолв строковых аннотаций (PEP 563, `from __future__ import annotations` — опционально с 3.7), но для функции из примера выше вернёт `{}` — локальная аннотация `result: 42` не сохраняется вообще (PEP 526).

## 7.2. `setattr`/`getattr`/`delattr` { #7.2 }

Три функции для динамической работы с атрибутами:

```python
# Динамически получить атрибут объекта
attr = getattr(str, "lower")   # то же, что str.lower
result = attr("Hello")          # "hello"

# Динамически установить
setattr(obj, "name", "Alice")   # то же, что obj.name = "Alice"
setattr(obj, "x_" + str(i), i)  # динамическое имя

# Динамически удалить
delattr(obj, "name")             # то же, что del obj.name

# Безопасное получение с дефолтом
value = getattr(obj, "missing_key", "default")
# если obj.missing_key нет — возвращается "default"
```

Главный кейс — работа с атрибутами, имя которых вычисляется в рантайме (например, из конфигурации, JSON-ключей, или при обходе полей ORM-модели).

⚠️ `getattr`/`setattr`/`delattr` проходят через протокол дескрипторов (включая `@property`) так же, как обычный точечный доступ `obj.name`. Только прямой доступ к `__dict__` минует дескрипторы — поэтому `obj.__dict__['x']` не вызовет `@property`.

## 7.3. Декораторы (параметризованные, классовые) { #7.3 }

**Простой декоратор:**

```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"Вызов {func.__name__}({args}, {kwargs})")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def add(x, y):
    return x + y

add(2, 3)   # напечатает "Вызов add((2, 3), {})" и вернёт 5
```

`@log_calls add` — декоратор над `add`, эквивалентен `add = log_calls(add)`.

**Параметризованный декоратор** — вложенность на один уровень больше:

```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)
def greet(name):
    print(f"Hi, {name}")

greet("Alice")   # "Hi, Alice" x3
```

`@repeat(3)` сначала вызовет `repeat(3)` → вернёт `decorator`. Потом `decorator(greet)` → вернёт `wrapper`. Итог: `greet = wrapper`.

**Декоратор класса:**

```python
def add_repr(cls):
    def __repr__(self):
        return f"{cls.__name__}({self.__dict__})"
    cls.__repr__ = __repr__
    return cls

@add_repr
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
print(p)   # Point({'x': 1, 'y': 2})
```

Декоратор класса получает класс, может его модифицировать и вернуть.

## 7.4. `functools.wraps` — зачем нужен { #7.4 }

Без `@wraps` функция-обёртка теряет метаданные исходной функции:

```python
def log(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log
def add(x, y):
    """Сложение."""
    return x + y

print(add.__name__)   # "wrapper" — потеряли имя!
print(add.__doc__)    # None — потеряли docstring!
import inspect
print(inspect.signature(add))   # (*args, **kwargs) — потеряли сигнатуру!
```

`functools.wraps` копирует метаданные:

```python
from functools import wraps

def log(func):
    @wraps(func)   # через WRAPPER_ASSIGNMENTS копирует __module__, __name__, __qualname__, __doc__, __annotations__, __type_params__ (3.12+); через WRAPPER_UPDATES обновляет __dict__; ставит __wrapped__
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@log
def add(x, y):
    """Сложение."""
    return x + y

print(add.__name__)   # "add"
print(add.__doc__)    # "Сложение."
print(inspect.signature(add))   # (x, y)
print(add.__wrapped__)   # <function add> — доступ к оригиналу
```

**Практическое применение**: `inspect.signature` без `@wraps` вернёт сигнатуру обёртки, а не оригинала. Это ломает `inject`-фреймворки, `pytest` (который инспектирует аргументы), OpenAPI-генераторы (FastAPI) и т.д.

## 7.5. `type()` — динамическое создание классов { #7.5 }

`type` — это и функция для получения типа, и **метакласс** для создания новых классов:

```python
# Получение типа
print(type(42))   # <class 'int'>

# Создание нового класса
Tomato = type('Tomato', (object,), {'color': 'Red'})
# Аналогично:
# class Tomato:
#     color = 'Red'

my_tomato = Tomato()
print(my_tomato.color)   # 'Red'
```

Сигнатура: `type(name, bases, namespace)`:

- `name` — имя класса (то, что будет в `__name__`).
- `bases` — кортеж родительских классов.
- `namespace` — словарь атрибутов и методов.

```python
def __init__(self, name):
    self.name = name

def greet(self):
    return f"Hi, I'm {self.name}"

User = type('User', (object,), {
    '__init__': __init__,
    'greet': greet,
})

u = User("Alice")
print(u.greet())   # "Hi, I'm Alice"
```

Полезно, когда структуру класса нужно построить из конфигурации или динамических данных.

## 7.6. `types.FunctionType` и `types.CodeType` { #7.6 }

> **→ см. также:** Часть VIII (8.7) — интроспекция через `__code__`, (8.9) — `dis` для дизассемблирования.

В Python функции — это **объекты**, которые можно собрать из сырого байт-кода.

```python
import types

# Байт-код для 'return 42' (LOAD_CONST 1; RETURN_VALUE):
#   0x64 0x01  = LOAD_CONST 1  (загружает 42 из consts[1])
#   0x53 0x00  = RETURN_VALUE
code_bytes = b'd\x01S\x00'
consts = (None, 42)
names = ()

# ⚠️ Сигнатура types.CodeType различается по версиям Python:
#   Python 3.6-3.7:  15 параметров (нет posonlyargcount; есть lnotab)
#   Python 3.8-3.10: 16 параметров (добавлен posonlyargcount; есть lnotab)
#   Python 3.11+:    18 параметров (добавлены qualname и exceptiontable; lnotab → linetable)
#                    из 18 параметров freevars и cellvars опциональны (дефолт ()),
#                    поэтому в большинстве вызовов хватает 16 позиционных аргументов.
#
# На практике ручная сборка CodeType почти никогда не нужна — см. ниже
my_runtime_func = types.FunctionType(
    types.CodeType(
        0,            # argcount
        0,            # posonlyargcount
        0,            # kwonlyargcount
        0,            # nlocals
        1,            # stacksize
        64,           # flags (NOFREE)
        code_bytes,   # b'd\x01S\x00' — LOAD_CONST 1; RETURN_VALUE
        consts,       # (None, 42)
        names,        # ()
        (),           # varnames
        '<s>',        # filename
        't',          # name
        't',          # qualname
        1,            # firstlineno
        b'',          # linetable
        b'',          # exceptiontable
    ),
    globals()
)

print(my_runtime_func())   # 42
```

⚠️ Сигнатура `CodeType` очень нестабильна между версиями. **На практике проще** взять готовый код-объект из существующей функции и заменить:

```python
def template():
    return 42

def another_func():
    pass

another_func.__code__ = template.__code__
print(another_func())   # 42 — теперь another_func ведёт себя как template
```

## 7.7. `compile`/`exec`/`eval` { #7.7 }

```python
# compile(source, filename, mode) — компилирует строку в code object
# mode: 'exec' (модуль), 'eval' (выражение), 'single' (один интерактивный оператор REPL; может быть составным — if/for/while; результат выражений печатается)

code_obj = compile("print('hello')", "<string>", "exec")
exec(code_obj)   # "hello"

expr_obj = compile("2 + 3", "<string>", "eval")
print(eval(expr_obj))   # 5

# compile с flags=ast.PyCF_ONLY_AST — получить AST без выполнения:
import ast
tree = compile("x = 1 + 2", "<s>", "exec", flags=ast.PyCF_ONLY_AST)
print(type(tree))  # <class 'ast.Module'> — AST, не байт-код, код НЕ выполнен
# Эквивалент ast.parse, но через compile — для совместимости с флагами

# exec/eval могут принимать code object или строку
exec("x = 10; print(x + 5)")   # 15
print(eval("x * 2"))            # 20 (x уже в globals после exec)
```

**Различие**:

- `exec` — выполняет операторы, ничего не возвращает (точнее, возвращает `None`).
- `eval` — вычисляет выражение и возвращает результат. Принимает только одно выражение (не оператор).

```python
exec("if True: print('yes')")   # OK
eval("if True: print('yes')")   # SyntaxError — eval не принимает if
```

**Передача словарей globals/locals:**

```python
code = "result = a + b"
my_globals = {'a': 10, 'b': 20}
my_locals = {}
exec(code, my_globals, my_locals)
print(my_locals['result'])   # 30

# eval с контекстом
result = eval("a + b", {'a': 1, 'b': 2})   # 3
```

⚠️ **Безопасность**: `eval`/`exec` с пользовательским вводом — это **ACE** (Arbitrary Code Execution; при сетевом вводе — RCE). Никогда не делайте `eval(user_input)` в продакшене.

⚠️ **`eval` — это не калькулятор.** Распространённая и **очень опасная** ошибка — использовать `eval` для вычисления математических выражений от пользователя, думая, что «это же просто числа»:

```python
# КАКАЯ ЧУДЕСНАЯ ИДЕЯ (нет):
expr = input("Введите выражение: ")    # пользователь вводит "2 + 2"
result = eval(expr)                     # 4
print(result)

# Что может ввести злоумышленник:
# __import__('os').system('echo hacked')         ← выполнение произвольной команды
# open('/etc/passwd').read()                  ← чтение системных файлов
# __import__('subprocess').check_output('whoami', shell=True)
# ().__class__.__base__.__subclasses__()       ← обход песочницы через __subclasses__() (см. Приложение B.5)
```

`eval` исполняет **любое** Python-выражение, не только арифметику. Строка `__import__('os').system('...')` — это валидное Python-выражение, оно вычислится и вернёт код завершения процесса. `eval` не делает различия между `2 + 2` и `os.system('echo hacked')` — для него это оба «выражения».

**Более того**: `eval` с ограниченным `globals`/`locals` тоже **не спасает**:

```python
# Пытались защититься — пустой builtins:
eval(user_input, {"__builtins__": {}}, {})
# Простой escape-вектор через __subclasses__():
# ().__class__.__base__.__subclasses__()   ← не требует builtins
```

**Правильная альтернатива** — специализированный AST-walker (пример `safe_eval_math` выше), который сам решает, какие узлы разрешить. Для разбора **только литералов** (без арифметики и вызовов) — `ast.literal_eval` (числа, строки, кортежи, списки, dict):

```python
import ast
# Только литералы — безопасно:
ast.literal_eval("[1, 2, 3]")           # [1, 2, 3]
ast.literal_eval("{'a': 1}")            # {'a': 1}
ast.literal_eval("2 + 2")               # ❌ ValueError — не литерал!

# Для арифметики — пишите свой парсер или используйте symengine/numexpr:
import ast
import operator as op
def safe_eval_math(expr):
    """Вычисляет только арифметические выражения, ничего больше."""
    node = ast.parse(expr, mode='eval').body
    def _eval(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp):
            return {
                ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                ast.Div: op.truediv, ast.Pow: op.pow,
            }[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -_eval(n.operand)
        raise ValueError(f"Запрещённый узел: {type(n).__name__}")
    return _eval(node)

print(safe_eval_math("2 + 2"))        # 4
print(safe_eval_math("2 ** 10"))      # 1024
print(safe_eval_math("__import__('os')"))   # ❌ ValueError
```

⚠️ **Разница между `exec` и `eval` в плане опасности** часто **недооценивается для `eval`**:

- `exec` очевидно опасен — он «исполняет операторы», все понимают, что `exec("os.system(...)")` выполнит команду.
- `eval` **выглядит безобиднее** — «вычисляет выражение». Но в Python **вызов функции** — это выражение. `os.system('...')` — валидное выражение. Так что `eval` **так же опасен**, как `exec`, просто об этом чаще забывают.

Правило: `eval(untrusted_input)` == `exec(untrusted_input)` по уровню угрозы. Если вы не принимаете `exec`, не принимайте и `eval`.

## 7.8. `locals()` и `globals()` { #7.8 }

```python
# globals() — словарь глобального пространства имён модуля
# locals() — словарь локальных переменных (внутри функции)

def f():
    x = 10
    print(locals())   # {'x': 10}
    print(globals() is globals())   # True — всегда один и тот же объект модуля

f()
```

**Динамическое создание переменных:**

```python
# Вместо:
# data = [1, 2, 3]
# target = 5

# Можно:
globals()['data'] = [1, 2, 3]
globals()['target'] = 5

print(data)    # [1, 2, 3] — переменная создана в globals()
print(target)  # 5
```

**Скрытый вызов функций через `locals()`:**

```python
def calculate_score(x):
    return x * 2

func_name = "calculate_score"
result = locals()[func_name](10)   # то же, что calculate_score(10)
print(result)   # 20
```

⚠️ Внутри функции `locals()` возвращает **снимок** локальных переменных, не синхронизированный с реальными локалами — изменения `locals()['x'] = ...` не сохраняются. На уровне модуля `locals()` совпадает с `globals()` (это один и тот же словарь модуля; `locals() is globals() → True`), поэтому изменения через `globals()['x'] = ...` или `locals()['x'] = ...` на модуле сохраняются.

## 7.9. `sys.modules` и `__import__` { #7.9 }

`sys.modules` — глобальный кэш всех импортированных модулей. Можно импортировать «тихо», не создавая переменную:

```python
import sys

# Вместо: import math; print(math.sqrt(16))
if 'math' not in sys.modules:
    __import__('math')   # тихий импорт без создания переменной math

result = sys.modules['math'].__dict__['sqrt'](16)
print(result)   # 4.0
```

`__import__('name')` — встроенная функция, аналог `import name`, но возвращает модуль и не привязывает имя в текущем namespace.

```python
# Явный импорт модуля и получение атрибута
mod = __import__('os.path', fromlist=['join'])
print(mod.join('a', 'b'))   # a/b
```

Работает и для внешних модулей (`httpx`, `requests`, `numpy`), и для ваших собственных файлов:

```python
import sys

if 'httpx' not in sys.modules:
    __import__('httpx')

response = sys.modules['httpx'].__dict__['get']('https://httpbin.org')
print(response.status_code)
```

⚠️ `importlib.import_module` — современный способ (Python 3.1+), который чище `__import__`:

```python
import importlib
math = importlib.import_module('math')
print(math.sqrt(16))   # 4.0
```

## 7.10. `builtins` — переопределение и интроспекция { #7.10 }

`builtins` модуль содержит все встроенные функции и константы (`len`, `print`, `True`, `None`, `Exception`, ...). К ним можно получить доступ и **переопределить**:

```python
import builtins

# Доступ к оригиналу
old_len = builtins.len

# Подмена
def broken_len(obj):
    if isinstance(obj, list):
        return old_len(obj) + 1   # ломаем для списков
    return old_len(obj)

builtins.len = broken_len

print(len([1, 2, 3]))   # 4, а не 3!
print(len("hello"))     # 5 — для строк работает как обычно

# Восстановление
builtins.len = old_len
print(len([1, 2, 3]))   # 3 — восстановлено
```

Это **глобальное** изменение — влияет на весь процесс. Полезно для отладки или тестирования, опасно — может сломать чужой код.

**Интроспекция: что есть в `builtins`?**

```python
import builtins
print([name for name in dir(builtins) if not name.startswith('_')])
# ['ArithmeticError', 'AssertionError', ..., 'abs', 'all', 'any', ..., 
#  'print', 'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
#  'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars',
#  'zip', ...]
```

`vars()` — короткая форма `__dict__` для объектов:

```python
class C:
    def __init__(self):
        self.x = 1
        self.y = 2

c = C()
print(vars(c))   # {'x': 1, 'y': 2} — то же, что c.__dict__
```

## 7.11. `inspect` — интроспекция всего { #7.11 }

`inspect` модуль — высокоуровневый интерфейс к интроспекции. Бóльшая часть того, что можно через `__code__`/`__closure__`/`__dict__`/`sys._getframe`, делается через `inspect` удобнее.

### Сигнатуры функций { #7.11-signatury }

```python
import inspect

def f(x: int, y: str = "default", *args, **kwargs) -> bool:
    return True

sig = inspect.signature(f)
print(sig)              # (x: int, y: str = 'default', *args, **kwargs) -> bool

for name, param in sig.parameters.items():
    print(f"{name}: {param.annotation}, default={param.default}, kind={param.kind}")
# x: <class 'int'>, default=<class 'inspect._empty'>, kind=POSITIONAL_OR_KEYWORD
# y: <class 'str'>, default=default, kind=POSITIONAL_OR_KEYWORD
# args: <class 'inspect._empty'>, default=<class 'inspect._empty'>, kind=VAR_POSITIONAL
# kwargs: <class 'inspect._empty'>, default=<class 'inspect._empty'>, kind=VAR_KEYWORD
```

### Источник кода функции { #7.11-istochnik }

```python
def my_func():
    print("Hello")

print(inspect.getsource(my_func))
# def my_func():
#     print("Hello")
# 

# Только исходник модуля
print(inspect.getsource(inspect))
```

⚠️ `getsource` работает только для функций, определённых в `.py`-файле (не в REPL и не в `compile`-строке).

### Список атрибутов и методов с фильтрами { #7.11-spisok }

```python
class C:
    public = 1
    _private = 2
    def method(self):
        pass
    @staticmethod
    def static():
        pass

c = C()   # экземпляр (без него — NameError)

# Только публичные bound methods (передаём ЭКЗЕМПЛЯР c, не класс C):
for name, member in inspect.getmembers(c, predicate=inspect.ismethod):
    print(name, member)
# method <bound method C.method of <__main__.C object at 0x...>>

# ⚠️ Если передать класс C (а не экземпляр c) с ismethod — вернётся пустой список,
# потому что на уровне класса методы — это обычные function (не bound method).
# Для класса используйте inspect.isfunction:

for name, fn in inspect.getmembers(C, predicate=inspect.isfunction):
    print(name, fn)
# method <function C.method at 0x...>
# static <function C.static at 0x...>   ← staticmethod на уровне класса тоже function

# Только функции
for name, fn in inspect.getmembers(C, predicate=inspect.isfunction):
    print(name, fn)

# Только классы в модуле
import my_module
for name, cls in inspect.getmembers(my_module, inspect.isclass):
    print(name, cls)
```

### Стек вызовов { #7.11-stek }

```python
def f():
    g()

def g():
    h()

def h():
    print("Текущий фрейм:")
    frame = inspect.currentframe()
    print(f"  Файл: {frame.f_code.co_filename}")
    print(f"  Функция: {frame.f_code.co_name}")
    print(f"  Строка: {frame.f_lineno}")
    
    print("\nСтек (от верхнего к нижнему):")
    for frame_info in inspect.stack():
        print(f"  {frame_info.filename}:{frame_info.lineno} в {frame_info.function}")

f()
# Текущий фрейм:
#   Файл: /tmp/test.py
#   Функция: h
#   Строка: 5
# 
# Стек (от верхнего к нижнему):
#   /tmp/test.py:5 в h
#   /tmp/test.py:10 в g
#   /tmp/test.py:3 в f
#   /tmp/test.py:15 в <module>
```

`inspect.stack()` — обёртка над `sys._getframe` + `inspect.getframeinfo` — даёт готовые `FrameInfo` объекты с уже распарсенным контекстом.

### Параметры и `bind` { #7.11-parametry }

```python
sig = inspect.signature(f)
bound = sig.bind(1, "hello", "extra", kw1="v")
print(bound)   # <BoundArguments (x=1, y='hello', args=('extra',), kwargs={'kw1': 'v'})>

# Можно получить как dict:
bound.apply_defaults()
print(bound.arguments)   # {'x': 1, 'y': 'hello', 'args': ('extra',), 'kwargs': {'kw1': 'v'}}
```

Полезно для написания декораторов, которые принимают произвольные аргументы и хотят их инспектировать:

```python
def my_decorator(func):
    sig = inspect.signature(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        for name, val in bound.arguments.items():
            print(f"{name} = {val!r}")
        return func(*args, **kwargs)
    return wrapper
```

### `inspect.getmro` — MRO любого класса { #7.11-inspectgetmro }

```python
class A: pass
class B(A): pass
class C(B): pass

print(inspect.getmro(C))
# [<class '__main__.C'>, <class '__main__.B'>, <class '__main__.A'>, <class 'object'>]
# То же, что C.__mro__
```

### `inspect.getcallargs` — как бы вызвали с конкретными аргументами { #7.11-inspectgetcallargs }

```python
def f(x, y=10):
    return x + y

print(inspect.getcallargs(f, 1))           # {'x': 1, 'y': 10}
print(inspect.getcallargs(f, 1, 2))         # {'x': 1, 'y': 2}
print(inspect.getcallargs(f, x=5))          # {'x': 5, 'y': 10}
# (Устаревший API — не рекомендуется, не имеет DeprecationWarning, но заменён на Signature.bind, см. выше.)
```

Используется в тестах и в mock-фреймворках (например, `unittest.mock`).

### `inspect.isgenerator`, `iscoroutine`, `isawaitable` { #7.11-inspectisgenerator }

```python
import inspect

def gen(): yield 1
async def coro(): return 1

print(inspect.isgenerator(gen()))       # True
print(inspect.iscoroutinefunction(coro))  # True
print(inspect.isasyncgenfunction(lambda: (yield)))   # False — это СИНХРОННЫЙ генератор!
async def agen():
    yield 1
print(inspect.isasyncgenfunction(agen))   # True
```

## 7.12. `importlib` — программный импорт { #7.12 }

`importlib` — современная альтернатива `__import__` для программного управления импортами.

### `importlib.import_module` — основной API { #7.12-importlibimportmodule }

```python
import importlib

# Импорт модуля как объект (вместо `import math`)
math = importlib.import_module('math')
print(math.sqrt(16))   # 4.0

# С submodules
path = importlib.import_module('os.path')
print(path.join('a', 'b'))   # a/b

# Динамическое имя модуля из строки (например, из конфига):
backend_name = config['backend']   # 'redis' или 'memcached'
backend = importlib.import_module(f'backends.{backend_name}')
```

### `importlib.reload` — перезагрузить модуль { #7.12-importlibreload }

```python
import importlib
import my_module

# my_module изменился на диске — перезагрузить
importlib.reload(my_module)
```

⚠️ `reload` **не** обновляет ссылки `from my_module import X` — только `my_module.X`. Также не обновляет экземпляры классов из модуля (они останутся старого типа).

### `importlib.invalidate_caches` — пересканировать sys.path { #7.12-importlibinvalidatecaches }

```python
import importlib

# Если в sys.path появились новые файлы, importlib их не увидит, пока вы не сбросите кэш
importlib.invalidate_caches()
# Теперь новый import найдёт свежесозданный модуль
```

### `importlib.util` — продвинутое API { #7.12-importlibutil }

```python
from importlib.util import spec_from_file_location, module_from_spec

# Загрузить модуль по произвольному пути (не из sys.path)
spec = spec_from_file_location('my_plugin', '/path/to/plugin.py')
module = module_from_spec(spec)
spec.loader.exec_module(module)

print(module.my_function())   # выполняем загруженный модуль
```

Это позволяет загружать плагины из любых путей, обходя стандартную систему импорта.

### `importlib.resources` — доступ к файлам ресурсов в пакете { #7.12-importlibresources }

```python
from importlib import resources

# Прочитать файл, поставляемый с пакетом (например, шаблон)
with resources.files('mypackage').joinpath('templates/email.html').open('r') as f:
    template = f.read()

# Или получить как bytes (для binary-ресурсов):
data = resources.files('mypackage').joinpath('data/icon.png').read_bytes()
```

Заменяет старый трюк с `pkg_resources` (из setuptools). Работает даже если пакет запакован в zip (внутри .egg, .whl).

### `importlib.metadata` — метаданные установленных пакетов { #7.12-importlibmetadata }

```python
from importlib.metadata import distributions, version, metadata, entry_points

# Все установленные пакеты
for dist in distributions():
    print(f"{dist.metadata['Name']}=={dist.version}")

# Версия конкретного пакета
print(version('requests'))   # '2.31.0'

# Метаданные пакета
m = metadata('requests')
print(m['Author'])
print(m['Summary'])

# Entry points (например, плагины для pytest)
for ep in entry_points(group='pytest.plugins'):
    print(ep.name, ep.value)
```

## 7.13. `ast` — разбор исходного кода в AST { #7.13 }

`ast` — парсер Python, превращает исходник в абстрактное синтаксическое дерево. Используется линтерами, форматерами, антиплагиат-системами.

### `ast.parse` — строка в AST { #7.13-astparse }

```python
import ast

code = """
def f(x):
    return x * 2 + 1
"""

tree = ast.parse(code)
print(ast.dump(tree, indent=2))
# Module(
#   body=[
#     FunctionDef(
#       name='f',
#       args=arguments(
#         posonlyargs=[],
#         args=[
#           arg(arg='x')],
#         kwonlyargs=[],
#         kw_defaults=[],
#         defaults=[]),
#       body=[
#         Return(
#           value=BinOp(
#             left=BinOp(
#               left=Name(id='x', ctx=Load()),
#               op=Mult(),
#               right=Constant(value=2)),
#             op=Add(),
#             right=Constant(value=1)))],
#       decorator_list=[],
#       type_params=[])],
#   type_ignores=[])
```

### `ast.unparse` — AST обратно в код (Python 3.9+) { #7.13-astunparse }

```python
tree = ast.parse("x = 1")
print(ast.unparse(tree))   # 'x = 1'
```

Полезно для генерации кода по AST.

### `ast.literal_eval` — безопасный `eval` для литералов { #7.13-astliteraleval }

```python
import ast

# Безопасно парсит литералы (str, int, list, dict, tuple, bool, None)
ast.literal_eval("[1, 2, {'key': 'value'}]")
# [1, 2, {'key': 'value'}]

# НЕ выполняет функции, импорты, присваивания:
# ast.literal_eval("__import__('os').system('echo hacked')")   # ValueError
```

⚠️ В отличие от `eval()`, `literal_eval` **безопасен** — не выполняет произвольный код. Но всё равно не идеален — большие литералы могут уронить парсер через stack overflow.

### `ast.NodeVisitor` — обход AST { #7.13-astnodevisitor }

```python
import ast

class FunctionCounter(ast.NodeVisitor):
    def __init__(self):
        self.count = 0
    def visit_FunctionDef(self, node):
        self.count += 1
        self.generic_visit(node)   # продолжить обход детей

tree = ast.parse(open('my_module.py').read())
counter = FunctionCounter()
counter.visit(tree)
print(f"Found {counter.count} functions")
```

### `ast.NodeTransformer` — модификация AST { #7.13-astnodetransformer }

```python
class DoubleMultiplier(ast.NodeTransformer):
    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mult):
            # Заменить x * y на x * y * 2
            return ast.BinOp(
                left=node,
                op=ast.Mult(),
                right=ast.Constant(2)
            )
        return node

tree = ast.parse("x * y")
new_tree = DoubleMultiplier().visit(tree)
ast.fix_missing_locations(new_tree)
print(ast.unparse(new_tree))   # 'x * y * 2'
```

### `ast.walk` — итерация по всем узлам { #7.13-astwalk }

```python
tree = ast.parse("x = 1; y = x + 2")
for node in ast.walk(tree):
    print(type(node).__name__)
# Module
# Assign
# Assign
# Name
# Constant
# Name
# BinOp
# Store
# Store
# Name
# Add
# Constant
# Load
# ⚠️ ast.walk — обход в ШИРИНУ (BFS через deque): сначала оба Assign,
# потом их дети. Для DFS пишите рекурсивный visitor.
```

### Полный пример: оптимизация `x + 0` → `x` (constant folding) { #7.13-polnyy-folding }

Реалистичная трансформация — найти все `BinOp` вида `something + 0` и заменить на `something`. Это базовая оптимизация, которую делают компиляторы; на Python её можно реализовать через `NodeTransformer`:

```python
import ast

class FoldAddZero(ast.NodeTransformer):
    """Удаляет сложение с нулём: x + 0 → x, 0 + x → x."""
    def visit_BinOp(self, node):
        # Сначала обходим детей — вдруг внутри тоже есть +0
        self.generic_visit(node)
        if not isinstance(node.op, ast.Add):
            return node
        # x + 0
        if isinstance(node.right, ast.Constant) and node.right.value == 0:
            return node.left
        # 0 + x
        if isinstance(node.left, ast.Constant) and node.left.value == 0:
            return node.right
        return node

code = """
def f(x, y):
    return x + 0 + y + 0 + (z + 0)
"""
tree = ast.parse(code)
FoldAddZero().visit(tree)
ast.fix_missing_locations(tree)
print(ast.unparse(tree))
# def f(x, y):
#     return x + y + z
```

### Полный пример: подмена имён переменных (обфускация) { #7.13-polnyy-renamer }

Превращаем осмысленные имена в `_0`, `_1`, `_2`... — типичный шаг обфускации:

```python
import ast

class Renamer(ast.NodeTransformer):
    def __init__(self):
        self.mapping = {}
        self.counter = 0
    def _name(self, old):
        if old not in self.mapping:
            self.mapping[old] = f"_{self.counter}"
            self.counter += 1
        return self.mapping[old]
    def visit_Name(self, node):
        node.id = self._name(node.id)
        return node
    def visit_FunctionDef(self, node):
        node.name = self._name(node.name)
        self.generic_visit(node)
        return node
    def visit_arg(self, node):
        node.arg = self._name(node.arg)
        return node

code = """
def calculate_score(player_id, bonus):
    return player_id * 10 + bonus
"""
tree = ast.parse(code)
Renamer().visit(tree)
ast.fix_missing_locations(tree)
print(ast.unparse(tree))
# def _0(_1, _2):
#     return _1 * 10 + _2
```

⚠️ Этот приём **не отменяет** плагиат-детекторы (см. Приложение A) — они тоже работают через AST-нормализацию, сливают `_0`, `_1` обратно в `IDENTIFIER`. Но он скрывает смысл от **человека**, читающего код.

### Полный пример: instrumentation — подсчёт вызовов функций { #7.13-polnyy-instrumentation }

Вставляем `__count_X += 1` в начало каждой функции — типичная основа профайлеров и coverage-инструментов:

```python
import ast

class Instrumenter(ast.NodeTransformer):
    def __init__(self):
        self.counter_names = []
    def visit_FunctionDef(self, node):
        self.generic_visit(node)   # обработать вложенные функции
        counter = f"__count_{node.name}"
        self.counter_names.append(counter)
        # Вставляем в начало body: __count_name += 1
        incr = ast.AugAssign(
            target=ast.Name(id=counter, ctx=ast.Store()),
            op=ast.Add(),
            value=ast.Constant(1),
        )
        node.body.insert(0, incr)
        return node

code = """
def f(x):
    return x * 2
def g(y):
    return y + 1
"""
tree = ast.parse(code)
inst = Instrumenter()
inst.visit(tree)
ast.fix_missing_locations(tree)
print(ast.unparse(tree))
# def f(x):
#     __count_f += 1
#     return x * 2
# def g(y):
#     __count_g += 1
#     return y + 1
```

Применения `ast`: написание своих линтеров, форматеров (Black, autopep8), анализаторов зависимостей, обфускаторов, и — да — систем плагиата (см. Приложение A).

## 7.14. `dir()` — самый быстрый способ исследования API { #7.14 }

`dir()` — встроенная функция, возвращающая **сортированный список имён атрибутов** объекта. Это первая команда, которую пишут, когда встречают незнакомый объект: `dir(obj)` показывает всё, что у него есть.

```python
>>> import datetime
>>> dir(datetime)
['MAXYEAR', 'MINYEAR', 'UTC', '__all__', '__builtins__', '__cached__', '__doc__', ...,
 'date', 'datetime', 'datetime_CAPI', 'time', 'timedelta', 'timezone', 'tzinfo']

>>> s = "hello"
>>> dir(s)
['__add__', '__class__', '__contains__', '__delattr__', '__dir__', ...,
 'capitalize', 'casefold', 'center', 'count', 'encode', 'endswith', ...,
 'upper', 'zfill']

>>> class Counter:
...     def __init__(self): self.value = 0
...     def inc(self): self.value += 1
...     def reset(self): self.value = 0
...
>>> c = Counter()
>>> dir(c)
['__class__', '__delattr__', '__dict__', '__dir__', ..., 'inc', 'reset', 'value']
```

### Как работает `dir()` под капотом { #7.14-kak }

1. Вызывает метод `obj.__dir__()` (если он есть). **Любой класс может переопределить `__dir__`**, чтобы вернуть кастомный список — например, скрыть приватные атрибуты или добавить виртуальные.
2. Если `__dir__` не определён — `dir()` собирает атрибуты сам:
   - Из `type(obj).__dict__` (атрибуты класса).
   - Из всех базовых классов по MRO (см. 5.4).
   - Из `obj.__dict__` (атрибуты экземпляра).
3. Дубликаты убираются, результат сортируется лексикографически.

```python
# Кастомный __dir__ — можно управлять тем, что видит dir()
class Hidden:
    def __init__(self):
        self.secret = "password"
        self.public = "ok"
    def __dir__(self):
        return ['public']   # dir() покажет только это

>>> h = Hidden()
>>> dir(h)
['public']
>>> h.secret        # но реальный доступ работает
'password'
```

### `dir()` vs `vars()` vs `inspect.getmembers()` { #7.14-dir }

Три функции, которые часто путают:

| Функция | Возвращает | Включает унаследованное? | Сортировка |
|---|---|---|---|
| `dir(obj)` | **список имён** (только строки) | да (по всему MRO) | да |
| `vars(obj)` | **`__dict__`** объекта (dict: имя→значение) | нет (только instance/class dict) | нет |
| `vars(Cls)` | `dict` атрибутов класса | нет (только один класс, не MRO) | нет |
| `inspect.getmembers(obj)` | **list of `(name, value)` tuples** | да (по MRO) | да (по имени) |
| `inspect.getmembers(obj, predicate=...)` | отфильтрованный список | да | да |

```python
>>> import inspect

# dir() — только имена
>>> dir(datetime)
['MAXYEAR', ..., 'timedelta', 'timezone', 'tzinfo']

# vars() — dict, только для самого объекта
>>> vars(datetime)
MappingProxyType({...})   # у модулей __dict__ — read-only mappingproxy

# inspect.getmembers() — пары (имя, значение)
>>> inspect.getmembers(datetime)
[('MAXYEAR', 9999), ('MINYEAR', 1), ..., ('timedelta', <class 'datetime.timedelta'>), ...]

# inspect.getmembers с фильтром — только классы
>>> inspect.getmembers(datetime, inspect.isclass)
[('date', <class 'datetime.date'>),
 ('datetime', <class 'datetime.datetime'>),
 ('time', <class 'datetime.time'>),
 ('timedelta', <class 'datetime.timedelta'>),
 ('timezone', <class 'datetime.timezone'>),
 ('tzinfo', <class 'datetime.tzinfo'>)]
```

### Практические приёмы с `dir()` { #7.14-prakticheskie }

```python
# 1. Найти все методы объекта по префиксу/суффиксу
>>> [m for m in dir(str) if m.startswith('is')]
['isalnum', 'isalpha', 'isascii', 'isdecimal', 'isdigit', 'isidentifier',
 'islower', 'isnumeric', 'isprintable', 'isspace', 'istitle', 'isupper']

# 2. Отфильтровать dunder-методы (часто мешают)
>>> [m for m in dir(str) if not m.startswith('_')]
['capitalize', 'casefold', 'center', 'count', 'encode', ..., 'upper', 'zfill']

# 3. Найти только «public» методы — без underscores вообще
>>> [m for m in dir(datetime) if not m.startswith('_')]

# 4. Получить атрибут по имени из dir() — через getattr
>>> methods = [m for m in dir(str) if m.startswith('is')]
>>> for m in methods:
...     print(f"{m}: {getattr('abc', m)()}")   # вызывает str.isXXX на 'abc'
isalpha: True
isascii: True
isdecimal: False
...

# 5. Сравнить API двух классов
>>> set(dir(list)) - set(dir(tuple))   # что есть у list, но нет у tuple
{'append', 'clear', 'copy', 'extend', 'insert', 'pop', 'remove', 'reverse', 'sort',
 '__delitem__', '__iadd__', '__imul__', '__reversed__', '__setitem__'}
>>> set(dir(tuple)) - set(dir(list))   # что есть у tuple, но нет у list
{'__getnewargs__'}   # count есть у обоих — это пересечение, а не разница
```

### `dir()` без аргументов — для текущей области видимости { #7.14-bez-argumentov }

```python
>>> x = 1
>>> def f(): pass
>>> import sys
>>> dir()
['__annotations__', '__builtins__', '__doc__', ..., 'f', 'sys', 'x']
```

`dir()` без аргументов возвращает имена в **текущей локальной области**. В REPL это все переменные сессии; внутри функции — локальные имена; на уровне модуля — то же, что `globals().keys()`, но отсортированно.

⚠️ **Ограничения `dir()`**:

- Возвращает **имена**, не значения. Для значений используйте `getattr(obj, name)` в цикле или `inspect.getmembers()`.
- Не показывает атрибуты, реализованные через `__getattr__` (динамические). Если у класса есть хитрый `__getattr__`, который создаёт атрибут на лету — `dir()` его не увидит, если только `__dir__` не переопределён.
- В REPL срабатывает на **любой** объект, включая модули, функции, классы, экземпляры, исключения. Универсальный разведчик.

`dir()` — это самый быстрый способ понять, **что вообще умеет объект**. Запомните: увидели новый класс — первым делом `dir(obj)`, потом уже читайте `help(obj.method)` или доку.


### Бенчмарки к Части VII { #7.14-benchmarki }

**1. `functools.wraps` — цена «правильного» декоратора.**
```python
import timeit, functools
def raw_dec(f):
    def wrapper(*a, **kw): return f(*a, **kw)
    return wrapper
def wraps_dec(f):
    @functools.wraps(f)
    def wrapper(*a, **kw): return f(*a, **kw)
    return wrapper

@raw_dec
def f1(): pass
@wraps_dec
def f2(): pass
# Замер вызова (без учёта одноразовых накладных расходов на декорирование)
print(timeit.timeit(f1, number=5_000_000))   # ≈ 0.55 с
print(timeit.timeit(f2, number=5_000_000))   # ≈ 0.55 с
```
В рантайме `wraps` **не даёт накладных расходов** — он только копирует
`__wrapped__`, `__module__`, `__name__`, `__qualname__`, `__doc__`, `__dict__`
один раз при декорировании. Берите его всегда.

**2. `lru_cache` vs ручная memoization через `dict`.**
```python
from functools import lru_cache
import timeit

@lru_cache(maxsize=None)
def fib_lru(n):
    return n if n < 2 else fib_lru(n-1) + fib_lru(n-2)

_cache = {}
def fib_manual(n):
    if n in _cache: return _cache[n]
    r = n if n < 2 else fib_manual(n-1) + fib_manual(n-2)
    _cache[n] = r
    return r

# fib(20) — 1M вызовов верхнего уровня, кеш тёплый
print(timeit.timeit("fib_lru(20)",    globals=globals(), number=1_000_000))   # ≈ 0.07 с (3.12.14)
print(timeit.timeit("fib_manual(20)", globals=globals(), number=1_000_000))   # ≈ 0.05 с (если кеш не чистить)
# С очисткой кеша перед каждым вызовом (более релевантно реальным workload'ам):
print(timeit.timeit("fib_manual(20); _cache.clear()", globals=globals(), number=1_000_000))  # ≈ 3.5 с
```
На CPython 3.12.14 при тёплом кеше `lru_cache` ≈ 0.07 с на 1M вызовов; `dict`-кеш на "один и тот же ключ" ≈ 0.05 с (немного быстрее, т.к. C-lookup в `_lru_cache_wrapper` имеет небольшую константу). **Главный козырь `lru_cache` — на холодных/cache-miss путях**: при пересчёте `fib(20)` с нуля `lru_cache` делает ~20 рекурсивных вызовов через C-wrapper, а `dict`-вариант — то же, но с Python-overhead на `in`/`[]`/`=`, плюс `lru_cache` потокобезопасен и даёт `cache_info()`/`cache_clear()`. C-реализация `_lru_cache_wrapper` существует с 3.8; на фоне специализаций PEP 659 чистый Python-вариант тоже ускорился, но `lru_cache` остаётся удобнее и безопаснее. **Нет причин** писать свой кеш, кроме случаев с очень специфическими требованиями.

**3. `type()` динамическое создание класса vs `class`.**
```python
import timeit
def via_class():
    class A:
        def m(self): return 1
    return A
def via_type():
    return type("A", (), {"m": lambda self: 1})
# Создание 10 000 классов
print(timeit.timeit(via_class, number=10_000))   # ≈ 0.44 с (зависит от CPU)
print(timeit.timeit(via_type,  number=10_000))   # ≈ 0.36 с
```
`type()` **в ~1.2–1.3× быстрее** при массовом создании классов — нет парсинга тела класса
и построения AST. Но для статического кода разница незаметна. Главный плюс `type()` —
динамичность (метапрограммирование, генерация DTO из схемы).

**4. `eval`/`exec` vs прямая функция — цена интерпретации.**
```python
import timeit
x = 41
# eval строки — каждый раз парсит + компилирует
print(timeit.timeit("eval('x + 1')", globals={'x': x, 'eval': eval}, number=1_000_000))   # ≈ 4.35 с (3.12.14)
# compile один раз, потом eval по code-объекту
code_obj = compile('x + 1', '<s>', 'eval')
print(timeit.timeit("eval(code_obj, {'x': 41})", globals={'code_obj': code_obj, 'eval': eval}, number=100_000))  # ≈ 0.021 с
# Прямая операция
print(timeit.timeit("x + 1", globals={'x': x}, number=1_000_000))                          # ≈ 0.016 с
```
`eval` строки **в ~270× медленнее** прямой операции (4.35 с vs 0.016 с на 1M вызовов). `eval` предкомпилированного code-объекта — в ~30× медленнее прямого кода, но в ~200× быстрее чем парсинг+exec строки каждый раз. На горячих путях — предкомпилируйте или переписывайте на нормальные функции.

**5. `getattr`/`setattr` vs прямой доступ — цена динамического доступа.**
```python
import timeit
class C: pass
c = C(); c.x = 42
print(timeit.timeit("c.x",            globals={'c': c}, number=5_000_000))      # ≈ 0.108 с (3.12.14)
print(timeit.timeit("getattr(c, 'x')", globals={'c': c}, number=5_000_000))     # ≈ 0.208 с — на ~92% медленнее
```
`getattr`/`setattr` проходят через протокол дескрипторов (как обычный `c.x`), но с дополнительным lookup'ом имени в строке. На горячих путях — кешируйте или используйте `operator.attrgetter`.

**6. `importlib.import_module` vs `import` statement.**
```python
import timeit, importlib
# import statement — кешируется в sys.modules после первого
print(timeit.timeit("import json", number=100_000))                                  # ≈ 0.007 с
# import_module — вызов функции + lookup в sys.modules
print(timeit.timeit("importlib.import_module('json')", globals={'importlib': importlib}, number=100_000))  # ≈ 0.047 с — в ~7× медленнее
```
`importlib.import_module` даёт ~6.7× overhead по сравнению с `import` statement на already-imported модулях (по сути — dict lookup vs function call + dict lookup). На горячих путях — кешируйте модуль в переменной.

**7. Decorator overhead — `wraps` vs naked wrapper.**
```python
import timeit, functools
def raw_dec(f):
    def wrapper(*a, **kw): return f(*a, **kw)
    return wrapper
def wraps_dec(f):
    @functools.wraps(f)
    def wrapper(*a, **kw): return f(*a, **kw)
    return wrapper

@raw_dec
def f1(x): return x
@wraps_dec
def f2(x): return x

print(timeit.timeit("f1(41)", globals={'f1': f1}, number=1_000_000))   # ≈ 0.181 с (3.12.14)
print(timeit.timeit("f2(41)", globals={'f2': f2}, number=1_000_000))   # ≈ 0.181 с — идентично
# Голая функция без декоратора для сравнения:
def plain(x): return x
print(timeit.timeit("plain(41)", globals={'plain': plain}, number=1_000_000))   # ≈ 0.050 с — декоратор даёт +262%
```
`@functools.wraps` **не даёт накладных расходов** в рантайме — копирование метаданных происходит один раз при декорировании. Сам wrapper-вызов через `*args, **kw` дорогой (+260% против голой функции), но это цена любой обёртки. Берите `wraps` всегда.

**8. `inspect.signature` — цена интроспекции.**
```python
import inspect, timeit
def f(a, b, c=1, *, d=2): pass
print(timeit.timeit(lambda: inspect.signature(f), number=100_000))   # ≈ 0.89 с (3.12.14)
print(timeit.timeit(lambda: f.__code__.co_varnames,  number=100_000))  # ≈ 0.008 с — в ~110× быстрее
```
`inspect.signature` **в ~110× медленнее** прямого чтения `__code__` — он строит
полноценный `Signature` объект с `Parameter`'ами, дефолтами, аннотациями.
На горячих путях DI-фреймворков — кешируйте по `f`.


