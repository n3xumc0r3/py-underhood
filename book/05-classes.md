# Часть V. Классы и интерфейсы

> Эта часть очень большая. Разделы расположены по принципу «от конкретного к абстрактному»: сначала `dataclasses` (как самый частый способ создавать классы), потом ABC/Protocol (контракты), потом internals (MRO, `super`, `__slots__`), потом `enum` и продвинутый `typing`.

## 5.1. `dataclasses` — современные data class builders (PEP 557, Python 3.7+)

`@dataclass` автоматически генерирует `__init__`, `__repr__`, `__eq__` (и опционально `__hash__`, `__lt__` и др.) по аннотациям полей:

```python
from dataclasses import dataclass, field

@dataclass
class Point:
    x: float
    y: float
    label: str = "origin"      # поле с дефолтом

p = Point(1.0, 2.0)
print(p)                       # Point(x=1.0, y=2.0, label='origin')
print(p == Point(1.0, 2.0))    # True — сгенерирован __eq__
```

**Параметры `@dataclass`:**

| Параметр | По умолчанию | Что делает |
|----------|-------------|-----------|
| `init` | `True` | Генерировать `__init__` |
| `repr` | `True` | Генерировать `__repr__` |
| `eq` | `True` | Генерировать `__eq__` (сравнение по полям) |
| `order` | `False` | Генерировать `__lt__`, `__le__`, `__gt__`, `__ge__` (для сортировки) |
| `unsafe_hash` | `False` | Генерировать `__hash__` даже если `eq=True` (опасно — может нарушить инвариант) |
| `frozen` | `False` | Immutable — присваивание полей запрещено, генерирует `__hash__` |
| `slots` | `False` (Python 3.10+) | Использовать `__slots__` — экономия памяти |
| `kw_only` | `False` (Python 3.10+) | Все поля — keyword-only |

**Frozen dataclass (immutable):**

```python
@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

c = Color(255, 0, 0)
c.r = 128          # FrozenInstanceError!
```

Хешируем — можно использовать в `set`/`dict`:

```python
colors = {Color(255, 0, 0), Color(0, 255, 0)}   # работает
```

**Slots dataclass (Python 3.10+) — экономия памяти:**

```python
@dataclass(slots=True)
class Point:
    x: float
    y: float
# Создаёт __slots__, убирает __dict__ — экономия ~40-50% на экземпляр
```

**`field()` — настройки отдельного поля:**

```python
@dataclass
class User:
    name: str
    tags: list = field(default_factory=list)   # mutable default — обязателен default_factory!
    email: str = field(default="", repr=False)  # не показывается в repr
    id: int = field(init=False)                  # не параметр __init__
    
    def __post_init__(self):
        # вызывается после __init__
        self.id = abs(hash(self.name))

u = User("Alice", tags=["admin"])
print(u.id)  # хэш имени
```

⚠️ **Mutable defaults в `@dataclass`**: `tags: list = []` — `@dataclass` **запрещает** mutable defaults на уровне декоратора и падает с `ValueError: mutable default <class 'list'> for field tags is not allowed: use default_factory`. Используйте `field(default_factory=list)`. В обычных классах (не dataclass) `tags = []` действительно создаст общий список — но `@dataclass` вас защитит.

**Post-init для валидации:**

```python
@dataclass
class Range:
    lo: int
    hi: int
    
    def __post_init__(self):
        if self.lo > self.hi:
            raise ValueError(f"lo ({self.lo}) > hi ({self.hi})")

Range(10, 5)   # ValueError
```

## 5.2. `abc.ABC` и `@abstractmethod`

`abc` модуль — для настоящих абстрактных классов. Нельзя инстанцировать, пока не реализованы все абстрактные методы:

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        ...
    
    @abstractmethod
    def perimeter(self) -> float:
        ...
    
    def describe(self):
        return f"Shape with area={self.area()}, perimeter={self.perimeter()}"

# shape = Shape()          # TypeError: Can't instantiate abstract class
# shape = Circle(5)        # TypeError: не реализован perimeter

class Circle(Shape):
    def __init__(self, r):
        self.r = r
    def area(self): return 3.14 * self.r ** 2
    def perimeter(self): return 2 * 3.14 * self.r

c = Circle(5)
print(c.describe())   # работает
```

**Абстрактные свойства/классовые методы:**

```python
class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "Plugin": ...
```

⚠️ **Порядок декораторов важен**: `@abstractmethod` всегда **ближе к функции**, чем `@property`/`@classmethod`/`@staticmethod`.

## 5.3. `Protocol` (PEP 544) — структурная типизация

В отличие от `ABC` (номинальная типизация — «должен наследоваться»), `Protocol` проверяет **структуру** («должен иметь такие методы»):

```python
from typing import Protocol

class SupportsClose(Protocol):
    def close(self) -> None: ...

# Не наследуется от SupportsClose!
class FileHandle:
    def close(self) -> None:
        print("closed")

def cleanup(resource: SupportsClose) -> None:
    resource.close()

cleanup(FileHandle())   # работает — у FileHandle есть close()
cleanup(open('x.txt'))   # работает — у file есть close()
cleanup([1, 2, 3])       # mypy ошибётся — у list нет close()
```

**Runtime checkable:**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class HasLen(Protocol):
    def __len__(self) -> int: ...

print(isinstance([1, 2, 3], HasLen))   # True
print(isinstance("hello", HasLen))    # True
print(isinstance(42, HasLen))         # False
```

⚠️ `@runtime_checkable` проверяет только **наличие методов**, не их сигнатуры. Для полной проверки — только mypy.

`Protocol` — это **duck typing для type checker'а**: «если ходит как утка и крякает как утка — это утка».

## 5.4. MRO и C3-линеаризация

**MRO (Method Resolution Order)** — порядок, в котором Python ищет методы при множественном наследовании. Алгоритм **C3-линеаризация**.

```python
class A:
    def f(self): return "A"

class B(A):
    def f(self): return "B"

class C(A):
    def f(self): return "C"

class D(B, C):
    pass

print(D.__mro__)
# (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)

print(D().f())   # "B" — D не имеет f, ищем в B — есть
```

Порядок: `D → B → A → C → object` (проверьте: `print(D.__mro__)`).

⚠️ **C3-линеаризация — это НЕ поиск в ширину** (BFS). Распространённое заблуждение: «сначала все прямые родители, потом их предки». На самом деле алгоритм C3 гарантирует:
1. **Локальный приоритет**: если `class D(B, C)` — то `B` всегда раньше `C`.
2. **Потомок раньше предка**: `B` раньше `A` (т.к. `B(A)`).
3. **Монотонность**: порядок в дочерних классах не может противоречить порядку в базовых.

Контрпример к BFS: `class D(B, C)` где `B(A)` — MRO даёт `[D, B, A, C, object]`, т.е. `A` (дедушка через `B`) стоит **раньше** `C` (прямого родителя). При BFS было бы `[D, B, C, A, object]` — но CPython выдаёт именно `[D, B, A, C, object]`.

Если C3 не может построить консистентный порядок — `TypeError: Cannot create a consistent method resolution order`.

**«Diamond problem»** — A.f вызывается через одну ветку:

```python
class A:
    def f(self): print("A.f")

class B(A):
    def f(self): print("B.f"); super().f()

class C(A):
    def f(self): print("C.f"); super().f()

class D(B, C):
    def f(self): print("D.f"); super().f()

D().f()
# D.f
# B.f
# C.f
# A.f
```

`super().f()` в `B` идёт не к `A`, а к следующему в MRO — то есть к `C`. Это позволяет корректно вызывать методы всех родителей при множественном наследовании.

**C3-линеаризация невозможна для некоторых иерархий** — тогда Python поднимает `TypeError: Cannot create a consistent method resolution order`:

```python
class X: pass
class Y(X): pass
class Z(X, Y): pass   # TypeError!
```

## 5.5. Mixins и множественное наследование

**Mixin** — небольшой класс, который **нельзя инстанцировать сам по себе**, он добавляет функциональность другим классам через наследование:

```python
class JsonMixin:
    def to_json(self):
        import json
        return json.dumps(self.__dict__)

class ComparableMixin:
    def __lt__(self, other):
        return self._cmp_key() < other._cmp_key()
    def __eq__(self, other):
        return self._cmp_key() == other._cmp_key()

class User(JsonMixin, ComparableMixin):
    def __init__(self, name, age):
        self.name = name
        self.age = age
    def _cmp_key(self):
        return self.age

u = User("Alice", 30)
print(u.to_json())   # {"name": "Alice", "age": 30}
print(u < User("Bob", 25))  # False
```

**Правила mixin:**
- Mixin не должен иметь `__init__` (или вызывает `super().__init__(*args, **kwargs)` — **обязательно** с `*args, **kwargs`, иначе разорвёт цепочку MRO).
- **Миксины всегда объявляются слева** от основного базового класса: `class User(JsonMixin, BaseEntity)` — не наоборот, иначе `BaseEntity` встанет в MRO раньше миксина и его методы никогда не вызовутся.
- Если проект использует `__slots__`, mixin обязан объявить `__slots__ = ()` — иначе CPython создаст `__dict__` и уничтожит экономию памяти.
- Mixin обычно использует методы, которые определит целевой класс (как `_cmp_key()` выше). Для типизации в mypy — объявляйте их через `@abstractmethod` или `typing.Protocol`.

⚠️ **Наследование от ABC + Mixin**:

```python
class Plugin(ABC, JsonMixin):
    @abstractmethod
    def run(self): ...
# Теперь абстрактный класс с JSON-функциональностью
```

## 5.6. `__init_subclass__` — хук при наследовании

> **→ см. также:** Часть VII (7.5) — `type()` как метапрограммный аналог; Часть VI (6.3) — `__set_name__` для дескрипторов. (PEP 487, Python 3.6+)

```python
class Plugin:
    registry = {}
    
    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)  # обязательно! иначе object упадёт на неизвестных kwargs
        # __init_subclass__ — неявный classmethod (без @classmethod), cls = создаваемый подкласс
        # Вызывается после __set_name__ но до завершения создания класса
        Plugin.registry[name or cls.__name__] = cls

class FooPlugin(Plugin, name="foo"):
    pass

class BarPlugin(Plugin):
    pass

print(Plugin.registry)  # {'foo': <class 'FooPlugin'>, 'BarPlugin': <class 'BarPlugin'>}
```

`__init_subclass__` — это **альтернатива метаклассам** для большинства случаев. Срабатывает когда кто-то наследуется от класса, можно валидировать подклассы или регистрировать их.

**Передача аргументов в `class Foo(Base, x=10)`:**

```python
class Base:
    def __init_subclass__(cls, log_level=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.log_level = log_level or "INFO"

class Service(Base, log_level="DEBUG"):
    pass

print(Service.log_level)   # DEBUG
```

## 5.7. `super()` — подробно

`super()` без аргументов внутри метода эквивалентен `super(CurrentClass, self)`. Возвращает прокси, который вызывает метод следующего класса в MRO.

⚠️ **`super()` без аргументов использует скрытую closure-ячейку `__class__`** (PEP 3135). Компилятор автоматически внедряет её при обнаружении `super()` в теле метода. Если скопировать метод из одного класса в другой (`B.f = A.f`), `__class__` всё равно будет указывать на `A` — MRO будет рассчитан относительно `A`, а не `B`.

⚠️ **`super()` в `@staticmethod` без аргументов запрещён** — `RuntimeError: super(): no arguments`. В статическом методе нет `self`/`cls`. Используйте `super(CurrentClass, target).method()` явно.

⚠️ **`super()` в `@classmethod` работает** — интерпретатор видит `cls` и компилирует как `super(CurrentClass, cls)`.

⚠️ **Связка `@classmethod @property` нестабильна между версиями**: на Python 3.12 `MyClass.name` возвращает значение свойства (`'Python'`), но на **Python 3.13** поведение изменилось — возвращается `<bound method>` вместо значения, нужно вызывать `MyClass.name()`. Для свойств уровня класса используйте `@property` в **метаклассе**:
```python
class Meta(type):
    @property
    def version(cls):
        return 'v1.0'
class Service(metaclass=Meta):
    pass
print(Service.version)  # 'v1.0' — работает стабильно во всех версиях
```

```python
class A:
    def __init__(self):
        print("A.__init__")

class B(A):
    def __init__(self):
        print("B.__init__ before super")
        super().__init__()        # вызывает A.__init__
        print("B.__init__ after super")

B()
# B.__init__ before super
# A.__init__
# B.__init__ after super
```

**`super()` с аргументами** (для не-`__init__` методов или странных иерархий):

```python
super(CurrentClass, self).method(args)
```

**Cooperative multiple inheritance** — `super().method()` в каждом классе вызывает следующий в MRO, что позволяет вызывать методы всех родителей:

```python
class Base:
    def save(self):
        print("Base.save")

class TimestampMixin:
    def save(self):
        print("Timestamp.save")
        super().save()        # идёт к следующему в MRO, не обязательно к Base!

class ValidatingMixin:
    def save(self):
        print("Validating.save")
        super().save()

class Document(TimestampMixin, ValidatingMixin, Base):
    pass

Document().save()
# Timestamp.save
# Validating.save
# Base.save
```

⚠️ Если в цепочке один класс забудет `super().save()` — следующие классы не вызовутся.

## 5.8. `__slots__` — оптимизация памяти

> **→ см. также:** Часть VI (6.1–6.2) — `__slots__` работает через data descriptor protocol; Часть VIII (8.2) — internals объектной модели CPython.

По умолчанию атрибуты экземпляров хранятся в словаре `__dict__`. Это тратит много памяти, если объектов создаются миллионы. `__slots__` фиксирует набор атрибутов и убирает `__dict__`:

```python
class Point:
    __slots__ = ('x', 'y')   # фиксируем набор атрибутов
    
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
print(p.x, p.y)               # 1 2
p.z = 3                       # AttributeError — 'Point' object has no attribute 'z'
print(p.__dict__)             # AttributeError — у Point нет __dict__!
```

**Экономия**: ~40-50% на экземпляр при миллионах объектов. Дополнительно: доступ к слотовым атрибутам быстрее, чем к `__dict__`.

**Нюансы:**
- Наследники не наследуют `__slots__` автоматически — каждый подкласс должен объявить свой `__slots__ = ()` (пустой, если новых атрибутов нет).
- Если в подклассе не объявить `__slots__`, у него появится `__dict__`, и экономия пропадёт.
- Нельзя использовать `@property` с тем же именем, что в `__slots__` (конфликт).
- `__slots__` + `__weakref__` нужно добавлять явно, если нужны weak references.

```python
class Base:
    __slots__ = ('x',)

class Child(Base):
    __slots__ = ('y',)   # если не объявить — будет __dict__

c = Child()
c.x = 1
c.y = 2
# c.z = 3   # AttributeError
```

### `__slots__` + множественное наследование — `lay-out conflict`

Самая частая внезапная ловушка: два класса с непустым `__slots__` нельзя совместно наследовать, если они не имеют общего слотового предка с совместимым C-level layout. CPython хранит slot-атрибуты в **фиксированном смещении внутри C-struct экземпляра** — и если два базовых класса каждый по-своему раскладывают атрибуты, нет способа их «слить».

```python
class A:
    __slots__ = ('x',)

class B:
    __slots__ = ('y',)

class C(A, B):       # ❌ TypeError!
    __slots__ = ()
# TypeError: multiple bases have instance lay-out conflict
```

**Что работает, что нет**:

| Сценарий | Работает? | Почему |
|---|---|---|
| Линейное наследование: `B(A)` со своими slots | ✅ | layout продолжается — B добавляет свои slots после A'овских |
| Подкласс без slots наследует slot-класс | ✅ | но `__dict__` появится — экономии нет |
| Два slot-класса без общего предка — множественно | ❌ | у каждого свой layout, конфликт |
| Два slot-класса с общим slot-предком | ⚠️ иногда | только если общий предок **первый** в MRO и имеет совместимый layout |
| Mixin с методами, но без slots + slot-класс | ✅ | mixin не добавляет layout, slot-класс диктует структуру |
| Обычный класс (с `__dict__`) + slot-класс | ✅ | `__dict__` «съедает» конфликт — но slot'ы всё равно работают |

**Решение для mixin-паттерна** — не давайте mixin'ам `__slots__`, тогда их можно множественно наследовать вместе со slot-классом:

```python
import json, pickle
from dataclasses import dataclass, asdict

# Mixin'ы БЕЗ __slots__ — у них есть __dict__, но они не добавляют атрибутов
class JsonMixin:
    def to_json(self):
        # dataclasses.asdict умеет работать со slots-классами
        return json.dumps(asdict(self))

class PickleMixin:
    def to_pickle(self):
        return pickle.dumps(self)

# Конкретный класс СО __slots__:
@dataclass(slots=True)
class User(JsonMixin, PickleMixin):
    name: str
    email: str

u = User("Alice", "a@b.c")
print(u.to_json())        # '{"name": "Alice", "email": "a@b.c"}'
print(u.to_pickle()[:8])  # b'\x80\x04\x95...'
# Slot'ы работают, mixin'ы работают, конфликтов нет.
```

⚠️ Если **оба** mixin'а имеют `__slots__` с разными атрибутами — это типичный сценарий конфликта. В Python **невозможно** наследовать два slot-класса с разными slots, если только они не образуют общую slot-иерархию. В этом случае откажитесь от slots у mixin'ов или переработайте архитектуру.

⚠️ **Скрытые проблемы со сторонними протоколами**:

- **`pickle`** со slots-классами не работает «из коробки» — default pickle path ищет `__dict__`. Чтобы pickle работал, нужно явно определить `__getstate__` и `__setstate__` (или `__reduce_ex__`), собирающие/восстанавливающие значения из slots через `__class__.__slots__` (учитывая наследование — обойти все классы в MRO). Если этого не сделать — `pickle.dumps(obj)` упадёт с `TypeError: cannot pickle`.
- **`copy.deepcopy`** для slots-классов обычно работает (через `__reduce_ex__`), но если в slots есть объекты без `__deepcopy__` — будут грабли.
- **`functools.cached_property`** **не работает** на slots-классе без `__dict__` — он пытается записать результат в `__dict__`, а его нет. Получите `AttributeError`. Если нужен cached_property на slots-классе — придётся либо добавить `'__dict__'` в `__slots__` (что убивает экономию памяти), либо реализовать кэш вручную через один из slots.
- **`@property` + `__slots__` с тем же именем** — конфликт, описано выше. Но есть менее очевидное: `@property` **без** сеттера блокирует запись в этот slot, даже если slot был объявлен. То есть `__slots__ = ('x',)` + `@property def x(self): return self._x` приведёт к тому, что `self.x = 1` упадет (нет setter), а `self._x = 1` тоже упадёт (`_x` не в slots). Порядок объявления важен — `property` перекрывает slot.

## 5.9. `@classmethod` vs `@staticmethod`

**`@classmethod`** — метод, получающий **класс** первым аргументом (обычно `cls`):

```python
class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
    
    @classmethod
    def from_string(cls, s):
        # Альтернативный конструктор
        y, m, d = s.split('-')
        return cls(y, m, d)   # cls — это Date или подкласс

d = Date.from_string("2026-09-05")
print(d.year)   # 2026
```

**`@staticmethod`** — метод без доступа к `self` или `cls`:

```python
class Math:
    @staticmethod
    def is_even(n):
        return n % 2 == 0

print(Math.is_even(4))   # True
```

**Когда что:**
- `@classmethod` — для альтернативных конструкторов (`from_string`, `from_dict`, `now`).
- `@staticmethod` — для утилит, которые логически принадлежат классу, но не требуют ни экземпляра, ни класса.

⚠️ `@classmethod` уважает наследование: `Date.from_string()` в подклассе вернёт экземпляр подкласса, а `Date`.

### Mutable class variables — главная ловушка OOP

**Самая частая ошибка** в классах Python — mutable class variable. Все экземпляры **разделяют** один и тот же объект:

```python
class ShoppingCart:
    items = []    # ❌ ПЛОХО — mutable class variable!

    def add(self, item):
        self.items.append(item)

cart1 = ShoppingCart()
cart2 = ShoppingCart()
cart1.add("apple")
print(cart2.items)   # ['apple'] ← ЧУЖОЙ apple в cart2!

# Python ищет items сначала в instance.__dict__, не находит,
# потом в class.__dict__ — находит тот самый list. append мутирует его.
```

```python
# ✅ ПРАВИЛЬНО — immutable class variable (или None), mutable — в __init__:
class ShoppingCart:
    items = None    # или просто не объявлять на уровне класса

    def __init__(self):
        self.items = []    # каждый экземпляр — свой list

cart1 = ShoppingCart()
cart2 = ShoppingCart()
cart1.add("apple")
print(cart2.items)   # [] ← корректно, cart2 пуст
```

Это та же ловушка, что `a = b = []` (см. 1.12) и `def f(x=[])` (default arguments — см. Приложение B). Правило: **mutable объекты на уровне класса — всегда баг**, если только ты не хочешь shared state (что редко).

⚠️ `__slots__` защищает от этой ловушки — слоты создаются на экземпляр, не разделяются. Но `__slots__` с mutable default — другая история (нужен `field(default_factory=list)` в dataclass).

## 5.10. `enum` — Enum, IntEnum, IntFlag, auto

`enum` модуль — для перечислений. Заменяет константы вида `RED = 1`, `GREEN = 2`.

```python
from enum import Enum, IntEnum, IntFlag, auto

# Базовый Enum
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

print(Color.RED)         # Color.RED
print(Color.RED.value)   # 1
print(Color.RED.name)    # 'RED'
print(Color(2))          # Color.GREEN — lookup по значению
print(Color['BLUE'])     # Color.BLUE — lookup по имени
```

**`auto` — автоматическая нумерация:**

```python
class Status(Enum):
    PENDING = auto()
    RUNNING = auto()
    DONE = auto()
    FAILED = auto()

print(Status.PENDING.value)   # 1
print(Status.RUNNING.value)   # 2

# Своё правило для auto:
class MyEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()  # значения будут 'pending', 'running', ...

    PENDING = auto()
    RUNNING = auto()
```

**`IntEnum` — сравним с int:**

```python
class Priority(IntEnum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10

print(Priority.HIGH > Priority.LOW)        # True
print(Priority.HIGH > 3)                   # True — сравним с обычным int
print(Priority.HIGH + 5)                   # 15 — арифметика работает

# Используется как обычный int везде
def set_priority(p: int):
    set_priority_impl(p)

set_priority(Priority.HIGH)   # OK — IntEnum это int
```

⚠️ Обычный `Enum` **не** сравним с int напрямую — `Priority.HIGH > 3` вызовет `TypeError`. `IntEnum` наследуется от `int` и сравним.

**`StrEnum` (Python 3.11+) — строковые перечисления:**

```python
from enum import StrEnum, auto

class Role(StrEnum):
    ADMIN = auto()   # значение = 'admin' (имя в нижнем регистре)
    USER = auto()     # 'user'

print(Role.ADMIN == "admin")  # True — прямое сравнение со строкой!
print(Role.ADMIN.value)       # 'admin'
# JSON-сериализация без кастомного энкодера:
import json; json.dumps({"role": Role.ADMIN})  # '{"role": "admin"}'
```

**Алиасы и `@unique`** — если два имени получают одинаковое значение, второе становится алиасом (молча). `@enum.unique` запрещает это:

```python
from enum import Enum, unique
class Status(Enum):
    ACTIVE = 1
    RUNNING = 1   # алиас для ACTIVE, при итерации пропускается

@unique
class Strict(Enum):
    A = 1
    B = 1   # ValueError: duplicate values found
```

⚠️ **Нельзя расширять Enum** с элементами через наследование: `class Extended(BaseEnum): NEW = 3` → `TypeError: Cannot extend enumerations`. Наследоваться можно только от Enum без элементов (для добавления методов).

⚠️ **Сравнение через `is`** — элементы Enum гарантированно singleton в рамках процесса. `status is Status.ACTIVE` быстрее и безопаснее `==`.

**`IntFlag` — побитовые флаги (комбинируются через `|`):**

```python
class Permission(IntFlag):
    R = 4      # read
    W = 2      # write
    X = 1      # execute

perm = Permission.R | Permission.W
print(perm)              # Permission.W|R
print(Permission.R in perm)   # True — проверка
print(perm & Permission.X)   # Permission.0 — нет X

# Итерация по флагам
for p in Permission.R | Permission.W | Permission.X:
    print(p)
# Permission.R
# Permission.W
# Permission.X
```

⚠️ `IntFlag` — это `int`, можно передавать в системные вызовы (`os.open(path, Permission.R | Permission.W)`).

**`Flag` — то же, но без int:**

```python
class Color2(Flag):
    RED = auto()
    GREEN = auto()
    BLUE = auto()

# Можно комбинировать через |, но не сравним с int
WHITE = Color2.RED | Color2.GREEN | Color2.BLUE
```

**Методы в Enum:**

```python
class OrderStatus(Enum):
    PENDING = auto()
    PAID = auto()
    SHIPPED = auto()
    DELIVERED = auto()
    
    def can_cancel(self):
        return self in (OrderStatus.PENDING, OrderStatus.PAID)
    
    @property
    def is_final(self):
        return self == OrderStatus.DELIVERED
    
    @classmethod
    def from_string(cls, s):
        return cls[s.upper()]

print(OrderStatus.PENDING.can_cancel())   # True
print(OrderStatus.DELIVERED.can_cancel())  # False
print(OrderStatus.from_string('paid'))     # OrderStatus.PAID
```

## 5.11. `dataclasses` advanced: `asdict`, `fields`, `replace`, `KW_ONLY`

### `dataclasses.asdict` — в словарь (рекурсивно)

```python
from dataclasses import dataclass, asdict

@dataclass
class User:
    name: str
    age: int

@dataclass
class Team:
    name: str
    leader: User

u = User("Alice", 30)
t = Team("Backend", u)

print(asdict(t))
# {'name': 'Backend', 'leader': {'name': 'Alice', 'age': 30}}
# Вложенные dataclass тоже конвертируются рекурсивно!
```

⚠️ `asdict` рекурсивно обходит вложенные dataclass, list/dict/tuple/... но **не** другие классы. Если внутри есть `datetime` или свой класс — `asdict` оставит его как есть (не преобразует).

### `dataclasses.astuple` — в кортеж

```python
from dataclasses import astuple

print(astuple(User("Alice", 30)))   # ('Alice', 30)
print(astuple(t))   # ('Backend', ('Alice', 30))
```

### `dataclasses.fields` — список Field объектов

```python
from dataclasses import fields

for f in fields(User):
    print(f"{f.name}: {f.type}, default={f.default}")
# name: <class 'str'>, default=<class 'inspect._empty'>
# age: <class 'int'>, default=<class 'inspect._empty'>

# Проверка поля
fields_dict = {f.name: f for f in fields(User)}
print(fields_dict['name'].default)
```

### `dataclasses.replace` — копия с изменёнными полями

```python
from dataclasses import replace

u = User("Alice", 30)
u2 = replace(u, age=31)
print(u2)        # User(name='Alice', age=31)
print(u)         # User(name='Alice', age=30) — оригинал не изменён
```

⚠️ Аналогично `_replace` у `namedtuple`, но для `dataclass`.

### `KW_ONLY` (Python 3.10+) — все поля после `KW_ONLY` — keyword-only

```python
from dataclasses import dataclass, field, KW_ONLY

@dataclass
class Service:
    name: str                    # positional or keyword
    _: KW_ONLY                   # всё ниже — keyword-only
    host: str = "localhost"
    port: int = 8080

# Service("api", port=9000)         # OK
# Service("api", "example.com", 9000)  # TypeError — host/port нельзя позиционно
```

Альтернативно — `kw_only=True` для одного поля:

```python
@dataclass
class Service:
    name: str
    host: str = field(default="localhost", kw_only=True)
    port: int = field(default=8080, kw_only=True)
```

### `metadata` в `field()` — свои аннотации для фреймворков

```python
from dataclasses import dataclass, field

@dataclass
class User:
    name: str = field(metadata={"max_length": 50, "regex": r"^\w+$"})
    age: int = field(metadata={"min": 0, "max": 150})

# Фреймворк (например, валидатор) читает metadata:
import dataclasses
for f in dataclasses.fields(User):
    if 'max_length' in f.metadata:
        # валидация
        ...
```

ORM (SQLAlchemy, Pydantic) и сериализаторы читают `metadata` для своей логики.

## 5.12. `typing` advanced: TypeVar, Generic, cast, overload, Literal, final, TypedDict, NamedTuple

### `TypeVar` — обобщённая переменная типа

```python
from typing import TypeVar

T = TypeVar('T')

def first(items: list[T]) -> T:
    return items[0]

print(first([1, 2, 3]))         # int → возвращает int
print(first(["a", "b"]))        # str → возвращает str

# С ограничением (bound)
Number = TypeVar('Number', bound='int | float')   # только числа

def add(a: Number, b: Number) -> Number:
    return a + b

# С перечислением возможных типов
StringOrBytes = TypeVar('StringOrBytes', str, bytes)
```

### `Generic` — обобщённый класс

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self):
        self._items: list[T] = []
    def push(self, x: T) -> None:
        self._items.append(x)
    def pop(self) -> T:
        return self._items.pop()

# Type hints:
int_stack: Stack[int] = Stack()
int_stack.push(1)
int_stack.push("x")   # mypy ошибётся
```

### `typing.cast` — статическая подсказка, runtime no-op

```python
from typing import cast

def get_value() -> object:
    return "hello"

# Уверены, что это строка, но type checker не знает:
val = cast(str, get_value())
print(val.upper())   # mypy считает, что val — str

# В runtime cast ничего не делает — это просто return value
```

⚠️ `cast` не проверяет тип в runtime. Это только для type-checker'а.

### `@overload` — несколько сигнатур

```python
from typing import overload

@overload
def parse(x: int) -> int: ...
@overload
def parse(x: str) -> str: ...
def parse(x):
    if isinstance(x, int):
        return x * 2
    return x.upper()

# mypy понимает, что parse(1) возвращает int, parse("a") — str
```

Реализация одна — overload'ы только для type checker. В runtime работает последняя функция.

### `Literal` — конкретное значение как тип

```python
from typing import Literal

def set_mode(mode: Literal["fast", "slow", "eco"]) -> None:
    ...

set_mode("fast")   # OK
set_mode("turbo")   # mypy ошибётся — не входит в Literal

# Для discriminated unions — через TypedDict (PEP 589):
from typing import Union, TypedDict

class ClickEvent(TypedDict):
    type: Literal["click"]
    x: int
    y: int

class KeyPressEvent(TypedDict):
    type: Literal["keypress"]
    key: str

Event = Union[ClickEvent, KeyPressEvent]

def handle(e: Event) -> None:
    if e["type"] == "click":
        # mypy и pyright сужают тип до ClickEvent внутри ветки
        print(e["x"], e["y"])
    elif e["type"] == "keypress":
        print(e["key"])

⚠️ `Union[dict, dict]` — **невалидная конструкция**: в `Union` нельзя передавать
dict-литералы, это типы, а не значения. Discriminated unions в Python строятся
только через `TypedDict` + `Literal`-поле-дискриминатор.
```

### `@final` — нельзя наследовать/переопределять

```python
from typing import final

@final
class Const:
    pass

class Sub(Const):   # mypy ошибётся — Const final
    pass

class Base:
    @final
    def critical(self):
        pass

class Derived(Base):
    def critical(self):   # mypy ошибётся
        pass
```

В runtime не работает — только для type checker.

### `TypedDict` — типизированный словарь (PEP 589)

```python
from typing import TypedDict

class UserDict(TypedDict):
    name: str
    age: int
    email: str   # required

# Можно опционально:
class UserOptional(TypedDict, total=False):
    name: str
    age: int
    email: str  # все поля опциональны

# Смешанное (Python 3.11+):
class UserMix(TypedDict):
    name: str          # required
    age: int           # required
class UserMix2(UserMix, total=False):
    email: str         # опционально

u: UserDict = {"name": "Alice", "age": 30, "email": "a@x.com"}
u["age"] = "30"   # mypy ошибётся — должно быть int
```

### `NamedTuple` — typed namedtuple

```python
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
    label: str = "origin"

p = Point(1.0, 2.0)
print(p.x, p.label)   # 1.0 'origin'

# Можно наследовать с дефолтами:
class Vector(NamedTuple):
    x: float
    y: float
    
    def magnitude(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5

v = Vector(3, 4)
print(v.magnitude())   # 5.0
```

⚠️ `NamedTuple` — это тот же `collections.namedtuple`, но с аннотациями. Неизменяемый.

### `Protocol` с типами-параметрами (Python 3.12+)

```python
from typing import Protocol, TypeVar

T = TypeVar('T')

class SupportsLen(Protocol[T]):
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> T: ...

# list[int] удовлетворяет SupportsLen[int]
def first(x: SupportsLen[int]) -> int:
    return x[0]

first([1, 2, 3])   # OK
```

### `Annotated` (PEP 593) — аннотация с метаданными

`Annotated[T, *metadata]` — тип `T` с дополнительными метаданными для фреймворков. В runtime = `T`, но фреймворки (Pydantic, FastAPI, SQLAlchemy) читают метаданные.

```python
from typing import Annotated

# Pydantic-стиль: валидация + метаданные
def get_user(
    user_id: Annotated[int, "Must be positive", lambda x: x > 0]
) -> dict:
    ...

# FastAPI: dependency injection через Annotated
from fastapi import Depends, FastAPI

def get_db():
    return Database()

async def get_user(
    db: Annotated[Database, Depends(get_db)],
    user_id: int,
):
    return db.find_user(user_id)

# SQLAlchemy 2.0:
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    # Mapped[int] = Annotated[int, ...] — встроенная в SQLAlchemy обёртка
```

`Annotated` позволяют third-party фреймворкам расширять систему типов без модификации самого Python.

⚠️ В runtime `Annotated[int, "label"]` ≈ `int` — `isinstance` проверки используют только первый аргумент. Метаданные читаются через `typing.get_type_hints` + ручной разбор.

### `Self` (PEP 673, Python 3.11+)

Тип «этот же класс», для методов, возвращающих экземпляр своего класса. Заменяет необходимость писать `"MyClass"` в строковом виде:

```python
from typing import Self

class Builder:
    def __init__(self):
        self.config = {}
    
    def with_host(self, host: str) -> Self:   # возвращает Builder
        self.config['host'] = host
        return self
    
    def with_port(self, port: int) -> Self:   # если наследник — вернёт наследник
        self.config['port'] = port
        return self

# Наследник получит правильный тип:
class HttpsBuilder(Builder):
    def with_ssl(self) -> Self:
        return self

b = HttpsBuilder().with_host("x").with_port(443).with_ssl()
# mypy понимает: тип b — HttpsBuilder (а не Builder, как было бы со строковым "Builder")
```

До 3.11 использовали `TypeVar("T", bound="Builder")` + `T` как возвращаемый тип.

### `ClassVar` — переменная класса (а не экземпляра)

```python
from typing import ClassVar

class Counter:
    instances: ClassVar[int] = 0   # общая для всех экземпляров
    
    def __init__(self):
        Counter.instances += 1
        # NOT self.instances += 1 — это создаст instance attribute
        # shadow класса

Counter()   # instances = 1
Counter()   # instances = 2
print(Counter.instances)   # 2
```

⚠️ `ClassVar` — для type checker. В runtime никаких проверок нет. `dataclass` уважает `ClassVar` и **не** включает её в `__init__`/`__repr__`.

### `Final` — нельзя переназначать

```python
from typing import Final

MAX_RETRIES: Final[int] = 3   # mypy будет ругаться, если попытаться переназначить

MAX_RETRIES = 5   # mypy ошибётся, в runtime — спокойно
```

Также как `@final` декоратор (см. §5.12 выше).

### `Literal` — конкретные значения

(См. выше в §5.12.)

### `Never` и `NoReturn` — недостижимый код

```python
from typing import Never, NoReturn

def fail(message: str) -> NoReturn:
    """Функция никогда не возвращается (всегда падает)."""
    raise ValueError(message)

def unreachable() -> Never:
    """Функция никогда не возвращает значение (тип её — пустой)."""
    while True:
        pass

# mypy понимает, что код после fail(...) не выполняется:
def f(x: int):
    if x < 0:
        fail("negative")   # дальше mypy не анализирует
    print("only if x >= 0")
```

`Never` (Python 3.11+) — более общее название, чем `NoReturn`. `NoReturn` теперь deprecated как alias для `Never` для контекста «функция без return».

### `Any` vs `object`

```python
from typing import Any

# Any — «что угодно, никаких проверок»
def f(x: Any) -> Any:
    return x.foo + x.bar()   # mypy не ругается на что угодно

# object — «это объект, но не знаем какой»
def g(x: object) -> None:
    # mypy не даст вызвать x.foo() — у object нет метода foo
    print(x)   # OK — print принимает что угодно
    print(str(x))   # OK — у object есть __str__
```

⚠️ `Any` отключает проверку типов. `object` — наоборот, самый строгий. Если не уверены — `object` безопаснее (mypy заставит вас кастить).

### `Required` и `NotRequired` (Python 3.11+) — для `TypedDict`

```python
from typing import TypedDict, Required, NotRequired

class User(TypedDict):
    name: str                    # required (по умолчанию)
    email: NotRequired[str]       # optional
    api_key: Required[str]        # явно required (если total=False)

class UserOptional(TypedDict, total=False):
    name: str                    # optional (потому что total=False)
    email: str                    # optional
    api_key: Required[str]       # required (явно)
```

До 3.11 — только через наследование:

```python
class _RequiredUser(TypedDict):
    name: str
class User(_RequiredUser, total=False):
    email: str
```

### `TypeAlias` (PEP 613, Python 3.10+)

Явное объявление алиаса типа:

```python
from typing import TypeAlias

# Явно:
Vector: TypeAlias = list[float]
Json: TypeAlias = dict[str, 'Json'] | list['Json'] | str | int | float | bool | None

# Неявно (без TypeAlias):
Vector = list[float]   # mypy обычно угадывает, но не всегда
```

В Python 3.12+ можно использовать `type` statement (PEP 695):

```python
type Vector = list[float]
type Json = dict[str, Json] | list[Json] | str | int | float | bool | None
```

### `ParamSpec` (PEP 612, Python 3.10+) — параметры декораторов

Для typing декораторов, которые сохраняют сигнатуру исходной функции:

```python
from typing import ParamSpec, TypeVar, Callable

P = ParamSpec('P')   # набор параметров функции
R = TypeVar('R')     # тип возврата

def logged(func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@logged
def add(x: int, y: int) -> int:
    return x + y

# mypy сохраняет сигнатуру add(x: int, y: int) -> int
add(1, 2)   # OK
add("a", 2)   # mypy ошибётся — int expected
```

Без `ParamSpec` декоратор принимает `*args: Any, **kwargs: Any` — теряется проверка типов.

### `Concatenate` — добавить параметр к существующей сигнатуре

```python
from typing import Concatenate

def add_self(func: Callable[Concatenate[int, P], R]) -> Callable[P, R]:
    # func принимает int первым, потом P
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(42, *args, **kwargs)
    return wrapper
```

Используется в `functools.partial`-стиле декораторов, которые «впрыскивают» аргумент.

### `TypeGuard` (PEP 647, Python 3.10+) — narrowing типов

Для функций-предикатов, которые сужают тип в type checker:

```python
from typing import TypeGuard

def is_str_list(x: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(item, str) for item in x)

def process(x: list[object]):
    if is_str_list(x):
        # здесь mypy считает, что x — list[str]
        for s in x:
            print(s.upper())   # OK — s это str
```

**`TypeIs` (PEP 742, Python 3.13+)** — более строгий вариант `TypeGuard`. Важное отличие от `TypeGuard`:

- `TypeGuard` сужает тип **только внутри `if`-ветки**, но в `else`-ветке тип остаётся прежним (`list[object]`).
- `TypeIs` требует, чтобы аргумент был **экземпляром** целевого типа, и сужает тип в обеих ветках: в `if` — до целевого типа, в `else` — до «исключения целевого».

```python
from typing import TypeIs

def is_str_list(x: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(item, str) for item in x)

def process(x: list[object]):
    if is_str_list(x):
        # здесь x: list[str] (как у TypeGuard)
        pass
    else:
        # здесь x: list[object] минус list[str] — mypy точнее, чем с TypeGuard
        pass
```

⚠️ `TypeIs` **не заменил** `TypeGuard` — оба остаются поддерживаемыми. `TypeIs` строже (не подходит для предикатов вроде `is_not_none`, где тип не сужается, а «обрезается»), `TypeGuard` гибче. Выбирай по семантике: если предикат реально проверяет принадлежность типу — `TypeIs`; если просто проверяет какое-то свойство — `TypeGuard`.

### `LiteralString` (PEP 675, Python 3.11+) — строка как литерал

```python
from typing import LiteralString

def run_query(query: LiteralString) -> None:
    """query должен быть строковым литералом, а не пользовательским вводом —
    защита от SQL injection на уровне типов."""
    ...

run_query("SELECT * FROM users")   # OK
user_input = input()
run_query(user_input)   # mypy ошибётся — user_input не LiteralString
```

Используется в security-чувствительном коде (DSL, SQL builders).

### `@override` (PEP 698, Python 3.12+) — явно переопределяет

```python
from typing import override

class Base:
    def process(self):
        ...

class Derived(Base):
    @override
    def process(self):   # mypy проверит, что в Base есть process
        super().process()

    @override
    def process2(self):   # mypy ошибётся — в Base нет process2
        ...
```

Защита от опечаток: если в базовом классе переименуют метод — mypy сообщит.

### `@deprecated` (PEP 702, Python 3.13+)

```python
from typing import deprecated

@deprecated("Use new_func instead")
def old_func():
    ...

old_func()   # mypy/IDE покажет deprecation warning
```

### `reveal_type` — что mypy думает о типе

```python
def f(x):
    reveal_type(x)   # mypy выведет: Revealed type is "Any"
    y = x + 1
    reveal_type(y)
    return y
```

`reveal_type` — это **mypy-specific** функция, не существует в runtime. Только для отладки аннотаций.

### `get_type_hints` — резолвить строковые аннотации

```python
from typing import get_type_hints

def f(x: 'int', y: 'str' = 'default') -> 'bool':
    return True

print(get_type_hints(f))
# {'x': <class 'int'>, 'y': <class 'str'>, 'return': <class 'bool'>}
```

PEP 563 (`from __future__ import annotations`) делает все аннотации **строками** — `get_type_hints` их резолвит в реальный тип. Полезно для фреймворков, которые читают аннотации в runtime (Pydantic, FastAPI).

### `get_origin` и `get_args` — разобрать generic тип

```python
from typing import get_origin, get_args, List, Dict

T = list[int]
print(get_origin(T))   # <class 'list'>
print(get_args(T))     # (<class 'int'>,)

T = dict[str, int]
print(get_origin(T))   # <class 'dict'>
print(get_args(T))     # (<class 'str'>, <class 'int'>)

T = list[int | str]
print(get_args(T))     # (typing.Union[int, str],)
```

Полезно при написании своего ORM/сериализатора — динамически проверять аннотации полей.

### `dataclass_transform` (PEP 712, Python 3.11+)

Для декораторов, которые делают то же, что `@dataclass` — добавляют методы, поля и т.д.:

```python
from typing import dataclass_transform

@dataclass_transform()
def my_dataclass(cls):
    """Декоратор, ведущий себя как dataclass — добавляет __init__, __repr__, ..."""
    # Ваша реализация
    return cls

@my_dataclass
class Point:
    x: int
    y: int
```

mypy будет проверять `Point` как dataclass — поддержка `__init__`, `__eq__`, и т.д.

## 5.13. `dataclasses` advanced2: `InitVar`, `__post_init__`, sentinel-поля

### `InitVar` — поле, передаваемое в `__init__`, но не сохраняемое

```python
from dataclasses import dataclass, InitVar

@dataclass
class Database:
    host: str
    port: int
    config_path: InitVar[str]   # принимается __init__, но не поле экземпляра
    
    def __post_init__(self, config_path: str):
        # config_path доступен только здесь
        self.config = self._load_config(config_path)
    
    def _load_config(self, path):
        # читает конфиг из файла
        return {"loaded_from": path}

db = Database("localhost", 5432, "/etc/db.conf")
print(db.host)         # 'localhost'
print(db.port)        # 5432
print(db.config)      # {'loaded_from': '/etc/db.conf'}
# print(db.config_path)   # AttributeError — InitVar не сохраняется
```

Главный кейс — параметры, которые нужны только для инициализации, не для состояния. Без `InitVar` пришлось бы сохранять `config_path` в экземпляре (лишнее поле).

⚠️ `InitVar` нельзя сделать `field(default=...)` напрямую — нужно указать default в `__init__`:

```python
@dataclass
class C:
    x: InitVar[str]
    y: int = 0

C("hello", 1)   # OK
C("hello")       # OK — y = 0 (default)
```

### `__post_init__` — инициализация после `__init__`

```python
@dataclass
class Range:
    lo: int
    hi: int
    
    def __post_init__(self):
        # Вызывается ПОСЛЕ сгенерированного __init__
        if self.lo > self.hi:
            raise ValueError(f"lo ({self.lo}) > hi ({self.hi})")

Range(10, 5)   # ValueError сразу при создании
```

**С `InitVar`** — `__post_init__` принимает его как параметр (см. пример выше).

**С frozen=True** — `__post_init__` не может модифицировать поля (нужен `object.__setattr__`):

```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float
    magnitude: float = 0   # вычисляется в post_init
    
    def __post_init__(self):
        # self.magnitude = ...   # ❌ FrozenInstanceError
        # Надо через object.__setattr__:
        object.__setattr__(self, 'magnitude', (self.x**2 + self.y**2) ** 0.5)

p = Point(3, 4)
print(p.magnitude)   # 5.0
```

### `KW_ONLY` sentinel (Python 3.10+)

```python
from dataclasses import dataclass, KW_ONLY

@dataclass
class Service:
    name: str             # positional or keyword
    _: KW_ONLY = KW_ONLY  # sentinel — все поля ниже keyword-only
    host: str = "localhost"
    port: int = 8080

Service("api", host="example.com", port=9000)   # OK
Service("api", "example.com", 9000)              # TypeError — host/port kw-only
```

`KW_ONLY` — это просто объект-маркер. Нельзя обращаться к нему как к значению (это не `None` и не `False`), но `dataclass`-декоратор распознаёт его как границу.

### `field(metadata=...)` — аннотации для third-party

(См. §5.11 metadata.)

### `@dataclass(match_args=True)` (Python 3.10+)

```python
@dataclass(match_args=True)
class Point:
    x: int
    y: int

# __match_args__ = ('x', 'y') — генерируется автоматически
# Используется в match/case:
match p:
    case Point(0, 0): print("origin")
    case Point(x=0, y=y): print(f"on Y axis at {y}")
    case Point(x=x, y=y): print(f"at ({x}, {y})")
```

### `@dataclass(order=True)` — генерирует `__lt__`, `__le__`, `__gt__`, `__ge__`

```python
@dataclass(order=True)
class Version:
    major: int
    minor: int
    patch: int

v1 = Version(1, 0, 0)
v2 = Version(1, 1, 0)
print(v1 < v2)        # True — сравнивает по полям по порядку
print(sorted([v2, v1, Version(0, 9, 0)]))
# [Version(major=0, minor=9, patch=0), Version(major=1, minor=0, patch=0), Version(major=1, minor=1, patch=0)]
```

⚠️ Сравнение идёт по полям **в порядке объявления**. Если хотите другой порядок — добавьте `field(compare=False)` к полям, которые не должны участвовать:

```python
@dataclass(order=True)
class User:
    age: int       # участвует в сравнении
    name: str = field(compare=False)   # не участвует

User(30, "Alice") < User(25, "Bob")   # False — 30 > 25, имя игнорируется
```

## 5.14. `typing` для async, IO, collections.abc

### typing async-типы

```python
from typing import Awaitable, AsyncIterator, AsyncIterable, Coroutine, AsyncGenerator

# Awaitable — любой объект, который можно await-нуть.
# Важно: аннотация async-функции — это ТИП РЕЗУЛЬТАТА await, а не тип самой корутины.
#   async def f() -> int   →  await f() вернёт int
#                          →  сама f() возвращает Coroutine[Any, Any, int]
async def fetch_int() -> int:
    return 42   # await fetch_int() даст int

# Если по какой-то причине нужна именно аннотация переменной-корутины
# (например, в промежуточной переменной):
my_coro: Coroutine[None, None, int] = fetch_int()

# AsyncIterator/AsyncIterable — для async генераторов
async def stream() -> AsyncIterator[int]:
    for i in range(10):
        yield i

# AsyncGenerator — для async генераторов с yield (T_send обычно None)
async def gen() -> AsyncGenerator[int, None]:
    yield 1
```

⚠️ **Частая ошибка** — писать `async def f() -> Awaitable[int]: return 42`. Это означает, что `await f()` вернёт `Awaitable[int]` (то есть нужно ещё раз await-ить), а не `int`. Type checker'ы (mypy, pyright) такое пропустят, но смысл будет неверный. Правильно — `async def f() -> int: return 42`. `Coroutine[None, None, T]` как return-аннотация для `async def` — та же ловушка.

Эти типы полезны в аннотациях сигнатур, особенно для абстракций (например, `async def process(stream: AsyncIterator[bytes]) -> None`).

### typing.IO / TextIO / BinaryIO

Абстракции над файлами, чтобы не привязываться к конкретному типу:

```python
from typing import IO, TextIO, BinaryIO

def read_lines(f: TextIO) -> list[str]:
    return f.readlines()

def process_binary(f: BinaryIO) -> bytes:
    return f.read()

# IO — базовый, TextIO — текстовый, BinaryIO — бинарный
with open('file.txt') as f:
    read_lines(f)   # TextIO

with open('file.bin', 'rb') as f:
    process_binary(f)   # BinaryIO

# StringIO / BytesIO тоже подходят
from io import StringIO, BytesIO
read_lines(StringIO("hello"))
```

### collections.abc — абстрактные базовые классы коллекций

```python
from collections.abc import (
    Iterable, Iterator, Generator,
    Hashable, Sized, Container, Callable,
    Sequence, MutableSequence,
    Mapping, MutableMapping,
    Set, MutableSet,
    Awaitable, Coroutine,
    AsyncIterable, AsyncIterator,
)

# Iterable — можно итерировать (for x in obj)
def total(items: Iterable[int]) -> int:
    return sum(items)

# Iterator — next/iter
def first(it: Iterator[int]) -> int:
    return next(it)

# Hashable — хешируется (можно в dict/set)
def count_unique(items: Iterable[Hashable]) -> int:
    return len(set(items))

# Sized — есть len()
def is_empty(x: Sized) -> bool:
    return len(x) == 0

# Container — поддерживает `in`
def has(items: Container[int], x: int) -> bool:
    return x in items

# Callable — можно вызвать
def apply(fn: Callable[[int], int], x: int) -> int:
    return fn(x)
```

⚠️ `collections.abc` (не `typing`) — это «настоящие» ABC, с методами по умолчанию. `typing.Iterable` — это typing-алиас для `collections.abc.Iterable`. В современном коде (Python 3.9+) можно писать просто `Iterable`, импортируя из `collections.abc`.

```python
# Старый (typing) и новый (collections.abc) — эквивалентны:
from typing import Iterable
from collections.abc import Iterable as IterableABC
Iterable is IterableABC   # True в Python 3.9+
```

### typing-алиасы для collections

Для typing коллекций в старом стиле (Python 3.8 и ниже). В 3.9+ используйте просто `list[int]`, `dict[str, int]`, и т.д.

```python
from typing import (
    List, Dict, Set, FrozenSet, Tuple,
    Counter, Deque, OrderedDict, DefaultDict, ChainMap,
    Pattern, Match,
)

# Старый стиль (Python <3.9):
def f() -> List[int]:
    return [1, 2, 3]

# Новый (Python 3.9+):
def f() -> list[int]:
    return [1, 2, 3]

# typing.Counter, typing.Deque и др.:
from collections import Counter as CounterCls, deque, OrderedDict as ODCls
def count_words(text: str) -> Counter[str]:   # typing.Counter
    return CounterCls(text.split())

def process(q: Deque[int]) -> None:   # typing.Deque
    q.append(1)
```

⚠️ В Python 3.9+ предпочтительно использовать встроенные типы (`list`, `dict`, `set`, `tuple`) и `collections.deque`, `collections.Counter` напрямую с аннотациями.

### typing.Pattern и typing.Match — regex

```python
from typing import Pattern, Match
import re

pattern: Pattern[str] = re.compile(r'\d+')
match: Match[str] = pattern.search("hello 42 world")
if match:
    print(match.group())   # '42'
```

⚠️ В Python 3.8+ `Pattern` и `Match` deprecated — используйте `re.Pattern[str]` и `re.Match[str]` напрямую.

## 5.15. `typing.TYPE_CHECKING` — типы только для статического анализа

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Этот блок выполняется ТОЛЬКО type-checker'ом (mypy)
    # В runtime — не выполняется (TYPE_CHECKING = False)
    from expensive_module import BigClass
    import heavy_dependency

def f(x: 'BigClass') -> None:
    # BigClass используется только в аннотации
    # В runtime не нужно — не импортируем на самом деле
    ...

print(TYPE_CHECKING)   # False — в runtime
```

Зачем: избежать тяжёлого импорта в production runtime, который нужен только для type checker.

```python
if TYPE_CHECKING:
    from sqlalchemy import Table, Column   # тяжёлый

class MyModel:
    table: 'Table'   # аннотация в строковом виде — mypy понимает
```

⚠️ Аннотации нужно писать как **строки** (`'BigClass'`), либо включить `from __future__ import annotations` (PEP 563) — все аннотации станут строками автоматически.

## 5.16. `ExceptionGroup` и `except*` (PEP 654, Python 3.11+)

```python
# Несколько исключений, собранных в одну группу
try:
    raise ExceptionGroup("multiple errors", [
        ValueError("bad value"),
        TypeError("bad type"),
        KeyError("missing key"),
    ])
except* ValueError as eg:
    print(f"ValueErrors: {eg.exceptions}")
except* TypeError as eg:
    print(f"TypeErrors: {eg.exceptions}")

# Если остались необработанные — пробрасываются как ExceptionGroup
```

`except*` (со звёздочкой) — новый синтаксис для ExceptionGroup. В отличие от `except`, который ловит **одно** исключение, `except*` ловит **все исключения** указанного типа из группы. Необработанные исключения остаются в новой (или исходной) группе и проверяются против следующего `except*` блока; если ни один не подошёл — пробрасываются наверх как `ExceptionGroup`.

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(risky_op_1())   # может упасть ValueError
        tg.create_task(risky_op_2())   # может упасть TypeError
    # Если обе упали — ExceptionGroup([ValueError, TypeError]).
    # except* ValueError обработает ValueError'ы, а TypeError соберётся
    # в новый ExceptionGroup и пойдёт в следующий except*.
```

`BaseExceptionGroup` — базовый класс, включая `BaseException` (например, `KeyboardInterrupt`). `ExceptionGroup` — подкласс, который содержит только `Exception` (не `BaseException`). `except*` работает с обоими, но по умолчанию ловит именно `Exception`.

## 5.17. Dunder-методы: полный обзор

В предыдущих секциях мы уже видели многие dunder'ы (`__init__`, `__eq__`, `__hash__`, `__repr__`, `__setattr__`, `__getattr__`, `__get__`/`__set__`). Этот раздел собирает остальные dunder-методы, которые редко упоминают, но которые определяют поведение объекта в стандартных операциях.

### `__str__` vs `__repr__` — два представления

```python
class Person:
    def __init__(self, name, age): self.name, self.age = name, age
    def __repr__(self):
        # Однозначное представление — для разработчиков, отладки, логов
        # Должно выглядеть как валидный Python (если возможно)
        return f"Person(name={self.name!r}, age={self.age})"
    def __str__(self):
        # Человекочитаемое — для print(), f"{p}", пользовательских сообщений
        return f"{self.name} ({self.age} лет)"

p = Person("Alice", 30)
>>> repr(p)            # "Person(name='Alice', age=30)"
>>> str(p)             # "Alice (30 лет)"
>>> p                  # в REPL — repr (через sys.displayhook)
>>> print(p)           # str
>>> f"{p}"             # str
>>> f"{p!r}"           # repr (через !r)
>>> [p, p]             # [Person(name='Alice', age=30), Person(...)] — всегда repr в коллекциях!
>>> "error: {!r}".format(p)   # repr
```

⚠️ **Если определён только `__repr__`** — `__str__` fallback'ит на него. Если только `__str__` — `repr()` покажет дефолтное `<Person object at 0x...>`. Практическое правило: **всегда определяй `__repr__`**, `__str__` — по необходимости.

⚠️ В коллекциях (`list`, `dict`, `set`) и в tracebacks всегда используется **`__repr__`**, не `__str__`. Поэтому «`print(my_list)` показывает непонятные `<Foo object at 0x...>`» — это потому, что у `Foo` нет `__repr__`.

### `__bool__` / `__len__` — преобразование к bool

Когда объект стоит в `if`/`while`/`and`/`or`/`filter` (см. truthiness в 1.8), Python зовёт:

1. `__bool__()` — если есть, использует его (должен вернуть `True`/`False`).
2. `__len__()` — если `__bool__` нет, использует длину (`0 → False`, `>0 → True`).
3. Иначе — всегда `True` (объект существует).

```python
class Box:
    def __init__(self, items): self.items = items
    def __bool__(self):
        return len(self.items) > 0   # явная семантика «есть ли что-то»

if Box([]):       # False
    process()
if Box([1, 2]):   # True
    process()

# Только __len__, без __bool__ — Python использует длину:
class Stack:
    def __init__(self): self._data = []
    def push(self, x): self._data.append(x)
    def __len__(self): return len(self._data)

if Stack():       # False — len == 0
    ...
```

⚠️ `__bool__` приоритетнее `__len__`. Если определишь оба — `__bool__` победит.

### `__len__` — для `len()`

```python
class Matrix:
    def __init__(self, rows, cols): self.rows, self.cols = rows, cols
    def __len__(self):               # для len(matrix)
        return self.rows * self.cols # «сколько элементов»
    def __bool__(self):              # если нужна другая семантика
        return self.rows > 0 and self.cols > 0

>>> m = Matrix(3, 4)
>>> len(m)          # 12 — через __len__
>>> bool(m)         # True — через __bool__ (не len>0!)
```

`len()` вызывает `__len__` напрямую (через C-level `tp_len`), без fallback'а — если `__len__` не определён, `TypeError: object of type 'X' has no len()`.

### `__iter__` / `__next__` — протокол итерации

```python
class Counter:
    """Итератор: 1, 2, 3, ..., high-1"""
    def __init__(self, low, high): self.cur, self.high = low, high
    def __iter__(self):
        return self                  # iterator = сам объект
    def __next__(self):
        if self.cur >= self.high:
            raise StopIteration      # сигнал конца итерации
        v = self.cur
        self.cur += 1
        return v

>>> list(Counter(1, 5))             # [1, 2, 3, 4]
>>> c = Counter(10, 13)
>>> iter(c) is c                     # True — итератор возвращает себя из __iter__
>>> next(c), next(c), next(c)        # (10, 11, 12)
>>> next(c)                          # StopIteration
```

**Два протокола**:
- **Iterable** — реализует только `__iter__`, возвращает **новый** итератор при каждом вызове. Можно итерировать многократно.
- **Iterator** — реализует `__iter__` (возвращает `self`) + `__next__`. **Одноразовый** — после `StopIteration` исчерпан.

```python
# Iterable: можно итерировать много раз
class Range:
    def __init__(self, low, high): self.low, self.high = low, high
    def __iter__(self):              # каждый раз — новый итератор
        return iter(range(self.low, self.high))

r = Range(1, 4)
list(r)        # [1, 2, 3]
list(r)        # [1, 2, 3] — снова работает
```

Альтернатива `__iter__` — генератор (yield), см. Часть III (3.1).

### `__call__` — вызов экземпляра как функции

```python
class Adder:
    def __init__(self, n): self.n = n
    def __call__(self, x):
        return self.n + x

>>> add5 = Adder(5)
>>> add5(3)                  # 8 — вызов как функция
>>> callable(add5)           # True (см. 1.23)
>>> add5(10) + add5(20)      # 15 + 25 = 40

# Stateful callable:
class Counter:
    def __init__(self): self.count = 0
    def __call__(self):
        self.count += 1
        return self.count

>>> c = Counter()
>>> c(), c(), c()            # (1, 2, 3)
```

**Когда `__call__` вместо функции**:
- Нужны **настраиваемые** callable-объекты (декораторы с параметрами, стратегии).
- Состояние между вызовами удобнее хранить в атрибутах, чем в closure.
- Проверка `callable(obj)` работает на экземплярах с `__call__`.

### `__contains__` — для `in`

```python
class EvenContainer:
    """«Содержит» только чётные числа — без реального хранения."""
    def __contains__(self, item):
        return item % 2 == 0

>>> 2 in EvenContainer()    # True
>>> 3 in EvenContainer()    # False
>>> 1000000 in EvenContainer()  # True — без аллокации массива

# Без __contains__ — Python fallback'ит на __iter__ и перебирает
class List:
    def __init__(self, items): self.items = items
    def __iter__(self): return iter(self.items)
    # __contains__ нет → `x in obj` пройдёт по __iter__ до x или конца
```

⚠️ Определи `__contains__`, если у тебя есть **более быстрый способ** проверить принадлежность, чем полный перебор (хеш-таблица, диапазон, regex-матч).

### `__missing__` — для `dict[key]` при отсутствии ключа

```python
class DefaultDict(dict):
    """Как collections.defaultdict, но через __missing__."""
    def __missing__(self, key):
        return f"<missing:{key}>"

>>> d = DefaultDict(a=1, b=2)
>>> d['a']           # 1 — обычный lookup
>>> d['z']           # '<missing:z>' — ключа нет, вызвался __missing__
>>> 'z' in d         # False! 'in' вообще не вызывает __missing__ — только __getitem__
>>> d.get('z')       # None — .get() тоже не вызывает __missing__

# Stateful: считать обращения к несуществующим ключам
class CountingDict(dict):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.misses = []
    def __missing__(self, key):
        self.misses.append(key)
        return None
```

⚠️ `__missing__` работает **только если класс наследуется от `dict`** (или реализует `__getitem__` так, чтобы он вызывал `__missing__`). У обычного `object.__getitem__` нет такой логики.

`collections.defaultdict` — это dict, у которого `__missing__` вставляет значение из `default_factory`. То есть `defaultdict(list)['new']` возвращает `[]` и **сохраняет** его в dict.

### `__reversed__` — для `reversed()`

```python
class Countdown:
    def __init__(self, n): self.n = n
    def __iter__(self):           # прямой: n, n-1, ..., 1
        return iter(range(self.n, 0, -1))
    def __reversed__(self):       # обратный: 1, 2, ..., n
        return iter(range(1, self.n + 1))

>>> list(Countdown(5))                # [5, 4, 3, 2, 1]
>>> list(reversed(Countdown(5)))      # [1, 2, 3, 4, 5] — через __reversed__
```

Без `__reversed__` Python fallback'ит на `__len__` + `__getitem__` (как в 1.14, протокол `__getitem__`-итерации) — строит индексы от `len-1` до `0`. Это работает, но если у тебя есть более эффективный обратный итератор — определи `__reversed__`.

### `__index__` — для неявного int-конвертирования

`__index__` вызывается, когда объект используется **как индекс** или в функциях, ожидающих целое:

```python
class Hex:
    """Число, представимое как hex."""
    def __init__(self, v): self.v = v
    def __index__(self):       # ← вызывается для slice, bin, hex, oct, int()
        return self.v

>>> h = Hex(255)
>>> bin(h)               # '0b11111111' — использует __index__
>>> hex(h)               # '0xff'
>>> oct(h)               # '0o377'
>>> [1,2,3,4,5][:Hex(3)] # [1, 2, 3] — slice использует __index__
>>> int.__index__(42)    # 42 — для обычного int __index__ = self

# Где используется __index__:
# - a[obj]            ← __getitem__ с __index__
# - a[i:j:k]          ← slice — все три через __index__
# - bin(obj), hex(obj), oct(obj)
# - int.from_bytes(..., byteorder) если byteorder — объект с __index__
# - array('i', ...) при определении размера
```

⚠️ **`__int__` vs `__index__`** — разные протоколы:
- `__int__` — для явного `int(obj)` конвертирования. Допускает «математическое» преобразование (напр. `int(3.14)`).
- `__index__` — для использования как индекс/битовое-представление. Должен возвращать **точно** int, без потери точности.

`bool` реализует `__index__` (True=1, False=0), но `float` — **нет** (`int(3.0)` работает через `__int__`, но `bin(3.0)` падает с `TypeError`).

### `__del__` — финализатор при сборке мусора

`__del__` вызывается, когда объект собирается сборщиком мусора. Это **не** деструктор в C++-смысле — момент вызова **не детерминирован**, и порядок `__del__` для связанных объектов не гарантирован.

```python
class Resource:
    def __init__(self, name):
        self.name = name
        print(f"  acquired {self.name}")
    def __del__(self):
        print(f"  released {self.name}")

>>> r = Resource("A")      # acquired A
>>> del r                  # released A — иногда сразу
>>> # но может быть и отложено до GC

# Практический (но рискованный) кейс:
class TempFile:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'w')
    def __del__(self):
        try:
            self.f.close()
            import os; os.unlink(self.path)
        except Exception:        # ← нельзя дать __del__ поднять исключение!
            pass                  # иначе Python напечатает "Exception ignored in __del__"
                                   # ⚠️ именно Exception, а не bare except — иначе
                                   # проглотится KeyboardInterrupt и SystemExit
```

⚠️ **Не полагайся на `__del__`** для критичных cleanup-операций (закрытие файлов, соединений с БД, снятие блокировок):
- GC может не вызвать `__del__` до выхода процесса (особенно для циклических ссылок).
- При `sys.exit()` или `os._exit()` `__del__` не вызывается.
- Порядок вызова между объектами не гарантирован.

Для детерминированного cleanup используй **контекстные менеджеры** (`with`, см. Часть II) или `weakref.finalize` (Часть VIII, 8.14). `__del__` — только для best-effort cleanup (логирование, статистика, кэш).

⚠️ Если `__del__` поднимает исключение — Python печатает `Exception ignored in: <obj>` в stderr и **продолжает** работу. Исключение не propagates — его некому ловить.

### Сводная таблица dunder'ов

| Категория | Dunder | Когда вызывается |
|---|---|---|
| **Инициализация** | `__init__`, `__new__`, `__del__` | создание, сборка мусора |
| **Строковое представление** | `__str__`, `__repr__`, `__format__`, `__bytes__` | `str()`, `repr()`, f-strings, `bytes()` |
| **Сравнения** | `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__hash__` | `==`, `<`, `>`, `hash()`, dict/set |
| **Арифметика** | `__add__`, `__sub__`, `__mul__`, `__truediv__`, `__floordiv__`, `__mod__`, `__pow__`, `__matmul__` | `+`, `-`, `*`, `/`, `//`, `%`, `**`, `@` |
| **Reflected** | `__radd__`, `__rsub__`, ... | когда левый операнд не реализует операцию |
| **In-place** | `__iadd__`, `__isub__`, ..., `__imatmul__` | `+=`, `-=`, ..., `@=` |
| **Унарные** | `__neg__`, `__pos__`, `__abs__`, `__invert__`, `__bool__` | `-x`, `+x`, `abs(x)`, `~x`, `bool(x)` |
| **Преобразования** | `__int__`, `__float__`, `__complex__`, `__index__`, `__round__`, `__trunc__`, `__floor__`, `__ceil__` | `int()`, `float()`, `complex()`, `bin/hex/oct`, `round()`, `math.trunc/floor/ceil` |
| **Итерация** | `__iter__`, `__next__`, `__reversed__`, `__contains__` | `for`, `iter()`, `next()`, `reversed()`, `in` |
| **Доступ по ключу** | `__getitem__`, `__setitem__`, `__delitem__`, `__missing__`, `__len__` | `obj[k]`, `obj[k]=v`, `del obj[k]`, `len()` |
| **Атрибуты** | `__getattr__`, `__getattribute__`, `__setattr__`, `__delattr__`, `__dir__` | доступ к атрибутам |
| **Дескрипторы** | `__get__`, `__set__`, `__delete__`, `__set_name__` | доступ через класс (Часть VI) |
| **Контекст** | `__enter__`, `__exit__`, `__aenter__`, `__aexit__` | `with`, `async with` (Часть II, IV) |
| **Callable** | `__call__` | `obj(args)` |
| **Класс-мета** | `__class__`, `__dict__`, `__mro__`, `__subclasses__`, `__init_subclass__` | интроспекция (Часть V, VIII) |
| **Размер** | `__sizeof__` | `sys.getsizeof()` |

### Бенчмарки к Части V

**1. `@dataclass` vs обычный класс — память одного экземпляра.**
```python
import sys
from dataclasses import dataclass

class PointClass:
    def __init__(self, x: float, y: float):
        self.x = x; self.y = y

@dataclass
class PointData:
    x: float
    y: float

p1 = PointClass(1.0, 2.0)
p2 = PointData(1.0, 2.0)
print(sys.getsizeof(p1), sys.getsizeof(p1.__dict__))   # 48 + 112 = 160 байт
print(sys.getsizeof(p2), sys.getsizeof(p2.__dict__))   # 48 + 112 = 160 байт
```
Память **идентична** — `dataclass` генерирует тот же `__init__`, что и ручной.
Выгода `dataclass` — в `__repr__`, `__eq__`, `__hash__`, `field()`, `__post_init__`
«из коробки», а не в скорости или памяти.

**2. `__slots__` — реальная экономия на миллионах объектов.**
```python
import sys
from dataclasses import dataclass

@dataclass
class NoSlots:
    x: float; y: float; label: str = "origin"

@dataclass(slots=True)
class WithSlots:
    x: float; y: float; label: str = "origin"

n, ns, ws = 100_000, [], []
ns = [NoSlots(i, i)   for i in range(n)]   # 1 000 000 объектов
ws = [WithSlots(i, i) for i in range(n)]
print(sys.getsizeof(ns[0]) + sys.getsizeof(ns[0].__dict__))  # ≈ 160 байт/объект
print(sys.getsizeof(ws[0]))                                  # ≈ 64 байта/объект
# На 1M объектов: 160 MB vs 64 MB — экономия ~96 MB (≈40%)
```
Дополнительно: доступ к слот-атрибуту ~1.05× быстрее обычного (`__dict__` lookup
— это хеш-таблица, slot — это смещение в массиве).

**3. `frozen=True` vs обычный класс — цена immutability.**
```python
from dataclasses import dataclass
import timeit

@dataclass(frozen=True)
class Frozen:
    x: float; y: float

@dataclass
class Mutable:
    x: float; y: float

# Конструктор
print(timeit.timeit("Frozen(1.0, 2.0)", globals=globals(), number=1_000_000))  # ≈ 0.43 с
print(timeit.timeit("Mutable(1.0, 2.0)", globals=globals(), number=1_000_000))  # ≈ 0.21 с
```

`frozen=True` **на ~100% медленнее** в конструкторе (в 2 раза) на CPython 3.12. Причина — **не** в проверках `__setattr__` (как часто думают), а в самой механике записи полей:

```python
import dis
from dataclasses import dataclass

@dataclass(frozen=True)
class Frozen:
    x: float; y: float

@dataclass
class Mutable:
    x: float; y: float

# Mutable.__init__ (упрощённо): прямая запись в __dict__
#   LOAD_FAST 'x'; STORE_FAST 'self.x'   ← один опкод на поле

# Frozen.__init__: ВЫЗОВ object.__setattr__ на каждое поле
dis.dis(Frozen.__init__)
#   LOAD_DEREF  __dataclass_builtins_object__
#   LOAD_ATTR   __setattr__              ← lookup через closure
#   LOAD_FAST   self
#   LOAD_CONST  'x'
#   LOAD_FAST   x
#   CALL        3                        ← CALL на каждое поле
#   POP_TOP
# (повторяется для y)
```

Mutable пишет поля напрямую в `self.__dict__` (опкод `STORE_FAST`-подобный). Frozen **не может** так делать — `__dict__` недоступен (точнее, писать в него напрямую нельзя, иначе frozen можно было бы обойти). Поэтому сгенерированный `__init__` идёт через `object.__setattr__(self, 'x', x)` — это **функциональный вызов** на каждое поле, плюс lookup `__setattr__` через closure (`__dataclass_builtins_object__`). Это и есть основная цена замедления.

**А что же проверяет `__setattr__`?** Сгенерированный `Frozen.__setattr__` поднимает `FrozenInstanceError`, **но он не вызывается из `__init__`** (тот идёт через `object.__setattr__` напрямую, минуя переопределённый `__setattr__` класса). Проверка работает только при **последующих** попытках мутации:

```python
f = Frozen(1.0, 2.0)
f.x = 10   # ← вот тут сработает Frozen.__setattr__ → FrozenInstanceError
```

Сам `Frozen.__setattr__` (через `dis`) проверяет два условия:

```
type(self) is cls              → если да, raise FrozenInstanceError
                                (мы в "своём" классе — frozen защищает)
name in frozenset({'x', 'y'})  → если да, raise FrozenInstanceError
                                (защита полей этого класса)
иначе → super().__setattr__(name, value)   # пускает дальше
```

Никакого флага `__dataclass_frozen__` в CPython 3.12+ **нет** (это часто цитируемая ошибка из старых блогов). Вся защита построена на `type(self) is cls` + `frozenset` имён полей — оба значения «зашиты» в кодген через замыкания (`cls`, `__dataclass_builtins_object__`).

**Берите `frozen` для иммутабельности и хешируемости, не для скорости.**

### ⚠️ frozen ≠ глубокая иммутабельность

`frozen=True` замораживает только **переприсваивание атрибутов**: `f.x = 10` упадёт. Но если поле — мутируемый объект (list, dict, set), его **содержимое** можно свободно менять:

```python
@dataclass(frozen=True)
class Article:
    title: str
    tags: list

a = Article("Python", ["x", "y"])
a.title = "Other"      # ❌ FrozenInstanceError
a.tags.append("z")     # ✅ работает! список мутирован
print(a)               # Article(title='Python', tags=['x', 'y', 'z'])
```

Это ломает **хеш-инвариант**: `hash(a)` строится из значений полей, а `tags` — список, который не хешируется. Если бы `tags` был tuple, хеш бы работал, но изменился бы при пересоздании tuple — и `a` в `set`/`dict` стал бы «потерян»:

```python
@dataclass(frozen=True)
class Article:
    title: str
    tags: tuple

a = Article("Python", ("x", "y"))
d = {a: 1}
a2 = Article("Python", ("x", "y", "z"))   # новый объект — другой хеш
print(d.get(a2))   # None — хотя "a" и "a2" по логике одна статья
```

**Правило**: для настоящей иммутабельности все поля должны быть иммутабельными типами (`int`, `str`, `tuple`, `frozenset`, другие `frozen` dataclass'ы). Если есть `list`/`dict`/`set` — frozen защищает только от `a.x = ...`, но не от `a.x.append(...)`. Для мутируемых полей используй `tuple`/`frozenset`/`MappingProxyType` либо клонируй при каждом изменении.

### Обход frozen через подкласс

Раз защита = `type(self) is cls OR name in frozenset`, **подкласс** легко обходит frozen для своих новых полей: их имена не в `frozenset`, и `type(self) is cls` ложно (self — экземпляр подкласса, не базового), значит срабатывает `super().__setattr__`:

```python
@dataclass(frozen=True)
class Base:
    x: int

class Sub(Base):
    __slots__ = ('y',)
    def __init__(self, x, y):
        super().__init__(x)        # x — через Frozen.__init__ (object.__setattr__)
        object.__setattr__(self, 'y', y)   # y — напрямую, минуя frozen-проверку

s = Sub(1, 2)
s.x = 100   # ❌ FrozenInstanceError — x в frozenset базового класса
s.y = 200   # ✅ работает — Sub не объявлял frozen, и __setattr__ унаследован,
            # но для Sub-полей срабатывает super().__setattr__
print(s)    # (если дать __repr__) Sub с x=1, y=200
```

Это не «баг» — это естественное следствие механики. Если нужно запретить подклассам мутировать свои поля — они должны явно пометить `@dataclass(frozen=True)`.

**4. ABC + `@abstractmethod` vs `Protocol` — цена `isinstance`.**
```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
import timeit

class ABCDrawable(ABC):
    @abstractmethod
    def draw(self) -> None: ...

@runtime_checkable
class ProtoDrawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None: pass

c = Circle()
print(isinstance(c, ABCDrawable))    # False (не наследует)
print(isinstance(c, ProtoDrawable))  # True (структурно)
# Скорость isinstance:
print(timeit.timeit(lambda: isinstance(c, ProtoDrawable), number=1_000_000))  # ≈ 0.20 с
```
`runtime_checkable`-проверка **медленнее** обычного `isinstance` (~0.2 мкс/вызов),
потому что проверяет наличие методов через `hasattr`. На горячих путях — кешируйте.

**5. `Enum` vs `str`-константы — скорость сравнения.**
```python
from enum import Enum, auto
import timeit
class Status(Enum):
    ACTIVE = auto()
    INACTIVE = auto()
# Сравнение Enum vs str
print(timeit.timeit("Status.ACTIVE == Status.ACTIVE", globals=globals(), number=10_000_000))  # ≈ 0.45 с
print(timeit.timeit("'active' == 'active'", number=10_000_000))                                # ≈ 0.18 с
```
Enum **в 2–3× медленнее** сравнения строк, но даёт типобезопасность и автодополнение.
На горячих путях (миллионы сравнений в секунду) — вынимайте `.value` один раз.


