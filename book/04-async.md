# Часть IV. Асинхронность

`async def` выглядит как обычная функция с лишним ключевым словом, но под капотом это генератор (Часть III) плюс цикл событий — один поток, который гоняет тысячи задач по очереди, пока те ждут I/O. Часть разбирает event loop руками (4.1), потом API asyncio — от `run` и `gather` до `TaskGroup`, отмен и таймаутов — и заканчивает выбором между threads, asyncio и multiprocessing (4.11), включая debug-режим asyncio (4.3).

## 4.1. Что такое event loop { #4.1 }

**Event loop (цикл событий)** — это единый поток, который:

1. Хранит очередь задач (корутин).
2. Запускает первую задачу, пока она не «приостановится» на `await`.
3. Переключается на следующую готовую задачу.
4. Когда приостановленная задача «просыпается» (пришёл ответ от I/O), возвращается к ней.

```python
# Синхронно: одна задача блокирует всё, пока ждёт ответа сервера
def sync_fetch_all():
    r1 = requests.get(url1)   # ждём 0.5 сек
    r2 = requests.get(url2)   # ждём 0.5 сек
    r3 = requests.get(url3)   # ждём 0.5 сек
    # Итого: 1.5 сек

# Асинхронно: ждём все три «одновременно»
async def async_fetch_all():
    r1, r2, r3 = await asyncio.gather(
        fetch(url1),          # ждём 0.5 сек
        fetch(url2),          # ждём 0.5 сек
        fetch(url3),          # ждём 0.5 сек
    )
    # Итого: 0.5 сек
```

Асинхронность = **конкурентность в одном потоке**. Не параллелизм (CPU не используется одновременно), а конкурентность по I/O (пока одна задача ждёт ответа — другая работает).

⚠️ **Кооперативная многозадачность**: в `asyncio` задача выполняется до тех пор, пока сама добровольно не отдаст управление через `await`. Если внутри корутины вызвать синхронную операцию (`time.sleep(5)`, `requests.get()`, долгий CPU-расчёт), она **блокирует поток event loop**: ни одна другая готовая корутина не получит управления, пока синхронный вызов не завершится, — для остальных задач цикл «замер», хотя формально ничего не сломалось.

⚠️ **Физика event loop**: цикл не опрашивает сокеты непрерывно. Через модуль `selectors` он делегирует наблюдение системным мультиплексорам I/O — `epoll` (Linux), `kqueue` (macOS/BSD), `IOCP` (Windows). Когда все корутины ждут I/O, поток засыпает в мультиплексоре I/O (`epoll_wait` на Linux и его аналогах на других платформах) с **0% CPU**.

## 4.2. `async def`, `await` — синтаксис и семантика { #4.2 }

```python
async def fetch(url):
    # корутина — функция с async def
    response = await make_request(url)   # приостанавливает fetch до готовности make_request
    return response.json()
```

- `async def` определяет **корутину**. Вызов `fetch(url)` не выполняет тело, а возвращает объект корутины.
- `await` можно ставить только **внутри `async def`**. Приостанавливает корутину, передаёт управление event loop'у. Когда `await`-able завершён — корутина возобновляется.
- `await`-able: корутины, `Task`, `Future`, объекты с `__await__`.

```python
async def main():
    coro = fetch(url)           # НЕ запускается — просто создаёт объект корутины
    result = await coro         # вот тут запускается и ждём

asyncio.run(main())             # точка входа — запускает event loop
```

⚠️ **Если корутина не была `await`-нута** — её тело никогда не выполнится, и Python выдаст `RuntimeWarning: coroutine '...' was never awaited`.

## 4.3. `asyncio.run` — точка входа { #4.3 }

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

asyncio.run(main())   # создаёт event loop, запускает main, закрывает loop
```

`asyncio.run` (Python 3.7+) — стандартный способ запустить asyncio-программу. Создаёт новый event loop, выполняет корутину, **принудительно отменяет** (`cancel()`) все оставшиеся фоновые задачи, закрывает async-генераторы и пул потоков, затем закрывает loop.

⚠️ **Нельзя вызывать `asyncio.run` внутри уже запущенного event loop** — будет `RuntimeError`. Если вы внутри Jupyter или уже в asyncio — используйте `await main()` напрямую.

Старый API (deprecated с 3.10, в будущем удалится; в 3.12 при отсутствии запущенного loop выдаёт `DeprecationWarning: There is no current event loop`):
```python
loop = asyncio.get_event_loop()       # ⚠️ deprecated
loop.run_until_complete(main())
loop.close()
```

**Debug-режим asyncio** — ловит блокирующий код и протечки:

```python
asyncio.run(main(), debug=True)   # loop_factory добавлен в 3.12; debug доступен с 3.7
```

```bash
$ python3 -X dev script.py                # Development Mode включает asyncio debug
$ PYTHONASYNCIODEBUG=1 python3 script.py  # то же самое прицельно
```

В debug-режиме asyncio логирует шаг цикла, дольше 100 мс (`loop.slow_callback_duration`) — и это главный индикатор заблокированного event loop:

```text
Executing <Task ... coro=<main() ...>> took 0.200 seconds
```

Так выглядит `time.sleep(0.2)` внутри корутины (блокирует весь loop) — замените на `await asyncio.sleep(0.2)`. Дополнительно debug-режим предупреждает о незакрытых транспортах/сессиях, ругается на коллбэки из чужого потока и запоминает место создания корутины для трейсбеков. Без смены запуска — `loop.set_debug(True)` на живом loop; порог «медленности» настраивается `loop.slow_callback_duration = 0.05`.

## 4.4. `asyncio.gather` — конкурентный запуск { #4.4 }

```python
async def fetch(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

async def main():
    urls = ['https://a.com', 'https://b.com', 'https://c.com']
    # Все три запроса стартуют одновременно
    results = await asyncio.gather(
        fetch(urls[0]),
        fetch(urls[1]),
        fetch(urls[2]),
    )
    # results — список в порядке аргументов (не в порядке завершения!)
    print(results)

asyncio.run(main())
```

`asyncio.gather(*coros)` запускает все корутины конкурентно, ждёт всех, возвращает список результатов в порядке аргументов.

**Исключения:**

- По умолчанию, если одна корутина падает — остальные продолжают работать, но `gather` поднимет исключение.
- `asyncio.gather(*coros, return_exceptions=True)` — исключения не пробрасываются, а возвращаются в списке как значения.

```python
results = await asyncio.gather(
    fetch('https://good.com'),
    fetch('https://bad.com'),
    return_exceptions=True,
)
# [html, ConnectionError(...)]
```

## 4.5. `asyncio.create_task` — фоновые задачи { #4.5 }

```python
async def main():
    task = asyncio.create_task(fetch('https://a.com'))   # запуск в фоне
    # ... делаем что-то, пока fetch выполняется ...
    result = await task   # ждём завершения, если ещё не завершилась
```

`create_task` (Python 3.7+) — планирует корутину как задачу в event loop. Возвращает `Task` объект. Можно `await`-ить позже, отменять (`task.cancel()`), проверять статус (`task.done()`).

```python
async def main():
    tasks = [asyncio.create_task(fetch(url)) for url in urls]
    # Все стартуют параллельно
    results = await asyncio.gather(*tasks)
```

⚠️ Если `task` не сохранить в переменную — garbage collector может её удалить, и задача не выполнится. Event loop хранит задачи через **слабые ссылки** (`weakref`). Всегда храните ссылку.

**Каноничный паттерн fire-and-forget** (официальная документация Python):

```python
background_tasks = set()

def run_background_task(coro):
    task = asyncio.create_task(coro)
    background_tasks.add(task)           # сильная ссылка
    task.add_done_callback(background_tasks.discard)  # авто-очистка
```

Если фоновая задача упадёт и никто не сделал `await task`, CPython в stderr напечатает: `Task exception was never retrieved`. Чтобы поймать — добавьте callback с `task.exception()`.

## 4.6. `asyncio.wait` — ожидание с таймаутом { #4.6 }

```python
async def main():
    tasks = [asyncio.create_task(fetch(url)) for url in urls]
    # Ждём, пока хотя бы одна завершится, но не больше 5 секунд
    done, pending = await asyncio.wait(
        tasks,
        timeout=5,
        return_when=asyncio.FIRST_COMPLETED,
    )
    # done — множество завершившихся задач
    # pending — ещё выполняющиеся
    
    for task in pending:
        task.cancel()   # отменим оставшиеся
```

`return_when` варианты:

- `ALL_COMPLETED` (по умолчанию) — ждать всех.
- `FIRST_COMPLETED` — ждать **первого** завершившегося (не "хотя бы N", для N>1 нужно писать свою логику или использовать `wait` в цикле).
- `FIRST_EXCEPTION` — ждать первого исключения (или всех, если исключений не было).

⚠️ В отличие от `gather`, `wait` **не возвращает результаты** — нужно доставать через `task.result()`:

```python
for task in done:
    print(task.result())
```

## 4.7. `asyncio.Queue`, `Lock`, `Semaphore` { #4.7 }

### `asyncio.Queue` — очередь для producer/consumer { #4.7-asyncioqueue }

```python
async def producer(queue):
    for i in range(10):
        await queue.put(i)
        await asyncio.sleep(0.1)
    await queue.put(None)   # сигнализируем конец

async def consumer(queue):
    while True:
        item = await queue.get()
        if item is None:
            break
        print(f"Got {item}")
        queue.task_done()

async def main():
    queue = asyncio.Queue(maxsize=5)
    await asyncio.gather(producer(queue), consumer(queue))

asyncio.run(main())
```

`asyncio.Queue` похож на `queue.Queue`, но `put`/`get` — корутины, приостанавливающие на заполненной/пустой очереди.

### `asyncio.Lock` — мьютекс { #4.7-asynciolock }

```python
lock = asyncio.Lock()

async def safe_update(shared_state):
    async with lock:   # эксклюзивный доступ
        shared_state['count'] += 1
```

### `asyncio.Semaphore` — ограничение конкурентности { #4.7-asynciosemaphore }

```python
sem = asyncio.Semaphore(10)   # не больше 10 одновременно

async def fetch_with_limit(url):
    async with sem:
        return await fetch(url)

# 100 URL, но не больше 10 параллельных запросов
await asyncio.gather(*[fetch_with_limit(url) for url in urls])
```

Полезно для ограничения нагрузки на API.

## 4.8. Async generators (`yield` в `async def`) { #4.8 }

Python 3.6+ поддерживает `yield` внутри `async def` — это **асинхронный генератор**:

```python
async def stream_lines(path):
    async with aiofiles.open(path) as f:
        async for line in f:
            yield line.strip()

async def main():
    async for line in stream_lines('huge.log'):
        if 'ERROR' in line:
            print(line)

asyncio.run(main())
```

`async for` — это `for`, который на каждой итерации `await`-ит `__anext__()` генератора. Полезно для стриминга — данные приходят порциями, можно начинать обрабатывать до того, как всё пришло.

⚠️ **Запреты в async-генераторах** (PEP 525):

- **`yield from` запрещён** внутри `async def` — `SyntaxError: 'yield from' inside async function`. Делегирование — через `async for` + `yield`.
- **`return value` запрещён** в async-генераторе — `SyntaxError: 'return' with value in async generator`. Только «голый» `return` (без аргумента). `StopAsyncIteration` не передаёт значение, в отличие от синхронного `StopIteration.value`.

**Асинхронные comprehensions** (PEP 530, Python 3.6+):

```python
results = [x * 2 async for x in ticker() if x % 2 == 0]   # async listcomp
mapping = {x: str(x) async for x in ticker()}               # async dictcomp
lazy = (x**2 async for x in ticker())                        # async genexp — O(1) память
```

## 4.9. Async context managers (`__aenter__`/`__aexit__`) { #4.9 }

Асинхронный контекстный менеджер реализует `__aenter__` и `__aexit__` как корутины:

```python
class AsyncDB:
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False
    
    async def connect(self): ...
    async def disconnect(self): ...
    async def query(self, sql): ...

async def main():
    async with AsyncDB() as db:
        result = await db.query("SELECT 1")
```

`async with` — это `with`, который `await`-ит `__aenter__` и `__aexit__`.

То же через `@asynccontextmanager`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_session():
    conn = await connect()
    try:
        yield conn
    finally:
        await conn.close()

async def main():
    async with db_session() as conn:
        ...
```

## 4.10. Конкурентность vs параллелизм { #4.10 }

**Параллелизм (parallelism)** — несколько задач **физически** выполняются одновременно (на разных ядрах CPU). В CPython даётся через `multiprocessing` (отдельные процессы — отдельные GIL'ы) или через C-расширения, которые отпускают GIL (`numpy`, `zlib`/`bz2`/`lzma`, некоторые операции `hashlib` через OpenSSL). `threading` **не** даёт параллелизма для pure-Python кода из-за GIL.

**Конкурентность (concurrency)** — несколько задач **логически** выполняются одновременно (одна может приостановиться, пойти другая). Event loop в одном потоке — это конкурентность без параллелизма. `threading` — тоже конкурентность (потоки чередуются через переключения ОС), но не параллелизм для Python-кода.

```python
# Параллелизм (CPU-bound, разные процессы):
from multiprocessing import Pool
with Pool(4) as p:
    results = p.map(heavy_computation, data)   # 4 процесса на 4 ядрах, у каждого свой GIL

# Конкурентность (I/O-bound, один поток):
async def main():
    await asyncio.gather(*[fetch(url) for url in urls])   # 1 поток, много I/O

# Конкурентность через threads (I/O-bound, но с переключением ОС):
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(10) as ex:
    results = list(ex.map(requests.get, urls))   # 10 потоков, но GIL не даёт параллельного Python
```

Правило простое:

- **CPU-bound** (тяжёлые расчёты) → multiprocessing (GIL мешает threads в CPython).
- **I/O-bound** (сеть, диск, БД) → asyncio (один поток, много ожиданий).

## 4.11. Threads vs asyncio vs multiprocessing — когда что { #4.11 }

| Подход | Когда использовать | Плюсы | Минусы |
|--------|-------------------|-------|--------|
| **`threading`** | I/O-bound, синхронный код (requests, blocking libraries) | Простой, можно использовать blocking libraries | GIL — только один Python-поток выполняется в любой момент |
| **`multiprocessing`** | CPU-bound (расчёты, ML) | Настоящий параллелизм, обходит GIL | Тяжёлый — fork/spawn процесса, IPC через pickle/Queue |
| **`asyncio`** | I/O-bound, много одновременных соединений | Лёгкий — тысячи корутин в одном потоке, минимальный overhead | Требует async-версий всех библиотек (aiohttp вместо requests) |
| **`concurrent.futures.ThreadPoolExecutor`** | I/O-bound, простая миграция синхронного кода | API как `map` — простой переход | Те же ограничения GIL |
| **`concurrent.futures.ProcessPoolExecutor`** | CPU-bound, простая миграция | API как `map` | Те же ограничения multiprocessing |

### ThreadPool — для блокирующего I/O { #4.11-threadpool }

```python
from concurrent.futures import ThreadPoolExecutor

def fetch(url):
    return requests.get(url).text   # blocking, но в разных потоках OK

with ThreadPoolExecutor(max_workers=10) as executor:
    results = list(executor.map(fetch, urls))
```

### ProcessPool — для CPU-bound { #4.11-processpool }

```python
from concurrent.futures import ProcessPoolExecutor

def heavy_compute(x):
    return sum(i**2 for i in range(x))   # CPU-bound

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(heavy_compute, [10**7] * 4))
```

### asyncio — для большого количества I/O { #4.11-asyncio }

```python
import asyncio, aiohttp

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[
            fetch(session, url) for url in urls
        ])

asyncio.run(main())
```

**Смешивать можно** — `asyncio.to_thread(sync_func, args)` запускает синхронную функцию в отдельном потоке, обернув в await-able:

```python
async def main():
    # blocking requests.get запускается в потоке, не блокируя event loop
    result = await asyncio.to_thread(requests.get, 'https://api.com')
```

### Decision-фреймворк: что выбрать { #4.11-decision-freymvork }

| Задача | Решение | Почему |
|---|---|---|
| HTTP-запросы к 100 URLам одновременно | `asyncio` + `httpx.AsyncClient` | тысячи корутин дешевле потоков, нет переключения контекста ядром |
| HTTP-запросы к 10 URLам, есть только `requests` | `ThreadPoolExecutor(max_workers=10)` | нет смысла переписывать на async ради 10 запросов |
| Умножение больших матриц, pure Python | `multiprocessing` (или `numpy` без Python) | GIL убивает параллелизм в потоках |
| Парсинг 1000 файлов с диска | `asyncio` (если OS поддерживает async I/O) или `ThreadPool` | I/O-bound, CPU простаивает |
| Вызов долгой C-функции (напр. `numpy.linalg.svd` на большом массиве) | `multiprocessing` **или** `threading` | C-расширения отпускают GIL, потоки работают |
| CPU-bound + I/O-bound смешанный | `multiprocessing` для CPU + `asyncio` для I/O | каждый работает в своей зоне |
| Legacy sync-код, который нужно ускорить | `ThreadPoolExecutor` для I/O, `ProcessPool` для CPU | минимальные изменения в коде |
| WebSocket-сервер на 10000 подключений | `asyncio` (websockets/aiohttp) | потоки не масштабируются до 10k (8 MB виртуального стека на поток × 10k = 80 GB **виртуального** адресного пространства + ~1–2 GB реальной RAM на kernel-структуры; asyncio уходит в десятки МБ) |
| Долгий background-task в sync-приложении | `threading.Thread(daemon=True)` | проще, чем поднимать event loop ради одной задачи |

**Эмпирические пороги** (на CPython 3.12):

- До **10 параллельных задач** I/O — разница между threads и asyncio незаметна, берите что проще.
- **10–1000** — asyncio начинает выигрывать (~10× меньше памяти).
- **1000+** — только asyncio, потоки упираются в лимиты OS (RLIMIT_NPROC / kernel.threads-max: от сотен в контейнерах до десятков тысяч на десктопе; на macOS — порядка тысяч).
- **CPU-bound** — threads **никогда** не дают ускорения в CPython (GIL), только multiprocessing или C-расширения.

## 4.12. `asyncio.as_completed` — по мере завершения { #4.12 }

В отличие от `gather` (который ждёт всех), `as_completed` даёт результаты **по мере готовности**:

```python
import asyncio
import time

async def fetch(url, delay):
    await asyncio.sleep(delay)
    return f"Done {url} after {delay}s"

async def main():
    tasks = [
        asyncio.create_task(fetch('fast', 0.5)),
        asyncio.create_task(fetch('medium', 1.0)),
        asyncio.create_task(fetch('slow', 1.5)),
    ]
    
    # Результаты в порядке завершения, не в порядке создания
    t0 = time.time()
    for coro in asyncio.as_completed(tasks):
        result = await coro
        print(f"{time.time() - t0:.2f}: {result}")   # время от старта задач

asyncio.run(main())
# 0.50: Done fast after 0.5s
# 1.00: Done medium after 1.0s
# 1.50: Done slow after 1.5s
```

Главный кейс — обработка результатов по готовности (например, рендеринг изображений, как только они загрузились).

⚠️ `as_completed` возвращает не задачи, а await-able корутины — `await` каждую по очереди.

## 4.13. `asyncio.TaskGroup` (Python 3.11+) — структурированная конкурентность { #4.13 }

> **→ см. также:** Часть V (5.16) — `ExceptionGroup` и `except*` для обработки ошибок из TaskGroup.

Современный способ запуска задач с автоматической отменой при ошибке:

```python
import asyncio

async def fetch(url):
    ...

async def main():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch('https://a.com'))
        t2 = tg.create_task(fetch('https://b.com'))
        t3 = tg.create_task(fetch('https://c.com'))
    # Выход из with = ожидание всех задач
    print(t1.result(), t2.result(), t3.result())

asyncio.run(main())
```

**Главное отличие от `gather`**:

- Если одна задача падает с исключением — `TaskGroup` **автоматически отменяет все остальные** (structured concurrency), а затем поднимает `ExceptionGroup` с собранными исключениями.
- `gather` **без** `return_exceptions=True` — поднимает первое исключение наверх, но **остальные задачи автоматически НЕ отменяются** — они продолжают работать в фоне, их результаты теряются. Их нужно отменять вручную через `try/finally` с `task.cancel()` для каждой. Это и есть главная причина, зачем в 3.11 ввели `TaskGroup`.
- `gather` **с** `return_exceptions=True` — исключения возвращаются как значения в списке результатов, задача считается «завершённой» (даже если упала), отмены остальных нет.

```python
# gather без return_exceptions — ручная отмена остальных:
async def main():
    tasks = [asyncio.create_task(fetch(u)) for u in urls]
    try:
        results = await asyncio.gather(*tasks)
    except Exception:
        # Если одна упала — отменяем остальные вручную, иначе они «висят» в фоне
        for t in tasks:
            if not t.done():
                t.cancel()
        raise
```

```python
async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fetch('https://good.com'))
            tg.create_task(fetch('https://broken.com'))   # упадёт
            tg.create_task(fetch('https://also-good.com'))
    except* ConnectionError as eg:
        # ExceptionGroup (Python 3.11+) — оборачивает все совпавшие по типу исключения.
        # Даже если упала одна задача — eg всё равно ExceptionGroup с одним элементом,
        # а не «голый» ConnectionError.
        print(f"Упало задач: {len(eg.exceptions)}")
        for exc in eg.exceptions:
            print(f"  - {exc!r}")
```

⚠️ `except*` — новый синтаксис Python 3.11 для обработки `ExceptionGroup`. Используйте `except*` (со звёздочкой), а не `except`.

### Откуда TaskGroup: nurseries, trio, anyio { #4.13-nurseries }

«Структурированная конкурентность» — не изобретение asyncio 3.11, а заимствование с точным адресом. Идея: **время жизни задач повторяет структуру кода** — задачи рождаются внутри блока, доживают до его конца и не утекают в фон. Концепцию сформулировал **Nathaniel Smith** в статье *«Notes on structured concurrency, or: go statement considered harmful»* (2018): `go`-стейтмент (и `create_task` до 3.11) — главная ошибка дизайна конкурентности, потому что задача уходит «в никуда» — без родителя, который дождался бы её ошибок.

Хронология идеи:

| Год | Что | Кто |
|---|---|---|
| 2015 | **curio** — первый фреймворк со строгими правилами отмены и «kernel»-подходом | Dave Beazley |
| 2017 | **trio** — nursery, «зонтик» отмены, `MultiError` (предок `ExceptionGroup`) | Nathaniel Smith |
| 2019+ | **anyio** — API структурированной конкурентности поверх asyncio **и** trio одним кодом | Alex Grönholm |
| 2022 | **asyncio.TaskGroup** (3.11) — прямой порт nursery в стандартную библиотеку; `ExceptionGroup`/`except*` (PEP 654, Python 3.11) — вдохновлены `MultiError` из trio, но реализованы на уровне языка | CPython |

Соответствие понятий один в один:

| Концепция | trio | asyncio 3.11+ |
|---|---|---|
| Блок, владеющий задачами | `async with trio.open_nursery() as nursery:` | `async with asyncio.TaskGroup() as tg:` |
| Рождение задачи | `nursery.start_soon(fn)` | `tg.create_task(fn)` |
| Ошибка одной → отмена всех | поведение nursery | поведение TaskGroup (см. выше) |
| Сбор исключений | `ExceptionGroup` (до trio 0.22 — `MultiError`) | `ExceptionGroup` + `except*` (5.16) |
| Запуск с подтверждением готовности | `nursery.start()` | в TaskGroup на 3.12 прямого аналога нет (`create_task` + `await` — не то же самое); в 3.13 добавлен `TaskGroup.start(coro)` |

**anyio** стоит упомянуть отдельно: до выхода 3.11 он был единственным способом писать структурированный код, работающий и на asyncio, и на trio. На anyio построены Starlette и FastAPI — их `anyio.create_task_group()` выглядит как TaskGroup, но живёт в обоих мирах. Если код должен портировать между рантаймами — писать на anyio с самого начала.

Что изменилось в мышлении с 3.11: раньше `create_task` — это «пускай крутится в фоне, соберём потом», и «потом» означало ручной `gather` с ручной отменой при ошибке (см. сравнение выше). Теперь вложенность задач в рантайме повторяет вложенность блоков кода — профилировщик, трейс и стек задач читаются как исходник. Одиночные `asyncio.create_task()` без владельца остаются легальным способом запустить фоновую работу (4.5) — но теперь это осознанное исключение, а не дефолт.

→ **см. также:** 5.16 — `ExceptionGroup` и `except*`; 4.15 — механика отмены, которую TaskGroup запускает автоматически; 4.5 — когда одиночный `create_task` уместен. Ссылки на curio/trio/anyio и статью-первоисточник — в Приложении D.

## 4.14. `asyncio.timeout` (Python 3.11+) и `asyncio.shield` { #4.14 }

### `asyncio.timeout` — современный способ задать таймаут { #4.14-asynciotimeout }

```python
import asyncio

async def slow_operation():
    await asyncio.sleep(10)
    return "done"

async def main():
    try:
        async with asyncio.timeout(1.0):
            result = await slow_operation()
            print(result)
    except TimeoutError:
        print("Не уложились в 1 секунду")

asyncio.run(main())
# "Не уложились в 1 секунду" через 1 сек
```

До Python 3.11 использовали `asyncio.wait_for`:

```python
try:
    result = await asyncio.wait_for(slow_operation(), timeout=1.0)
except asyncio.TimeoutError:   # в 3.11+ это просто TimeoutError
    print("timeout")
```

### `asyncio.shield` — защита от внешней отмены { #4.14-asyncioshield }

`shield(coro)` защищает внутреннюю корутину от **внешней** отмены: если отменят корутину, которая делает `await asyncio.shield(inner)`, внутренняя `inner` продолжит выполняться. Сам `shield` при этом поднимет `CancelledError` в вызывающем коде, но `inner` это не затронет.

**Когда реально нужен**:

- **Critical cleanup** — запись в БД, отправка финальной метрики, закрытие сетевого соединения. Если сервер отменяет запрос, вы всё равно хотите завершить транзакцию, а не оставить её в подвешенном состоянии.
- **Гарантия атомарности** — операция, которая должна либо завершиться, либо не начаться; отмена посередине оставит систему в неконсистентном состоянии.
- **Фоновые задачи, запущенные через `create_task` из обработчика** — если HTTP-запрос отменён, фоновая обработка должна продолжаться.

```python
async def critical_save():
    """Запись в БД, которую нельзя прерывать посередине."""
    await asyncio.sleep(2)
    # COMMIT транзакции

async def handler():
    task = asyncio.create_task(critical_save())
    # Без shield отмена handler каскадом дошла бы до critical_save
    # (отмена распространяется через ожидаемый future).
    # shield разрывает связь: CancelledError получает только handler,
    # task продолжает работать.
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        # handler отменили, но critical_save продолжает работать в фоне.
        # Если хотите дождаться — передайте task дальше или await task в finally.
        raise

async def main():
    h = asyncio.create_task(handler())
    await asyncio.sleep(0.5)
    h.cancel()   # отмена handler
    try:
        await h
    except asyncio.CancelledError:
        pass
    # critical_save всё ещё работает — дождёмся:
    await asyncio.sleep(2)
    print("critical_save завершился")
```

⚠️ **Что `shield` НЕ делает**:

- **Не защищает от прямой отмены самой `critical_save`**. Если вызвать `.cancel()` на task, в котором выполняется `critical_save` (а не на родителе), `CancelledError` поднимется внутри `critical_save`, и `shield` ничего с этим не сделает. `shield` защищает только от отмены, распространяющейся **через `await` родителя** — т.е. от cascade-отмены при падении/отмене выше по стеку.
- **Не делает корутину «бессмертной»** — она всё равно умирает при прямой отмене внутреннего task.
- **Сам `await asyncio.shield(coro)` отменяем** — если отменили родителя, `CancelledError` поднимется в нём, но `coro` продолжит работать в фоне. **Важный нюанс**: чтобы `coro` реально продолжила работу, кто-то должен держать ссылку на её task — иначе GC может собрать task вместе с корутиной, когда на них не останется сильных ссылок (пока у задачи есть запланированные колбэки, loop держит её). Поэтому в примере выше `task = asyncio.create_task(critical_save())` держит ссылку в `handler`, но если сам `handler` отменили и его фрейм умер — `task` тоже может быть собран. Чтобы гарантировать завершение — сохраняйте task в более долгоживущем контейнере (атрибут модуля, `asyncio.create_task` + явная ссылка в долгоживущем объекте).

В Python 3.11+ **`TaskGroup`** во многих случаях делает `shield` избыточным — структурированная конкурентность даёт более чистые гарантии. Но для **точечной** защиты одной операции `shield` всё ещё полезен.

## 4.15. `asyncio.CancelledError` — корректная отмена { #4.15 }

Когда задачу отменяют (`task.cancel()`), внутри неё поднимается `asyncio.CancelledError` (в Python 3.8+ это `BaseException`, не `Exception`):

```python
import asyncio

async def worker():
    try:
        await asyncio.sleep(60)
    except asyncio.CancelledError:
        print("Отменены, но cleanup успеем сделать")
        # Закрыть соединения, сохранить состояние...
        cleanup()
        raise   # ⚠️ ВАЖНО: re-raise, иначе задача считается «успешно завершённой», а не отменённой

async def main():
    task = asyncio.create_task(worker())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Задача корректно отменена")

asyncio.run(main())
# "Отменены, но cleanup успеем сделать"
# "Задача корректно отменена"
```

⚠️ **Про re-raise**: если поймать `CancelledError` и **не** re-raise — задача помечается как **успешно завершённая** (`done`, не `cancelled`). Это может быть желаемым поведением в редких случаях (cleanup + вернуть дефолт), но обычно re-raise нужен, чтобы upstream (TaskGroup, await-ящий корутину) знал, что задача была отменена. Внутри `TaskGroup` (Python 3.11+) глотать `CancelledError` без re-raise **особенно опасно** — TaskGroup может не понять, что задачу отменили, и вести себя неожиданно.

⚠️ **Главная ловушка**: в Python 3.8+ `CancelledError` — это `BaseException`, а не `Exception`. Поэтому `except Exception:` её **не поймает**. Это специально — чтобы случайно не проглотить отмену.

```python
async def worker():
    try:
        await asyncio.sleep(60)
    except Exception:   # ❌ НЕ поймает CancelledError
        cleanup()

async def worker_correct():
    try:
        await asyncio.sleep(60)
    except asyncio.CancelledError:
        cleanup()
        raise
    except Exception:
        # другие ошибки
        ...
```

**Отмена через `asyncio.timeout` и `TaskGroup`** — `timeout` отменяет текущую задачу (`CancelledError` поднимается в коде внутри блока и на выходе конвертируется в `TimeoutError`), `TaskGroup` отменяет дочерние задачи. Cleanup нужно держать в `finally` (не в `except CancelledError`, иначе при обычном исключении cleanup не выполнится):

```python
async def with_cleanup():
    conn = await connect()
    try:
        await do_work(conn)
    finally:
        await conn.close()   # гарантированно — при успехе, исключении И отмене
```

⚠️ **Не дублируйте cleanup в `except` и `finally`** — это приведёт к двойному выполнению:

```python
# ❌ Плохо — conn.close() вызовется дважды при CancelledError:
try:
    await do_work(conn)
except asyncio.CancelledError:
    await conn.close()   # 1-й раз
    raise
finally:
    await conn.close()   # 2-й раз — double-close, возможна ошибка

# ✅ Хорошо — только finally:
try:
    await do_work(conn)
finally:
    await conn.close()
```

**Coroutine-таймаут без отмены задачи целиком**:

```python
async def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with asyncio.timeout(5):
                return await fetch(url)
        except TimeoutError:
            print(f"Попытка {attempt+1} не удалась")
    raise RuntimeError("Все попытки провалены")
```

## 4.16. `asyncio.current_task`, `all_tasks`, `run_coroutine_threadsafe`, `to_thread`, `Runner`, `eager_task_factory` { #4.16 }

### `asyncio.current_task` — текущая задача { #4.16-asynciocurrenttask }

```python
import asyncio

async def worker():
    task = asyncio.current_task()
    print(f"My name: {task.get_name()}, coro: {task.get_coro()}")
    # My name: Task-1, coro: <coroutine object worker at 0x...>

asyncio.run(worker())
```

`get_name()`/`set_name()` (Python 3.8+) — для отладки, особенно в логах:

```python
async def worker():
    task = asyncio.current_task()
    task.set_name("db-worker")
    log.info(f"[{task.get_name()}] started")
```

### `asyncio.all_tasks` — все активные задачи в этом loop { #4.16-asyncioalltasks }

```python
import asyncio

async def slow(n):
    await asyncio.sleep(n)

async def main():
    t1 = asyncio.create_task(slow(1))
    t2 = asyncio.create_task(slow(2))
    t3 = asyncio.create_task(slow(3))
    
    # Все активные задачи (включая main)
    for task in asyncio.all_tasks():
        print(task.get_name(), task.get_coro())
    # Task-1 <coroutine object main at 0x...>   ← main тоже в списке
    # Task-2/3/4 <coroutine object slow at 0x...>
    # (порядок выдачи не гарантирован — all_tasks возвращает множество)
    
    await asyncio.gather(t1, t2, t3)

asyncio.run(main())
```

⚠️ Включает `main` (текущую). Чтобы получить только фоновые — отфильтровать `t is not asyncio.current_task()`.

### `asyncio.run_coroutine_threadsafe` — запустить корутину из другого потока { #4.16-asyncioruncoroutinethreadsafe }

Если у вас есть event loop в одном потоке, а из другого потока нужно поставить корутину в очередь:

```python
import asyncio, threading, time

async def slow_op():
    await asyncio.sleep(1)
    return "done"

# Главный поток держит event loop
async def main():
    # Пусть другой поток что-то сделает
    await asyncio.sleep(2)

loop = asyncio.new_event_loop()

def background_thread():
    time.sleep(0.5)
    # Из НЕ-async потока: запускаем корутину в loop
    future = asyncio.run_coroutine_threadsafe(slow_op(), loop)
    result = future.result(timeout=5)   # блокирует до готовности
    print(f"From thread: {result}")

threading.Thread(target=background_thread).start()
loop.run_until_complete(main())
loop.close()
```

`run_coroutine_threadsafe` ставит корутину в очередь loop'а, возвращает `concurrent.futures.Future`, по которому можно дождаться из любого потока. Используется, когда event loop крутится в одном потоке, а UI/сервер в другом.

### `asyncio.iscoroutine`, `iscoroutinefunction`, `isfuture` { #4.16-asyncioiscoroutine }

```python
import asyncio

async def coro():
    return 1

print(asyncio.iscoroutine(coro()))            # True — объект корутины
print(asyncio.iscoroutinefunction(coro))      # True — функция, возвращающая корутину
print(asyncio.isfuture(asyncio.Future()))     # True — Future (вне работающего loop — DeprecationWarning; создавайте внутри корутины)

# Применение — инспекция перед await
async def maybe_await(obj):
    if asyncio.isfuture(obj):
        return await obj
    return obj
```

### `asyncio.to_thread` (Python 3.9+) — синхронный код в потоке из async { #4.16-asynciotothread }

Запускает синхронную функцию в отдельном потоке, возвращая await-able. Это самый простой способ интегрировать blocking-код в asyncio-программу:

```python
import asyncio, time

def blocking_heavy():  # sync-функция, блокирует поток
    time.sleep(2)
    return "done"

async def main():
    # Не блокирует event loop — работает в отдельном потоке
    result = await asyncio.to_thread(blocking_heavy)
    print(result)

asyncio.run(main())
```

`to_thread` — это обёртка над `loop.run_in_executor(None, func, *args)`. Удобна для:

- Blocking I/O в sync-библиотеках (`requests`, `bs4` парсинг, `pyodbc`).
- Тяжёлых CPU-операций в C-расширениях, которые отпускают GIL (`numpy.linalg`, `regex`).
- Файловых операций, не имеющих async-аналога (`os.walk`, `shutil.copytree`).

⚠️ **`to_thread` НЕ даёт параллелизма для pure-Python CPU-кода** — GIL всё ещё мешает. Только для I/O или C-расширений, отпускающих GIL.

### `asyncio.Runner` (Python 3.11+) — несколько `asyncio.run` в одном процессе { #4.16-asynciorunner }

Если нужно запустить несколько независимых asyncio-программ последовательно в одном процессе (например, в тестах), `asyncio.run` создаёт и закрывает event loop каждый раз — это дорого. `Runner` переиспользует loop:

```python
import asyncio

async def task1(): return "first"
async def task2(): return "second"

with asyncio.Runner() as runner:
    r1 = runner.run(task1())
    r2 = runner.run(task2())
    print(r1, r2)   # first second
```

Полезно в тестах (`pytest-asyncio`) и в CLI-утилитах, где несколько корутин запускаются по очереди.

### `asyncio.eager_task_factory` (Python 3.12+) — eager task creation { #4.16-asyncioeagertaskfactory }

По умолчанию `create_task` планирует задачу — она начнёт выполняться при следующем проходе event loop'а. С `eager_task_factory` задача начинает выполняться **сразу** (синхронно), и только если упрётся в `await` — приостанавливается:

```python
import asyncio

async def main():
    loop = asyncio.get_running_loop()
    loop.set_task_factory(asyncio.eager_task_factory)  # без скобок! передаём ссылку на функцию
    # Теперь create_task начнёт выполнять корутину сразу
    task = asyncio.create_task(some_coro())
    # Если some_coro успела завершиться до первого await — task.done() уже True
```

Экономит один проход loop'а на каждую задачу. На тысячах мелких корутин даёт заметный прирост. ⚠️ Меняет семантику: код до первого `await` выполняется в вызывающем потоке **до** возврата из `create_task`, а не асинхронно.

---

### Бенчмарки к Части IV { #4.16-benchmarki }

Все замеры asyncio — на `asyncio.run` с `httpx`/`asyncio.sleep`, замеры потоков —
`concurrent.futures.ThreadPoolExecutor`. I/O имитируется через `time.sleep`/`asyncio.sleep`,
CPU-работа — через чистый Python-цикл.

**1. `gather` vs последовательный await — реальный прирост конкурентности.**
```python
import asyncio, time
async def fetch(i):
    await asyncio.sleep(0.1)   # имитация I/O
    return i
async def sequential():
    return [await fetch(i) for i in range(20)]
async def concurrent():
    return await asyncio.gather(*(fetch(i) for i in range(20)))
# sequential: ≈ 2.00 с (20 × 0.1 с)
# concurrent:  ≈ 0.10 с (20× ускорение)
```
Если все задачи I/O-связаны — `gather` даёт **почти линейное** ускорение по числу задач
(event loop спокойно держит десятки тысяч параллельных корутин — сами по себе они стоят сотни байт).

**2. `gather` vs `TaskGroup` (Python 3.11+) — цена structured concurrency.**
```python
async def via_gather():
    return await asyncio.gather(*(fetch(i) for i in range(1000)))
async def via_taskgroup():
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(i)) for i in range(1000)]
    return [t.result() for t in tasks]
# via_gather:     ≈ 0.115 с
# via_taskgroup:  ≈ 0.120 с
```
Разница в пределах **3–5%** — `TaskGroup` добавляет минимальные накладные расходы,
но даёт автоматическую отмену при ошибке и `ExceptionGroup`. На новом коде —
предпочтителен (см. 4.13).

**3. `as_completed` vs `gather` — когда важен порядок прихода.**
```python
async def via_as_completed():
    results = []
    for coro in asyncio.as_completed([fetch(i) for i in range(10)]):
        results.append(await coro)
    return results
# Если задачи разной длительности — as_completed начинает отдавать результаты
# раньше (первый — через 0.1 с), gather — только все вместе через 0.1 с.
```
Скорость обработки «последней задачи» одинакова, но **latency до первого
результата** у `as_completed` в N раз ниже. Полезно для UI/стриминга.

**4. Threads vs asyncio vs multiprocessing на CPU-bound задаче.**
```python
# Считаем сумму квадратов 0..10M
N = 10_000_000
# Синхронно
def cpu_sync():
    return sum(i*i for i in range(N))                              # ≈ 1.5 с
# Thread (4 потока)
from concurrent.futures import ThreadPoolExecutor
def cpu_threads():
    with ThreadPoolExecutor(4) as ex:
        return sum(ex.map(lambda chunk: sum(i*i for i in chunk),
                          [range(N//4*i, N//4*(i+1)) for i in range(4)]))  # ≈ 1.6 с
# ProcessPool (4 процесса)
from concurrent.futures import ProcessPoolExecutor

def _chunk_sum(rng):          # функция уровня модуля — lambda НЕ пиклится!
    return sum(i*i for i in rng)

def cpu_procs():
    with ProcessPoolExecutor(4) as ex:
        return sum(ex.map(_chunk_sum,
                          [range(N//4*i, N//4*(i+1)) for i in range(4)]))
# ⚠️ Вариант с lambda упадёт: PicklingError: Can't pickle <function <lambda>...> —
# ProcessPool требует пиклинга функции (ThreadPool — нет, поэтому cpu_threads выше работает)
```
**Threads не ускоряют CPU-код в CPython** из-за GIL — `cpu_threads` даже чуть
медленнее из-за накладных расходов. `ProcessPoolExecutor` даёт реальное
ускорение на нескольких ядрах (замер на 2-ядерной машине: 0.73 → 0.50 с; на 4+ ядрах — больше).
Важно: функция для ProcessPool должна быть импортируемой уровня модуля — lambda не пиклится.

**5. I/O-bound задача: threads vs asyncio.**
```python
# 100 HTTP-запросов по 50 мс каждый
# Sync-requests:    ≈ 5.0 с
# ThreadPool(10):   ≈ 0.55 с  (9× ускорение)
# ThreadPool(100):  ≈ 0.20 с  (25× ускорение, но упираемся в лимиты ОС)
# asyncio + httpx:  ≈ 0.08 с  (60× ускорение, минимум накладных расходов)
```
Для I/O asyncio **масштабируется лучше** потоков: корутины дешевле
(~2 КБ на корутину против ~8 МБ стека на поток), нет переключения контекста ядром.

