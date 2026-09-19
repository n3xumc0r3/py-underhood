# Часть VI. Дескрипторы и property

## 6.1. `__get__`/`__set__`/`__delete__` — протокол дескрипторов { #6.1 }

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

## 6.2. Data vs non-data descriptors { #6.2 }

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

## 6.3. `__set_name__` — автоматическая инициализация (PEP 487, Python 3.6+) { #6.3 }

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

## 6.4. `@property` — что под капотом { #6.4 }

> **→ см. также:** Часть VII (7.4) — `functools.wraps`; `cached_property` — в 6.6 и Части XI (11.1) как частные случаи дескрипторов.

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
c.area = 100   # AttributeError: property 'area' of 'Circle' object has no setter (текст на 3.12)
```

⚠️ **Property не должно быть тяжёлым** — пользователь ожидает мгновенного доступа. Не делайте в `@property` HTTP-запросы или чтение файлов.

## 6.5. `__getattr__` vs `__getattribute__` vs `__setattr__` { #6.5 }

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

### `__getattr__` — fallback для отсутствующих атрибутов { #6.5-getattr }

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

### `__getattribute__` — для каждого доступа (осторожно!) { #6.5-getattribute }

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

### `__setattr__` — для каждого присваивания { #6.5-setattr }

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

## 6.6. `functools.cached_property` vs `@property` + кэш в `__dict__` { #6.6 }

Вся разница между `@property` и `@cached_property` выводится из 6.2: `property` — **data**-дескриптор (есть `__set__`), поэтому его `__get__` срабатывает при **каждом** доступе; `cached_property` — **non-data**-дескриптор, и после первого вызова значение, положенное в `instance.__dict__`, **затеняет** дескриптор — дальше работает обычный поиск атрибута, дескриптор не вызывается вовсе.

Механизм в чистом виде — вся начинка `cached_property` на десяти строках:

```python
class CachedProperty:
    def __init__(self, func):
        self.func = func
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name                      # чтобы знать, куда писать кэш

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = self.func(instance)
        instance.__dict__[self.name] = value  # затеняем себя — больше не вызовемся
        return value

class Circle:
    def __init__(self, r):
        self.r = r

    @CachedProperty
    def area(self):
        print("вычисляю")                     # маркер: сколько раз вызывалось
        return 3.14159 * self.r ** 2

c = Circle(2)
c.area        # вычисляю  → 12.57
c.area        # 12.57 — print не сработал: вернулось значение из __dict__
c.__dict__    # {'r': 2, 'area': 12.57} — кэш лежит в обычном __dict__
```

`functools.cached_property` — то же самое плюс реализация `__set_name__` внутри и поддержка параллельных потоков «как получится» (об этом ниже):

```python
from functools import cached_property

class Circle:
    def __init__(self, r):
        self.r = r

    @cached_property
    def area(self):
        return 3.14159 * self.r ** 2
```

**Сброс кэша.** Поскольку кэш — обычный атрибут `__dict__`, им управляют стандартные средства:

```python
del c.area          # удалить затеняющее значение — следующий доступ пересчитает
c.area              # снова заходит в дескриптор
c.__dict__.pop('area', None)   # то же самое в лоб
```

С `@property` такой трюк не нужен — там каждый доступ и так свежий.

Сравнение механизмов:

| | `@property` | `@cached_property` | кэш вручную в `__init__` |
|---|---|---|---|
| Тип дескриптора | data (есть `__set__`) | non-data | — |
| Момент вычисления | каждый доступ | первый доступ | создание объекта |
| Повторные вызовы | пересчитывает | `__dict__` затеняет дескриптор | готово сразу |
| Память | нулевая | растёт с числом экземпляров | растёт с числом экземпляров |
| Запись извне | контролируется `__set__` | просто перезапишет кэш | как обычный атрибут |
| `__slots__` | работает | **ломается** (нет `__dict__`) | на выбор: слот или `__dict__` |
| Ленивость | да | да | нет |

**⚠️ Потокобезопасность.** `cached_property` не берёт блокировку — это задокументировано в `functools`. Окно гонки: два потока одновременно видят отсутствие значения в `__dict__`, оба вычисляют функцию, побеждает запись последнего. Для чистой функции это просто потерянный такт; для функции с побочными эффектами (создание файла, соединения, запись метрик) — двойное исполнение. Если вычисление дорогое и конкурентное — блокировка поверх:

```python
import threading

class LockedCachedProperty:
    """cached_property с двойной проверкой: конкурентные доступы вычисляют один раз."""

    def __init__(self, func):
        self.func = func
        self.lock = threading.Lock()

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.name]        # быстрый путь без замка
        except KeyError:
            with self.lock:
                try:
                    return instance.__dict__[self.name]  # второй поток дождался
                except KeyError:
                    value = self.func(instance)
                    instance.__dict__[self.name] = value
                    return value
```

**Когда что выбирать.** `cached_property` — для дорогих **чистых** вычислений, производных от неизменяемых полей (`area` от `r`). Для функций с побочными эффектами или от изменяемого состояния он опасен именно тем, чем хорош: молчаливым запоминанием. Обратились к атрибуту до изменения данных — и получили устаревшее значение без всякой ошибки. Если состояние меняется — либо `@property`, либо явный `del obj.attr` в месте изменения.

→ **см. также:** 6.2 — почему затенение работает только для non-data; 6.10 — жизнь cached_property на `__slots__`-классе; 5.8 — `__slots__`.

## 6.7. `__set_name__` на практике: поле ORM { #6.7 }

В 6.3 `__set_name__` просто запоминал своё имя. То же событие — фундамент декларативных ORM (Django, SQLAlchemy declarative, peewee): дескриптор-поле при создании класса узнаёт имя колонки, валидирует значения при записи, а при доступе **через класс** возвращает метаданные для построения запросов.

```python
class Column:
    """Декларативное поле таблицы в духе мини-Django."""
    py_type = object
    sql_type = "TEXT"

    def __init__(self, *, default=None, nullable=True, primary_key=False):
        self.default = default
        self.nullable = nullable
        self.primary_key = primary_key
        self.name = None                      # придёт из __set_name__
        self.owner = None                     # класс-владелец

    def __set_name__(self, owner, name):
        if self.name is not None:             # защита от повторной привязки
            raise TypeError(
                f"Поле {self.name!r} уже привязано к {self.owner.__name__},"
                f" повторная привязка: {owner.__name__}.{name}"
            )
        self.name = name
        self.owner = owner

    def __get__(self, instance, owner):
        if instance is None:
            return self                       # доступ через класс → метаданные
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):
        if value is None:
            if not self.nullable:
                raise ValueError(f"{self.name}: NOT NULL")
        elif not isinstance(value, self.py_type):
            raise TypeError(
                f"{self.name}: ожидалось {self.py_type.__name__},"
                f" получено {type(value).__name__}"
            )
        instance.__dict__[self.name] = value

class IntColumn(Column):
    py_type = int
    sql_type = "INTEGER"

class TextColumn(Column):
    py_type = str

class User:
    id = IntColumn(primary_key=True)
    name = TextColumn(nullable=False)
    email = TextColumn()

u = User()
u.id = 1
u.name = "ann"
print(User.name.sql_type)     # TEXT — доступ через класс: метаданные поля
print(u.name)                 # ann  — доступ через экземпляр: значение
u.id = "1"                    # TypeError: id: ожидалось int, получено str
```

Ключ к двойной природе — `if instance is None` в `__get__`: `User.name` возвращает само поле (для DDL, миграций, построения `WHERE`), `u.name` — значение конкретного экземпляра. Отсюда один шаг до генерации схемы:

```python
def create_table(model):
    cols = []
    for name, col in vars(model).items():
        if isinstance(col, Column):
            parts = [name, col.sql_type]
            if col.primary_key: parts.append("PRIMARY KEY")
            if not col.nullable: parts.append("NOT NULL")
            cols.append(" ".join(parts))
    return f"CREATE TABLE {model.__name__.lower()} ({', '.join(cols)})"

print(create_table(User))
# CREATE TABLE user (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT)
```

**⚠️ Name mangling.** Поле, привязанное к «приватному» атрибуту, приходит в `__set_name__` уже с искажённым именем — компилятор выполняет mangling **до** создания класса:

```python
class Secret:
    __code = TextColumn()          # атрибут __code

    def show(self):
        return self._Secret__code  # обращение — только через mangled имя

print(Secret.__dict__["_Secret__code"].name)   # _Secret__code, не "__code"
```

Дескриптор хранит имя как есть; если коду важно «настоящее» имя приватного поля — это отдельная причина не использовать ведущее двойное подчёркивание для колонок.

**⚠️ Наследование — общее состояние полей.** Поле, определённое в базовом классе, — **один объект** для всей иерархии:

```python
class Base:
    tags = TextColumn(default="")

class Child(Base):
    pass

print(Base.tags is Child.tags)    # True — не два поля, а одно
Base.tags.default = "injected"
print(Child().tags)               # injected — подкласс унаследовал изменённое поле
```

Имя при этом не перезаписывается (`name = "tags"` в обоих классах), но изменяемое состояние (`default`, кэши внутри поля) становится общим. Отсюда и защита от повторной привязки в начале примера: привязать то же поле ко **второму** классу нельзя — Django на этом месте поднимает check-ошибку `fields.E006` (wrapped в `SystemCheckError` при migrate). Честное решение — клонировать поля в подклассах через `__init_subclass__` (см. 6.8) или не хранить изменяемое состояние в дескрипторе вовсе.

**Бонус: поле как кусок SQL.** Раз доступ через класс возвращает объект поля, магические методы поля превращаются в построитель запросов:

```python
class Filter:
    def __init__(self, col, op, value):
        self.col, self.op, self.value = col, op, value
    def __str__(self):
        return f"{self.col.name} {self.op} {self.value!r}"

class ExprColumn(IntColumn):
    def __eq__(self, other): return Filter(self, "=", other)
    def __gt__(self, other): return Filter(self, ">", other)

class Item:
    qty = ExprColumn()          # поля-выражения вместо обычных Column

print(Item.qty == 5)         # qty = 5 — это не сравнение, а кусок WHERE
```

Именно поэтому в Django `User.objects.filter(name="ann")`, а не `filter(User.name == "ann")` — но с дескрипторами возможен и второй вариант (в духе peewee/SQLAlchemy-выражений).

→ **см. также:** 6.3 — базовый `__set_name__`; 6.8 — клонирование полей и реестры через `__init_subclass__`; Часть V (5.6).

## 6.8. `__init_subclass__` + дескрипторы: декларативная регистрация { #6.8 }

`__set_name__` сообщает дескриптору, **кем** он назван; `__init_subclass__` (5.6) сообщает базовому классу, **что** в подклассе объявлено. В паре они закрывают задачу, для которой раньше писали метаклассы: автоматический сбор полей, реестры плагинов, клонирование наследованных дескрипторов.

Порядок событий (PEP 487) гарантирует, что связка работает: сначала для всех дескрипторов тела класса вызывается `__set_name__`, и только затем — `__init_subclass__` родителя. К моменту `__init_subclass__` каждое поле уже знает своё имя.

**Реестр полей модели.** Продолжение примера 6.7 — базовый класс собирает `Column`-дескрипторы подкласса в словарь:

```python
class Model:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # vars(cls) — только собственные атрибуты, без наследованных
        cls._fields = {
            name: obj
            for name, obj in vars(cls).items()
            if isinstance(obj, Column)
        }

class User(Model):
    id = IntColumn(primary_key=True)
    name = TextColumn(nullable=False)
    email = TextColumn()

print(sorted(User._fields))                          # ['email', 'id', 'name']
print(", ".join(f"{n} {c.sql_type}" for n, c in User._fields.items()))
# id INTEGER, name TEXT, email TEXT
```

Важно использовать `vars(cls)`, а не walk по MRO: наследованные поля и так доступны через атрибуты, а реестр обычно нужен именно про «что объявлено здесь». Если нужен полный набор — добавить обход `cls.__mro__`.

**Клонирование наследованных полей.** Из 6.7: поле из базового класса — один общий объект для всех наследников. Клонирование в `__init_subclass__` даёт каждому классу собственные копии:

```python
import copy

class Model:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # поля родительских классов, не переопределённые в теле подкласса
        for parent in cls.__mro__[1:]:
            for name, obj in vars(parent).items():
                if isinstance(obj, Column) and name not in vars(cls):
                    clone = copy.copy(obj)
                    clone.name = None           # сброс перед повторной привязкой
                    setattr(cls, name, clone)   # вызовет __set_name__ у клона

class Base(Model):
    tags = TextColumn(default="")

class Child(Base):
    pass

print(Base.tags is Child.tags)    # False — теперь у каждого свои
```

`setattr(cls, name, clone)` внутри `__init_subclass__` снова вызывает `__set_name__` у клона — перед этим нужно сбросить `name`, иначе защита от повторной привязки из 6.7 честно сработает на уже привязанном клоне. Именно на этом месте Django поднимает `FieldError`, если поле привязывают ко второму классу без клонирования: `contribute_to_class` у него делает ту же работу, что наш `__init_subclass__`.

**Реестр плагинов.** Второй стандартный сценарий — само-регистрация подклассов:

```python
PLUGINS = {}

class Plugin:
    def __init_subclass__(cls, *, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        PLUGINS[key or cls.__name__.lower()] = cls

class ZipExport(Plugin):
    pass

class PdfExport(Plugin, key="pdf"):
    pass

print(PLUGINS)    # {'zipexport': <class ZipExport>, 'pdf': <class PdfExport>}
```

**Почему не метакласс.** Оба сценария исторически делали через `Meta.__new__`, но `__init_subclass__` — обычный метод обычного класса:

- **композируется**: базовый класс с `__init_subclass__` спокойно входит в множественное наследование; два метакласса в одной иерархии — `TypeError: metaclass conflict`;
- **не требует `metaclass=`** у каждого автора модели — достаточно унаследоваться от `Model`;
- **проще отлаживать**: это нормальный метод с нормальным стеком, а не неявный слой `type.__new__`.

Метаклассы остаются нужны для перехвата **самого создания** класса (подмена `__slots__`, контроль за `class`-statement'ом) — см. Часть VII. Для «собрать поля и зарегистрировать» их избыточно.

→ **см. также:** 5.6 — сам `__init_subclass__`; 6.7 — поля ORM; Часть VII (7.5) — метаклассы как тяжёлая артиллерия.

## 6.9. Функции — тоже дескрипторы { #6.9 }

Bound methods существуют не «сами по себе»: обычная функция — это **non-data-дескриптор** с методом `__get__`, который и приклеивает `self`. Протокол из 6.1 объясняет половину семантики классов одним предложением: `obj.method` — это `type(obj).__dict__['method'].__get__(obj, type(obj))`.

```python
class C:
    def method(self, x):
        return f"{self} ← {x}"

f = C.__dict__["method"]      # из класса: голая функция
print(f)                      # <function C.method ...> — обычный function object

print(C.method)               # <function C.method ...> — доступ через класс: без привязки

obj = C()
bound = f.__get__(obj, C)     # вот здесь происходит «магия»
print(bound)                  # <bound method C.method of <C object ...>>

print(obj.method)             # то же самое — атрибутный доступ разворачивается в f.__get__
print(obj.method.__self__ is obj)   # True — привязанный self живёт здесь
print(obj.method.__func__ is f)     # True — а это исходная функция
```

Интерпретатор делает `types.MethodType(f, obj)` — оборачивает функцию и экземпляр. Можно и руками:

```python
import types

def shout(self):
    return f"{self}!!"

C.say = shout                        # положили функцию в класс — она стала дескриптором
obj.say()                            # <C object>!! — привязалась автоматически

weird = types.MethodType(shout, "строка-вместо-self")
print(weird())                       # строка-вместо-self!! — привязка это просто (func, obj)
```

Отсюда же выводятся `staticmethod` и `classmethod` (5.9) — это дескрипторы-обёртки, меняющие поведение `__get__`:

```python
class MyStaticMethod:
    def __init__(self, func):
        self.func = func
    def __get__(self, instance, owner):
        return self.func             # вся работа: НЕ привязывать self

class MyClassMethod:
    def __init__(self, func):
        self.func = func
    def __get__(self, instance, owner):
        owner = owner or type(instance)
        return types.MethodType(self.func, owner)   # привязываем КЛАСС вместо экземпляра
```

Три следствия, которые объясняют «странности» на собеседованиях:

- **Привязка происходит при доступе через атрибут**, а не при определении. Функция, положенная в словарь/список, не биндится:

```python
dispatch = {"a": C.method}     # доступ по ключу — не атрибутный
# dispatch["a"](obj, 42)       # self приходится передавать руками
# obj.method(42)               # а тут self подставился сам
```

- **Функция, присвоенная в `__init__` как атрибут экземпляра, не привязывается** — она лежит в `instance.__dict__` и затеняет бы дескриптор (non-data!), да и дескриптором на классе не является:

```python
class D:
    def __init__(self):
        self.f = lambda: "no self"    # self не прилетит — это не метод

D().f()        # no self — лямбда вызвана без аргументов
```

- **`__slots__` не мешает методам** — методы живут в `__dict__` класса, а не экземпляра (5.8). Экономия памяти слотами на методы не влияет.

→ **см. также:** 6.1 — протокол; 6.2 — почему функция non-data и не может быть затенена из класса; 5.9 — `@classmethod`/`@staticmethod` снаружи.

## 6.10. Дескрипторы и `__slots__` { #6.10 }

В 5.8 зафиксировано: `functools.cached_property` на slots-классе падает — ему нужен `instance.__dict__`, а его нет. Разберём, **что именно** ломается и как делать ленивые кэши слотами.

Что работает на `__slots__`-классе без оговорок:

- **`@property`** — data-дескриптор с собственным кодом `__get__`/`__set__`, никакого `__dict__` не требует;
- **обычные дескрипторы** (валидация из 6.7 при адаптации) — если пишут не в `__dict__`, а в слот;
- **методы** — живут на классе (6.9).

Что ломается: всё, что кэширует через `instance.__dict__` — `cached_property` и самодельные non-data-кэши из 6.6. Исключение `AttributeError` при первой записи — это `__dict__`-затенение, упёршееся в отсутствие словаря.

**Паттерн 1: выделенный слот под кэш.** Простой и чаще всего правильный:

```python
class Point:
    __slots__ = ("x", "y", "_r")           # слот под кэш объявляем честно

    def __init__(self, x, y):
        self.x, self.y = x, y
        self._r = None

    @property
    def r(self):
        if self._r is None:
            self._r = (self.x ** 2 + self.y ** 2) ** 0.5
        return self._r
```

**Паттерн 2: универсальный дескриптор со слотом-кэшем.** Тот же non-data-дескриптор из 6.6, но кэш — в слоте с производным именем (который обязан быть в `__slots__`):

```python
class SlotCached:
    """cached_property для __slots__-классов: кэш в слоте '_' + имя."""
    def __init__(self, func):
        self.func = func

    def __set_name__(self, owner, name):
        self.slot = "_" + name            # класс обязан объявить этот слот!

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return getattr(instance, self.slot)
        except AttributeError:            # слот ещё не заполнен
            value = self.func(instance)
            setattr(instance, self.slot, value)   # запись в слот, не в __dict__
            return value

class Vector:
    __slots__ = ("x", "y", "_norm")

    def __init__(self, x, y):
        self.x, self.y = x, y

    @SlotCached
    def norm(self):
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

Несоответствие между `self.slot` и списком `__slots__` обнаружится не сразу, а при первом обращении (`AttributeError: 'Vector' object has no attribute '_norm'`) — проверяйте тестом.

**Паттерн 3: `functools.lru_cache` на методе.** Работает на slots-классах, потому что кэш живёт на обёртке функции, а не на экземпляре. Но у него два подводных камня:

```python
from functools import lru_cache

class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x, self.y = x, y

    @lru_cache(maxsize=1024)
    def dist_to(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
```

- **self участвует в ключе кэша** → каждый экземпляр удерживается кэшем сильной ссылкой: `Point` нельзя собрать, пока он в кэше (дело не в `__weakref__` — кэш хранит объект напрямую). При ограниченном `maxsize` это управляемо; на большом потоке экземпляров — утечка по памяти.
- **`self` обязан быть hashable** — обычный класс (в том числе slots-класс) хешируем по умолчанию по `id()`; `TypeError` будет только если в классе определён `__eq__` без `__hash__` — тогда Python сам выставит `__hash__ = None`.

Итоговая таблица по слотам:

| Механизм | На `__slots__` | Комментарий |
|---|---|---|
| `@property` | работает | кэш руками через слот |
| `cached_property` | падает | нужен `instance.__dict__` |
| `SlotCached` (выше) | работает | слот обязан быть объявлен |
| `lru_cache` на методе | работает | кэш держит экземпляры, `self` должен быть hashable |
| `'__dict__'` в `__slots__` | работает | но съедает всю экономию — тогда зачем слоты |

Правило выбора: один-два дорогих значения — выделенный слот + `@property`; много ленивых полей или класс генерируется динамически — `SlotCached`; кэш по аргументам (не только по self) — `lru_cache` с осознанием удержания объектов.

→ **см. также:** 6.6 — механика cached_property; 5.8 — `__slots__` целиком; 6.9 — почему методы слотам не мешают.

---

### Бенчмарки к Части VI { #6.5-benchmarki }

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
print(timeit.timeit("wc.heavy", globals={"wc": wc}, number=1_000_000))   # ≈ 0.04 с (зависит от CPU)
print(timeit.timeit("m.heavy",  globals={"m": m},   number=1_000_000))   # ≈ 0.07 с
```
`cached_property` **в ~1.8× быстрее** ручной memoization через `@property` +
`hasattr` (замер на 3.12, зависит от CPU) — после первого вычисления он сохраняет значение прямо в `__dict__`
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
print(timeit.timeit("g1.a", globals={"g1": g1}, number=5_000_000))   # ≈ 0.16 с (зависит от CPU)
print(timeit.timeit("g2.a", globals={"g2": g2}, number=5_000_000))   # ≈ 0.64 с
```
`__getattribute__` **в ~4× медленнее** — он вызывается на **каждый** доступ
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

