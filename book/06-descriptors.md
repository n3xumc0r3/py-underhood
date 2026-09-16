# Часть VI. Дескрипторы и property

## 6.1. `__get__`/`__set__`/`__delete__` — протокол дескрипторов

**Дескриптор** — это объект, который реализует один или несколько из методов `__get__`, `__set__`, `__delete__`. Когда такой объект используется как атрибут класса, Python **перехватывает** доступ и вызывает эти методы.

```python
class TypedField:
    def __init__(self, name, type_):
        self.name = name
        self.type_ = type_
    
    def __set_name__(self, owner, name):
        # вызывается при создании класса, позволяет узнать имя атрибута
        self.name = name
    
    def __get__(self, instance, owner):
        if instance is None:
            return self   # доступ через класс, не через экземпляр
        return instance.__dict__.get(self.name)
    
    def __set__(self, instance, value):
        if not isinstance(value, self.type_):
            raise TypeError(f"{self.name} должен быть {self.type_.__name__}")
        instance.__dict__[self.name] = value
    
    def __delete__(self, instance):
        del instance.__dict__[self.name]

class User:
    name = TypedField("", str)
    age = TypedField("", int)

u = User()
u.name = "Alice"
u.age = 30           # OK
u.age = "30"         # TypeError!
print(u.name)        # Alice
```

Сигнатуры:
```python
def __get__(self, instance, owner=None):
    # instance — объект, через который обратились (None если через класс)
    # owner — класс (то же что type(instance))
    ...

def __set__(self, instance, value):
    ...

def __delete__(self, instance):
    ...
```

## 6.2. Data vs non-data descriptors

| Тип | Реализует | Приоритет |
|------|-----------|-----------|
| **Data descriptor** | `__set__` (и/или `__delete__`) + `__get__` | **Выше**, чем `__dict__` экземпляра |
| **Non-data descriptor** | только `__get__` | **Ниже**, чем `__dict__` экземпляра |

```python
class DataDesc:
    def __get__(self, obj, owner): return "from data descriptor"
    def __set__(self, obj, value): pass

class NonDataDesc:
    def __get__(self, obj, owner): return "from non-data descriptor"

class C:
    data = DataDesc()
    non_data = NonDataDesc()

c = C()
c.__dict__['data'] = "instance value"
c.__dict__['non_data'] = "instance value"

print(c.data)        # "from data descriptor" — data descriptor побеждает __dict__
print(c.non_data)    # "instance value" — __dict__ экземпляра побеждает non-data descriptor
```

Это фундаментальное правило, на котором построены `@property` (data descriptor, `__set__` валидирует), `@classmethod`/`@staticmethod` (non-data descriptors).

## 6.3. `__set_name__` — автоматическая инициализация (PEP 487, Python 3.6+)

`__set_name__(self, owner, name)` вызывается для каждого дескриптора при создании класса. Позволяет дескриптору узнать, под каким именем он привязан:

```python
class Field:
    def __init__(self, default=None):
        self.default = default
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = name   # теперь знаем, как нас зовут
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)
    
    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

class Config:
    host = Field("localhost")
    port = Field(8080)
    debug = Field(False)

c = Config()
print(c.host)         # localhost
c.host = "example.com"
print(c.host)         # example.com
```

Без `__set_name__` пришлось бы передавать имя в `__init__`: `Field("host", "localhost")` — теперь можно автоматически.

## 6.4. `@property` — что под капотом

> **→ см. также:** Часть VII (7.4) — `functools.wraps` и `cached_property` как частные случаи дескрипторов-декораторов.

`@property` — это **data descriptor**. Под капотом `property(fget, fset, fdel, doc)`:

```python
# @property эквивалентно:
class Property:
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc
    
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(instance)
    
    def __set__(self, instance, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(instance, value)
    
    def __delete__(self, instance):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(instance)
    
    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__)
    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__)
    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__)
```

Поэтому `@property` + `@x.setter` работают как декораторы:

```python
class C:
    @property
    def x(self):
        return self._x
    
    @x.setter
    def x(self, value):
        if value < 0:
            raise ValueError("must be non-negative")
        self._x = value
```

`@property` создаёт `Property(fget=x)`. `@x.setter` возвращает новый `Property(fget, fset)`. `@x.deleter` — то же с `fdel`.

⚠️ **Если у свойства только getter — это read-only:**

```python
class Circle:
    def __init__(self, r): self.r = r
    @property
    def area(self): return 3.14 * self.r ** 2

c = Circle(5)
c.area = 100   # AttributeError: can't set attribute
```

⚠️ **Property не должно быть тяжёлым** — пользователь ожидает мгновенного доступа. Не делайте в `@property` HTTP-запросы или чтение файлов.

## 6.5. `__getattr__` vs `__getattribute__` vs `__setattr__`

```python
class Flexible:
    def __getattr__(self, name):
        # Вызывается ТОЛЬКО когда атрибут НЕ найден обычным путём
        print(f"__getattr__ for {name}")
        return None
    
    def __getattribute__(self, name):
        # Вызывается при ЛЮБОМ доступе к атрибуту (даже если он есть)
        print(f"__getattribute__ for {name}")
        return super().__getattribute__(name)
    
    def __setattr__(self, name, value):
        # Вызывается при ЛЮБОМ присваивании
        print(f"__setattr__ {name}={value}")
        super().__setattr__(name, value)
    
    def __delattr__(self, name):
        # Вызывается при del obj.attr
        print(f"__delattr__ {name}")
        super().__delattr__(name)
```

### `__getattr__` — fallback для отсутствующих атрибутов

```python
class DictLike:
    def __init__(self):
        self.real_data = {}
    
    def __getattr__(self, name):
        # Вызывается только если name не найдено в __dict__ и в классе
        return self.real_data.get(name, "not found")

d = DictLike()
d.real_data['x'] = 42
print(d.x)       # 42 — нашёл в real_data
print(d.y)       # "not found" — fallback
print(d.real_data)  # словарь — обычный доступ, не fallback
```

### `__getattribute__` — для каждого доступа (осторожно!)

```python
class Logging:
    def __getattribute__(self, name):
        print(f"Доступ к {name}")
        return super().__getattribute__(name)
    
    def method(self):
        # Если внутри вызвать self.helper() — будет рекурсия!
        # __getattribute__ вызывается для self.helper,
        # который внутри себя вызовет __getattribute__...
        pass
```

⚠️ **Главная ловушка `__getattribute__`** — лёгкая рекурсия. Любое обращение к `self.X` внутри `__getattribute__` вызывает сам `__getattribute__`. Чтобы избежать — **всегда** вызывайте `super().__getattribute__(name)`:

```python
def __getattribute__(self, name):
    # ПРАВИЛЬНО:
    real_data = super().__getattribute__('real_data')
    if name in real_data:
        return real_data[name]
    return super().__getattribute__(name)
    # НЕПРАВИЛЬНО:
    # if name in self.real_data: ...   # рекурсия!
```

### `__setattr__` — для каждого присваивания

```python
class Immutable:
    def __setattr__(self, name, value):
        raise AttributeError("immutable object")

class OnceSet:
    def __setattr__(self, name, value):
        # Разрешить установить только один раз
        if name in self.__dict__:
            raise AttributeError(f"{name} already set")
        super().__setattr__(name, value)

obj = OnceSet()
obj.x = 1   # OK
obj.x = 2   # AttributeError
```

⚠️ Та же проблема с рекурсией — внутри `__setattr__` нельзя `self.X = ...`, нужно `super().__setattr__(name, value)` или `self.__dict__[name] = value`.

**Когда что:**
- `__getattr__` — для динамических атрибутов (lazy properties, прокси к словарям, ORM).
- `__getattribute__` — для перехвата любого доступа (логирование, аудит). Редко нужен.
- `__setattr__` — для валидации или immutability.
- `__delattr__` — аналогично для удаления.

---

### Бенчмарки к Части VI

**1. `@property` vs прямой атрибут vs дескриптор.**
```python
import timeit

class Direct:
    def __init__(self): self.x = 0

class WithProperty:
    @property
    def x(self): return self._x
    @x.setter
    def x(self, v): self._x = v
    def __init__(self): self._x = 0

class Descriptor:
    class _Desc:
        def __get__(self, obj, owner): return obj._x
        def __set__(self, obj, v): obj._x = v
    x = _Desc()
    def __init__(self): self._x = 0

d, p, de = Direct(), WithProperty(), Descriptor()
print(timeit.timeit("d.x = 1; _ = d.x",     globals={"d": d},  number=5_000_000))  # ≈ 0.35 с
print(timeit.timeit("p.x = 1; _ = p.x",     globals={"p": p},  number=5_000_000))  # ≈ 0.85 с
print(timeit.timeit("de.x = 1; _ = de.x",   globals={"de": de},number=5_000_000))  # ≈ 0.95 с
```
`@property` и дескриптор **в 2–3× медленнее** прямого доступа из-за вызова
`__get__`/`__set__`. На горячих путях (миллионы операций) — храните значение
в обычном атрибуте, валидацию делайте в `__init__`.

**2. `functools.cached_property` vs ручной memoization.**
```python
from functools import cached_property
import timeit

class WithCache:
    @cached_property
    def heavy(self):
        return sum(range(1_000_000))

class Manual:
    @property
    def heavy(self):
        if not hasattr(self, "_heavy"):
            self._heavy = sum(range(1_000_000))
        return self._heavy

# Первый вызов — одинаково (~30 мс на sum(range(1_000_000)))
# Второй и далее:
wc, m = WithCache(), Manual()
_ = wc.heavy; _ = m.heavy   # прогрев
print(timeit.timeit("wc.heavy", globals={"wc": wc}, number=1_000_000))   # ≈ 0.08 с
print(timeit.timeit("m.heavy",  globals={"m": m},   number=1_000_000))   # ≈ 0.30 с
```
`cached_property` **в ~4× быстрее** ручной memoization через `@property` +
`hasattr` — после первого вычисления он сохраняет значение прямо в `__dict__`
и `@property` больше не вызывается.

**3. `__getattr__` vs `__getattribute__` — цена перехвата.**
```python
import timeit
class GetAttr:
    def __getattr__(self, name):
        raise AttributeError(name)
    a = 1   # реальный атрибут

class GetAttribute:
    def __getattribute__(self, name):
        return object.__getattribute__(self, name)
    a = 1

g1, g2 = GetAttr(), GetAttribute()
print(timeit.timeit("g1.a", globals={"g1": g1}, number=5_000_000))   # ≈ 0.30 с
print(timeit.timeit("g2.a", globals={"g2": g2}, number=5_000_000))   # ≈ 0.55 с
```
`__getattribute__` **в ~2× медленнее** — он вызывается на **каждый** доступ
к любому атрибуту, тогда как `__getattr__` только при отсутствии атрибута
в `__dict__`/классе. Используйте `__getattr__` по умолчанию,
`__getattribute__` — только для аудита/прокси (см. 6.5).

**4. Data descriptor vs non-data descriptor.**
```python
# Data descriptor (с __set__) — перехватывает и чтение, и запись
# Non-data descriptor (только __get__) — перехватывает только чтение,
# запись идёт в instance.__dict__ и «затеняет» дескриптор.
class DataDesc:
    def __get__(self, obj, owner): return 1
    def __set__(self, obj, v): pass
class NonDataDesc:
    def __get__(self, obj, owner): return 1
class C:
    d1 = DataDesc()
    d2 = NonDataDesc()
c = C()
c.d2 = 99   # затеняет дескриптор
print(c.d2) # 99 — дескриптор «не виден»
```
Это не скорость, а **семантика**: data descriptor всегда побеждает
`instance.__dict__`, non-data — только если атрибута ещё нет в `__dict__`.

