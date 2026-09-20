# Часть III. Генераторы и итераторы

Генератор — это функция, исполнение которой ставится на паузу с сохранением всего фрейма. Из этого одного факта следует всё остальное: ленивость, конвейеры с нулевой памятью, `send`/`throw`/`close`, делегирование через `yield from` — и, в конечном счёте, `async/await` (Часть IV), который компилируется в те же механизмы (4.2). Здесь — генераторы как таковые, плюс итераторный инструментарий `itertools`/`collections`, которым они питаются.

## 3.1. `yield`, `next`, `StopIteration` { #3.1 }

Функция с `yield` вместо `return` — это **генератор**. Она возвращает не значение, а итератор.

```python
def generate_numbers():
    print("Начало")
    yield 1
    print("После 1")
    yield 2
    print("После 2")
    yield 3
    print("После 3")

gen = generate_numbers()    # функция не выполнена — вернула генератор
print(next(gen))            # "Начало" + 1
print(next(gen))            # "После 1" + 2
print(next(gen))            # "После 2" + 3
print(next(gen))            # "После 3" + StopIteration
```

`yield` работает как **умная пауза**:

1. Возвращает значение вызывающему.
2. **Замораживает** состояние функции (все локальные переменные сохраняются в фрейме).
3. При следующем `next` продолжает с того же места.

Когда функция доходит до конца (или `return`), генератор поднимает `StopIteration`.

⚠️ **PEP 479 (Python 3.7+): запрет `raise StopIteration` внутри генератора**. Любой необработанный `StopIteration`, вылетающий из тела генератора, CPython **принудительно трансформирует в `RuntimeError: generator raised StopIteration`**. Это защита от скрытого прерывания цикла `for` при случайном вызове `next(empty_iterator)` внутри генератора. Единственный корректный способ остановить генератор — `return` (или `return value`).

**`return value` в генераторе** — значение сохраняется в `StopIteration.value`:
```python
def calc():
    yield 10
    yield 20
    return "Итого: 30"   # значение при завершении

g = calc()
next(g); next(g)
try:
    next(g)
except StopIteration as e:
    print(e.value)   # 'Итого: 30'
```
Обычный `for` игнорирует `e.value`, но `yield from` перехватывает его (см. 3.3).

**4 состояния генератора** (`inspect.getgeneratorstate`):
```python
import inspect
# GEN_CREATED  — создан, ещё не стартовал
# GEN_RUNNING  — исполняется прямо сейчас (видно изнутри)
# GEN_SUSPENDED — заморожен на yield
# GEN_CLOSED   — исчерпан или закрыт через .close()
```
У исчерпанного генератора `g.gi_frame` становится `None` — фрейм удалён из памяти.

```python
def infinite():
    n = 0
    while True:
        yield n
        n += 1

g = infinite()
print(next(g), next(g), next(g))   # 0 1 2
# Не вызывает StopIteration — бесконечный
```

## 3.2. Generator expressions vs list comprehensions { #3.2 }

```python
# List comprehension — материализует сразу
squares_list = [x**2 for x in range(1_000_000)]   # ~8 MB в памяти

# Generator expression — ленивый
squares_gen = (x**2 for x in range(1_000_000))    # ~200 байт (только состояние, sys.getsizeof на 3.12)
```

Генераторное выражение не вычисляет значения до обращения — каждый `next` даёт следующее. Можно передать напрямую в `sum`, `max`, `min`, `any`, `all`, `sorted`:

```python
total = sum(x**2 for x in range(1_000_000))     # не материализует список
maximum = max(x**2 for x in range(1_000_000))   # то же самое
```

⚠️ **Генератор — одноразовый**:

```python
gen = (x**2 for x in range(5))
print(list(gen))   # [0, 1, 4, 9, 16]
print(list(gen))   # [] — пусто, генератор исчерпан
```

Если нужно пройти дважды — материализуйте в список, либо создайте новый генератор.

⚠️ **Раннее связывание источника vs позднее связывание выражения**: входная последовательность `for x in data` превращается в `iter(data)` **немедленно** при создании генератора, а выражение `x * factor` вычисляется **только при `next()`**:
```python
data = [1, 2, 3]; factor = 10
gen = (x * factor for x in data)
data = [100, 200, 300]   # изменение data НЕ повлияет — iter уже зафиксирован
factor = 100             # изменение factor ПОВЛИЯЕТ — вычисление ленивое
print(list(gen))   # [100, 200, 300] (не [10000, 20000, 30000]!)
```

⚠️ **`sorted(gen)` материализует данные** — внутри полностью разворачивает генератор в список перед сортировкой. Выигрыша по памяти по сравнению с `sorted([...])` нет.

⚠️ **`reversed(gen)` падает** — `TypeError: 'generator' object is not reversible`. `reversed()` требует `__reversed__` или `__len__` + `__getitem__`. Сначала материализуйте: `reversed(list(gen))`.

## 3.3. `yield from` — делегирование { #3.3 }

> **→ см. также:** Часть IV (4.8) — `async for` и `async generators` как асинхронный аналог `yield from`. (PEP 380, Python 3.3+)

`yield from gen` делегирует все элементы из `gen` (любого итератора) в текущий генератор:

```python
def inner():
    yield 1
    yield 2
    yield 3

def outer():
    yield 0
    yield from inner()      # эквивалентно: for x in inner(): yield x
    yield 4

print(list(outer()))       # [0, 1, 2, 3, 4]
```

Но `yield from` делает больше, чем простой `for-yield`:

- **Проксирует `send()`, `throw()`** в под-генератор.
- **Возвращает значение** `return`-а из под-генератора:

```python
def inner():
    yield 1
    yield 2
    return "inner done"

def outer():
    result = yield from inner()
    print(f"Внутренний вернул: {result}")

g = outer()
print(next(g))  # 1
print(next(g))  # 2
print(next(g))  # "Внутренний вернул: inner done" + StopIteration
```

## 3.4. `send()`, `throw()`, `close()` — корутины на генераторах { #3.4 }

Генератор можно использовать как **корутину** — двунаправленно обмениваться данными с вызывающим.

### `send(value)` — отправить значение в генератор { #3.4-send }

```python
def accumulator():
    total = 0
    while True:
        x = yield total      # yield возвращает значение из send
        total += x

acc = accumulator()
print(next(acc))    # 0 — нужно сначала "прокрутить" до первого yield
print(acc.send(10))  # 10 — total=10
print(acc.send(20))  # 30
print(acc.send(5))   # 35
```

⚠️ **Первый вызов обязан быть `next()`**, а не `send()` — генератор ещё не дошёл до `yield` и нечего получать значение. Альтернатива: `acc.send(None)` для первого «пинка».

### `throw(exc_type)` — вбросить исключение внутрь { #3.4-throw }

```python
def safe_gen():
    try:
        while True:
            x = yield
            print(f"Получил {x}")
    except ValueError:
        print("Поймал ValueError")
        yield "after error"

g = safe_gen()
next(g)             # прокручиваем до yield
g.send(1)           # "Получил 1"
g.throw(ValueError)  # "Поймал ValueError"
```

Исключение вбрасывается **в точке, где генератор сейчас приостановлен** (на `yield`).

### `close()` — остановить генератор { #3.4-close }

```python
g = accumulator()
next(g)
g.send(10)
g.close()            # генератор поднимет GeneratorExit, очистится
next(g)             # StopIteration
```

`close()` вставляет `GeneratorExit` в генератор. Если генератор поймал `GeneratorExit` и продолжил `yield`-ить — это `RuntimeError: generator ignored GeneratorExit`.

⚠️ **`GeneratorExit` наследуется от `BaseException`**, а не от `Exception` — поэтому `except Exception:` его **не поймает**. Это гарантирует, что генератор можно закрыть даже если внутри есть широкий `except Exception`. Внутри `except GeneratorExit` разрешено только освобождать ресурсы и завершаться через `return` — **нельзя `yield`**.

## 3.5. Бесконечные генераторы { #3.5 }

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Берём только нужное:
for num in fibonacci():
    print(num)
    if num > 100:
        break
# 0 1 1 2 3 5 8 13 21 34 55 89 144
```

```python
def counter(start=0, step=1):
    n = start
    while True:
        yield n
        n += step

evens = counter(0, 2)
odds = counter(1, 2)
print([next(evens) for _ in range(5)])  # [0, 2, 4, 6, 8]
print([next(odds) for _ in range(5)])   # [1, 3, 5, 7, 9]
```

Главный плюс — память не растёт, потому что значения создаются по одному и сразу потребляются.

## 3.6. `itertools` — избранные рецепты { #3.6 }

```python
# В реальном коде — импортируйте по имени, не через `*`:
from itertools import count, cycle, repeat, chain, islice, starmap
from itertools import accumulate, groupby, zip_longest, product
from itertools import permutations, combinations, tee

# count() — бесконечный счётчик
for i, x in zip(count(), ['a', 'b', 'c']):
    print(i, x)        # 0 a, 1 b, 2 c

# cycle() — повторяет итератор бесконечно
for x in cycle([1, 2, 3]):
    print(x, end=' ')
    if x == 3: break   # напечатает ровно "1 2 3" и прервётся после первого круга

# repeat() — повторяет одно значение
list(repeat('A', 3))   # ['A', 'A', 'A']

# chain() — объединяет итераторы без создания нового списка
list(chain([1, 2], [3, 4], [5]))   # [1, 2, 3, 4, 5]

# islice() — slice для итераторов (работает лениво)
list(islice(range(100), 5, 10))   # [5, 6, 7, 8, 9]

# starmap() — применяет функцию, распаковывая аргументы
list(starmap(pow, [(2, 3), (3, 2), (10, 3)]))   # [8, 9, 1000]

# accumulate() — кумулятивные значения
list(accumulate([1, 2, 3, 4]))           # [1, 3, 6, 10] — суммы
list(accumulate([1, 2, 3, 4], max))      # [1, 2, 3, 4] — кумулятивный max
from operator import mul                    # если ещё не импортирован (ниже используется itemgetter)
list(accumulate([1, 2, 3, 4], mul))      # [1, 2, 6, 24] — факториалы

# groupby() — группирует подряд идущие одинаковые элементы
from operator import itemgetter
data = [('A', 1), ('A', 2), ('B', 1), ('A', 3)]
for key, group in groupby(data, key=itemgetter(0)):
    print(key, list(group))
# A [('A', 1), ('A', 2)]
# B [('B', 1)]
# A [('A', 3)]   ← группа A появилась второй раз!

# zip_longest() — zip, дополняющий короткий итератор
list(zip_longest([1, 2, 3], [4, 5], fillvalue=0))
# [(1, 4), (2, 5), (3, 0)]

# product() — декартово произведение
list(product('AB', repeat=2))
# [('A', 'A'), ('A', 'B'), ('B', 'A'), ('B', 'B')]

# permutations / combinations
list(permutations('ABC', 2))      # [('A','B'),('A','C'),('B','A'),...]
list(combinations('ABC', 2))      # [('A','B'),('A','C'),('B','C')]

# tee() — несколько независимых итераторов из одного
a, b = tee(range(5))
next(a); next(a)
print(list(a))   # [2, 3, 4]
print(list(b))   # [0, 1, 2, 3, 4]  — b не зависит от a
```

⚠️ `groupby` группирует только **подряд идущие** элементы — нужно сначала отсортировать по ключу, иначе один и тот же ключ появится в нескольких группах.

## 3.7. Экономия памяти через ленивые вычисления { #3.7 }

```python
# ПЛОХО: загружает весь файл в память
with open('huge.log') as f:
    lines = f.readlines()        # весь файл в списке
    total = sum(len(line) for line in lines)

# ХОРОШО: итерируемся по файлу напрямую
with open('huge.log') as f:
    total = sum(len(line) for line in f)   # f — итератор по строкам
```

`f` после `open()` — это итератор, который читает строки по одной. `sum(... for line in f)` не материализует список — генераторное выражение отдаёт строки по одной.

```python
# Чтение файла кусками через генератор-функцию
# (однострочник через идиому iter(callable, sentinel): chunks = iter(lambda: f.read(8192), b"")):
def read_chunks(f, size=8192):
    while True:
        chunk = f.read(size)
        if not chunk:
            return
        yield chunk

with open('huge.bin', 'rb') as f:
    for chunk in read_chunks(f):
        process(chunk)
```

**Применения генераторов:**

- Обработка больших файлов, не влезающих в RAM.
- Бесконечные последовательности (фибоначчи, поток событий).
- Stream processing — данные приходят порциями.
- Lazy evaluation — вычисления только когда нужны.

## 3.8. `itertools.pairwise`, `batched` (Python 3.10+/3.12+) { #3.8 }

Новые ленивые итераторы, которых не было в старых версиях Python:

### `pairwise` (Python 3.10+) — пары соседних элементов { #3.8-pairwise }

```python
from itertools import pairwise

# Соседние пары: (n, n+1)
list(pairwise([1, 2, 3, 4]))
# [(1, 2), (2, 3), (3, 4)]

# Полезно для вычисления разностей:
data = [10, 15, 13, 20, 18]
diffs = [b - a for a, b in pairwise(data)]
# [5, -2, 7, -2]

# Поиск локальных максимумов
peaks = [b for a, b, c in zip(data, data[1:], data[2:]) if a < b > c]
# 15, 20 — но это через срезы, а pairwise ленивее
```

### `batched` (Python 3.12+) — чанки фиксированного размера { #3.8-batched }

```python
from itertools import batched

# Разбить на группы по 3
list(batched([1, 2, 3, 4, 5, 6, 7], 3))
# [(1, 2, 3), (4, 5, 6), (7,)]   ← последний может быть короче

# Пагинация
def paginate(items, page_size):
    for i, batch in enumerate(batched(items, page_size)):
        print(f"Page {i+1}: {batch}")

paginate(range(10), 4)
# Page 1: (0, 1, 2, 3)
# Page 2: (4, 5, 6, 7)
# Page 3: (8, 9)
```

`batched` возвращает кортежи (не списки) — ленивый, как весь `itertools`. В 3.13 добавлен строгий режим `strict=True` — `ValueError`, если последний чанк короче `n`.

⚠️ Если последний чанк короткий — он остаётся короче остальных (не дополняется). Если нужна равная длина — дополните вручную:

```python
from itertools import batched

def padded_batched(iterable, n, fillvalue=None):
    """Как batched, но последний чанк дополняется fillvalue до длины n."""
    for batch in batched(iterable, n):
        if len(batch) < n:
            batch = batch + (fillvalue,) * (n - len(batch))
        yield batch

list(padded_batched([1, 2, 3, 4, 5, 6, 7], 3))
# [(1, 2, 3), (4, 5, 6), (7, None, None)]
```

## 3.9. `collections` — Counter, defaultdict, deque, ChainMap, OrderedDict, namedtuple { #3.9 }

### `Counter` — счётчик элементов { #3.9-counter }

```python
from collections import Counter

# Посчитать элементы
c = Counter("abracadabra")
print(c)   # Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

# Топ-N
print(c.most_common(2))   # [('a', 5), ('b', 2)]

# Сложение/вычитание счётчиков
c1 = Counter(a=3, b=1)
c2 = Counter(a=1, b=2)
print(c1 + c2)   # Counter({'a': 4, 'b': 3})
print(c1 - c2)   # Counter({'a': 2})  — отрицательные отбрасываются

# Множественные операции
print(c1 | c2)   # union — максимум по каждому ключу: Counter({'a': 3, 'b': 2})
print(c1 & c2)   # intersection — минимум: Counter({'a': 1, 'b': 1})
```

### `set` / `frozenset` — множества и их операции { #3.9-set }

`set` — изменяемое множество, `frozenset` — неизменяемое (хешируемое, можно как ключ dict). Создание:

```python
set()              # пустой set ({} — это пустой dict!)
{1, 2, 3}          # set из литерала
{*iterable}        # set из итератора (короткий синоним set(iterable))
frozenset([1, 2])  # immutable set
```

**Операции проверки:**

```python
{1, 2}.issubset({1, 2, 3})     # True — s1 ⊆ s2
{1, 2, 3}.issuperset({1, 2})   # True — s1 ⊇ s2
1 in {1, 2}                     # True — членство
```

**Операции, возвращающие новый set:**

```python
{1, 2} | {2, 3}                 # {1, 2, 3} — объединение (union)
{1, 2} & {2, 3}                 # {2}     — пересечение (intersection)
{1, 2} - {2, 3}                 # {1}     — разность (difference)
{1, 2} ^ {2, 3}                 # {1, 3}  — симметрическая разность (symmetric_difference)
# С методом (принимает любой iterable, не только set):
{1, 2}.union([2, 3])           # {1, 2, 3} — метод принимает iterable
{1, 2}.intersection([2, 3])    # {2}
{1, 2}.difference([2, 3])      # {1}
```

**In-place операции (мутируют исходный set):**

```python
s = {1, 2}
s |= {2, 3}                     # s = {1, 2, 3} — update (union)
s &= {2, 3}                     # s = {2, 3}    — intersection_update
s -= {2}                        # s = {3}       — difference_update
s ^= {3, 4}                     # s = {4}       — symmetric_difference_update
# Методы-эквиваленты:
s.update(other)                 # = s |= other
s.intersection_update(other)    # = s &= other
s.difference_update(other)      # = s -= other
s.symmetric_difference_update(other)  # = s ^= other
```

**Модификация элементов:**

```python
s = {1, 2, 3}
s.add(4)          # {1, 2, 3, 4}
s.remove(4)       # {1, 2, 3} — KeyError если нет
s.discard(99)     # {1, 2, 3} — НЕ падает если нет (remove с default)
s.pop()           # удаляет и возвращает случайный элемент (KeyError если пусто)
s.clear()         # {} — очистить
s.copy()          # shallow copy
```

⚠️ **`remove` vs `discard`**: `s.remove(x)` падает с `KeyError`, если `x` нет. `s.discard(x)` — тихо пропускает. Используйте `discard`, когда не уверены в наличии.

⚠️ **`pop()` удаляет случайный элемент** — set неупорядочен, нельзя выбрать конкретный. Для упорядоченного удаления — используйте `s.remove(min(s))` (`sorted(s)` нужен только если нужен полный порядок обхода).

**frozenset** — immutable-версия set. Не поддерживает `add`/`remove`/`update` и т.д., но поддерживает все read-only операции (`|`, `&`, `-`, `^`, `in`, `issubset`, ...). Главное применение — как **ключ dict** или элемент другого set:

```python
d = {frozenset({1, 2}): "pair"}    # OK — frozenset хешируем
# d[{1, 2}] = "pair"               # TypeError: unhashable type: 'set'
```

### `defaultdict` — словарь с дефолт-фабрикой { #3.9-defaultdict }

```python
from collections import defaultdict

# Группировка
words = ['apple', 'banana', 'apricot', 'cherry', 'blueberry']
by_first = defaultdict(list)
for w in words:
    by_first[w[0]].append(w)
print(dict(by_first))
# {'a': ['apple', 'apricot'], 'b': ['banana', 'blueberry'], 'c': ['cherry']}

# Счётчик через defaultdict
counter = defaultdict(int)
for word in words:
    counter[word[0]] += 1
print(dict(counter))   # {'a': 2, 'b': 2, 'c': 1}

# Вложенные defaultdict — multi-level
nested = defaultdict(lambda: defaultdict(list))
nested['users']['admins'].append('alice')
```

### `deque` — двухсторонняя очередь { #3.9-deque }

```python
from collections import deque

# O(1) операции с обоих концов (у list вставка в начало insert(0, x) и pop(0) — O(n))
d = deque([1, 2, 3])
d.appendleft(0)
d.append(4)
print(d)   # deque([0, 1, 2, 3, 4])

d.popleft()   # 0
d.pop()       # 4
print(d)      # deque([1, 2, 3])

# Ограниченный размер — для скользящего окна
recent = deque(maxlen=3)
for x in range(10):
    recent.append(x)
print(recent)   # deque([7, 8, 9], maxlen=3)

# Rotate
d = deque([1, 2, 3, 4, 5])
d.rotate(2)   # вправо
print(d)   # deque([4, 5, 1, 2, 3])
d.rotate(-1)   # влево
print(d)   # deque([5, 1, 2, 3, 4])
```

### `ChainMap` — объединение словарей без копирования { #3.9-chainmap }

```python
from collections import ChainMap

defaults = {'host': 'localhost', 'port': 8080, 'debug': False}
user_config = {'port': 9000, 'debug': True}

config = ChainMap(user_config, defaults)
print(config['host'])   # 'localhost' (из defaults)
print(config['port'])   # 9000 (из user_config — первый приоритет)
print(config['debug'])  # True

# Запись идёт в первый мап:
config['new_key'] = 'value'
print(user_config)   # {'port': 9000, 'debug': True, 'new_key': 'value'}

# Получить "как один словарь":
merged = dict(config)
# {'host': 'localhost', 'port': 9000, 'debug': True, 'new_key': 'value'}
```

Главный кейс — многоуровневые конфиги (CLI → env → defaults) без копирования:

```python
import os
config = ChainMap(os.environ, user_overrides, defaults)
```

### `OrderedDict` — словарь с сохранением порядка { #3.9-ordereddict }

⚠️ С Python 3.7 обычный `dict` тоже сохраняет порядок вставки. `OrderedDict` нужен, только если:

- Требуется равенство по порядку: `OrderedDict([(1,1),(2,2)]) == OrderedDict([(2,2),(1,1)])` → `False`, а для обычных `dict` — `True`.
- `move_to_end(key, last=False)` — переместить ключ в начало.
- `popitem(last=False)` — удалить из начала (FIFO вместо LIFO).

```python
from collections import OrderedDict

d = OrderedDict([('a', 1), ('b', 2), ('c', 3)])
d.move_to_end('a')   # 'a' в конец
print(list(d))   # ['b', 'c', 'a']

d.popitem(last=False)   # FIFO: удаляет 'b'
print(list(d))   # ['c', 'a']

# LRU cache на OrderedDict:
class LRU:
    def __init__(self, capacity):
        self.cap = capacity
        self.cache = OrderedDict()
    
    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)   # пометить как недавно использованный
        return self.cache[key]
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)   # удалить самый старый
```

### `namedtuple` — кортеж с именованными полями { #3.9-namedtuple }

```python
from collections import namedtuple

# Простой способ
Point = namedtuple('Point', ['x', 'y'])
p = Point(1, 2)
print(p.x, p.y)   # 1 2
print(p[0], p[1])  # 1 2 — кортежный доступ работает
print(p._asdict())   # {'x': 1, 'y': 2}

# Распаковка
x, y = p
# Замена (immutable — `_replace` создаёт новый)
p2 = p._replace(x=10)
print(p2)   # Point(x=10, y=2)

# Значения по умолчанию
Person = namedtuple('Person', ['name', 'age', 'email'], defaults=[''])
print(Person('Alice', 30))   # Person(name='Alice', age=30, email='')
```

⚠️ `namedtuple` неизменяемый и хешируемый — можно использовать как ключ в словаре. `typing.NamedTuple` — тот же namedtuple с аннотациями, он тоже НЕизменяемый. Если нужна мутабельность — берите `@dataclass`.

## 3.10. Мост в асинхронность: async-генераторы глазами Части III { #3.10 }

Механика из 3.1–3.4 (протокол, `send`/`throw`/`close`, `GeneratorExit`) не делится на «синхронную» и «асинхронную» — она одна. Async-генератор (PEP 525) — это тот же генератор, у которого каждый шаг итерации может содержать `await`. Здесь — взгляд со стороны Части III; интеграция с event loop (producer/consumer, план очистки при отмене) — в 4.8.

`async def` с `yield` создаёт **async generator function** — вызов возвращает объект, у которого нет `__next__`, зато есть `__anext__`, `asend`, `athrow`, `aclose`:

```python
import asyncio

async def counter(n):
    for i in range(n):
        await asyncio.sleep(0.01)    # между yield можно await — весь смысл PEP 525
        yield i

async def main():
    gen = counter(3)
    print(type(gen))                 # <class 'async_generator'> — не generator из 3.1!
    # next(gen)                      # TypeError: 'async_generator' object is not an iterator

    print(await gen.__anext__())     # 0 — «next» через await
    print(await gen.asend(None))     # 1 — тройка send/throw/close из 3.4 в async-мире
    async for x in gen:              # хвост доедает async for
        print(x)                     # 2

    # await gen.__anext__()          # StopAsyncIteration — асинхронный аналог StopIteration

asyncio.run(main())
```

`async for` — сахар ровно по той же схеме, что `for` в 3.1: вызвать `__aiter__()`, затем `await obj.__anext__()` до `StopAsyncIteration`. Полная таблица соответствия:

| Синхронный (Часть III) | Асинхронный (здесь и 4.8) | Что общего |
|---|---|---|
| `next(g)` | `await g.__anext__()` | шаг итерации |
| `g.send(v)` | `await g.asend(v)` | передача значения внутрь |
| `g.throw(E)` | `await g.athrow(E)` | вброс исключения |
| `g.close()` | `await g.aclose()` | `GeneratorExit` → `finally` |
| `StopIteration` | `StopAsyncIteration` | сигнал конца |
| `for x in g` | `async for x in g` | сахар над протоколом |

Тройка `asend`/`athrow`/`aclose` работает как зеркальный близнец из 3.4 — включая глотание исключения, вброшенного внутрь `try`:

```python
async def stubborn():
    try:
        while True:
            try:
                await asyncio.sleep(0.01)
                yield "тик"
            except ValueError:
                yield "проглотил ValueError"   # как в 3.4: athrow ловится генератором
    finally:
        print("cleanup")

async def main():
    g = stubborn()
    print(await g.asend(None))          # тик
    print(await g.athrow(ValueError))   # проглотил ValueError
    await g.aclose()                    # cleanup — аналог close() из 3.4

asyncio.run(main())
```

**⚠️ StopIteration в async-коде запрещён жёстче, чем в синхронном.** Из 3.1: `StopIteration`, вылетевшая из генератора, превращается в `RuntimeError` (PEP 479). Для корутин — с первого дня по PEP 492, для async-генераторов — PEP 525 — но ошибка выглядит неочевиднее, потому что `StopAsyncIteration` можно перепутать с `StopIteration`:

```python
async def bad():
    raise StopIteration            # внутри async-функции

# await bad() → RuntimeError: coroutine raised StopIteration
```

Классическая ловушка: `next()` на **обычном** итераторе внутри async-функции. `next(d)` на исчерпанном dict-итераторе бросает `StopIteration` — и он, всплывая через `await`, станет `RuntimeError` без исходного стека. В async-коде исчерпание проверяют через `for`/защитные конструкции, а не ловят `StopIteration`.

**Async comprehensions** — генераторные выражения из 3.2 с одним отличием в синтаксисе (`async for`, опционально `await` внутри):

```python
async def main():
    results = [x * 2 async for x in counter(3)]        # async-комprehension
    filtered = [x async for x in counter(10) if x % 2 == 0]
    mapped = [await transform(x) async for x in counter(3)]   # await на каждом элементе
```

Проверки «это корутина или футура?» (`asyncio.iscoroutine`/`isfuture`) — в 4.16; отдельного предиката для async-генераторов в asyncio нет — используют `inspect.isasyncgen`.

Почему генераторы и async-генераторы живут в разных частях: здесь — протокол (он полностью выводится из 3.1–3.4), в Части IV — поведение под event loop: кто и когда дергает `__anext__`, что происходит с async-генератором при отмене задачи и закрытии loop, `aclosing` для гарантированной очистки.

→ **см. также:** 3.1 — протокол итерации; 3.4 — `send`/`throw`/`close`; 4.8 — async-генераторы под event loop; 4.16 — `iscoroutine`/`isfuture`; async-dunder'ы (`__aiter__`/`__anext__`/`__aenter__`/`__aexit__`) — в 4.8–4.9.

---

### Бенчмарки к Части III { #3.10-benchmarki }

**1. List comprehension vs generator expression — память.**
```python
import sys
N = 1_000_000
lst = [x**2 for x in range(N)]
gen = (x**2 for x in range(N))
print(sys.getsizeof(lst))   # 8 448 728 байт (≈8.4 MB)
print(sys.getsizeof(gen))   # ~200 байт (только состояние генератора)
```
Разница в **~42 000×** по памяти. Но `sum(lst)` и `sum(gen)` дают **одинаковый**
результат за **сравнимое время** — генератор не быстрее, он просто не требует
одновременного существования всех элементов.

**2. `sum(genexpr)` vs `sum(listcomp)` — скорость.**
```python
import timeit
print(timeit.timeit("sum(x**2 for x in range(1_000_000))",     number=10))  # ≈ 0.68 с — генератор
print(timeit.timeit("sum([x**2 for x in range(1_000_000)])",   number=10))  # ≈ 0.80 с — listcomp
```
На CPython 3.12+ генератор **на ~5–17% быстрее** listcomp в `sum()` (разброс между прогонами) — это переворачивает старую рекомендацию (раньше listcomp был быстрее). Причина: специализирующий адаптивный интерпретатор (PEP 659; PEP 657 — это трейсбеки) снизил накладные расходы генератора. Генератор также **экономит память** — не аллоцирует список.

**3. `itertools.batched` (3.12+) vs ручной `iter`+`tuple`.**
```python
from itertools import batched, islice
import timeit
data = list(range(1_000_000))
def via_batched():
    return list(batched(data, 64))
def via_manual():
    args = [iter(data)] * 64
    return list(zip(*args, strict=True))
print(timeit.timeit(via_batched, number=20))   # ≈ 0.17 с (зависит от CPU)
print(timeit.timeit(via_manual,  number=20))   # ≈ 0.22 с
```
`batched` быстрее в ~1.3× (замер: 0.166 vs 0.222 с на 20 прогонов, зависит от CPU) и не теряет «хвост» длиной ≠ N: zip-трюк выше использует strict=True и на некратных данных падает с `ValueError: zip() argument is shorter`, а zip БЕЗ strict молча теряет хвост.

**4. `itertools.pairwise` vs ручной сдвиг.**
```python
from itertools import pairwise
import timeit
data = list(range(100_000))
def via_pairwise():
    return [b - a for a, b in pairwise(data)]
def via_index():
    return [data[i+1] - data[i] for i in range(len(data) - 1)]
print(timeit.timeit(via_pairwise, number=50))  # ≈ 0.45 с (зависит от CPU)
print(timeit.timeit(via_index,    number=50))  # ≈ 0.45 с — разница в пределах шума
```
На 3.12 разрыв почти исчез (listcomp-версия ускорена специализациями PEP 659: разница 1–3% между прогонами) — выбирайте `pairwise` за ленивость и работу с итераторами без `len()`.

**5. Ленивые вычисления — реальная экономия на раннем выходе.**
```python
# Найти первое число > 100 в последовательности из 10M элементов
N = 10_000_000
# List comp: построит весь список, потом найдёт
def eager():
    return next((x for x in [i**2 for i in range(N)] if x > 100), None)
# Generator: остановится на первом совпадении
def lazy():
    return next((x for x in (i**2 for i in range(N)) if x > 100), None)
import timeit
print(timeit.timeit(eager, number=1))   # ≈ 1.8 с
print(timeit.timeit(lazy,  number=1))   # ≈ 0.00002 с (90 000× быстрее)
```
Это **самый сильный** аргумент за генераторы: при раннем выходе
(`any`, `all`, `next`, `break`) они экономят не память, а время.


