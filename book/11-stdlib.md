# Часть XI. Полезные модули стандартной библиотеки

## 11.1. `functools.lru_cache`, `functools.cache` { #11.1 }

> **→ см. также:** Часть VII (7.4) — `functools.wraps` и общее устройство декораторов; Часть VIII (8.15, бенчмарки) — `OrderedDict`-based LRU как альтернатива C-реализации `lru_cache`.

Мемоизация — кэширование результатов функции по аргументам:

```python
from functools import lru_cache, cache

@lru_cache(maxsize=128)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(100))   # мгновенно — без кэша это была бы экспонента
```

`lru_cache` (LRU = Least Recently Used) хранит последние `maxsize` вызовов. Когда кэш заполняется — вытесняет **наименее недавно использованную** запись (порядок по обращениям, не по времени добавления).

⚠️ **`@lru_cache` без скобок** (Python 3.8+) — `@lru_cache` эквивалентно `@lru_cache(maxsize=128)`.

⚠️ **Позиционные и именованные аргументы создают РАЗНЫЕ ключи кэша**:
```python
@lru_cache
def f(a, b): return a + b
f(1, 2)       # Cache Miss — ключ: (1, 2), ()
f(a=1, b=2)   # Cache Miss! — ключ: (), (('a', 1), ('b', 2))
f(1, b=2)     # Cache Miss! — третий уникальный ключ
# Все три вызова вычисляются заново, хотя результат одинаковый
```
Вызывайте мемоизированные функции в едином стиле (лучше — строго позиционно).

⚠️ **Кэш возвращает ссылку на тот же объект** — если функция возвращает mutable (list, dict), мутация результата повлияет на все последующие вызовы:
```python
@lru_cache
def get_headers(): return {"Content-Type": "application/json"}
h1 = get_headers()
h1["Auth"] = "token1"   # ❌ мутирует объект в кэше!
h2 = get_headers()
print(h2)  # {'Content-Type': '...', 'Auth': 'token1'} — утечка данных!
```
Возвращайте immutable типы (tuple, frozenset, frozen dataclass) или делайте `copy.deepcopy()`.

**`@cache` (Python 3.9+) — без лимита:**

```python
@cache   # эквивалентно @lru_cache(maxsize=None)
def hash_string(s):
    return hashlib.sha256(s.encode()).hexdigest()
```

**`typed=True` — различать типы аргументов:**

```python
@lru_cache(typed=True)
def f(x):
    return x * 2

f(1)      # int 1 → 2
f(1.0)    # float 1.0 → 2.0 (без typed=True — попадёт в кэш, вернёт int 2)
```

**Интроспекция кэша:**

```python
fib.cache_info()
# CacheInfo(hits=98, misses=101, maxsize=128, currsize=101)

fib.cache_clear()   # очистить кэш
```

⚠️ Аргументы должны быть хешируемыми — `list`, `dict`, `set` нельзя, используйте `tuple`, `frozenset`.

⚠️ **Скрытые проблемы при использовании на методах**:

```python
class Service:
    @lru_cache(maxsize=128)
    def get_user(self, user_id):
        return db.fetch(user_id)
```

Если сделать так — кэш живёт на уровне класса (это атрибут **дескриптора** функции), и в нём **навсегда** остаются ссылки на `self` каждого экземпляра, который хоть раз вызывал метод. Это **утечка памяти**: пока жив кэш (а он живёт пока жив класс), не удаляется ни один экземпляр `Service`. На долгоживущих процессах (веб-сервер, демон) это съедает память незаметно.

Если кэш на методах всё-таки нужен — либо делайте кэш на уровне экземпляра через `@property` + свой `dict`, либо используйте `functools.cached_property` (тоже на экземпляре, не на классе):

```python
from functools import cached_property

class Repo:
    @cached_property
    def config(self):
        return load_config()   # считается один раз на экземпляр, умрёт с ним
```

Если нужно кэшировать метод с аргументами на экземпляре — придётся писать обёртку вручную или использовать сторонние библиотеки (например, `cachetools` с `LRUCache` per-instance).

Ещё одно последствие: кэш на методе **общий для всех экземпляров** — то есть `Service().get_user(1)` и `Service().get_user(1)` разделят кэш-попадание, даже если это разные объекты с разными подключениями к БД. Если это не желаемое поведение — кэш должен быть на экземпляре.

## 11.2. `functools.partial` { #11.2 }

«Заморозить» часть аргументов функции, получив новую функцию с оставшимися:

```python
from functools import partial

def power(base, exp):
    return base ** exp

square = partial(power, exp=2)   # фиксируем exp=2
cube = partial(power, exp=3)

print(square(5))   # 25
print(cube(3))      # 27

# С позиционными:
int_base2 = partial(int, base=2)
print(int_base2('1010'))   # 10 — int('1010', base=2)
```

Полезно для callback-ов — передать в `sorted(key=...)`, `map`, `filter`, `apply_async`:

```python
from functools import partial

def send_email(to, subject, body):
    ...

# Колбэк для фреймворка, который передаёт только один аргумент
notify_admin = partial(send_email, 'admin@example.com', subject='Alert')
notify_admin(body='Server down!')
```

⚠️ **`functools.partial` не работает как метод класса** — он не реализует протокол дескрипторов (`__get__`), поэтому `self` не подставляется:
```python
class Cell:
    def set_state(self, state): self.alive = state
    set_alive = partial(set_state, state=True)  # ❌ TypeError: missing 'self'

# ✅ Решение — functools.partialmethod (Python 3.4+):
from functools import partialmethod
class Cell:
    def set_state(self, state): self.alive = state
    set_alive = partialmethod(set_state, state=True)  # ✅ корректно
```

⚠️ **Именованные аргументы можно переопределить при вызове, позиционные — нельзя**:
```python
square = partial(power, exp=2)
square(5)         # 25 (exp=2)
square(5, exp=3)  # 125 — kwargs переопределён!

sub = partial(lambda a, b: a - b, 10)  # 10 зафиксирован как первый аргумент
sub(3)            # 7 (10-3), позиционный аргумент нельзя переопределить
```

⚠️ **У `partial` нет `__name__`** (`__doc__` есть, но общий, не от оборачиваемой функции) — при передаче во фреймворки (Celery, Flask) используйте `functools.update_wrapper(p, p.func)`, он скопирует оба.

## 11.3. `functools.reduce` { #11.3 }

Свертка последовательности в одно значение через бинарную функцию:

```python
from functools import reduce

# Сумма
total = reduce(lambda a, b: a + b, [1, 2, 3, 4])   # 10

# Произведение
product = reduce(lambda a, b: a * b, [1, 2, 3, 4])   # 24

# С аккумулятором-инициализатором
total = reduce(lambda a, b: a + b, [1, 2, 3, 4], 100)   # 110

# Сцепление словарей
merged = reduce(lambda d1, d2: {**d1, **d2}, [{'a':1}, {'b':2}, {'c':3}])
# {'a': 1, 'b': 2, 'c': 3}
```

`reduce(func, iterable, initializer)`:

1. `acc = initializer` (если нет — `acc = iterable[0]`).
2. Для каждого `x` в `iterable`: `acc = func(acc, x)`.
3. Возвращает `acc`.

⚠️ Часто `reduce` — антипаттерн. Для сумм используйте `sum`, для произведений — `math.prod`, для сцепления словарей — `{**d1, **d2}`.

```python
# Вместо:
total = reduce(lambda a, b: a + b, [1, 2, 3])
# Лучше:
total = sum([1, 2, 3])

# Вместо:
from math import prod
product = reduce(lambda a, b: a * b, [1, 2, 3])
# Лучше:
product = prod([1, 2, 3])
```

## 11.4. `weakref` { #11.4 }

Слабые ссылки — указатели на объекты, не препятствующие их сборке мусором:

```python
import weakref

class Big:
    def __init__(self, name):
        self.name = name

obj = Big("huge_data")
ref = weakref.ref(obj)

print(ref())           # <__main__.Big object at 0x...>
print(ref().name)      # "huge_data"

del obj                # удаляем сильную ссылку
print(ref())           # None — объект удалён GC
```

**`WeakValueDictionary` — кэш, который не держит значения:**

```python
class ImageCache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()
    
    def get(self, path):
        img = self._cache.get(path)
        if img is None:
            img = load_image(path)
            self._cache[path] = img
        return img

# Когда последняя сильная ссылка на img исчезнет — он удалится из кэша автоматически
```

**`WeakKeyDictionary` — то же, но по ключам:**

```python
# Кэш-метаданных, привязанных к объектам, не держащий объекты в памяти
metadata = weakref.WeakKeyDictionary()

def set_meta(obj, key, value):
    metadata.setdefault(obj, {})[key] = value
```

**`finalize` — колбэк при удалении объекта:**

```python
def cleanup(name):
    print(f"закрываем {name}")

obj = open('x.txt')
weakref.finalize(obj, cleanup, obj.name)
del obj   # вызовет cleanup('x.txt')

# ⚠️ Ловушка: finalize держит args СИЛЬНО. Передача самого obj аргументом
# (weakref.finalize(obj, cleanup, obj)) удерживает объект — при del obj
# cleanup НЕ вызовется. Передавайте вместо объекта его данные (obj.name, путь).
```

## 11.5. `copy`/`deepcopy` { #11.5 }

```python
import copy

# Поверхностное копирование — копирует ссылки на вложенные объекты
original = [[1, 2], [3, 4]]
shallow = copy.copy(original)
shallow[0].append(99)
print(original)   # [[1, 2, 99], [3, 4]] — внутренний список изменился!

# Глубокое копирование — рекурсивно копирует все вложенные объекты
deep = copy.deepcopy(original)
deep[0].append(100)
print(original)   # [[1, 2, 99], [3, 4]] — НЕ изменился
print(deep)       # [[1, 2, 99, 100], [3, 4]]
```

**Своя логика через `__copy__` и `__deepcopy__`:**

```python
class Node:
    def __init__(self, value, parent=None):
        self.value = value
        self.parent = parent
    
    def __copy__(self):
        # Поверхностная копия — новый объект, но parent тот же
        return Node(self.value, self.parent)
    
    def __deepcopy__(self, memo):
        # memo — словарь id→копия для предотвращения циклов
        if id(self) in memo:
            return memo[id(self)]
        new = Node(self.value)
        memo[id(self)] = new
        new.parent = copy.deepcopy(self.parent, memo)
        return new
```

⚠️ `deepcopy` медленный. Для больших объектов (DataFrame, NumPy array) используйте их собственные методы (`df.copy(deep=True)`, `arr.copy()`).

## 11.6. `warnings` { #11.6 }

Предупреждения — для deprecation, для подсветки проблем без прерывания работы:

```python
import warnings

# Выдать предупреждение
warnings.warn("Это устаревший API", DeprecationWarning)

# Категории:
# - UserWarning (по умолчанию)
# - DeprecationWarning — для разработчиков (по умолчанию игнорируется)
# - FutureWarning — для пользователей (по умолчанию показывается)
# - RuntimeWarning — для подозрительного поведения в рантайме
# - SyntaxWarning — для подозрительного синтаксиса
# - ResourceWarning — unclosed file/socket/etc
```

**Управление фильтрами:**

```python
# Глобально игнорировать категорию
warnings.simplefilter("ignore", DeprecationWarning)

# Действие только в одном блоке
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    legacy_code()

# Конвертировать в исключение
warnings.simplefilter("error", DeprecationWarning)   # DeprecationWarning поднимет исключение

# Один раз показать
warnings.simplefilter("once")
```

**Флаг `-W` и `PYTHONWARNINGS` — те же фильтры снаружи процесса** (не меняя код):

```bash
$ python3 -W error::DeprecationWarning script.py    # категория → исключение
$ python3 -W ignore::UserWarning script.py          # заглушить категорию
$ python3 -W error::ResourceWarning -W once::SyntaxWarning script.py   # фильтров может быть несколько
$ PYTHONWARNINGS="ignore::DeprecationWarning" python3 script.py        # то же через окружение
```

Формат записи — `action::category::module::lineno` — в точности аргументы `warnings.filterwarnings`. Фильтры применяются по порядку, **последний совпавший побеждает**, поэтому `-W` перекрывает `PYTHONWARNINGS` (его фильтры добавляются позже):

```bash
$ PYTHONWARNINGS=ignore python3 -W error::DeprecationWarning -c "import warnings; warnings.warn('old', DeprecationWarning)"
Traceback (most recent call last):
  ...
DeprecationWarning: old
```

Комбо `-X warn_default_encoding -W error::EncodingWarning` превращает «забыл `encoding=`» в ошибку старта (см. 9.1) — жёсткий линтер для I/O-кода.

**Свои категории:**

```python
class MyCustomWarning(UserWarning):
    pass

warnings.warn("...", MyCustomWarning)
```

## 11.7. `__all__` { #11.7 }

`__all__` — список имён, которые экспортируются по `from module import *`:

```python
# mymodule.py
__all__ = ['public_func', 'PublicClass']

def public_func():
    pass

def _private_func():
    pass

class PublicClass:
    pass

class _PrivateClass:
    pass
```

```python
from mymodule import *
print(public_func)   # OK
print(PublicClass)   # OK
print(_private_func)  # NameError — не в __all__
print(_PrivateClass)  # NameError
```

⚠️ Без `__all__` `from module import *` экспортирует все имена, не начинающиеся с `_`. С `__all__` — только из списка.

⚠️ **`__all__` не скрывает** имена от `import module; module._private_func` — это лишь про `*`-импорт. Для настоящей приватности — отдельный модуль или префикс `_`.

## 11.8. `pickle` и его опасности { #11.8 }

`pickle` сериализует почти любой Python-объект. **Но**: `pickle.loads(data)` исполняет произвольный код через `__reduce__`:

```python
import pickle, os

class Malicious:
    def __reduce__(self):
        # pickle.loads этого объекта вызовет os.system('echo HACKED')
        return (os.system, ('echo "HACKED"',))

# Злонамеренная "строка"
payload = pickle.dumps(Malicious())
# ...
pickle.loads(payload)   # напечатает "HACKED" — команда выполнилась!
```

`__reduce__` возвращает callable и аргументы, которые `pickle.loads` вызовет, чтобы реконструировать объект. Любой callable — включая `os.system`, `subprocess.run`, `eval`.

⚠️ **Никогда не `pickle.loads` пользовательские данные** — это **RCE** (Remote Code Execution).

**Альтернативы:**

- `json` — безопасный, но только для простых типов (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`).
- `dataclasses` + `dataclasses.asdict()` + `json` — для дата-классов.
- `protobuf`, `msgpack` — для продакшена.
- `marshal` — для внутренних файлов Python (тоже небезопасен).

## 11.9. `tracemalloc` { #11.9 }

Профайлер памяти — показывает, где выделялись объекты:

```python
import tracemalloc

tracemalloc.start(10)   # сохраняем 10 кадров стека для каждого блока

# ... код, который может течь ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
#  ваш_файл.py:42: size=10 MiB, count=1000, average=10 KiB
#  ...
```

**Сравнение двух снапшотов — найти утечку:**

```python
tracemalloc.start(10)

# Первый снимок
snap1 = tracemalloc.take_snapshot()
# ... код, который подозревается в утечке ...
heavy_operation()

# Второй снимок
snap2 = tracemalloc.take_snapshot()

# Разница
for stat in snap2.compare_to(snap1, 'lineno')[:10]:
    print(stat)
# ваш_файл.py:55: size=5.2 MiB (+5.2 MiB), count=520 (+520)
```

**По конкретному объекту:**

```python
tracemalloc.start()
# ... код ...
snapshot = tracemalloc.take_snapshot()

# Найти выделения, чей файл подходит под маску (fnmatch) —
# Filter фильтрует по ИМЕНИ ФАЙЛА, не по функции:
filters = [tracemalloc.Filter(True, "*/leaky_module.py")]
filtered = snapshot.filter_traces(filters)
for stat in filtered.statistics('traceback'):
    print(stat.traceback)
```

## 11.10. `operator` модуль { #11.10 }

Функциональные аналоги операторов — передаются как callback'и:

```python
from operator import (
    add, sub, mul, truediv, mod, pow,
    eq, ne, lt, le, gt, ge,
    and_, or_, not_, xor,
    itemgetter, attrgetter, methodcaller,
    neg, pos, abs, truth, contains,
)

# Арифметика
add(2, 3)    # 5
mul(2, 3)    # 6
pow(2, 10)   # 1024

# Сравнения
eq(2, 2)   # True
lt(2, 3)   # True

# itemgetter — получить элемент по индексу/ключу
get_first = itemgetter(0)
get_first([1, 2, 3])   # 1

get_name = itemgetter('name')
get_name({'name': 'Alice', 'age': 30})   # 'Alice'

# attrgetter — получить атрибут
get_x = attrgetter('x')
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
get_x(Point(1, 2))   # 1

# Несколько атрибутов сразу
get_xy = attrgetter('x', 'y')
get_xy(Point(1, 2))   # (1, 2)

# methodcaller — вызвать метод
upper = methodcaller('upper')
upper('hello')   # 'HELLO'

replace_a = methodcaller('replace', 'a', 'X')
replace_a('banana')   # 'bXnXnX'
```

**Применения:**

```python
# Сортировка по ключу
sorted(users, key=attrgetter('age'))
sorted(pairs, key=itemgetter(1))   # по второму элементу

# reduce
from functools import reduce
reduce(add, [1, 2, 3, 4])   # 10 — вместо lambda a, b: a + b
reduce(mul, [1, 2, 3, 4])   # 24

# Замена стандартных операторов в функциональном стиле
list(map(add, [1, 2, 3], [10, 20, 30]))   # [11, 22, 33]
```

Главный кейс — передавать операторы как объекты в `map`, `reduce`, `sorted(key=...)`, конвейеры обработки данных.

## 11.11. `functools.singledispatch`, `cached_property`, `total_ordering` { #11.11 }

### `singledispatch` — полиморфизм по типу первого аргумента { #11.11-singledispatch }

```python
from functools import singledispatch

@singledispatch
def to_json(obj):
    raise TypeError(f"Не умею сериализовать {type(obj)}")

@to_json.register
def _(obj: dict):
    return '{' + ', '.join(f'"{k}": {to_json(v)}' for k, v in obj.items()) + '}'

@to_json.register
def _(obj: list):
    return '[' + ', '.join(to_json(x) for x in obj) + ']'

@to_json.register(str)
def _(obj):
    return f'"{obj}"'

@to_json.register(int)
def _(obj):
    return str(obj)

print(to_json({'name': 'Alice', 'age': 30}))
# {"name": "Alice", "age": 30}
```

Регистрация через аннотацию типа (если имя `_` — берётся из `__annotations__`).

Внешние модули могут **добавлять** новые варианты для вашей функции без правки исходника:

```python
# В чужом модуле:
import datetime
@to_json.register
def _(obj: datetime.datetime):
    return f'"{obj.isoformat()}"'
```

⚠️ `singledispatch` работает только по типу **первого аргумента**. Для метода класса — `singledispatchmethod` (Python 3.8+).

### `cached_property` — `@property` с кэшем { #11.11-cachedproperty }

```python
from functools import cached_property

class DataFrame:
    def __init__(self, data):
        self.data = data
    
    @cached_property
    def stats(self):
        # Считается один раз, потом кэшируется
        print("Computing stats...")
        return {'mean': sum(self.data) / len(self.data), 'max': max(self.data)}

df = DataFrame([1, 2, 3, 4])
print(df.stats)   # Computing stats... {'mean': 2.5, 'max': 4}
print(df.stats)   # {'mean': 2.5, 'max': 4} — без вычисления
```

В отличие от `@property` (который вычисляется каждый раз), `cached_property` считает **один раз** и хранит в `__dict__`. Чтобы пересчитать — удалите атрибут: `del df.stats`.

⚠️ Требует `__dict__` (не работает с `__slots__` без явного `'__dict__'` в слотах). Не потокобезопасен (для многопоточного — `functools.cached_property` + `threading.Lock`).

### `total_ordering` — дополнить `__lt__` до всех сравнений { #11.11-totalordering }

```python
from functools import total_ordering

@total_ordering
class Student:
    def __init__(self, name, grade):
        self.name = name
        self.grade = grade
    
    def __eq__(self, other):
        return self.grade == other.grade
    
    def __lt__(self, other):
        return self.grade < other.grade
    # И всё! total_ordering добавит __le__, __gt__, __ge__

s1 = Student("Alice", 90)
s2 = Student("Bob", 85)
print(s1 > s2)     # True — автоматически сгенерировано
print(s1 >= s2)    # True
print(s1 != s2)    # True
```

Требуется определить `__eq__` и один из (`__lt__`, `__le__`, `__gt__`, `__ge__`). Остальные сгенерируются из этих двух.

## 11.12. `queue` — Queue, LifoQueue, PriorityQueue, SimpleQueue { #11.12 }

Потокобезопасные очереди для producer/consumer паттерна в `threading`.

```python
from queue import Queue, LifoQueue, PriorityQueue, SimpleQueue
import threading, time

# Queue — FIFO
q = Queue(maxsize=10)
q.put(1)
q.put(2)
print(q.get())   # 1
print(q.get())   # 2

# LifoQueue — LIFO (стек)
lq = LifoQueue()
lq.put(1); lq.put(2); lq.put(3)
print(lq.get())   # 3 (последний)
print(lq.get())   # 2

# PriorityQueue — приоритеты (минимальный первым)
pq = PriorityQueue()
pq.put((3, "low"))
pq.put((1, "high"))
pq.put((2, "medium"))
print(pq.get())   # (1, 'high')
print(pq.get())   # (2, 'medium')

# SimpleQueue — без maxsize, без приоритетов, быстрее
sq = SimpleQueue()
sq.put(1)
sq.put(2)
print(sq.get())   # 1
```

**Blocking vs non-blocking:**

```python
q = Queue(maxsize=2)
q.put(1)
q.put(2)
q.put(3, block=False)   # queue.Full — не ждать
q.put(3, timeout=1)     # ждать 1 секунду, потом queue.Full

q.get(block=False)     # если пусто — queue.Empty
q.get(timeout=1)       # ждать 1 секунду, потом queue.Empty

# Неблокирующий с default:
val = q.get_nowait()   # = get(block=False)
q.put_nowait(x)        # = put(block=False)
```

**Producer/consumer пример:**

```python
import threading, queue

def worker(q):
    while True:
        item = q.get()
        if item is None:
            q.task_done()
            break
        print(f"Обрабатываю {item}")
        q.task_done()

q = queue.Queue()
threads = [threading.Thread(target=worker, args=(q,)) for _ in range(3)]
for t in threads:
    t.start()

for i in range(10):
    q.put(i)

q.join()   # ждать, пока все task_done() не вызовут
for _ in threads:
    q.put(None)
for t in threads:
    t.join()
```

⚠️ `queue.Queue` — для `threading`. Для `asyncio` — `asyncio.Queue` (см. §4.7).

## 11.13. `reprlib` — ограничение repr для больших структур { #11.13 }

`reprlib` — для управления тем, как `repr()` показывает большие объекты (рекурсивно обрезает).

```python
import reprlib

# Длинный список
big = list(range(1000))
print(repr(big))
# [0, 1, 2, ..., 999] (полностью)

print(reprlib.repr(big))
# [0, 1, 2, 3, 4, 5, ...]  — обрезано (максимум 6 элементов по умолчанию)

# Длинная строка
print(reprlib.repr("a" * 1000))
# 'aaaaaaaaaaaa...aaaaaaaaaaaaa' (30 chars)

# Свои настройки
r = reprlib.Repr()
r.maxlist = 5       # максимум элементов списка
r.maxstring = 50    # максимум символов строки
r.maxlevel = 3      # глубина рекурсии
print(r.repr({'a': [1, 2, 3, 4, 5, 6, 7], 'b': {'c': 'd'}}))
```

Полезно для отладки — большие структуры не засоряют вывод. Используется внутри `functools` (recursive_repr), `collections`, `asyncio` (format_helpers), `pydoc`, `pdb`; `pprint` и `dataclasses` имеют собственную логику обрезки.

## 11.14. `os.scandir`, `os.fwalk` — продвинутый обход файловой системы { #11.14 }

### `os.scandir` — быстрее `os.listdir` { #11.14-osscandir }

```python
import os

# Старый способ — медленный
for name in os.listdir('/tmp'):
    path = os.path.join('/tmp', name)
    if os.path.isdir(path):
        print(f"DIR:  {name}")
    elif os.path.isfile(path):
        print(f"FILE: {name}")

# Через scandir — быстрее, потому что информация о типе уже в DirEntry
with os.scandir('/tmp') as entries:
    for entry in entries:
        if entry.is_dir():
            print(f"DIR:  {entry.name}")
        elif entry.is_file():
            print(f"FILE: {entry.name} ({entry.stat().st_size} bytes)")
```

`scandir` возвращает `DirEntry` объекты, которые кэшируют данные каталога: `is_dir()`/`is_file()` обычно обходятся без syscall (тип берётся из readdir, кроме редкого DT_UNKNOWN), а `stat()` делает syscall один раз и кэширует результат.

### `os.walk` — стандартный обход дерева { #11.14-oswalk }

```python
for root, dirs, files in os.walk('/home/user'):
    for file in files:
        if file.endswith('.py'):
            print(os.path.join(root, file))
```

`walk` — генератор, который лениво обходит дерево. `root` — текущий каталог, `dirs` — подкаталоги, `files` — файлы в нём.

**Оптимизация**: можно изменять `dirs` inplace, чтобы пропустить подкаталоги:

```python
for root, dirs, files in os.walk('.'):
    # Пропустить .git, __pycache__, node_modules
    dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules'}]
    # Использование dirs[:] = ... изменяет список inplace
    
    for file in files:
        if file.endswith('.py'):
            print(os.path.join(root, file))
```

⚠️ Важно: `dirs[:] = ...` (присваивание срезу) изменяет список, который `walk` использует дальше. Без `[:]` создаётся новый список — `walk` про изменения не узнает.

### `os.fwalk` — с файловыми дескрипторами { #11.14-osfwalk }

```python
for root, dirs, files, root_fd in os.fwalk('/home/user'):
    print(root, dirs, files)
    # root_fd — файловый дескриптор каталога
    # Можно использовать с os.open(..., dir_fd=root_fd) для избежания TOCTOU
```

`fwalk` использует `*at` системные вызовы (`openat`, `readdir`) — более безопасно (нет race conditions типа symlink attacks). Используется реже, но в security-чувствительном коде — обязательно.

### `pathlib` — современная альтернатива { #11.14-pathlib }

```python
from pathlib import Path

# Рекурсивно все .py файлы:
for p in Path('/home/user').rglob('*.py'):
    print(p)

# По размеру:
for p in Path('/tmp').iterdir():
    if p.is_file():
        print(p.stat().st_size, p)
```

## 11.15. `logging` — стандартная библиотека логирования { #11.15 }

```python
import logging

# Базовая настройка
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    filename='app.log',
)
log = logging.getLogger(__name__)

log.debug("debug message")        # не пишется, level=INFO
log.info("Processing request")     # пишется
log.warning("Deprecated API used")
log.error("Failed to save")
log.critical("System down")
log.exception("With traceback")    # = log.error + traceback
```

**Иерархия логгеров** — `app.api.v1` наследует настройки от `app.api`, тот от `app`, тот от root:

```python
api_log = logging.getLogger('app.api')
api_log.setLevel(logging.DEBUG)

v1_log = logging.getLogger('app.api.v1')
v1_log.info("from v1")   # хендлеры НЕ копируются вниз: запись propagируется вверх (обработают root-хендлеры, если настроены)
```

**Handlers — куда писать:**

```python
logger = logging.getLogger('myapp')
logger.setLevel(logging.DEBUG)

# В файл
file_handler = logging.FileHandler('app.log')
file_handler.setLevel(logging.DEBUG)

# В консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# С форматом
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
```

**RotatingFileHandler** — ротация по размеру:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
# Создаст app.log, app.log.1, app.log.2, ... при достижении 10 MB
```

**TimedRotatingFileHandler** — по времени:

```python
from logging.handlers import TimedRotatingFileHandler
handler = TimedRotatingFileHandler('app.log', when='midnight', backupCount=7)
# Ротация каждый день в полночь, хранить 7 дней
```

**dictConfig** — конфигурация через словарь:

```python
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'verbose': {'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'myapp': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

## 11.16. `signal` и `atexit` { #11.16 }

### `signal` — обработка Unix-сигналов { #11.16-signal }

```python
import signal

def handle_sigterm(signum, frame):
    print(f"Got signal {signum}, gracefully shutting down...")
    cleanup()
    sys.exit(0)

# SIGTERM — стандартный "soft kill"
signal.signal(signal.SIGTERM, handle_sigterm)

# SIGINT — Ctrl+C
signal.signal(signal.SIGINT, handle_sigterm)

# SIGALRM — таймер (только Unix)
def timeout_handler(signum, frame):
    raise TimeoutError("Took too long")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)   # через 5 секунд поднимется TimeoutError
try:
    long_running()
finally:
    signal.alarm(0)   # отменить
```

⚠️ `signal` работает только в главном потоке: в другом потоке — `ValueError: signal only works in main thread`. В asyncio используйте `loop.add_signal_handler` (см. ниже).

### `atexit` — финализаторы при выходе { #11.16-atexit }

```python
import atexit

def cleanup():
    print("Doing cleanup")

atexit.register(cleanup)
atexit.register(cleanup, additional_arg=True)

# Можно unregister:
atexit.unregister(cleanup)

print("Program running...")
# При sys.exit() или нормальном завершении — вызовутся в обратном порядке
```

⚠️ `atexit` НЕ вызывается при:

- `os._exit()` (hard exit)
- `SIGKILL` (kill -9)
- Segfault

Только при нормальном завершении или `sys.exit()`. Если нужно гарантированно — `signal.signal(SIGTERM, ...)` + cleanup.

### Типичные Unix-сигналы для daemon-процессов { #11.16-tipichnye }

| Сигнал | Номер | Когда приходит | Типичная реакция |
|---|---|---|---|
| `SIGINT` | 2 | Ctrl+C в терминале | graceful shutdown |
| `SIGTERM` | 15 | `kill <pid>` (без -9) | graceful shutdown, стандарт для systemd/k8s |
| `SIGHUP` | 1 | Терминал закрылся / `kill -HUP` | reload конфига (классика daemon'ов) |
| `SIGKILL` | 9 | `kill -9` | нельзя перехватить, процесс убивается ОС |
| `SIGSTOP` | 19 | `kill -STOP` | нельзя перехватить, процесс замораживается |
| `SIGUSR1`, `SIGUSR2` | 10, 12 | пользовательские | любая логика: dump стека, rotate логов |
| `SIGALRM` | 14 | `signal.alarm(N)` | таймер (только Unix) |
| `SIGCHLD` | 17 | дочерний процесс завершился | `wait()` для reaping (иначе зомби) |

### Связка `signal` + `atexit` для graceful shutdown { #11.16-svyazka }

В production нужно обрабатывать и `SIGTERM` (от оркестратора), и `SIGINT` (от разработчика в Ctrl+C), и нормальный выход через `sys.exit`:

```python
import signal, sys, atexit, threading

shutdown_requested = threading.Event()

def graceful_shutdown(signum, frame):
    print(f"\nПолучен сигнал {signum}, завершаемся...", flush=True)
    shutdown_requested.set()   # сигнал фоновым задачам остановиться
    # НЕ вызываем sys.exit здесь — пусть основной цикл сам дойдёт до выхода
    # и atexit-хуки отработают нормально

signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)

@atexit.register
def final_cleanup():
    if not shutdown_requested.is_set():
        return   # аварийный выход — не делаем долгий cleanup
    print("Cleanup: закрываем соединения с БД...", flush=True)
    db.close()
    print("Cleanup: flush логов...", flush=True)
    log_handler.flush()

# Основной цикл
while not shutdown_requested.is_set():
    process_one_request()
    shutdown_requested.wait(timeout=0.1)  # таймаут, чтобы не крутить впустую

print("Завершение работы")
# При выходе из main — atexit.register-хуки отработают автоматически
```

⚠️ **Что НЕ делает `signal.signal`**:

- Не работает в потоках, кроме главного (raise `ValueError`).
- В asyncio-приложениях — обработчик вызывается между корутинами, не прерывает текущую. Для асинхронной обработки — `loop.add_signal_handler` (Unix-only).
- Не перехватывает `SIGKILL` и `SIGSTOP` — их невозможно перехватить в принципе.
- На Windows поддерживаются только `SIGINT`, `SIGBREAK`, `SIGTERM` (но `SIGTERM` эмулируется через `TerminateProcess`), `SIGALRM` не работает.

## 11.17. `datetime`, `timedelta`, `timezone` { #11.17 }

```python
import datetime

# Создание
now = datetime.datetime.now()         # локальное время
utcnow = datetime.datetime.now(datetime.timezone.utc)   # UTC
dt = datetime.datetime(2026, 9, 5, 12, 30, 0)   # конкретное
date = datetime.date(2026, 9, 5)
time = datetime.time(12, 30, 0)

# ISO-формат (взаимодействие с API)
print(utcnow.isoformat())   # '2026-09-05T12:30:00.123456+00:00'
parsed = datetime.datetime.fromisoformat('2026-09-05T12:30:00+00:00')

# strptime/strftime — человекочитаемые форматы
dt = datetime.datetime.strptime('2026-09-05', '%Y-%m-%d')
print(dt.strftime('%d.%m.%Y'))   # '05.09.2026'

# timestamp (Unix epoch)
ts = datetime.datetime.now().timestamp()   # float, секунды с 1970 UTC
back = datetime.datetime.fromtimestamp(ts)

# timedelta — разница
delta = datetime.timedelta(days=7, hours=3)
next_week = datetime.datetime.now() + delta
diff = datetime.datetime(2026, 12, 31) - datetime.datetime(2026, 1, 1)
print(diff.days)         # 364
print(diff.total_seconds())

# timezone-aware vs naive
naive = datetime.datetime(2026, 9, 5, 12, 0)   # без tzinfo
aware = datetime.datetime(2026, 9, 5, 12, 0, tzinfo=datetime.timezone.utc)

# Сравнение: naive vs aware — TypeError
# aware vs aware — OK, конвертирует tz
# naive vs naive — OK

# Конвертация tz
moscow_tz = datetime.timezone(datetime.timedelta(hours=3))
aware_moscow = aware.astimezone(moscow_tz)

# zoneinfo — база tz (Python 3.9+)
from zoneinfo import ZoneInfo
tz_msk = ZoneInfo('Europe/Moscow')
aware_msk = datetime.datetime.now(tz_msk)
```

⚠️ Всегда используйте **tz-aware** datetime в коде, который работает с разными часовыми поясами. Naive datetime — главная причина багов в коде, который работает с временем.

## 11.18. `bisect` и `heapq` — быстрые операции на отсортированных данных { #11.18 }

### `bisect` — бинарный поиск в отсортированном списке { #11.18-bisect }

```python
import bisect

sorted_list = [1, 3, 5, 7, 9, 11]

# Найти позицию для вставки (без вставки)
print(bisect.bisect_left(sorted_list, 6))   # 3 — место для 6
print(bisect.bisect_right(sorted_list, 5))  # 3 — позиция после 5

# Вставить, сохраняя отсортированность
bisect.insort(sorted_list, 6)
print(sorted_list)   # [1, 3, 5, 6, 7, 9, 11]

# bisect_left vs bisect_right — для дубликатов
nums = [1, 2, 2, 2, 3]
print(bisect.bisect_left(nums, 2))   # 1 — первая позиция 2
print(bisect.bisect_right(nums, 2))  # 4 — позиция после последней 2
```

O(log n) для поиска, O(n) для вставки (из-за сдвига).

### `heapq` — куча (heap) { #11.18-heapq }

Куча — список, поддерживающий быстрое извлечение минимума. Не сортирует весь список, но всегда даёт O(1) на минимум и O(log n) на insert/extract.

```python
import heapq

# Создать кучу из списка (in-place)
nums = [3, 1, 4, 1, 5, 9, 2, 6]
heapq.heapify(nums)   # in-place → [1, 1, 2, 3, 5, 9, 4, 6]

# Добавить
heapq.heappush(nums, 0)   # теперь минимум 0

# Достать минимум
print(heapq.heappop(nums))   # 0
print(heapq.heappop(nums))   # 1

# Получить N наименьших/наибольших
print(heapq.nsmallest(3, [3, 1, 4, 1, 5, 9]))   # [1, 1, 3]
print(heapq.nlargest(2, [3, 1, 4, 1, 5, 9]))    # [9, 5]
```

**Применения:**

- Очередь с приоритетом на минимуме (быстрее `PriorityQueue`).
- Top-N: например, 10 самых больших чисел из потока — `heapq.nlargest(10, stream)`.
- Слияние K отсортированных списков: `heapq.merge(*sorted_lists)`.

```python
# Очередь с приоритетом
import heapq, itertools

pq = []   # список (tuple, value)
counter = itertools.count()

def add_task(priority, task):
    heapq.heappush(pq, (priority, next(counter), task))

def pop_task():
    return heapq.heappop(pq)[2]   # возвращает task

add_task(3, "low")
add_task(1, "high")
add_task(2, "medium")

print(pop_task())   # "high"
print(pop_task())   # "medium"
print(pop_task())   # "low"
```

## 11.19. `csv`, `json`, `urllib.parse` { #11.19 }

### `csv` — чтение/запись CSV { #11.19-csv }

```python
import csv

# Запись
with open('data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['name', 'age'])
    writer.writerow(['Alice', 30])
    writer.writerow(['Bob', 25])

# DictWriter/DictReader
with open('data.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'age'])
    writer.writeheader()
    writer.writerow({'name': 'Alice', 'age': 30})

with open('data.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row['name'], row['age'])

# Разные диалекты
csv.writer(f, dialect='excel')   # стандартный Excel
csv.writer(f, dialect='excel-tab')   # tab-separated

# Свой диалект
csv.register_dialect('myformat', delimiter=';', quotechar='"')
```

### `json` — JSON { #11.19-json }

```python
import json

# dumps/loads — строки
data = {'name': 'Alice', 'age': 30, 'tags': ['admin', 'user']}
s = json.dumps(data)   # в строку
print(s)   # '{"name": "Alice", "age": 30, "tags": ["admin", "user"]}'
back = json.loads(s)   # обратно

# dump/load — файлы
with open('data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

with open('data.json') as f:
    data = json.load(f)

# Параметры
json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=str)
# indent — отступы (читаемый)
# sort_keys — сортировать ключи
# ensure_ascii=False — не экранировать не-ASCII (русский)
# default=str — fallback для неизвестных типов (например, datetime)

# Свой сериализатор/десериализатор
import datetime  # для примера ниже

class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)

json.dumps({'ts': datetime.datetime.now()}, cls=MyEncoder)

# json.tool — CLI для красивого вывода
# $ echo '{"x":1}' | python -m json.tool
```

⚠️ `json.loads` по умолчанию **принимает** `NaN`/`Infinity`/`-Infinity` (это расширение сверх стандарта: `json.loads('NaN')` → `nan`). Для строгого JSON передайте `parse_constant`, поднимающий `ValueError`; `json.dumps` тоже пишет `NaN` по умолчанию (`allow_nan=True`).

### `urllib.parse` — работа с URL { #11.19-urllibparse }

```python
from urllib.parse import urlparse, parse_qs, urlencode, urljoin

# Разбор URL
parsed = urlparse('https://example.com/path?x=1&y=2#frag')
print(parsed.scheme)    # 'https'
print(parsed.netloc)    # 'example.com'
print(parsed.path)      # '/path'
print(parsed.query)     # 'x=1&y=2'
print(parsed.fragment)  # 'frag'

# Параметры запроса в dict
qs = parse_qs('x=1&y=2&y=3')   # {'x': ['1'], 'y': ['2', '3']}
qs_single = {k: v[0] for k, v in qs.items()}

# Сборка параметров
urlencoded = urlencode({'x': 1, 'y': 'hello world'})
# 'x=1&y=hello+world'

# Склейка base + relative
full = urljoin('https://example.com/api/v1/', '../v2/users')
# 'https://example.com/api/v2/users'
```

## 11.20. `mmap` — memory-mapped files { #11.20 }

`mmap` — отображение файла в память. Большие файлы читаются как память (через страничный кэш ОС, страницы подгружаются по требованию), не загружаясь целиком в RAM.

```python
import mmap

# Открыть файл и mmap-нуть
with open('huge.bin', 'r+b') as f:
    mm = mmap.mmap(f.fileno(), 0)   # 0 = весь файл
    
    # Читать как bytes (через индекс)
    print(mm[0:10])   # первые 10 байт
    
    # Записать (если 'r+b')
    mm[0:4] = b'HEAD'
    
    # Итерация по строкам
    for line in iter(mm.readline, b''):
        process(line)
    
    mm.close()
```

### `find()` / `rfind()` — поиск без загрузки в RAM { #11.20-find }

Главное преимущество `mmap` для больших файлов — поиск подстроки **без чтения файла в Python**. Поиск идёт на C-уровне внутри CPython (`mmapmodule.c`) и не аллоцирует промежуточных Python-объектов:

```python
with open('huge.log', 'rb') as f:
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    
    # Найти первое вхождение (возвращает смещение или -1)
    pos = mm.find(b'ERROR')
    if pos != -1:
        # Прочитать контекст: 200 байт до, 500 после
        start = max(0, pos - 200)
        end = min(len(mm), pos + 500)
        print(mm[start:end].decode('utf-8', errors='replace'))
    
    # Найти последнее вхождение
    last_pos = mm.rfind(b'ERROR')
    
    # Все вхождения — через find с аргументом start:
    positions = []
    p = 0
    while True:
        p = mm.find(b'ERROR', p)
        if p == -1: break
        positions.append(p)
        p += 1
    print(f"Найдено {len(positions)} совпадений")
```

⚠️ `find`/`rfind` работают только на **bytes** (`mmap.mmap` всегда байтовый, не str). Для текстового поиска — `b'ERROR'`, не `'ERROR'`.

### Случайный доступ через `seek()` и срезы { #11.20-sluchaynyy }

`mmap` поддерживает оба способа — `seek` (как у file) и индексацию (как у bytes). ⚠️ Срезы на mmap **копируют** данные: каждый срез — новый объект `bytes` (`mm[0:4] is mm[0:4]` → `False`). Zero-copy — только `memoryview` (способ 3 ниже):

```python
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

# Способ 1: seek + read (как у file)
mm.seek(1024 * 1024 * 100)   # перейти на 100 MB
chunk = mm.read(4096)        # прочитать 4 KB

# Способ 2: срезы (как у bytes) — короче
chunk = mm[1024*1024*100 : 1024*1024*100 + 4096]

# Способ 3: memoryview — zero-copy
mv = memoryview(mm)
chunk = mv[100_000_000:100_004_096]   # не копирует, пока не понадобится
```

### `MAP_SHARED` — разделяемая память между процессами { #11.20-mapshared }

Когда несколько процессов должны работать с одним и тем же регионом памяти, `mmap` с `MAP_SHARED` даёт дешёвый IPC — без pickle, без очередей, без sockets. Изменения, сделанные одним процессом, **сразу** видны другим:

```python
import mmap, os

# Создать общий файл (или /dev/shm для in-memory)
shared_path = '/tmp/shared.bin'
with open(shared_path, 'w+b') as f:
    f.write(b'\x00' * 4096)   # 4 KB общий регион
    f.flush()
    
    # Префикс MAP_SHARED (по умолчанию на Unix, но явно для переносимости):
    mm = mmap.mmap(f.fileno(), 4096, flags=mmap.MAP_SHARED)
    
    # Записать данные
    mm[0:4] = b'PING'
    print("Ожидание ответа от другого процесса...")
    while mm[0:4] != b'PONG':
        pass   # busy-wait; в реальном коде — sleep или pipe-сигнал
    print("Получен PONG")
```

⚠️ На Windows `MAP_SHARED` работает только для **файлов** (не анонимной памяти). Для анонимной shared memory между процессами на всех платформах — `multiprocessing.shared_memory` (Python 3.8+), см. ниже.

### `multiprocessing.shared_memory` — кроссплатформенная shared memory { #11.20-multiprocessingsharedmemory }

Python 3.8+ даёт высокоуровневую обёртку над `mmap` для IPC между процессами:

```python
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory
from multiprocessing.managers import SharedMemoryManager

def worker(shm_name):
    # Подключиться к существующему сегменту из другого процесса
    shm = SharedMemory(shm_name)
    try:
        # Прочитать данные, записанные родителем
        data = bytes(shm.buf[:5])   # buf[:100] дал бы b'HELLO' + 95 нулевых байт
        print(f"Child получил: {data!r}")
        # Ответить
        shm.buf[100:104] = b'DONE'
    finally:
        shm.close()

if __name__ == '__main__':
    with SharedMemoryManager() as smm:
        # Создать сегмент 1 KB (авто-удалится при выходе из with)
        shm = smm.SharedMemory(size=1024)
        shm.buf[:5] = b'HELLO'
        
        p = Process(target=worker, args=(shm.name,))
        p.start()
        p.join()
        
        print(f"Родитель увидел ответ: {bytes(shm.buf[100:104])!r}")
# HELLO → DONE
```

Преимущества над pipes/queues:

- **Без сериализации** — данные в «сыром» виде, без pickle.
- **Произвольный доступ** — процессы могут читать/писать любое смещение, не только поток.
- **Мгновенная видимость** — изменения видны всем процессам без явной отправки.

Минусы:

- **Синхронизация на тебе** — `multiprocessing.Lock` или `mmap`+атомики. Без этого — race conditions.
- **Размер фиксирован** при создании; для динамических данных — `multiprocessing.Array` или `queue.Queue`.

### `access=` — режимы доступа { #11.20-access }

| Флаг | Чтение | Запись | Синхронизация с файлом |
|---|---|---|---|
| `ACCESS_WRITE` (по умолчанию для `'r+b'`) | ✅ | ✅ | ✅ изменения пишутся в файл |
| `ACCESS_READ` | ✅ | ❌ | — (только чтение, файл должен быть открыт для чтения) |
| `ACCESS_COPY` | ✅ | ✅ | ❌ copy-on-write — изменения в памяти, файл не трогается |

```python
# Copy-on-write: можно "модифицировать" mmap, но файл останется нетронутым
mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_COPY)
mm[0:4] = b'TEST'   # изменяет только память, не файл
```

### ⚠️ Платформенные особенности { #11.20-platformennye }

| Платформа | Что отличается |
|---|---|
| **Linux** | `MAP_SHARED` / `MAP_PRIVATE` работают как в POSIX; `/dev/shm` — tmpfs для in-memory shared (без файла на диске). `mmap.ANONYMOUS` поддерживается. |
| **macOS** | То же, что Linux, но `/dev/shm` нет — используй `tempfile` или `multiprocessing.shared_memory`. |
| **Windows** | `MAP_SHARED` эмулируется через `CreateFileMapping`; анонимная память — `mmap.mmap(-1, length)` (fileno=-1), фиктивный файл не нужен. `tagname` — необязательное имя сегмента для межпроцессного шаринга. `ACCESS_COPY` ведёт себя иначе. |

Универсальный совет: если нужен IPC между процессами — используй `multiprocessing.shared_memory` (Python 3.8+), он скрывает платформенные различия. Чистый `mmap` — для работы с большими файлами в одном процессе.

> **→ см. также:** Часть IV (4.11) — `multiprocessing` для CPU-bound параллелизма; `multiprocessing.shared_memory` — логичное расширение mmap для межпроцессного обмена.

## 11.21. `shutil` и `tempfile` { #11.21 }

### `shutil` — высокоуровневые операции с файлами { #11.21-shutil }

```python
import shutil

# Копирование
shutil.copy('src.txt', 'dst.txt')      # копирует + метаданные прав доступа
shutil.copy2('src.txt', 'dst.txt')     # + метаданные времени (mtime, atime)
shutil.copyfile('src', 'dst')         # только содержимое

# Копирование каталогов
shutil.copytree('src_dir', 'dst_dir')   # рекурсивно
shutil.copytree('src_dir', 'dst_dir', dirs_exist_ok=True)  # не падать, если dst существует

# Удаление
shutil.rmtree('non_empty_dir')   # рекурсивное удаление

# Перемещение
shutil.move('src', 'dst')

# Поиск исполняемого
path = shutil.which('python')   # /usr/bin/python — аналог which в bash

# Архивация
shutil.make_archive('backup', 'zip', root_dir='src')   # создает backup.zip
shutil.unpack_archive('backup.zip', 'unpacked/')
```

### `tempfile` — временные файлы { #11.21-tempfile }

```python
import tempfile

# Временный файл (delete=False — останется после close, удалять вручную)
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
    f.write('hello')
    path = f.name   # что-то вроде /tmp/tmpXXXXXX.txt

# Если delete=True (по умолчанию) — удалится при close
# delete=False — останется, надо удалять вручную

# Временный каталог
with tempfile.TemporaryDirectory() as tmpdir:
    print(tmpdir)   # /tmp/tmpXXXXXX
    # ... работаем с файлами внутри ...
# При выходе из with — каталог удаляется

# mkdtemp — создать, но не удалять автоматически
tmpdir = tempfile.mkdtemp(prefix='myapp_', suffix='_data')
# /tmp/myapp_XXXXXX_data

# mkstemp — безопасное создание (race-free)
fd, path = tempfile.mkstemp()
# fd — открытый файловый дескриптор, path — путь
```

⚠️ `TemporaryDirectory` через `with` — самый безопасный вариант. Если не `with` — то `shutil.rmtree(tmpdir)` вручную в `finally`.

## 11.22. `decimal` и `fractions` { #11.22 }

### `decimal` — точная арифметика с фиксированной точкой { #11.22-decimal }

Для финансовых расчётов, где `float` даёт погрешности:

```python
from decimal import Decimal, getcontext

# Float даёт ошибки
print(0.1 + 0.2)   # 0.30000000000000004

# Decimal — точно
print(Decimal('0.1') + Decimal('0.2'))   # Decimal('0.3')

# Десятичные константы (всегда через строку, не float!)
print(Decimal('0.1') * 3)   # Decimal('0.3')
print(Decimal(0.1))   # Decimal('0.1000000000000000055511151231257827021181583404541015625') — плохо!

# Контекст — настройки точности
getcontext().prec = 28   # 28 значащих цифр (по умолчанию)
# rounding принимает либо строку, либо константу из decimal:
getcontext().rounding = 'ROUND_HALF_EVEN'   # работает (строка)
# Но идиоматичнее — константа:
import decimal
getcontext().rounding = decimal.ROUND_HALF_EVEN   # тот же эффект, но без опечаток

# Контекст для конкретных операций
from decimal import localcontext
with localcontext() as ctx:
    ctx.prec = 10
    result = Decimal('1') / Decimal('7')

# Quantize — округление до заданной точности
price = Decimal('19.999')
rounded = price.quantize(Decimal('0.01'))   # Decimal('20.00')
```

### `fractions` — рациональные числа { #11.22-fractions }

```python
from fractions import Fraction

# Точные рациональные числа
print(Fraction(1, 3) + Fraction(1, 6))   # Fraction(1, 2)
print(Fraction(1, 3) * 3)   # Fraction(1, 1) = 1

# Из строки (с десятичной точкой)
print(Fraction('1.5'))   # Fraction(3, 2)

# Из float (с потерей точности)
print(Fraction(0.5))   # Fraction(1, 2)
print(Fraction(0.1))   # Fraction(3602879701896397, 36028797018963968) — плохо!
print(Fraction(Decimal('0.1')))   # Fraction(1, 10) — правильно!

# Арифметика
print(Fraction(1, 2) ** 3)   # Fraction(1, 8)
print(Fraction(5, 4) / Fraction(3, 2))   # Fraction(5, 6)
```

⚠️ `Fraction` — точные, но **медленные** (целочисленная арифметика с произвольной точностью). Для большинства задач `float` достаточно.

## 11.23. `re` — регулярные выражения { #11.23 }

```python
import re

# Поиск первого совпадения
m = re.search(r'\d+', 'hello 42 world')
print(m.group())    # '42'
print(m.start(), m.end())   # 6 8

# Поиск с начала
m = re.match(r'\d+', 'hello 42')   # None — не начинается с цифры
m = re.match(r'\d+', '42 hello')  # совпадение

# Все совпадения
print(re.findall(r'\d+', 'a1 b22 c333'))   # ['1', '22', '333']

# Все совпадения с группами
for m in re.finditer(r'(\w+)=(\d+)', 'a=1, b=22, c=333'):
    print(m.groups())   # ('a', '1'), ('b', '22'), ('c', '333')

# Замена
re.sub(r'\d+', 'N', 'a1 b22 c333')   # 'aN bN cN'
re.sub(r'(\w+)=(\d+)', r'\2=\1', 'a=1')   # '1=a' — обратные ссылки \1, \2

# Компиляция (для повторного использования — быстрее)
pattern = re.compile(r'\d+')
print(pattern.findall('1 22 333'))
```

**Флаги:**

```python
re.IGNORECASE   # case-insensitive
re.MULTILINE    # ^ и $ работают для каждой строки (а не только начала/конца строки)
re.DOTALL       # . матчит \n
re.VERBOSE      # можно писать пробелы и комментарии в паттерне
re.ASCII        # \w, \d, \s только ASCII
re.UNICODE      # по умолчанию в Python 3

# Inline-флаги в паттерне:
re.search(r'(?i)hello', 'HELLO')   # case-insensitive

# VERBOSE — паттерн в несколько строк с комментариями
pattern = re.compile(r"""
    \d{3}-\d{2}-\d{4}    # формат SSN: 123-45-6789
    |                    # или
    \d{9}                # просто 9 цифр
""", re.VERBOSE)
```

**Именованные группы:**

```python
m = re.search(r'(?P<year>\d{4})-(?P<month>\d{2})', '2026-09')
print(m.group('year'))      # '2026'
print(m.groupdict())         # {'year': '2026', 'month': '09'}
```

**Backreference `(?P=name)`** — ссылка на ранее захваченную именованную группу внутри того же regex:

```python
# Найти повторяющиеся слова "the the", "is is":
re.search(r'\b(?P<word>\w+)\s+(?P=word)\b', 'hello hello world')
# (?P=word) = сопоставить то же, что в группе word
# Эквивалент через номер: r'\b(\w+)\s+\1\b'  — \1 = backreference на 1-ю группу
```

**Lookahead / lookbehind** — проверки «впереди/позади» без потребления символов:

```python
# (?=...)  — positive lookahead: следующее должно совпасть
re.findall(r'\d+(?= dollars)', '5 dollars and 10 euros')   # ['5']
# (?!...)  — negative lookahead: следующее НЕ должно совпасть
re.findall(r'\d+(?! dollars)', '5 dollars and 10 euros')   # ['10']
# (?<=...) — positive lookbehind: предыдущее должно совпасть (фиксированной длины)
re.findall(r'(?<=\$)\d+', '$5 and 10€')                     # ['5']
# (?<!...) — negative lookbehind: предыдущее НЕ должно совпасть (фиксированной длины)
re.findall(r'(?<!\$)\d+', '$5 and 10€')                     # ['10']
```

⚠️ **Lookbehind требует фиксированной длины** — `(?<=\d+)` упадёт с `re.error: look-behind requires fixed-width pattern`. Lookahead — любой длины.

**Условный матч `(?(id)yes|no)`** — матч в зависимости от того, была ли захвачена группа `id`:

```python
# Если есть открывающая кавычка — должна быть закрывающая; если нет — оба отсутствуют
pattern = r'(?P<q>[\"\']?)\w+(?(q)(?P=q))'
re.findall(pattern, '"hello" \'world\' test')
# ['"', "'", '']  — группы: '"' у hello, "'" у world, '' у test (без кавычек)
# (?(q)(?P=q)) — если группа q совпала (есть кавычка), требует ту же кавычку в конце
```

Редкая фича, но полезная для «опциональных парных разделителей».

**`subn` — `sub` + счётчик замен**:

```python
new_str, count = re.subn(r'\d+', 'N', 'a1 b22 c333')
# new_str = 'aN bN cN', count = 3
# Удобно, когда нужно знать, сколько замен произошло
```

⚠️ **Не используйте re для парсинга XML/HTML** — используйте `xml.etree.ElementTree` или `lxml`. Регулярки не справляются с вложенными структурами.

## 11.24. `unicodedata` — нормализация Unicode { #11.24 }

Строки, выглядящие одинаково, могут быть разными:

```python
>>> 'café'   # 'café' (4 символа, é как один символ U+00E9)
>>> 'cafe\u0301'   # 'café' (5 символов, é = e + ◌́ U+0301)

>>> 'café' == 'cafe\u0301'   # False!
```

Для нормализации:

```python
import unicodedata

# NFC — composed (по умолчанию в большинстве систем)
a = unicodedata.normalize('NFC', 'cafe\u0301')
b = unicodedata.normalize('NFC', 'café')
print(a == b)   # True

# NFD — decomposed (accent + base separately)
print(repr(unicodedata.normalize('NFD', 'café')))   # 'cafe\u0301'

# NFKC, NFKD — compatibility (заменяя визуально-одинаковые символы)
print(unicodedata.normalize('NFKC', '①'))   # '1'
print(unicodedata.normalize('NFKC', 'ﬁ'))   # 'fi' (ligature)
```

**Четыре формы:**

- **NFC** — composed, canonically equivalent. Дефолт для хранения/обмена.
- **NFD** — decomposed. Полезно для сортировки и поиска с учётом accent-insensitive.
- **NFKC** — compatibility composed. Заменяет «одинаковые по виду» символы (① → 1, ﬁ → fi). Теряет смысл.
- **NFKD** — compatibility decomposed.

**Применения:**

- Сравнение строк (нормализовать оба, потом сравнить).
- Хеширование как идентификатор (избежать разных хешей для одной строки).
- Поиск в базах данных с accent-insensitive.

```python
def normalize_search(s):
    # lower + NFKD + remove accents → для accent-insensitive поиска
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if not unicodedata.combining(c))

print(normalize_search('Café'))   # 'cafe'
print(normalize_search('CAFÉ'))   # 'cafe'
```

## 11.25. `struct`, `memoryview` — бинарные данные { #11.25 }

### `struct` — упаковка/распаковка бинарных данных { #11.25-struct }

```python
import struct

# pack — упаковать в bytes
data = struct.pack('>I', 42)   # > — big-endian, I — unsigned int (4 байта)
print(data)   # b'\x00\x00\x00*'

# unpack — распаковать
print(struct.unpack('>I', data))   # (42,)

# Несколько значений
data = struct.pack('>HHf', 100, 200, 3.14)
# > — big-endian, H — unsigned short (2), H — unsigned short (2), f — float (4)
print(struct.unpack('>HHf', data))   # (100, 200, 3.140000104904175)

# calcsize — размер формата
print(struct.calcsize('>HHf'))   # 8

# Свой struct-объект (быстрее при повторах)
s = struct.Struct('>HHf')
print(s.pack(100, 200, 3.14))
print(s.unpack(data))
```

**Коды форматов:**

- `x` — pad byte, `c` — char (1 байт), `b`/`B` — signed/unsigned char
- `?` — bool, `h`/`H` — short, `i`/`I` — int, `l`/`L` — long
- `q`/`Q` — long long (8 байт), `f` — float, `d` — double
- `s` — char[], `p` — Pascal string

**Prefix:**

- `<` — little-endian, `>` — big-endian
- `!` — network byte order (как `>`)
- без prefix — native

### `memoryview` — zero-copy срезы bytes { #11.25-memoryview }

```python
data = b'0123456789' * 1000   # 10000 байт

# slice bytes — копирует!
chunk = data[100:200]
print(len(chunk))   # 100
print(type(chunk))  # <class 'bytes'> — новый объект

# memoryview — НЕ копирует
mv = memoryview(data)
chunk = mv[100:200]
print(len(chunk))   # 100
print(type(chunk))  # <class 'memoryview'> — view на исходные данные

# Можно привести к bytes при необходимости
b = bytes(chunk)

# Каст к другому типу (reinterpret)
mv_int = memoryview(b'\x01\x00\x00\x00').cast('I')
print(mv_int[0])   # 1 — интерпретируем 4 байта как unsigned int

# Запись в memoryview (на mutable source)
arr = bytearray(b'0123456789')
mv = memoryview(arr)
mv[0:3] = b'XYZ'
print(arr)   # bytearray(b'XYZ3456789')
```

Применение `memoryview` — чтение больших бинарных файлов без копирования срезов, парсинг протоколов, mmap.

## 11.26. `hashlib`, `hmac`, `secrets` — криптография { #11.26 }

### `hashlib` — хеши { #11.26-hashlib }

```python
import hashlib

data = b'hello, world'
print(hashlib.sha256(data).hexdigest())
# 09ca7e4eaa6e8ae9c7d261167129184883644d07dfba7cbfbc4c8a2e08360d5b
# (64 hex-символа = 256 бит; b94d27b9… — это хеш другой строки, b'hello world')

# Алгоритмы
print(hashlib.algorithms_available)   # все доступные (включая OpenSSL)
print(hashlib.algorithms_guaranteed)   # гарантированные на всех платформах
# sha1, sha256, sha512, md5, sha3_256, blake2b, blake2s, ...

# Пошагово (для потоков)
h = hashlib.sha256()
with open('big.bin', 'rb') as f:
    while chunk := f.read(8192):
        h.update(chunk)
print(h.hexdigest())

# file_digest (Python 3.11+)
digest = hashlib.file_digest(open('big.bin', 'rb'), 'sha256')
print(digest.hexdigest())
```

⚠️ `md5` и `sha1` — **сломаны** для криптографии. Используйте `sha256`/`sha512`/`blake2b`. Для file deduplication — md5 ещё ок.

### `hmac` — keyed-hash (для аутентификации сообщений) { #11.26-hmac }

```python
import hmac, hashlib

secret = b'my_secret_key'
message = b'transfer $100 to Alice'

# HMAC-SHA256
signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

# Верификация на стороне получателя
expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
print(hmac.compare_digest(signature, expected))   # True — constant-time comparison
```

⚠️ Используйте `hmac.compare_digest` (constant-time) для проверки подписей, не `==` — иначе timing-атаки.

### `secrets` — криптостойкая случайность { #11.26-secrets }

```python
import secrets

# Случайные токены
secrets.token_bytes(16)        # 16 случайных байт
secrets.token_hex(16)         # 32 hex-символа
secrets.token_urlsafe(16)     # 22 URL-safe символа (для API-ключей, восстановление пароля)

# Случайный элемент
secrets.choice(['A', 'B', 'C'])

# Случайное число в диапазоне (равномерное, криптостойкое)
secrets.randbelow(1000)   # 0..999

# Сравнение строк (constant-time)
secrets.compare_digest('hello', 'hello')   # True
```

⚠️ **Никогда** не используйте `random` для криптографии — он не криптостойкий. Только `secrets`.

## 11.27. `math` — матфункции и `statistics` { #11.27 }

### `math` — основные { #11.27-math }

```python
import math

# Округление (более предсказуемое, чем round)
math.ceil(2.1)     # 3
math.floor(2.9)    # 2
math.trunc(-2.9)   # -2 (в сторону нуля)
math.isfinite(2.0)  # True
math.isfinite(math.inf)   # False
math.isnan(math.nan)   # True

# Константы
print(math.pi, math.e, math.inf, math.nan, math.tau)   # tau = 2*pi

# Логарифмы, степени
math.log(8, 2)    # 3.0
math.log2(8)      # 3.0
math.log10(1000)  # 3.0
math.exp(1)       # e
math.pow(2, 10)   # 1024.0
math.sqrt(16)     # 4.0
math.isqrt(15)    # 3 — целочисленный корень (точно)
math.cbrt(27)     # 3.0 — кубический корень (Python 3.11+)

# Целочисленная арифметика (малоизвестные, Python 3.8+)
math.prod([1, 2, 3, 4])   # 24 — произведение (заменяет functools.reduce(operator.mul))
math.gcd(12, 18)         # 6 — НОД
math.lcm(4, 6)           # 12 — НОК (Python 3.9+)

# Комбинаторика (Python 3.8+)
math.comb(10, 3)   # 120 — C(10, 3), "10 choose 3"
math.perm(10, 3)   # 720 — A(10, 3), "10 permute 3"
math.factorial(5)  # 120
```

`math.prod`, `math.comb`, `math.perm`, `math.isqrt`, `math.lcm` — малоизвестные, но очень полезные функции, заменяющие кучи `reduce` и `factorial`-обёрток.

### `statistics` — статистика { #11.27-statistics }

```python
import statistics

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]

print(statistics.mean(data))     # 14.5 — среднее
print(statistics.median(data))  # 5.5 — медиана (immune to outliers)
print(statistics.mode(data))    # 1 (первое из самых частых; с 3.8 детерминированно)
print(statistics.multimode([1,1,2,2,3]))   # [1, 2] — все моды (Python 3.8+)

# Стандартное отклонение
print(statistics.stdev(data))    # стандартное отклонение (sample)
print(statistics.pstdev(data))   # стандартное отклонение (population)

# Квантили
print(statistics.quantiles(data, n=4))   # квартили
# [2.75, 5.5, 8.25]

# Корреляция
print(statistics.correlation([1,2,3], [2,4,6]))   # 1.0
print(statistics.linear_regression([1,2,3], [2,4,6]))   # LinearRegression(slope=2.0, intercept=0.0)
```

`statistics` — для быстрой аналитики без numpy. Не такая быстрая, но для 10000 значений достаточно.

## 11.28. `random` — псевдослучайные числа { #11.28 }

```python
import random

# Заполнение
random.seed(42)        # воспроизводимая последовательность
print(random.random()) # float [0, 1)
print(random.uniform(1.5, 5.5))   # float [1.5, 5.5]

# Целые
print(random.randint(1, 100))     # 1..100 включительно
print(random.randrange(0, 100, 5)) # 0, 5, 10, ..., 95

# Случайный элемент
print(random.choice(['a', 'b', 'c']))
print(random.choices(['a', 'b', 'c'], k=5, weights=[1, 1, 8]))  # с весами

# Перемешать (in-place)
nums = [1, 2, 3, 4, 5]
random.shuffle(nums)
print(nums)

# Sample без повторений
print(random.sample(range(100), 5))   # 5 уникальных из 0..99

# SystemRandom — криптостойкий (обёртка над os.urandom)
sr = random.SystemRandom()
print(sr.randint(1, 100))
```

⚠️ `random` — **не** криптостойкий. Для паролей, токенов, API-ключей — `secrets` (см. §11.26).

## 11.29. `argparse`, `configparser`, `subprocess` — CLI, конфиги, процессы { #11.29 }

### `argparse` — парсер аргументов командной строки { #11.29-argparse }

```python
import argparse

parser = argparse.ArgumentParser(description='Process some data.')
parser.add_argument('input', help='input file')
parser.add_argument('-o', '--output', default='out.txt', help='output file')
parser.add_argument('-v', '--verbose', action='store_true')
parser.add_argument('-n', '--count', type=int, default=1)
parser.add_argument('--mode', choices=['fast', 'slow'], default='fast')

args = parser.parse_args()
# args.input, args.output, args.verbose, args.count, args.mode

# Пример:
# $ python script.py data.csv -o result.csv -v -n 5 --mode slow
print(args.input)   # 'data.csv'
print(args.output)  # 'result.csv'
print(args.verbose) # True
print(args.count)   # 5
print(args.mode)    # 'slow'
```

`--help` генерируется автоматически. `argparse` — стандарт для всех CLI-утилит.

### `configparser` — INI-файлы { #11.29-configparser }

```ini
# config.ini
[database]
host = localhost
port = 5432

[features]
debug = true
max_items = 100
```

```python
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

print(config['database']['host'])   # 'localhost'
print(config.getint('database', 'port'))   # 5432 (как int)
print(config.getboolean('features', 'debug'))   # True
```

### `tomllib` — TOML (Python 3.11+) { #11.29-tomllib }

```toml
# config.toml
title = "My App"

[database]
host = "localhost"
port = 5432
tags = ["primary", "fast"]
```

```python
import tomllib

with open('config.toml', 'rb') as f:   # ⚠️ режим 'rb', не 'r'
    config = tomllib.load(f)

print(config['title'])   # 'My App'
print(config['database']['tags'])   # ['primary', 'fast']
```

TOML — современная замена INI, поддерживает массивы, числа, bool, даты. `tomllib` только читает (не пишет). Для записи — `tomli-w`.

### `subprocess` — запуск внешних процессов { #11.29-subprocess }

```python
import subprocess

# Простой запуск
result = subprocess.run(['ls', '-l'], capture_output=True, text=True)
print(result.stdout)
print(result.returncode)   # 0 — успех

# check=True — поднимает CalledProcessError при ненулевом returncode
result = subprocess.run(['ls', '/nonexistent'], check=True, capture_output=True, text=True)

# shell=True — для пайпов и редиректов (⚠️ опасно с user input)
subprocess.run('ls | grep py', shell=True, check=True)

# Направить ввод/вывод
result = subprocess.run(['python', '-c', 'print(42)'], 
    capture_output=True, text=True)
print(result.stdout)   # '42\n'

# DEVNULL — «никуда»
subprocess.run(['noisy_cmd'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Popen — интерактивный процесс
proc = subprocess.Popen(['python', '-i'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
proc.stdin.write('print(1+1)\n')
proc.stdin.flush()
print(proc.stdout.readline())   # '2\n'
proc.terminate()
```

⚠️ `shell=True` с пользовательским вводом — **command injection**. Всегда передавайте список аргументов, не строку.

### `shell=True` — почему это опасно { #11.29-shelltrue }

Когда передаёшь **строку** с `shell=True`, Python вызывает `/bin/sh -c "твоя строка"`. Shell парсит строку по своим правилам — метасимволы `;`, `|`, `&`, `` ` ``, `$()`, `>`, `<` интерпретируются. Если в строке есть данные от пользователя — он может «дописать» команду:

```python
import subprocess

# ❌ ОПАСНО — command injection
filename = input("Файл: ")   # пользователь введёт: x; echo hacked
subprocess.run(f"cat {filename}", shell=True)
# /bin/sh -c "cat x; echo hacked"  ← cat файла, потом выполнение команды

# ✅ БЕЗОПАСНО — список аргументов, shell=False (по умолчанию)
filename = input("Файл: ")
subprocess.run(["cat", filename])
# exec("cat") с argv=["cat", "x; echo hacked"]
# cat попытается открыть файл с именем "x; echo hacked" — не найдёт, и только
```

| Способ | shell | Аргументы | Вердикт |
|---|---|---|---|
| `subprocess.run(["ls", "-l"])` | `False` (по умолч.) | список | ✅ безопасно |
| `subprocess.run(["ls", user_input])` | `False` | список | ✅ безопасно (user_input — один argv) |
| `subprocess.run(f"ls {user_input}", shell=True)` | `True` | строка | ❌ injection |
| `subprocess.run(["ls", user_input], shell=True)` | `True` | список + shell | ⚠️ **почти всегда баг**: на POSIX выполняется `["/bin/sh", "-c", args[0], args[1], ...]` — командой становится ровно `args[0]` (`"ls"`), а `user_input` уходит в позиционный параметр `$0` и до команды не доходит (потерян). Injection тут нет, но и желаемого вызова не получится — соберите строку через `shlex.join` или уберите `shell`. |
| `subprocess.run(shlex.join(["ls", user_input]), shell=True)` | `True` | строка с экранированием | ✅ безопасно (но избыточно) |

**Когда `shell=True` реально нужен**:

- **Пайпы и редиректы**: `ls | grep py > files.txt`. Без shell — нужно вручную создавать пайпы через `subprocess.Popen` и `stdout=proc1.stdin`.
- **Глоббинг**: `cat *.txt`. Без shell — `glob.glob("*.txt")` + list arg.
- **shell-встроенные**: `cd /tmp && ls` (хотя обычно лучше сделать `os.chdir` в Python).
- **Сложные команды с `&&`, `||`, `;`**: `make && make test || echo fail`.

Если `shell=True` неизбежен — **всегда** используй `shlex.quote()` для пользовательских данных:

```python
import shlex
user_input = "x; echo hacked"
safe = shlex.quote(user_input)   # "'x; echo hacked'" — экранировано
subprocess.run(f"cat {safe}", shell=True)
# /bin/sh -c "cat 'x; echo hacked'"  ← cat попытается открыть файл 'x; echo hacked'
```

### `subprocess.run` vs `Popen` — когда что { #11.29-subprocessrun }

| API | Для чего |
|---|---|
| `subprocess.run(...)` | один запуск → дождаться → получить `CompletedProcess`. **95% случаев**. |
| `subprocess.check_output(...)` | `run` + `capture_output=True` + `check=True`. Возвращает stdout как bytes/str. |
| `subprocess.check_call(...)` | `run` + `check=True`. Возвращает 0 или падает. |
| `subprocess.Popen(...)` | интерактивный процесс: пишешь в stdin, читаешь stdout построчно, общаешься с долгоживущим процессом. |
| `os.system(cmd)` | ❌ устаревший. Не возвращает вывод, не безопасен, только returncode. |
| `os.popen(cmd)` | ❌ устаревший. Используй `subprocess.Popen` с `PIPE`. |

### `sys.argv` — простой доступ к аргументам { #11.29-sysargv }

```python
import sys

# sys.argv[0] — имя скрипта, sys.argv[1:] — аргументы
print(sys.argv)
# ['script.py', 'arg1', 'arg2']
```

⚠️ Для чего-то сложнее «взять первый аргумент» — используйте `argparse`.

## 11.30. `timeit`, `bdb`, `profile`/`cProfile`, `code`/`codeop` — профилирование, отладка и REPL-движки { #11.30 }

Эти модули собраны вместе не случайно — все они **выполняют произвольный Python-код в управляемом окружении**. Понимание их устройства полезно и для инструментов разработки, и для песочниц (или способов их обхода).

### `timeit` — замер производительности { #11.30-timeit }

Главное правило — **не использовать `time.time()`** для бенчмарков: он измеряет «wall clock», на который влияют другие процессы, GC, тепловое регулирование CPU. `timeit` выполняет stmt N раз и возвращает **суммарное** время (для best-of — `timeit.repeat` и `min()`), отключает GC на время замера.

```python
import timeit

# Быстрый замер одной конструкции
t = timeit.timeit('"-".join(str(n) for n in range(100))', number=10000)
# ≈ 0.08 с (зависит от CPU)

# Сравнение альтернатив
print(timeit.timeit('"-".join(str(n) for n in range(100))', number=10000))  # 0.082 с — genexp медленнее всех
print(timeit.timeit('"-".join([str(n) for n in range(100)])', number=10000))# 0.069 с — listcomp быстрее (PEP 709 инлайнит)
print(timeit.timeit('"-".join(map(str, range(100)))',       number=10000))  # 0.077 с — map чуть медленнее listcomp на 3.12+

# repeat для оценки стабильности
results = timeit.repeat('"-".join(map(str, range(100)))', number=10000, repeat=5)
# [0.098, 0.097, 0.099, 0.098, 0.097] — берём min, не avg
```

API:

- `timeit.timeit(stmt='...', setup='...', number=N, globals=...)` — выполнить `stmt` N раз, вернуть суммарное время.
- `timeit.repeat(stmt, setup, number=N, repeat=R)` — R независимых прогонов, каждый по N итераций. Берём `min(results)` — это лучшее, на что способен код.
- `timeit.Timer(stmt, setup)` — объект с методами `.timeit()`, `.repeat()`, `.autorange()` (сам подбирает `number` для замера ≥0.2 с).
- CLI: `python -m timeit -s "import json" "json.loads('[1,2,3]')"`.

⚠️ **Тонкости**:

- `setup` выполняется один раз, не входит в замер. Используй для импортов и подготовки данных.
- `globals={'x': x}` позволяет передать локальные переменные в `stmt` (Python 3.5+). Без этого — stmt выполняется в изолированном namespace.
- `timeit` **отключает GC** на время замера (`gc.disable()`/`gc.enable()`). Если твой код создаёт циклы — это искажает реальную картину. Для реалистичной картины — включай обратно руками.

### `bdb` — базовый класс для отладчиков { #11.30-bdb }

`bdb` (базовый дебаггер) — это **фреймворк для написания своего отладчика**. На нём построены `pdb` (стандартный) и `ipdb` (ipython-версия); `debugpy` (VS Code) построен на pydevd — свой механизм трейсинга, но идея та же. Не отладчик сам по себе — каркас с хуками `break()`, `user_line()`, `user_return()`, `user_exception()`, которые ты переопределяешь.

```python
import bdb

class MyTracer(bdb.Bdb):
    def user_line(self, frame):
        # Вызывается на КАЖДОЙ выполняемой строке (пошаговый режим),
        # не только на breakpoint'ах
        print(f"  → {frame.f_code.co_filename}:{frame.f_lineno}")
        # Можно прочитать локальные переменные:
        print(f"    locals: {list(frame.f_locals.keys())}")

    def user_call(self, frame, arg):
        print(f"  → call {frame.f_code.co_name}")

    def user_return(self, frame, ret):
        print(f"  ← return from {frame.f_code.co_name}: {ret!r}")

    def user_exception(self, frame, exc_info):
        print(f"  ! exception in {frame.f_code.co_name}: {exc_info[1]}")
```

`bdb` важен и в контексте **песочниц**: если отладчик может поставить хук на любой строке, значит, код песочницы, разрешающий `breakpoint()` или `sys.settrace`, даёт злоумышленнику полный контроль над выполнением. Блокировка `bdb`/`pdb`/`settrace` — стандартная мера.

### `profile` и `cProfile` — профилирование кода { #11.30-profile }

`profile` (чистый Python) и `cProfile` (C-расширение, быстрее в 10–20×) измеряют, **сколько времени ушло на каждую функцию**. В отличие от `timeit`, который сравнивает куски кода, профайлер показывает полную картину вызовов.

```python
import cProfile
import pstats

def slow_function():
    total = 0
    for i in range(1_000_000):
        total += i ** 2
    return total

# Профилирование в коде
cProfile.run('slow_function()', sort='cumulative')
#          4 function calls in 0.082 seconds
#    Ordered by: cumulative time
#    ncalls  tottime  percall  cumtime  percall filename:lineno(function)
#         1    0.000    0.000    0.082    0.082 {built-in method builtins.exec}
#         1    0.082    0.082    0.082    0.082 <string>:1(<module>)
#         1    0.000    0.000    0.082    0.082 script.py:3(slow_function)
#         1    0.000    0.000    0.000    0.000 {method 'disable' of '_lsprof.Profiler' objects}

# Программный API с сохранением в файл
profiler = cProfile.Profile()
profiler.enable()
slow_function()
profiler.disable()
profiler.dump_stats("profile.prof")
# Анализ: python -m pstats profile.prof
# Или визуализация через snakeviz: snakeviz profile.prof
```

CLI:
```bash
python -m cProfile -o profile.prof script.py       # сохранить профиль
python -m cProfile -s cumulative script.py         # сразу вывести в stdout
```

⚠️ **`profile` vs `cProfile`**: всегда используй `cProfile`, если нет специфических причин. `profile` — чистый Python, в нём накладные расходы на каждый вызов ~10× больше, чем измеряемая функция. `cProfile` на C, почти не влияет на скорость.

`profile.Profile` можно инстанцировать программно и точечно — `enable()`/`disable()` вокруг критического участка. Так делают Django/Flask-профайлеры в middleware.

### `code` и `codeop` — движок интерактивной консоли { #11.30-code }

`code` — модуль для создания **своих интерактивных REPL**. На нём построены `code.interact`/`InteractiveConsole`, `python -m code` и многие встраиваемые консоли; сам `python -i` (C-уровневый REPL) и `IPython` (prompt_toolkit) — не на нём. Если ты делаешь песочницу или встраиваемую консоль — это твой фундамент.

```python
import code

# Простой REPL с заданным globals
namespace = {'x': 42, 'helper': lambda: print("hi")}
code.interact(local=namespace)
# >>> x
# 42
# >>> helper()
# hi
# >>> ^D
# now exiting InteractiveConsole

# Интерактивная консоль с поддержкой многострочного ввода
console = code.InteractiveConsole(locals={'data': [1, 2, 3]})
console.interact(banner="My REPL — type 'exit()' to quit")
```

`code.InteractiveConsole` корректно обрабатывает:

- Многострочные конструкции (`for ... :`, `def ... :`, классы) — накапливает ввод, пока блок не завершён.
- `SyntaxError` и другие исключения — показывает traceback и продолжает работу.
- `__future__`-импорты и `from __future__ import annotations`.

`codeop` — более низкоуровневый модуль: компилятор команд REPL, определяющий, **завершена ли команда** (в том числе многострочная). Главный кейс — определить, **нужна ли ещё одна строка** (например, после `def f():` пользователь нажал Enter — REPL ждёт тело):

```python
import codeop

# Компилятор с флагом «single» — для REPL
c = codeop.CommandCompiler()

# Одна строка — полный оператор?
code_obj = c("x = 1\n", "<input>", "single")
# Возвращает code object → можно exec

# После "def f():" — нужен ещё ввод
code_obj = c("def f():\n", "<input>", "single")
# Возвращает None — команда не завершена, жди следующую строку
```

### Почему эти модули важны для песочниц { #11.30-pochemu }

Все четыре (`timeit`, `bdb`, `profile`/`cProfile`, `code`/`codeop`) — это **готовые движки выполнения Python-кода**. Если ты пишешь песочницу:

1. **`timeit`** — выполняет произвольный `stmt` через `compile()` + `exec()`, игнорируя многие ограничения. Если он доступен — песочница обойдётся: `timeit.timeit("__import__('os').system('ls')", number=1)`.
2. **`bdb`** — через `set_trace()` ставит хук на **каждую** строку. Злоумышленник может прочитать локальные переменные, изменить их, пропустить проверку. Запрети `sys.settrace` и `breakpoint` в песочнице.
3. **`profile`/`cProfile`** — используют `sys.setprofile`, который похож на `settrace`, но вызывается на enter/exit функций. Тоже вектор обхода.
4. **`code`/`codeop`** — если доступен, позволяет злоумышленнику поднять **свой REPL** внутри песочницы и интерактивно исследовать окружение, даже если исходная программа не была интерактивной.

**Минимальная блокировка** для песочницы:
```python
import sys
# Запретить settrace/setprofile
sys.settrace = lambda f, *a, **kw: (_ for _ in ()).throw(RuntimeError("blocked"))
sys.setprofile = lambda f, *a, **kw: (_ for _ in ()).throw(RuntimeError("blocked"))
# Удалить модули из sys.modules
for m in ('bdb', 'pdb', 'profile', 'cProfile', 'code', 'codeop', 'timeit'):
    sys.modules.pop(m, None)
    # Но это не поможет, если доступен __import__ и можно сделать importlib.import_module
```

Реальная защита — это `ast`-фильтрация (Часть VII, 7.13) + изоляция процесса (seccomp, namespaces) + ограниченный `__builtins__`. Модульная блокировка — лишь первый уровень.

## 11.31. `venv`, `pip`, `site` — виртуальные окружения, пакеты и site-packages { #11.31 }

Эти три темы — фундамент **Python-окружения**. Без понимания `venv`/`pip`/`site-packages` невозможно вести разработку сколь-нибудь сложного проекта, но в большинстве учебников они упоминаются вскользь.

### `venv` — виртуальные окружения { #11.31-venv }

**Виртуальное окружение** — изолированная директория с собственным набором пакетов. Каждый проект — свой `venv`, пакеты не конфликтуют между проектами.

```bash
# Создание окружения (без активации):
python3 -m venv .venv

# Активация (Linux/macOS):
source .venv/bin/activate

# Активация (Windows):
.venv\Scripts\activate

# После активации — pip ставит пакеты ТОЛЬКО в .venv:
(.venv) $ pip install requests
# → установлен в .venv/lib/python3.12/site-packages/

# Деактивация:
(.venv) $ deactivate

# Удаление — просто удалить директорию:
rm -r .venv
```

**Структура `venv`**:

```
.venv/
├── bin/                    # Linux/macOS (или Scripts/ на Windows)
│   ├── python              # симлинк на системный python3
│   ├── pip                 # pip этого окружения
│   ├── activate            # скрипт активации
│   └── python3.12          # симлинк для специфичной версии
├── lib/
│   └── python3.12/
│       └── site-packages/  # ← сюда ставятся все пакеты
├── pyvenv.cfg              # конфиг: версия Python, путь к системному интерпретатору
└── include/                # заголовочные файлы (для C-расширений)
```

`pyvenv.cfg` — текстовый конфиг, который делает `venv` «магическим»:

```ini
home = /usr/bin
include-system-site-packages = false
version = 3.12.14
prompt = .venv              # что показывать в PS1 после активации (3.6+)
```

Python при старте читает `pyvenv.cfg` и понимает: **я в venv**, `site-packages` — `lib/python3.12/site-packages/`, системные пакеты **не** подключать (если `include-system-site-packages = false`).

**`python -m venv` флаги**:

```bash
python3 -m venv .venv --system-site-packages   # разрешить доступ к системным пакетам
python3 -m venv .venv --prompt myproject       # кастомный PS1: (myproject) $
python3 -m venv .venv --upgrade                # перевести venv на новую версию Python
python3 -m venv .venv --upgrade-deps           # обновить pip до последнего с PyPI (3.9+)
python3 -m venv .venv --without-pip            # без pip (для минимальных образов)
python3 -m venv .venv --copies                 # копии вместо симлинков (для portability)
```

⚠️ **`venv` ≠ `virtualenv`**. `virtualenv` — сторонний пакет (`pip install virtualenv`), быстрее, больше фич (можно выбрать любую версию Python). `venv` — встроенный (с 3.3), медленнее, но всегда доступен. Для нового кода — `venv`, если не нужна специфика `virtualenv`.

⚠️ **venv и системные пакеты**: `--system-site-packages` — **не рекомендуется**. Если системный `requests` обновится, твой код сломается без предупреждения. Изолируй полностью.

### `pip` — менеджер пакетов { #11.31-pip }

```bash
# Базовые операции:
pip install requests               # установить пакет
pip install requests==2.31.0       # конкретная версия
pip install "requests>=2.25,<3"    # диапазон версий
pip install requests --upgrade     # обновить
pip uninstall requests             # удалить
pip show requests                  # инфо об установленном пакете
pip list                           # все установленные пакеты
pip list --outdated                # какие можно обновить

# Из requirements.txt:
pip install -r requirements.txt

# Заморозить текущие версии:
pip freeze > requirements.txt

# Editable install (для разработки пакета):
pip install -e ./my-package/       # изменения в коде видны сразу, без переустановки

# Установка из git:
pip install git+https://github.com/user/repo.git
pip install git+https://github.com/user/repo.git@v1.2.3  # конкретный тег

# Установка из локального wheel:
pip install ./package-1.0.0-py3-none-any.whl
```

**`requirements.txt` — форматы**:

```bash
# Простые версии:
requests==2.31.0
numpy>=1.20
pandas<2.0

# С хешами (для reproducible installs):
requests==2.31.0 \
    --hash=sha256:abc123... \
    --hash=sha256:def456...

# С extras:
celery[redis]==5.3.0    # установить celery + redis-зависимости

# С маркерами окружения:
pywin32==306; sys_platform == 'win32'   # только на Windows
uvloop==0.17.0; sys_platform != 'win32' # только не на Windows

# Из git:
git+https://github.com/user/repo.git@main#egg=package
```

**`pyproject.toml` — современная замена `setup.py`** (PEP 517/518):

```toml
[project]
name = "my-package"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.25",
    "numpy>=1.20,<2.0",
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]
docs = ["sphinx"]

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

```bash
# Установка из pyproject.toml:
pip install .                # собрать и установить
pip install -e .[dev]        # editable + dev-зависимости
pip install .[dev,docs]      # несколько extras
```

**`pip` и безопасность**:

```bash
# Проверка на известные уязвимости:
pip install pip-audit
pip-audit                    # проверит все установленные пакеты

# Установка только из доверенных индексов:
pip install --index-url https://pypi.org/simple/ requests
pip install --no-index --find-links ./wheels/ requests  # только локальные wheels
```

⚠️ **Никогда не запускай `pip` с `sudo`** — это сломает системный Python. Всегда в `venv`.

⚠️ **`pip install` выполняет код build-backend** (а при наличии `setup.py` — и его) — пакет может запустить arbitrary code при установке. Ставь только доверенные пакеты.

### `site` модуль — что происходит при старте Python { #11.31-site }

При запуске `python3` (без `-S`) автоматически выполняется модуль `site`. Он:

1. **Добавляет `site-packages`** в `sys.path` — чтобы установленные пакеты были доступны.
2. **Добавляет пользовательские пакеты** — `~/.local/lib/python3.12/site-packages/` (`pip install --user`).
3. **Создаёт `exit`, `quit`, `copyright`, `credits`, `license`** — `_sitebuiltins` (см. 1.25, пасхалки).
4. **Читает `.pth` файлы** — дополнительные пути.

```python
import site

# Куда site добавляет пакеты:
site.getsitepackages()       # ['/usr/lib/python3.12/site-packages', ...]
site.getusersitepackages()   # '/home/user/.local/lib/python3.12/site-packages'

# Включён ли site:
import sys
sys.flags.no_site            # 0 = site загружен, 1 = запущен с -S (site НЕ загружался)
```

**`.pth` файлы** — «path extension». Любой `.pth` файл в `site-packages` обрабатывается при старте Python: каждая строка — путь, добавляемый в `sys.path`:

```
# /usr/lib/python3.12/site-packages/my_paths.pth
/usr/local/my/custom/path
/another/path/to/packages
```

```python
# После старта Python:
import sys
sys.path   # [..., '/usr/local/my/custom/path', '/another/path/to/packages']  — пути добавляются в КОНЕЦ
```

⚠️ **`.pth` файлы могут выполнять arbitrary code**: если строка начинается с `import`, Python выполнит её. Это известный вектор атак (см. Приложение B — обход проверяющих систем).

```
# malicious.pth:
import os; os.system("echo hacked")
```

При `python3` (без `-S`) — этот код выполнится. При `python3 -S` — `site` не загружается, `.pth` не обрабатываются.

**`site.ENABLE_USER_SITE`** — флаг, можно ли ставить пакеты в `~/.local`:

```python
import site
site.ENABLE_USER_SITE   # True по умолчанию, False если PYTHONNOUSERSITE=1
```

```bash
# Запретить user-site:
PYTHONNOUSERSITE=1 python3
# или:
python3 -s    # -s = no user site (но site-packages загружается)
python3 -S    # -S = no site вообще (нет site-packages, нет exit/quit, нет .pth)
```

**`usercustomize` и `sitecustomize`** — модули, которые `site` импортирует при старте (если они существуют):

```python
# ~/.local/lib/python3.12/site-packages/usercustomize.py
# Выполняется при каждом старте Python (если site включён):
import warnings
warnings.filterwarnings("ignore", module=".*legacy.*")

# /usr/lib/python3.12/site-packages/sitecustomize.py
# То же, но для всей системы (для всех пользователей):
import sys
sys.setrecursionlimit(5000)
```

Эти модули — **hooks при старте интерпретатора**. `sitecustomize` — системный (обычно пустой или от дистрибутива), `usercustomize` — пользовательский.

⚠️ `usercustomize`/`sitecustomize` — **выполняются до вашего кода**. Если они падают с ошибкой — старт не рушится: сообщение уйдёт в stderr («Error in sitecustomize; set PYTHONVERBOSE for traceback»), и Python продолжит работу; полный трейсбек — `python3 -v`.

### `python -m` — запуск модулей как скриптов { #11.31-python }

`python -m <module>` — находит модуль в `sys.path` и выполняет его `__main__` (или `if __name__ == "__main__":` блок):

```bash
python3 -m http.server          # HTTP-сервер (см. 1.23)
python3 -m venv .venv           # создать venv
python3 -m pip install requests # установить пакет
python3 -m json.tool data.json  # форматировать JSON
python3 -m zipfile -l arc.zip   # список файлов в zip
python3 -m unittest discover    # найти и запустить тесты
python3 -m doctest module.py    # запустить doctest'ы
python3 -m cProfile script.py   # профилирование
python3 -m pdb script.py        # отладчик
python3 -m base64               # base64 encode/decode из stdin
python3 -m tokenize script.py   # токенизация исходника
python3 -m ast script.py        # AST-дамп исходника
python3 -m compileall src/      # скомпилировать все .py в .pyc
```

`-m` ищет модуль по имени (через `sys.path`), не по пути к файлу. Это позволяет запускать модули из `site-packages` без знания их точного пути.

⚠️ `python3 -m pip` предпочтительнее `pip` напрямую — гарантирует, что pip относится к **тому же** интерпретатору, которым запущен. `pip` может указывать на другой Python (если в `PATH` несколько версий).

**Под капотом `python -m` — модуль `runpy`:** `runpy.run_module("http.server", run_name="__main__")` выполняет модуль как `__main__` (не импортируя его под обычным именем — поэтому срабатывает `if __name__ == "__main__":`), а `runpy.run_path("file.py", run_name="__main__")` — то же для произвольного файла. Для пакетов `python -m pkg` запускает `pkg/__main__.py`.

Семантика `sys.argv[0]` зависит от способа запуска (аргументы после скрипта/`-m`/`-c` попадают в `sys.argv[1:]`):

```bash
$ python3 script.py        # argv[0] = 'script.py' — как набрано в командной строке
$ python3 /tmp/script.py   # argv[0] = '/tmp/script.py'
$ python3 -c "..."         # argv[0] = '-c'
$ python3 -m modname       # argv[0] = полный путь к найденному модулю (…/modname.py)
$ echo "..." | python3     # argv[0] = '-' — код из stdin (явная форма: python3 -)
```

### Сводная таблица: флаги запуска Python { #11.31-svodnaya }

| Флаг | Что делает | Когда использовать |
|---|---|---|
| `python3 -S` | не загружать `site` (нет site-packages, exit/quit, .pth) | минимальный интерпретатор, sandbox |
| `python3 -s` | не загружать user-site (`~/.local`) | чистое окружение без пользовательских пакетов |
| `python3 -E` | игнорировать `PYTHON*` env vars | воспроизводимость |
| `python3 -i` | REPL после выполнения скрипта | отладка (см. 1.16) |
| `python3 -O` | удалить `assert`, `__debug__=False` | production |
| `python3 -OO` | `-O` + удалить docstrings | минимальный размер |
| `python3 -v` | verbose import (каждый модуль в stderr) | отладка импортов |
| `python3 -m <mod>` | запустить модуль по имени | унифицированный запуск |
| `python3 -c "code"` | выполнить строку | однострочники |
| `python3 -u` | unbuffered stdout/stderr | логи в реальном времени, CI/CD |
| `python3 -B` | не писать `.pyc` файлы | чистота директории, Docker |
| `python3 -X utf8` | принудительный UTF-8 mode | кроссплатформенность |
| `python3 -b` | `BytesWarning` при сравнениях `bytes`↔`str` (`-bb` — сразу исключение) | ловим типовые bytes/str-баги |
| `python3 -d` | отладочный вывод парсера (`PYTHONDEBUG`) | с PEG-парсером (3.9+) почти молчит |
| `python3 -I` | изолированный режим: `-E` + `-s` + без каталога скрипта в `sys.path` | максимальная изоляция, security |
| `python3 -P` | не добавлять каталог скрипта в `sys.path` (3.11+) | защита от затенения stdlib импортов |
| `python3 -R` | принудительная рандомизация `hash()` | проверять независимость от порядка хешей |
| `python3 -q` | REPL без баннера версии/копирайта | тихий старт сессии (в т.ч. после `-i`) |
| `python3 -V` / `-VV` | версия; `-VV` — ещё сборка и компилятор | скрипты-обёртки, CI-диагностика |
| `python3 -W <фильтр>` | фильтры `warnings` из CLI (`action::category`, см. 11.6) | `-W error` в CI — предупреждения как ошибки |
| `python3 -x script.py` | пропустить первую строку скрипта | не-Python шапка (исторический shebang-хак) |
| `python3 -` | читать код из stdin (`argv[0] = '-'`) | one-liners из пайпов |
| `python3 -X importtime` | лог импортов с таймингами в stderr | искать медленные импорты |
| `python3 -X dev` | Development Mode: строже warnings/asyncio/ресурсы | локальная разработка, CI |
| `python3 -X perf` | поддержка Linux perf-профайлера (3.12+) | профилирование средствами ОС |
| `python3 --check-hash-based-pycs always\|default\|never` | режим проверки hash-based pyc (см. 13.2) | деплой без надёжного mtime |

### Бенчмарки к Части XI { #11.31-benchmarki }

**1. `lru_cache` vs `cache` (Python 3.9+) vs ручной `dict`.**
```python
from functools import lru_cache, cache
import timeit

@lru_cache(maxsize=128)
def fib_lru(n): return n if n < 2 else fib_lru(n-1) + fib_lru(n-2)

@cache   # эквивалент lru_cache(maxsize=None) — без eviction
def fib_cache(n): return n if n < 2 else fib_cache(n-1) + fib_cache(n-2)

_d = {}
def fib_dict(n):
    if n in _d: return _d[n]
    r = n if n < 2 else fib_dict(n-1) + fib_dict(n-2)
    _d[n] = r
    return r

# 1M вызовов fib(20) (кеш тёплый)
print(timeit.timeit("fib_lru(20)",    globals=globals(), number=1_000_000))   # ≈ 0.07 с
print(timeit.timeit("fib_cache(20)",  globals=globals(), number=1_000_000))   # ≈ 0.07 с
print(timeit.timeit("fib_dict(20)",   globals=globals(), number=1_000_000))   # ≈ 0.18 с
```
На CPython 3.12+ `lru_cache` и `cache` **идентичны по скорости** (~0.07 с) и **обгоняют ручной dict** (~0.18 с) в ~2.5 раза. До 3.11 соотношение было другим. `cache` чуть проще (нет eviction), `lru_cache` — для случаев с лимитом размера. Ручной `dict` теперь имеет смысл только при очень специфических требованиях (напр., eviction по памяти, а не по количеству).

**2. `functools.partial` vs `lambda` — замыкание аргументов.**
```python
from functools import partial
import timeit
def f(a, b, c): return a + b + c
p = partial(f, 1, 2)
l = lambda c: f(1, 2, c)
print(timeit.timeit("p(3)", globals={"p": p}, number=2_000_000))   # ≈ 0.14 с (зависит от CPU)
print(timeit.timeit("l(3)", globals={"l": l}, number=2_000_000))   # ≈ 0.17 с
```
`partial` **на ~20% быстрее** `lambda` — это C-уровневая обёртка, без
Python-фрейма. На горячих путях (колбеки в event loop'ах, map/pool) — заметно.

**3. `functools.singledispatch` vs `if/elif isinstance`.**
```python
from functools import singledispatch
import timeit

@singledispatch
def process(x): raise TypeError(f"unsupported {type(x)}")
@process.register
def _(x: int):   return x * 2
@process.register
def _(x: str):   return x.upper()
@process.register
def _(x: list):  return [process(i) for i in x]

def process_if(x):
    if isinstance(x, int):  return x * 2
    if isinstance(x, str):  return x.upper()
    if isinstance(x, list): return [process_if(i) for i in x]
    raise TypeError

# 1M вызовов process(42)
print(timeit.timeit(lambda: process(42),    number=1_000_000))   # ≈ 0.38 с (зависит от CPU)
print(timeit.timeit(lambda: process_if(42), number=1_000_000))   # ≈ 0.09 с
```
`singledispatch` **в ~4× медленнее** — lookup по типу в `dict` + вызов обёртки.
Берите его для **расширяемости** (сторонние модули могут зарегистрировать
свой обработчик), не для скорости.

**4. `heapq.nlargest` vs `sorted(...)[:N]`.**
```python
import heapq, random, timeit
data = [random.random() for _ in range(1_000_000)]
# N = 10
print(timeit.timeit(lambda: heapq.nlargest(10, data),  number=10))   # ≈ 0.3 с
print(timeit.timeit(lambda: sorted(data)[:10],         number=10))   # ≈ 2.2 с
# N = 100_000 (len/10)
print(timeit.timeit(lambda: heapq.nlargest(100_000, data),  number=10))  # ≈ 2.0 с
print(timeit.timeit(lambda: sorted(data)[:100_000],         number=10))  # ≈ 1.1 с — sorted уже быстрее
# N = 500_000 (половина)
print(timeit.timeit(lambda: heapq.nlargest(500_000, data),  number=10))  # ≈ 6.4 с
print(timeit.timeit(lambda: sorted(data)[:500_000],         number=10))  # ≈ 1.1 с
```
`heapq.nlargest` **выигрывает на маленьком N** (в ~7× для N=10) — сложность
`O(N log k)`. Кроссовер — между `len/100` и `len/10`: уже при `N = len/10`
`sorted` выигрывает (один проход vs k-heap с перестройками).
Правило: `nlargest` если `N ≲ len/100`.

**5. `ProcessPoolExecutor` vs `ThreadPoolExecutor` на CPU-bound.**
```python
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
def cpu_burn(n):
    return sum(i*i for i in range(n))
N = 5_000_000
chunks = [N] * 4   # 4 задачи по 5M итераций
# Threads
t0 = time.perf_counter()
with ThreadPoolExecutor(4) as ex:
    list(ex.map(cpu_burn, chunks))
print(f"Threads: {time.perf_counter() - t0:.2f}s")   # ≈ 4× время одной задачи (GIL: почти последовательно)
# Processes
t0 = time.perf_counter()
with ProcessPoolExecutor(4) as ex:
    list(ex.map(cpu_burn, chunks))
print(f"Processes: {time.perf_counter() - t0:.2f}s")  # ≈ время одной задачи (~3.5× к threads на 4 ядрах)
```
Для CPU-bound задач **threads не дают ускорения** в CPython из-за GIL — четыре задачи идут почти последовательно.
`ProcessPoolExecutor` даёт ~3.5× на 4 ядрах (меньше 4× из-за IPC + fork).
Для I/O — берите asyncio или ThreadPool.


