# Часть II. Контекстные менеджеры

## 2.1. `with` — внутренности (`__enter__`/`__exit__`) { #2.1 }

Контекстный менеджер — это объект, реализующий протокол из двух методов:

1. **`__enter__()`** — вызывается перед началом блока `with`. Возвращаемое значение попадает в переменную после `as`.
2. **`__exit__(exc_type, exc_val, exc_tb)`** — гарантированно вызывается в конце, **даже если внутри блока было исключение**.

```python
with X as y:
    # 1. Вызывается X.__enter__() — результат в y
    # 2. Выполняется тело
    pass
    # 3. Вызывается X.__exit__(None, None, None)
    # (или с параметрами исключения, если оно было)
```

`__exit__` принимает три аргумента описывающих исключение:

- `exc_type` — класс исключения (`ValueError`, `KeyError`, ...).
- `exc_val` — сам объект исключения.
- `exc_tb` — traceback (объект `types.TracebackType`).

Если исключения не было — все три `None`.

## 2.2. Свой менеджер через класс { #2.2 }

```python
class ManagedResource:
    def __enter__(self):
        print("Ресурс открыт")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Ресурс закрыт")
        # Вернуть True → подавить исключение, программа продолжит работу
        # Вернуть False/None → исключение пробрасывается дальше
        return False

with ManagedResource():
    print("Внутри блока")
# Печатает:
# Ресурс открыт
# Внутри блока
# Ресурс закрыт
```

## 2.3. `@contextmanager` — без класса { #2.3 }

Писать целый класс ради простого менеджера — лень. `contextlib.contextmanager` превращает обычную функцию с одним `yield` в контекстный менеджер:

```python
from contextlib import contextmanager
import time

@contextmanager
def timer():
    start = time.time()
    try:
        yield  # управление передаётся внутрь блока with
    finally:
        end = time.time()
        print(f"Время: {end - start:.4f} сек.")

with timer():
    sum(i**2 for i in range(1_000_000))
```

`yield` делит функцию: **всё до него** — это `__enter__`, **всё после** (обычно в `try...finally`) — это `__exit__`. Если нужно передать значение в `as`, его надо `yield`-нуть:

```python
@contextmanager
def open_db(name):
    conn = connect(name)
    try:
        yield conn   # это попадёт в `as conn:`
    finally:
        conn.close()
```

## 2.4. `contextlib.suppress` и `contextlib.ExitStack` { #2.4 }

**`contextlib.suppress(*exceptions)`** — контекстный менеджер, подавляющий указанные исключения:

```python
from contextlib import suppress
import os

# Было:
try:
    os.remove("temp_file.txt")
except FileNotFoundError:
    pass

# Стало:
with suppress(FileNotFoundError):
    os.remove("temp_file.txt")
```

Под капотом — менеджер с `__exit__`, возвращающим `True`, если тип исключения совпадает.

**`contextlib.ExitStack`** — для динамического набора менеджеров, когда их число неизвестно заранее:

```python
from contextlib import ExitStack

files = ['a.txt', 'b.txt', 'c.txt']
with ExitStack() as stack:
    handles = [stack.enter_context(open(f)) for f in files]
    # Все три файла откроются, и все закроются гарантированно
    for h in handles:
        print(h.read())
```

Также через `stack.callback(fn)` можно зарегистрировать произвольную функцию очистки:

```python
with ExitStack() as stack:
    stack.callback(lambda: print("cleanup 1"))
    stack.callback(lambda: print("cleanup 2"))
    # При выходе вызовутся в обратном порядке: cleanup 2, cleanup 1
```

## 2.5. Несколько менеджеров в одном `with` { #2.5 }

```python
# Перечисление через запятую
with open('input.txt', 'r', encoding='utf-8') as f_in, \
     open('output.txt', 'w', encoding='utf-8') as f_out:
    content = f_in.read()
    f_out.write(content.upper())

# Скобки (современный синтаксис, Python 3.10+)
with (
    open('input.txt', 'r', encoding='utf-8') as f_in,
    open('output.txt', 'w', encoding='utf-8') as f_out,
):
    ...
```

Если открытие второго файла упадёт — первый корректно закроется. Все `__exit__` вызываются в обратном порядке.

⚠️ **Второй менеджер может использовать результат первого** — поскольку `as` связывается сразу после `__enter__`:
```python
import tempfile, os
with (
    tempfile.TemporaryDirectory() as tmpdir,
    open(os.path.join(tmpdir, "test.txt"), "w") as f,
):
    f.write("Данные во временном файле")
```

⚠️ **Статический `with A, B` vs динамический `ExitStack`**: `with (*managers):` — `SyntaxError`. Для переменного числа ресурсов — `contextlib.ExitStack` (см. 2.4).

## 2.6. Подавление ошибок через `__exit__` { #2.6 }

Если ваш контекстный менеджер вернёт `True` из `__exit__` — **ошибка полностью поглощается**, и программа не падает:

```python
class SwallowAll:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Поглощено: {exc_type.__name__ if exc_type else 'нет ошибки'}")
        return True   # подавляет любое исключение

with SwallowAll():
    raise ValueError("Эту ошибку никто не увидит")
print("Программа продолжает работу")
```

⚠️ **Это опасный паттерн** — можно случайно проглотить критическую ошибку. Так работает `contextlib.suppress`, но для общего случая лучше перехватывать конкретные исключения.

⚠️ **Безусловный `return True` блокирует `KeyboardInterrupt` и `SystemExit`** — пользователь не сможет остановить процесс Ctrl+C, а `sys.exit()` будет молча проигнорирован. Подавлять можно **только ожидаемые бизнес-исключения**, проверяя `issubclass(exc_type, ExpectedException)`.

⚠️ **Truthy/Falsy контракт `__exit__`**: интерпретатор проверяет результат в булевом контексте. Любое truthy (`True`, `1`, `"str"`) — подавляет. Любое falsy (`None`, `False`, `0`, `""`) — пробрасывает дальше. Поскольку функция без `return` возвращает `None`, стандартный `def __exit__(self, *args): pass` **гарантирует проброс всех ошибок**.

## 2.7. `contextlib.redirect_stdout`/`redirect_stderr` { #2.7 }

Перенаправление `sys.stdout`/`sys.stderr` в другой поток, файл или объект:

```python
import io
from contextlib import redirect_stdout

# Поймать вывод функции в строку
buffer = io.StringIO()
with redirect_stdout(buffer):
    print("Это не попадёт в консоль")
    print("А это тоже")
captured = buffer.getvalue()
print(f"Поймано: {captured!r}")
# Поймано: 'Это не попадёт в консоль\nА это тоже\n'
```

```python
# Редирект в файл
with open('output.log', 'w') as f:
    with redirect_stdout(f):
        print("Это идёт в файл, не в консоль")
        some_noisy_function()   # чьи print-ы тоже пойдут в файл

# Редирект stderr (например, для тестирования warnings)
import sys
from contextlib import redirect_stderr
err_buf = io.StringIO()
with redirect_stderr(err_buf):
    import warnings
    warnings.warn("Привет!")
print(f"В stderr было: {err_buf.getvalue()!r}")
```

⚠️ Редирект глобально меняет `sys.stdout` на время `with` — все `print` (даже из других модулей) попадут в ваш буфер.

Под капотом `redirect_stdout` — простой менеджер, сохраняющий и восстанавливающий `sys.stdout`. Аналогично можно написать свой для `stdin`:

```python
@contextmanager
def redirect_stdin(new):
    import sys
    old = sys.stdin
    sys.stdin = new
    try:
        yield
    finally:
        sys.stdin = old
```

**Классический кейс** — тестирование кода, который печатает через `print`:

```python
def test_greeting():
    buf = io.StringIO()
    with redirect_stdout(buf):
        greet_user("Alice")
    assert "Hello, Alice" in buf.getvalue()
```

## 2.8. `contextlib.closing` и `aclosing` { #2.8 }

`closing` — для объектов, у которых есть метод `close()`, но нет `__enter__`/`__exit__`. Оборачивает их в контекстный менеджер, который вызывает `close()` при выходе.

```python
from contextlib import closing

class Connection:
    def __init__(self, host):
        self.host = host
    def close(self):
        print(f"closing {self.host}")
    def query(self, sql):
        return ["row1", "row2"]

# Без closing — если бы была ошибка, close бы не вызвался:
conn = Connection("example.com")
try:
    results = conn.query("SELECT *")
finally:
    conn.close()

# С closing — короче:
with closing(Connection("example.com")) as conn:
    results = conn.query("SELECT *")
# При выходе из with автоматически вызывается conn.close()
```

⚠️ В отличие от обычного `with`, `closing` **не** реализует протокол менеджера на самом объекте — это обёртка, которая зовёт `close` через `__exit__`. Если у объекта есть `__enter__/__exit__` — они не вызываются, только `close`.

**Применение**: оборачивать сторонние классы, которые нельзя изменить (например, из C-расширений), но у которых есть `close()`.

### `aclosing` (Python 3.10+) — для async-генераторов { #2.8-aclosing }

```python
from contextlib import aclosing

async def stream():
    try:
        yield 1
        yield 2
        yield 3
    finally:
        print("cleanup")

async def main():
    async with aclosing(stream()) as gen:
        async for x in gen:
            print(x)
            if x == 2:
                break   # выходим из with — gen.aclose() вызовется
# Выведет: 1, 2, cleanup
```

`aclosing` вызывает `agen.aclose()` при выходе — корректно закрывает async-генератор, что гарантирует выполнение `finally` блока. Без него генератор может «зависнуть» неочищенным — GC работает синхронно и **не может выполнить `await`** для кода внутри `finally` асинхронного генератора, что приводит к `ResourceWarning: unclosed asynchronous generator`.

### `nullcontext` (Python 3.7+) — менеджер-заглушка { #2.8-nullcontext }

Незаменим для **опциональных** контекстных менеджеров — «ничего не делать», если ресурс не нужен:

```python
from contextlib import nullcontext

# Если lock передан — захватываем, если None — nullcontext (no-op):
cm = lock if lock is not None else nullcontext()
with cm:
    process_data()   # потокобезопасно, если lock есть; без накладных расходов, если нет

# Также для функций, принимающих путь ИЛИ файловый объект:
def read_data(file_or_path):
    cm = open(file_or_path) if isinstance(file_or_path, str) else nullcontext(file_or_path)
    with cm as f:
        return f.read()
```

### `chdir` (Python 3.11+) — временная смена рабочей директории { #2.8-chdir }

```python
from contextlib import chdir
import os

with chdir("/tmp/build"):
    # Внутри блока os.getcwd() == "/tmp/build"
    run_build_script()
# При выходе директория гарантированно возвращается в исходную
```

Заменяет бойлерплейт `old = os.getcwd(); try: os.chdir(new); ... finally: os.chdir(old)`.

> **→ см. также:** Часть IV (4.8) — async generators и `aclose()` как часть протокола; Часть III (3.4) — `close()` для синхронных генераторов.

---

### Бенчмарки к Части II { #2.8-benchmarki }

**1. Класс-менеджер vs `@contextmanager` vs `contextlib.suppress`.**
```python
import timeit
from contextlib import contextmanager, suppress

class CtxClass:
    __enter__ = lambda self: self
    __exit__  = lambda self, *exc: False

@contextmanager
def ctx_dec():
    yield

def use_class(): 
    with CtxClass(): pass
def use_dec():
    with ctx_dec(): pass
def use_suppress():
    with suppress(): pass

for f in (use_class, use_dec, use_suppress):
    print(f.__name__, timeit.timeit(f, number=2_000_000))
# use_class   ≈ 0.55 с  ← быстрее всего: прямые вызовы методов
# use_dec     ≈ 1.10 с  ← накладные расходы на генератор
# use_suppress≈ 0.95 с
```
Класс-менеджер **в ~2 раза быстрее** `@contextmanager`, потому что декоратор
строит генератор + прокси-обёртку `_GeneratorContextManager` на каждый вызов.
На горячих путях (открытие файлов в цикле) — заметно.

**2. Несколько менеджеров в одном `with` vs вложенные.**
```python
# Вложенно
with open(a) as fa:
    with open(b) as fb:
        with open(c) as fc:
            pass
# В одну строку
with open(a) as fa, open(b) as fb, open(c) as fc:
    pass
```
Байт-код **идентичен** — `SETUP_WITH` + `WITH_CLEANUP` повторяются трижды.
Разница только в читаемости: одна строка короче, но при длинных именах
вложенность лучше переносится в IDE.

**3. `ExitStack` для динамического числа ресурсов.**
```python
from contextlib import ExitStack
# 100 файлов через ExitStack
with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
```
Накладные расходы на каждый `enter_context` — ~1.2 мкс. Для 1000 файлов это
~1.2 мс — пренебрежимо мало по сравнению с реальным I/O.

**4. `redirect_stdout` — стоимость перехвата.**
```python
import timeit, io, sys
from contextlib import redirect_stdout
def plain():   print("x", end="")
def captured():
    with redirect_stdout(io.StringIO()):
        print("x", end="")
print(timeit.timeit(plain,    number=100_000))   # ≈ 0.13 с
print(timeit.timeit(captured, number=100_000))   # ≈ 0.30 с
```
Перехват удваивает стоимость `print`. На горячих путях логирования
лучше использовать `logging` с фильтром, чем `redirect_stdout`.

**5. Подавление исключений: `suppress` vs `try/except: pass`.**
```python
def try_except():
    try: 1 / 0
    except ZeroDivisionError: pass
def use_suppress():
    with suppress(ZeroDivisionError): 1 / 0
# try_except  ≈ 0.18 с / 1M вызовов
# use_suppress≈ 0.32 с / 1M вызовов
```
`suppress` почти вдвое медленнее из-за накладных расходов на контекстный менеджер.
Берите его для **читаемости**, а не для скорости.

