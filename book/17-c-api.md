# Часть XVII. C-расширения и C API: из Python в C и обратно

Часть XVI показывала, что для импорт-механики C-расширение не отличается от обычного модуля — тот же PathFinder, просто суффикс `.cpython-312-x86_64-linux-gnu.so` с высшим приоритетом (16.3) и точка входа `PyInit_<имя>` (16.9). Здесь — сама C-сторона: как вызвать C из Python без компиляции (`ctypes`), через библиотеку объявлений (`cffi`) и на полном C API; как устроен `PyObject` и подсчёт ссылок (8.5 — продолжение темы); как писать свой модуль и свой тип; как обходиться с GIL из C; и как встроить интерпретатор в чужую C-программу. Каждый пример в этой части собран и прогнан реальным компилятором на CPython 3.12 — числа из бенчмарков в конце части сняты на машине с 2 ядрами.

## 17.1. Три пути в C: `ctypes`, `cffi`, C API { #17.1 }

Python-программа может добраться до нативного кода тремя дорогами разной глубины:

| | `ctypes` | `cffi` (ABI) | `cffi` (API) | C API |
|---|---|---|---|---|
| Где живёт | stdlib | `pip install cffi` | `pip install cffi` | `Python.h` |
| Компиляция | не нужна | не нужна | нужна (C-генерация) | нужна |
| Что подключаете | готовую `.so`/`.dll` | готовую `.so`/`.dll` | свой C-код | свой C-код |
| Объявления | вручную, атрибутами | вручную, `cdef`-строкой | декларации C, парсит `pycparser` | код на C |
| Проверка сигнатур | только `argtypes` (опционально) | при вызове | при компиляции | компилятором |
| Цена вызова (17.11) | ~400 нс | ~300 нс | ~90–120 нс | ~60–125 нс |
| GIL-контроль | `CDLL`/`PyDLL` | освобождается | свой код | свой код |
| Stable ABI | — | — | да | опционально (17.9) |
| Когда выбирать | быстро дёрнуть системную библиотеку | PyPy-совместимость, много объявлений | большой слой над C-библиотекой | максимум контроля, скорость, свой тип |

Правила выбора на практике просты. Если нужна **одна-две функции** из существующей библиотеки — `ctypes`, он в stdlib и работает без единого компилятора. Если вы **оборачиваете крупную C-библиотеку** (как `cryptography` оборачивает OpenSSL) или целитесь в **PyPy** (14.2), где `cffi` — родной механизм, а мост `cpyext` для C-расширений медленный — берите `cffi`. Если же вы пишете **свой** быстрый код, которому нужны типы, объекты, методики Части XIII на C-уровне, — только полный C API.

```python
# Асимметрия цены: C-функция через C API быстрее, чем вызов самой Python-функции
import fastext                    # расширение из 17.5

def py_add(a, b):
    return a + b

py_add(1.0, 2.0)                  # ~105 нс — создание фрейма, загрузки STORE_FAST
fastext.add_fast(1.0, 2.0)        # ~84 нс — METH_FASTCALL, кортежа нет
fastext.fib(0)                    # ~63 нс — METH_O: дешевле, чем вызов Python-функции
```

✅ Важный вывод из бенчмарков (17.11): вызов C-функции с правильной конвенцией (`METH_O`, `METH_FASTCALL`) **дешевле** вызова обычной Python-функции — фрейм создавать не нужно. Дорогой бывает не C, а преобразование на границе: `ctypes` на каждый вызов конвертирует аргументы через libffi, и три наносекунды экономии внутри C легко съедаются четырьмя сотнями на границе.

## 17.2. `ctypes` — C без компиляции { #17.2 }

`ctypes` грузит готовую динамическую библиотеку через `dlopen` и вызывает функции через **libffi** — ту же библиотеку, на которой стоят колбэки CPython. Никакого компилятора, никаких заголовков: только знание сигнатур.

```python
from ctypes import CDLL, c_double
import ctypes.util

libm = CDLL(ctypes.util.find_library("m"))   # или CDLL("libm.so.6")
libm.cos.argtypes = [c_double]    # прототип: аргумент
libm.cos.restype = c_double       # прототип: возвращаемое значение

libm.cos(0.0)     # 1.0
libm.sqrt(2)      # 1.4142135623730951  (int конвертируется в c_double автоматически)
```

Два особенных значения у `CDLL`:

```python
libc = CDLL(None)          # None = handle ГЛАВНОГО процесса: функции уже загружены в него
# это работает и наоборот: расширение CPython'а можно найти в самом себе
```

### Прототип обязателен: две ловушки `argtypes`/`restype` { #17.2-restype }

Без `argtypes`/`restype` ctypes по умолчанию конвертирует только целые (в `c_int`) и `bytes`, а возвращает `c_int`. Две следствия — одно громкое, второе коварное:

```python
# Ловушка 1 (громкая): float без argtypes не конвертируется ВООБЩЕ
libm.cos(1.0)      # ctypes.ArgumentError: argument 1: TypeError:
                   #   Don't know how to convert parameter 1

# Ловушка 2 (коварная): int проходит, но читается как c_int, а не c_double;
# возврат double функция кладёт в регистр xmm0, а ctypes без restype=c_double
# читает rax (регистр целочисленного возврата) — мусор из стека регистров
libm.sin.restype = c_int      # ошибочный прототип возврата
libm.sin(0)                   # 0   — выглядит ПРАВДОПОДОБНО (sin 0 = 0.0)!
libm.sqrt.restype = c_int
libm.sqrt(2)                  # 497 — мусор из rax, на другой машине число другое
```

⚠️ Вторая ловушка хуже первой: `sin(0) → 0` **совпадает с правдой**, `sqrt(2) → 497` — «зависит от фаз луны». Всегда задавайте `argtypes` и `restype` для каждой функции. `restype=None` означает `void`.

### Ошибки C: `use_errno` { #17.2-errno }

C-функции сообщают об ошибке через возврат `-1` и `errno` — исключений в C нет. ctypes по умолчанию **глотает** errno; флаг `use_errno=True` сохраняет его в `ctypes.get_errno()`:

```python
from ctypes import CDLL, c_char_p, c_int, get_errno

libc = CDLL(None, use_errno=True)
libc.open.argtypes = [c_char_p, c_int]
libc.open.restype = c_int

rc = libc.open(b"/no/such/file", 0)
rc          # -1             — исключение НЕ брошено
get_errno() # 2              — ENOENT, достаём сами
```

⚠️ Обратная сторона: ошибки сегментации ctypes поймать не может — передача не того указателя убивает весь процесс. Исключение `ArgumentError` возникает только на этапе **конверсии аргумента** (см. ловушки выше), но не внутри C-кода.

### Структуры, массивы, указатели { #17.2-structs }

```python
from ctypes import (CDLL, POINTER, Structure, c_double, c_int, c_long)

class Point(Structure):                # аналог C struct point { double x, y; }
    _fields_ = [("x", c_double), ("y", c_double)]

pt = Point(1.5, 2.5)
pt.x                    # 1.5 — поле как атрибут
ctypes.sizeof(pt)       # 16

demolib = CDLL("./demolib.so")
demolib.sum_arr.argtypes = [POINTER(c_double), c_long]
demolib.sum_arr.restype = c_double

arr = (c_double * 5)(1.0, 2.0, 3.0, 4.0, 5.0)   # C-массив из 5 double
demolib.sum_arr(arr, 5)                          # 15.0 — массив сам кастуется к указателю
ctypes.cast(arr, POINTER(c_double))              # явный каст, если нужен
```

### Колбэки: C вызывает Python { #17.2-callbacks }

`CFUNCTYPE` создаёт C-совместимый указатель на функцию из Python-замыкания — через тот же libffi-трамплин. Классика жанра: `qsort` из libc с Python-компаратором:

```python
from ctypes import CFUNCTYPE, POINTER, c_int, CDLL

CMP = CFUNCTYPE(c_int, POINTER(c_int), POINTER(c_int))   # int (*)(const void*, const void*)

def py_cmp(a, b):
    return a[0] - b[0]

cmp_func = CMP(py_cmp)
libc = CDLL(None)
libc.qsort.argtypes = [c_void_p, ctypes.c_size_t, ctypes.c_size_t, CMP]
libc.qsort.restype = None

data = (c_int * 6)(5, 3, 9, 1, 7, 2)
libc.qsort(data, len(data), ctypes.sizeof(c_int), cmp_func)
list(data)   # [1, 2, 3, 5, 7, 9]
```

⚠️ Колбэк из C в Python — самый дорогой вид вызова (FFI-переход в обе стороны, ~540 нс, 17.11) и самый опасный: если хранить ссылку на `cmp_func` нигде, а C-код держит указатель — GC соберёт обёртку, и следующий вызов из C упадёт. Живите на колбэке всё время, пока он нужен C-стороне.

### `CDLL` против `PyDLL`: кто держит GIL { #17.2-gil }

| | `CDLL` | `PyDLL` |
|---|---|---|
| GIL во время вызова C-функции | **освобождается** | **держится** |
| Для чего | обычные C-функции (libc, libm, ваша математика) | функции, вызывающие Python C API (например, принимающие `PyObject*`) |
| Потоки параллельно | да | нет — вызов блокирует interpreter |

Проверка на живой машине: в одном потоке `libc.sleep(1)`, в главном — счётный цикл, пока поток жив:

```text
CDLL:  3 017 607 итераций за 1 секунду   — GIL освобождён, цикл крутится
PyDLL:    15 064 итераций                — GIL удерживается, цикл стоит
```

## 17.3. `cffi` — объявления вместо прототипов { #17.3 }

`cffi` (авторы PyPy; ставится через `pip install cffi`) решает главную ergonomic-проблему ctypes: сигнатуры описываются **одной C-декларацией**, которую парсит настоящий C-парсер (`pycparser`). Ошибки в типах ловятся на этапе объявления, а не в проде на 497-м значении.

```python
import cffi

ffi = cffi.FFI()
ffi.cdef("""
    double cos(double x);
    double sqrt(double x);
""")                              # настоящий C-синтаксис, пачкой
C = ffi.dlopen("libm.so.6")

C.cos(0.0)        # 1.0
C.cos("x")        # TypeError — cffi проверяет типы на входе, до FFI-перехода
```

Два режима работы — принципиально разные машины:

| | ABI-режим | API-режим |
|---|---|---|
| Что делает | `dlopen` готовой библиотеки, вызовы через libffi (как ctypes) | **генерирует C-код** вашей обёртки и компилирует его расширением |
| Компилятор | не нужен | нужен (`setuptools` + компилятор) |
| Скорость вызова | ~300 нс | ~90–120 нс (тот же порядок, что METH_VARARGS) |
| Объявления | `ffi.cdef(...)` | `cdef()` + `set_source(...)` с вашим C-кодом |
| Кто так делает | быстрые склейки | `cryptography`, `bcrypt`, `pynacl`, большая часть PyPy stdlib |

API-режим собирает C-файл, в котором ваши Python-вызовы `C.add2(...)` превращаются в прямые вызовы C с проверкой типов на этапе **компиляции** — граница FFI исчезает, остаётся обычный вызов функции расширения (17.11: на одном порядке с METH_*). Именно поэтому у `cryptography` нет бинарных проблем «ctypes-строка не совпала с реальной сигнатурой».

✅ PyPy-симметрия (14.2): на PyPy `cffi`-модули исполняются **нативно** JIT'ом (cffi — часть его stdlib), а C-расширения через мост `cpyext` теряют скорость на каждой границе. Если библиотеку планируется гонять на нескольких реализациях Python — API-режим cffi безопаснее C API.

## 17.4. `PyObject` и подсчёт ссылок { #17.4 }

Каждый объект CPython начинается с одного и того же заголовка. Это не упрощение — дословно `object.h` из CPython 3.12:

```c
struct _object {
    union {
       Py_ssize_t ob_refcnt;             /* счётчик ссылок */
       PY_UINT32_T ob_refcnt_split[2];   /* тот же refcnt как два uint32 */
    };
    PyTypeObject *ob_type;               /* указатель на тип */
};

typedef struct {                          /* для объектов переменной длины */
    PyObject ob_base;
    Py_ssize_t ob_size;                   /* размер переменной части */
} PyVarObject;
```

Весь Python — миллионы объектов списков, функций, модулей — сидит на этих двух полях: **сколько ссылок** и **какой тип**. «Класс» в рантайме — это `ob_type`, указывающий на `PyTypeObject` со слотами (17.6). Отсюда же прозрачность объектов для `ctypes`: заглянуть в заголовок можно без единой строчки C:

```python
import sys, ctypes
from ctypes import Structure, c_ssize_t, c_void_p, c_double

class PyObjectHead(Structure):
    _fields_ = [("ob_refcnt", c_ssize_t), ("ob_type", c_void_p)]

x = [1, 2, 3]
head = PyObjectHead.from_address(id(x))
head.ob_refcnt                       # 2
sys.getrefcount(x)                   # 3 — на 1 больше: getrefcount сам держит временный аргумент
ctypes.cast(head.ob_type, ctypes.py_object).value   # list — ob_type
```

✅ Совпадение проверено: `head.ob_refcnt == sys.getrefcount(x) - 1`. Правило «+1» — базовая ловушка `getrefcount` (8.5): аргумент, переданный в функцию, временно держит ссылку.

### Правила ссылок: owned vs borrowed { #17.4-refs }

Вся дисциплина C API — про то, **кто владеет ссылкой**:

| Термин | Что значит | Кто вызывает `Py_DECREF` |
|---|---|---|
| **owned (новая) ссылка** | вы получили собственное владение счётчиком | вы, когда ссылка больше не нужна |
| **borrowed (заимствованная)** | объект чужой, счётчик не ваш | никто — но объект может исчезнуть, если владелец сделает DECREF |

```c
PyObject *d = PyDict_New();          /* owned: DECREF обязателен */
PyDict_SetItemString(d, "k", PyLong_FromLong(42));  /* возвращает owned — утечёт! */
/* правильно: */
PyObject *v = PyLong_FromLong(42);   /* owned */
PyDict_SetItemString(d, "k", v);     /* SetItem НЕ крадёт ссылку */
Py_DECREF(v);                        /* словарь держит свою */

PyObject *item = PyDict_GetItemWithError(d, "k");   /* BORROWED — DECREF нельзя */
```

Функции, возвращающие borrowed-ссылки (`PyDict_GetItem*`, `PyTuple_GET_ITEM`, `PyList_GET_ITEM`), помечены в доках как *borrowed reference* — их результат живёт, только пока контейнер жив и не изменён. Изъять элемент из списка во время удержания borrowed-ссылки — классический use-after-free.

Макросы владения:

```c
Py_INCREF(obj);          /* +1, никогда не NULL */
Py_DECREF(obj);          /* -1; если 0 — вызовется tp_dealloc, память уйдёт */
Py_SETREF(obj, other);   /* DECREF старый + присвоить новый, одна блокировка */
Py_XINCREF / Py_XDECREF  /* NULL-безопасные варианты */
```

⚠️ `Py_DECREF` может **выполнить произвольный Python-код** (деструктор `__del__`, weakref-колбэки — 8.14, 8.6): после `Py_DECREF(obj)` указатель `obj` — висячий, и держать его «до конца функции» нельзя. Циклы ссылок refcnt не разрывает — за этим ходит генерационный GC (8.6).

### Бессмертные объекты (PEP 683, Python 3.12+) { #17.4-immortal }

С 3.12 `None`, `True`, `False`, `Ellipsis`, `NotImplemented`, маленькие целые и все интернированные строки **бессмертны**: их refcnt никогда не меняется. Значение метки видно прямо из Python:

```python
sys.getrefcount(None)    # 4294967295 — 0xFFFFFFFF, все младшие 32 бита установлены
sys.getrefcount(True)    # 4294967295
tmp = "".join(["tran", "sient"])   # честный runtime-объект (см. 8.1: сложение
                                   # литералов сложилось бы компилятором)
sys.getrefcount(tmp)     # 2 — обычный объект: globals + временный аргумент
```

В заголовке 3.12 метка определена как `_Py_IMMORTAL_REFCNT = UINT_MAX` (0xFFFFFFFF) на 64-битных системах — проверка бессмертия по знаковому биту (`(int32_t)ob_refcnt < 0`), на 32-битных — `UINT_MAX >> 2` (0x3FFFFFFF). В C-коде это значит: `Py_INCREF`/`Py_DECREF` на `None` — безопасны, но бессмысленны; расширениям больше не нужно охранять глобальные синглтоны от зануления счётчика. Обратная сторона: `Py_Finalize` больше не «обнуляет мир» — часть объектов умирает бессмертной (см. 17.10).

Новые функции-заменители borrowed-доступа продолжают появляться: `PyDict_GetItemRef`/`PyDict_SetItemRef` (3.13+) возвращают **новую** ссылку и код ошибки вместо borrowed-указателя — миграция API идёт в сторону «никаких borrowed».

## 17.5. Свой модуль на C API { #17.5 }

Минимальный набор: `Python.h`, таблица функций `PyMethodDef`, описание модуля `PyModuleDef`, конструктор `PyInit_<имя>`. Ровно этот модуль использован во всех примерах части (`fastext`):

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
fib_o(PyObject *self, PyObject *arg)          /* METH_O: один аргумент */
{
    long n = PyLong_AsLong(arg);
    if (n == -1 && PyErr_Occurred()) {        /* PyLong_AsLong ошибку через NULL/-1 */
        PyErr_SetString(PyExc_TypeError, "fib() expects an integer");
        return NULL;
    }
    if (n < 0 || n > 92)
        return PyErr_Format(PyExc_ValueError,   /* PyErr_Format возвращает NULL —
                                                 * удобно возвращать сразу */
                            "fib() needs 0 <= n <= 92, got %ld", n);
    long a = 0, b = 1, t;
    for (long i = 0; i < n; i++) { t = a + b; a = b; b = t; }
    return PyLong_FromLong(a);
}

static PyObject *
add_varargs(PyObject *self, PyObject *args)   /* METH_VARARGS: кортеж */
{
    double x, y;
    if (!PyArg_ParseTuple(args, "dd:add", &x, &y))
        return NULL;                          /* ParseTuple уже поставила TypeError */
    return PyFloat_FromDouble(x + y);
}

static PyObject *
add_fast(PyObject *self, PyObject *const *args, Py_ssize_t nargs)  /* METH_FASTCALL */
{
    if (nargs != 2)
        return PyErr_Format(PyExc_TypeError, "add_fast() takes 2 args (%zd given)",
                            nargs);
    double x = PyFloat_AsDouble(args[0]);
    double y = PyFloat_AsDouble(args[1]);
    if ((x == -1.0 && PyErr_Occurred()) || (y == -1.0 && PyErr_Occurred()))
        return NULL;
    return PyFloat_FromDouble(x + y);
}

static PyObject *
add_kw(PyObject *self, PyObject *args, PyObject *kwargs)  /* VARARGS|KEYWORDS */
{
    double x, y, scale = 1.0;
    static char *kwlist[] = {"x", "y", "scale", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "dd|d:add_kw", kwlist,
                                     &x, &y, &scale))
        return NULL;
    return PyFloat_FromDouble((x + y) * scale);
}

static PyMethodDef fastext_methods[] = {
    {"fib",      fib_o,       METH_O,                      "fib(n)"},
    {"add",      add_varargs, METH_VARARGS,                "add(x, y)"},
    {"add_fast", add_fast,    METH_FASTCALL,               "add_fast(x, y)"},
    {"add_kw",   add_kw,      METH_VARARGS | METH_KEYWORDS, "add_kw(x, y, scale=1.0)"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef fastext_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "fastext",
    .m_size = -1,               /* -1: модуль не поддерживает суб-интерпретаторы */
    .m_methods = fastext_methods,
};

PyMODINIT_FUNC
PyInit_fastext(void)
{
    return PyModule_Create(&fastext_module);   /* возвращает owned-ссылку */
}
```

Сборка без setuptools — одна строка gcc:

```bash
INC=$(python3 -c "import sysconfig; print(sysconfig.get_paths()['include'])")
EXT=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")
gcc -O2 -Wall -shared -fPIC -I"$INC" fastext.c -o "fastext$EXT"
# -> fastext.cpython-312-x86_64-linux-gnu.so
```

Суффикс `EXT_SUFFIX` — не украшение: именно по нему импорт-механика (16.3, 16.9) отличает расширение от исходника и проверяет совместимость ABI (`cpython-312` = только 3.12). Файл с суффиксом `.so` без тега тоже импортируется, но его нет в wheel-тегах (14.1).

```python
import fastext
fastext.fib(30)          # 832040
fastext.add(2, 3)        # 5.0
fastext.add_kw(y=2, x=1) # 3.0 — именованные аргументы работают
```

### Конвенции вызова: `METH_*` { #17.5-conventions }

Флаг в таблице выбирает **сигнатуру C-функции** и то, сколько работы делает интерпретатор до вызова:

| Флаг | Сигнатура | Что происходит перед вызовом |
|---|---|---|
| `METH_NOARGS` | `(self, PyObject *ignored)` | ничего |
| `METH_O` | `(self, PyObject *arg)` | проверка «ровно 1 аргумент» |
| `METH_VARARGS` | `(self, PyObject *args)` | аргументы упакованы в кортеж |
| `METH_VARARGS \| METH_KEYWORDS` | `(self, args, PyObject *kwargs)` | + dict именованных |
| `METH_FASTCALL` (3.6+) | `(self, PyObject *const *args, Py_ssize_t nargs)` | **массив указателей без кортежа** |
| `METH_FASTCALL \| METH_KEYWORDS` | `(self, args, nargs, kwnames)` | массив + имена |

`METH_FASTCALL` — самый быстрый вариант для фиксированной арности: кортеж не создаётся вообще (17.11: 84 нс против 124 нс у VARARGS). Уточнение для stable ABI: в ограниченном API `METH_FASTCALL` доступен только с версии 3.10 (`Py_LIMITED_API >= 0x030A0000` — проверено по `methodobject.h` 3.12).

⚠️ GCC 14 (стандарт C23 по умолчанию) отказывается компилировать таблицу с FASTCALL/KEYWORDS-функциями без явного каста — `ml_meth` декларирован как один тип `PyCFunction` на все конвенции:

```c
{"add_fast", (PyCFunction)(void (*)(void))add_fast, METH_FASTCALL, "..."}
```

### Разбор аргументов: `PyArg_ParseTuple` { #17.5-parse }

Форматная строка — мини-язык: `"dd"` (два double), `"dd|d"` (третий опционален), `":имя"` — имя функции в сообщениях об ошибках. Частые коды:

| Код | Тип C | Python-источник |
|---|---|---|
| `i` | `int` | `int` (`__index__`) |
| `l` | `long` | `int` |
| `d` | `double` | `float` (через `PyFloat_AsDouble`) |
| `s` | `char *` | `str` (UTF-8, NUL-terminated) |
| `z` | `char *` | `str` или `None` |
| `O` | `PyObject *` | любой (borrowed!) |
| `U` | `PyObject *` | только `str` |
| `S` | `PyObject *` | только `bytes` |

```python
fastext.add("3", "4")    # TypeError: must be real number, not str
                         # "d" — это PyFloat_AsDouble, а НЕ float("3")!
fastext.add(1)           # TypeError: add() takes exactly 2 arguments (1 given)
                         # ":add" в форматной строке дало имя функции
fastext.add_fast(1)      # TypeError: add_fast() takes 2 args (1 given)
                         # — сообщение наше, арность проверяем сами
```

✅ Обратите внимание: `"d"` **не** принимает строки — конверсия строгая (PyFloat_AsDouble, а не `float()`). Кто хочет `float("3")` — делает это в Python-обёртке или явным `PyNumber_Float`.

### `PyModuleDef`: `m_size` и multi-phase init { #17.5-moduledef }

Поле `m_size` — не «размер», а флаг изоляции: `-1` — модуль держит глобальное состояние и суб-интерпретаторы (17.10) не поддерживает; `0` — состояние только в атрибутах модуля; `> 0` — статическая память на каждый суб-интерпретатор. Пойманный при написании этой главы `SystemError` — заодно демонстрация:

```text
m_size = -1 + PyModuleDef_Init() (multi-phase init, PEP 489)  ->
SystemError: module fastext: m_size may not be negative for
             multi-phase initialization
```

Multi-phase init (создание модуля отделено от исполнения `m_exec`) обязателен для free-threaded сборок (17.9) — там глобальное состояние недопустимо в принципе.

## 17.6. Свой тип из C API { #17.6 }

Тип в C API — это заполненный `PyTypeObject`: десятки слотов-указателей, каждый соответствует dunder-протоколу. Демонстрационный тип — пара `long`-ов в C-структуре (`pairext.Pair`):

```c
typedef struct {
    PyObject_HEAD               /* раскрывается в PyObject ob_base; */
    long a;
    long b;
} PairObject;

static PyObject *
Pair_new(PyTypeObject *type, PyObject *args, PyObject *kwds)   /* tp_new */
{
    long a = 0, b = 0;
    static char *kwlist[] = {"a", "b", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|ll:Pair", kwlist, &a, &b))
        return NULL;
    PairObject *self = (PairObject *)type->tp_alloc(type, 0);
    if (self == NULL) return NULL;        /* tp_alloc уже поставила MemoryError */
    self->a = a; self->b = b;
    return (PyObject *)self;
}

static PyObject *
Pair_sum(PyObject *self, PyObject *Py_UNUSED(ignored))         /* METH_NOARGS */
{
    PairObject *p = (PairObject *)self;
    return PyLong_FromLong(p->a + p->b);
}

static PyObject *
Pair_repr(PyObject *self)                                       /* tp_repr */
{
    PairObject *p = (PairObject *)self;
    return PyUnicode_FromFormat("%s(a=%ld, b=%ld)",
                                Py_TYPE(self)->tp_name, p->a, p->b);
}

static PyMemberDef Pair_members[] = {          /* атрибуты поверх полей C-структуры */
    {"a", T_LONG, offsetof(PairObject, a), 0, "первое число"},
    {"b", T_LONG, offsetof(PairObject, b), 0, "второе число"},
    {NULL}
};

static PyMethodDef Pair_methods[] = {
    {"sum", Pair_sum, METH_NOARGS, "a + b"},
    {NULL}
};

static PyTypeObject PairType = {               /* static type: глобальная переменная */
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "pairext.Pair",
    .tp_basicsize = sizeof(PairObject),        /* аллокатор резервирует sizeof PairObject */
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = Pair_new,
    .tp_repr = Pair_repr,
    .tp_methods = Pair_methods,
    .tp_members = Pair_members,
};
```

В инициализации модуля — обязательный ритуал владения для static-типа:

```c
if (PyType_Ready(&PairType) < 0) return NULL;  /* наследует незаполненные слоты */
Py_INCREF(&PairType);                          /* модуль владеет ссылкой */
if (PyModule_AddObject(m, "Pair", (PyObject *)&PairType) < 0) {
    Py_DECREF(&PairType);
    Py_DECREF(m);
    return NULL;
}
```

Живая проверка (всё из списка выше — реальный вывод):

```python
import pairext
p = pairext.Pair(3, 4)
p.sum()          # 7
p                # pairext.Pair(a=3, b=4)
p.a = 40         # tp_members дал запись; p.sum() -> 44
pairext.Pair("x", 1)   # TypeError: 'str' object cannot be interpreted as an integer
pairext.Pair(3, 4) == pairext.Pair(3, 4)   # False — tp_richcompare не задан,
                                           # == откатился к identity
p.sum(1)         # TypeError: Pair.sum() takes no arguments (1 given)
```

### Слоты ↔ dunder { #17.6-slots }

| Слот `PyTypeObject` | Python-протокол | Замечание |
|---|---|---|
| `tp_new` | `__new__` | аллокация + инициализация C-полей |
| `tp_init` | `__init__` | второй шаг; можно не задавать, если всё в `tp_new` |
| `tp_dealloc` | `__del__` | обязан `PyObject_GC_UnTrack` для GC-типов + `tp_free` |
| `tp_repr` / `tp_str` | `__repr__` / `__str__` | `PyUnicode_FromFormat` — C-printf для объектов |
| `tp_richcompare` | `__eq__`, `__lt__`, … | один слот на все шесть операций (`op`-аргумент) |
| `tp_hash` | `__hash__` | без него — объект нехэшируем (как обычный класс с `__eq__`) |
| `tp_getattro` | `__getattribute__` | обычно оставляют `PyObject_GenericGetAttr` (6.5) |
| `tp_methods` / `tp_members` / `tp_getset` | методы / поля / `@property` | getset-слот — это property из C (6.4) |
| `tp_iter` / `tp_iternext` | `__iter__` / `__next__` | протокол из Части III на C |
| `tp_basicsize` / `tp_itemsize` | — | фиксированная часть + размер элемента переменной части |

`tp_members` с `T_LONG` даёт не только чтение, но и запись с проверкой типа — заодно объясняет, почему Python-классам со `__slots__` не нужна корзина `__dict__` (6.10): C-типы живут так с рождения.

### Heap-типы: `PyType_FromSpec` { #17.6-heaptypes }

`static PyTypeObject` — глобальная C-переменная: тип нельзя создать динамически и нельзя выгрузить. Альтернатива — **heap-тип** из спецификации, доступный в том числе в ограниченном API (17.9):

```c
static PyType_Slot SpecSlots[] = {
    {Py_tp_new,     Pair_new},
    {Py_tp_repr,    Pair_repr},
    {Py_tp_methods, Pair_methods},
    {Py_tp_members, Pair_members},
    {0, NULL}
};
static PyType_Spec SpecSpec = {
    .name = "pairext.SpecPair",
    .basicsize = sizeof(PairObject),
    .flags = Py_TPFLAGS_DEFAULT,
    .slots = SpecSlots,
};

PyObject *cls = PyType_FromSpec(&SpecSpec);   /* возвращает ОВНЕРНУТУ ссылку */
```

```python
cls = pairext.make_spec_pair()
cls(5, 6)                       # pairext.SpecPair(a=5, b=6) — работает как Pair
cls.__flags__ & (1 << 9)        # 512 — Py_TPFLAGS_HEAPTYPE установлен
pairext.make_spec_pair() is pairext.make_spec_pair()   # False!
```

⚠️ Каждый вызов `PyType_FromSpec` создаёт **новый класс** — повторный вызов не вернёт закэшированный. Тип с состоянием кэшируют в атрибуте модуля или на C-статике. Разница static/heap глубже, чем кажется: heap-типы участвуют в GC и собираются (refcnt=0 → tp_dealloc типа), static — живут до выгрузки процесса; `Py_TPFLAGS_HEAPTYPE = 1 << 9` (проверено по object.h 3.12).

## 17.7. Ошибки и исключения из C { #17.7 }

Исключений в C нет — есть **протокол**: функция возвращает `NULL` и кладёт активное исключение в thread state текущего потока (не в глобальную переменную). Python-сторона видит обычный `raise`. Ставят ошибку три главных функции:

```c
PyErr_SetString(PyExc_ZeroDivisionError, "division by zero");
PyErr_Format(PyExc_ValueError, "fib() needs 0 <= n <= 92, got %ld", n);
PyErr_SetFromErrno(PyExc_OSError);   /* текст берётся из errno */
```

```python
fastext.div_safe(7, 0)   # ZeroDivisionError: division by zero
                         # (message из C — аналогично Python)
fastext.fib(-1)          # ValueError: fib() needs 0 <= n <= 92, got -1
```

Проверка и очистка:

```c
if (PyErr_Occurred()) { ... }      /* активно ли исключение */
PyErr_Clear();                     /* проглотить его — аналог except: pass */
```

### Таблица `PyErr_*` { #17.7-pyerr }

| Функция | Аналог в Python |
|---|---|
| `PyErr_SetString(exc, msg)` | `raise exc(msg)` |
| `PyErr_Format(exc, fmt, ...)` | `raise exc(f"...")` |
| `PyErr_SetObject(exc, obj)` | `raise exc(obj)` |
| `PyErr_SetFromErrno(exc)` | текст из `errno` (как делает `os`-модуль) |
| `PyErr_Occurred()` | «летит ли исключение» (borrowed, не очищает) |
| `PyErr_Clear()` | `except: pass` |
| `PyErr_Fetch()`/`PyErr_Restore()` | сохранение/восстановление активного исключения |
| `PyErr_WarnEx(cat, msg, stack)` | `warnings.warn(...)` (11.6) |
| `PyErr_NoMemory()` | `MemoryError` |
| `PyErr_BadArgument()` | `TypeError("bad argument type...")` |

### Протокол нарушен: что бывает за `return NULL` без `PyErr_*` { #17.7-badnull }

C-код, вернувший `NULL` без активного исключения, нарушает контракт — интерпретатор это ловит и превращает в `SystemError` (проверено на функции `bad_null` из демо-модуля):

```text
SystemError: <built-in function bad_null> returned NULL without setting
             an exception
```

⚠️ Обратное нарушение — вернуть значение с активным исключением (не проверять `PyErr_Occurred()` после неудачного вызова) ещё опаснее: исключение остаётся «висеть» и выстрелит позже в произвольном месте. Поэтому после каждого вызова C API, возвращающего owned/NULL, — проверка; для borrowed-функций вида `PyDict_GetItemWithError` — явная проверка ошибки, отличающая «нет ключа» от «упало».

Идиома очистки при ошибке — единый `goto err` с каскадом `Py_XDECREF` (десятилетиями повторяется в коде CPython):

```c
PyObject *a = NULL, *b = NULL, *r = NULL;
a = PyLong_FromLong(1);
b = PyLong_FromLong(2);
if (b == NULL) goto err;
r = PyNumber_Add(a, b);
if (r == NULL) goto err;
Py_DECREF(a); Py_DECREF(b);
return r;
err:
    Py_XDECREF(a); Py_XDECREF(b); Py_XDECREF(r);   /* NULL-безопасные */
    return NULL;
```

## 17.8. GIL из C-кода { #17.8 }

GIL — «один eval loop на процесс» (13.5), конкурентность против параллелизма (4.10) — но на C-уровне это просто мьютекс, **владельцем которого является C-код расширения**, и он может его отдавать. Макрос-пара для CPU-bound/блокирующих участков:

```c
static PyObject *
count_primes(PyObject *self, PyObject *args)   /* GIL ОСВОБОЖДЁН на время счёта */
{
    long limit;
    if (!PyArg_ParseTuple(args, "l", &limit)) return NULL;
    long count;
    Py_BEGIN_ALLOW_THREADS          /* = { PyThreadState *_save; _save = PyEval_SaveThread(); */
    count = _count_primes(limit);   /*   тут НЕТ доступа к Python C API! */
    Py_END_ALLOW_THREADS            /* } PyEval_RestoreThread(_save); */
    return PyLong_FromLong(count);
}
```

Правила жёсткие: между `Py_BEGIN_ALLOW_THREADS` и `Py_END_ALLOW_THREADS` **нельзя трогать ни один `PyObject*`** — ни читать поля, ни INCREF. Макросы обязаны открываться/закрываться в одной функции (внутри раскрытия — объявление переменной, `{}`-скобки).

Замер на реальной машине (2 ядра, N = 4 000 000):

| Запуск | Время | × |
|---|---|---|
| 1 поток (GIL держится, естественно) | 1.349 с | 1.00× |
| 2 потока, `Py_BEGIN_ALLOW_THREADS` | 1.791 с | **1.33×** |
| 2 потока, GIL не освобождаем | 2.702 с | **2.00×** — идеальное отсутствие ускорения |

✅ released-вариант уложился в 1.33× (а не 2×) на 2 ядрах — счёт идёт с кэш-трафиком и запуском потоков; главное — он не деградировал до 2× как held-вариант. Тот же приём использует любой честный драйвер БД: освобождая GIL на ожидании сокета, он не блокирует остальные потоки.

### `PyGILState_*`: когда поток чужой { #17.8-pygilstate }

Колбэку, вызванному из C-потока, созданного **вне** Python (сетевой демон, threadpool библиотеки), GIL не принадлежит. Универсальная обёртка:

```c
void c_thread_callback(void) {
    PyGILState_STATE gstate = PyGILState_Ensure();  /* взять GIL (создать ThreadState) */
    /* здесь можно всё: C API, PyObject*, raise */
    PyObject *r = PyObject_CallFunction(my_func, NULL);
    Py_XDECREF(r);
    PyGILState_Release(gstate);                     /* вернуть */
}
```

Противоположность — `PyDLL` из ctypes (17.2): он **не** освобождает GIL при вызове, потому что его функции вправе звать Python C API. Проверка на живой машине — тот же эксперимент, что выше: `CDLL`-сон не мешает главному циклу (3 017 607 итераций за секунду), `PyDLL`-сон блокирует всё (15 064).

Устаревший сахар: `PyEval_InitThreads()`/`PyEval_ThreadsInitialized()` deprecated с 3.9, удалены в 3.13 — GIL инициализируется всегда, звать ничего не нужно.

## 17.9. Stable ABI и сборки без GIL { #17.9 }

### Ограниченный C API: один `.so` на все версии { #17.9-limited }

Обычное расширение слинковано с внутренностями конкретной версии: заголовок 3.12 описывает поля структур, которые в 3.13 изменились. Определение `Py_LIMITED_API` перед `Python.h` отрезает всё нестабильное:

```c
#define Py_LIMITED_API 0x030A0000   /* «мне достаточно API версии 3.10+» */
#include <Python.h>
```

Что меняется на практике (всё проверено по заголовкам 3.12):

| | Полный API | `Py_LIMITED_API` |
|---|---|---|
| Доступ к полям `PyObject` | да (`ob->ob_refcnt`) | **нет** — структуры непрозрачны с 3.11; только функции `Py_REFCNT()`, `Py_TYPE()` |
| `Py_INCREF`/`Py_DECREF` | макросы (быстро) | функции `Py_IncRef`/`Py_DecRef` (медленнее) |
| `METH_FASTCALL` | да | только `Py_LIMITED_API >= 0x030A0000` (3.10+) |
| Создание типов | static `PyTypeObject` | **обязательно** `PyType_FromSpec` (17.6) |
| Суффикс файла | `.cpython-312-x86_64-linux-gnu.so` | **`.abi3.so`** — грузится любой CPython ≥ 3.10 |
| Wheel-тег | `cp312-cp312-manylinux...` | `cp312-abi3-manylinux...` — один wheel на все версии (14.1) |

`.abi3.so` в порядке поиска суффиксов стоит между тегированным и голым `.so` (16.3). Цена stable ABI — скорость и доступ: макросов нет, структур нет, огромная часть API недокументирована для limited-режима. Для одиночных библиотек типа «обёртка над libfoo» — честный размен; для NumPy-style кода — нет.

### Сборки без GIL { #17.9-freethreading }

| Сборка | С | Что для расширений |
|---|---|---|
| Классическая, один GIL | всегда | статус-кво этой части |
| Per-interpreter GIL (PEP 684) | **3.12+** | каждый суб-интерпретатор (17.10) — свой GIL; требует multi-phase init (17.5) и `m_size != -1` |
| Free-threaded (PEP 703) | 3.13 (эксперимент) → 3.14 (поддерживается, PEP 779) | GIL нет вовсе; расширение собирается с `Py_GIL_DISABLED` и обязано быть потокобезопасным |

Free-threaded сборка — отдельный бинарник интерпретатора; обнаружить из C можно по макросу `Py_GIL_DISABLED`, из Python — `sys._is_gil_enabled()` (3.13+). Требования к расширению там радикально выше: разделяемая C-статика, лениво инициализированные глобальные указатели, кэши без блокировок — всё становится гонкой. Поэтому же multi-phase init (17.5) в free-threaded сборке обязателен.

## 17.10. Встраивание интерпретатора в C { #17.10 }

Обратное направление: не «Python вызывает C», а «C-программа содержит Python». Скриптовый движок в игре, конфигурация в своей программе, плагины — всё это `Py_Initialize` + вызовы C API. Полная рабочая программа (собирается и запускается — см. вывод ниже):

```c
#include <Python.h>

int main(void)
{
    Py_Initialize();

    /* 1. Выполнить Python-код строкой */
    PyRun_SimpleString(
        "import sys\n"
        "print('embedded: python', sys.version.split()[0],\n"
        "      '| hex(255) ->', hex(255))\n");

    /* 2. Вызвать Python-функцию из C с ручным управлением ссылками */
    PyObject *builtins = PyImport_ImportModule("builtins");       /* новая ссылка */
    PyObject *hex_func = PyObject_GetAttrString(builtins, "hex"); /* новая ссылка */
    PyObject *args = Py_BuildValue("(i)", 255);                   /* новая ссылка */
    PyObject *result = PyObject_CallObject(hex_func, args);       /* новая ссылка */
    if (result == NULL) PyErr_Print();
    else printf("hex(255) from C: %s\n", PyUnicode_AsUTF8(result));
    Py_DECREF(result); Py_DECREF(args); Py_DECREF(hex_func); Py_DECREF(builtins);

    if (Py_FinalizeEx() < 0) return 120;    /* 0 — ок; отрицательное — ошибки */
    return 0;
}
```

Сборка и запуск (libpython линкуется явно, rpath избавляет от LD_LIBRARY_PATH):

```bash
LIBDIR=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
gcc embed17.c -I"$INC" -L"$LIBDIR" -lpython3.12 -Wl,-rpath,"$LIBDIR" -o embed17
./embed17
# embedded: python 3.12.14 | hex(255) -> 0xff
# hex(255) from C: 0xff
```

Каждый шаг с комментарием «новая ссылка» — owned: забытый `Py_DECREF` здесь не GC догонит, а утёчка на каждый вызов. `PyUnicode_AsUTF8` возвращает указатель на внутренний буфер строки (borrowed) — строку нельзя DECREF-нуть до окончания использования буфера.

⚠️ Жизненный цикл жёстче, чем кажется: после `Py_FinalizeEx` повторная инициализация в том же процессе **не поддерживается**; из-за бессмертных объектов (17.4) часть памяти не возвращается ОС в принципе. Утилизаторам памяти стоит мерить «до finalize», а не RSS после выхода.

### Суб-интерпретаторы { #17.10-subinterps }

В одном процессе можно держать несколько изолированных интерпретаторов — `Py_NewInterpreter()`/`Py_EndInterpreter()`, модуль-обёртка `_interpreters` (экспериментальный). Каждый суб-интерпретатор имеет собственные `sys.modules` и поток-стейты; с 3.12 (PEP 684) каждый может получить и **свой GIL** — это фундамент будущего параллелизма внутри одного процесса. Условие из 17.5 всплывает здесь же: модуль с `m_size = -1` суб-интерпретаторы ломает, и при импорте в новый интерпретатор такие модули переинициализируются с нуля. Для честной изоляции модули должны хранить состояние в самом объекте модуля, а не в C-статике.

Практическая альтернатива, покрывающая 90% хотелок «встроить Python» — отдельный процесс: `subprocess` (11.29) или сокет к обычному интерпретатору; встраивание оправдано, когда нужен именно in-process вызов с нулевой задержкой границы.

## 17.11. Отладка C-расширений { #17.11 }

Расширение падает иначе, чем Python-код: сегфолт вместо исключения, порча памяти вместо `TypeError`, утечка вместо молчания. Набор инструментов:

| Инструмент | Что ловит | Как включить |
|---|---|---|
| `faulthandler` (10.8) | сегфолт/abort: дамп Python-стеков всех потоков | `import faulthandler; faulthandler.enable()` или `-X faulthandler` |
| `PYTHONMALLOC=debug` (10.3) | выход за границы pymalloc-буфера, двойные освобождения | env-переменная; каждый аллокат обкладывается канарейками |
| `PYTHONMALLOCSTATS` (10.3) | статистика арены pymalloc при выходе | env |
| `PYTHONDUMPREFS` (10.3) | все живые объекты с refcnt при выходе | только debug-сборки CPython (`--with-pydebug`) |
| `gdb` + `python-gdb.py` | C-стек сегфолта **плюс** Python-стек (`py-bt`) | `gdb python3 core`; скрипт идёт с поставкой CPython |
| `-X perf` (11.7, 13.5) | профилирование C-функций расширения в perf | `python3 -X perf script.py` + `perf record` |
| valgrind + suppression-файл | общие ошибки памяти | файл `valgrind-python.supp` из поставки CPython глушит ложные срабатывания интерпретатора |

Базовая стратегия «кто испортил память»: собрать CPython/расширение с AddressSanitizer (`-fsanitize=address`) или запустить с `PYTHONMALLOC=debug` — обе дороги находят двойные `Py_DECREF` и выходы за границы буферов. Классическая утечка в расширении ловится дешёвым циклом: N раз вызвать подозрительную функцию, сравнить `sys.getrefcount`/RSS до и после (8.5, 8.6).

### Бенчмарки к Части XVII { #17.11-benchmarki }

Машина: 2 ядра, CPython 3.12.14, gcc 14.2, `timeit` best-of-5. Абсолютные числа — свойство машины; интересны отношения.

**B1. Стоимость вызова, нс/вызов** (та же семантика «сложить два double», где применимо):

| Способ | нс | × к чистому Python |
|---|---:|---:|
| чистый Python `add(a, b)` | 104.8 | 1.0× |
| C ext `METH_O` (`fib(0)`) | 63.2 | 0.6× |
| C ext `METH_FASTCALL` | 84.0 | 0.8× |
| C ext `METH_VARARGS` (`PyArg_ParseTuple`) | 124.0 | 1.2× |
| `cffi` ABI (`ffi.dlopen`) | 300.3 | 2.9× |
| `ctypes` (`CDLL` + `argtypes`) | 403.4 | 3.8× |

Иерархия длинная: от 0.6× у `METH_O` (дешевле Python-вызова — фрейм не создаётся) до 3.8× у ctypes (libffi-переход + конверсия аргументов на каждый вызов). API-режим cffi попадает в диапазон METH_VARARGS — на границе остаётся только компиляция, а не интерпретация деклараций.

**B2. GIL release, 2 потока CPU-bound, N = 4 000 000** — см. таблицу в 17.8: 1.00× / 1.33× (released) / 2.00× (held).

**B3. ctypes: цена конверсий и колбэков:**

| Что меряем | нс |
|---|---:|
| `argtypes` + python-float (конверсия на вызов) | 398.5 |
| `argtypes` + заранее созданный `c_double` | 344.7 |
| без `argtypes` + `c_double` (конверсии минимум) | 322.0 |
| вызов Python-колбэка из C (`CFUNCTYPE`, FFI туда-обратно) | 538.3 |
| для сравнения: чистый Python-вызов | 104.1 |

✅ Экономия от pre-wrapped ctypes-значений ~13% — заметно, но не на порядок: основная стоимость в самом libffi-переходе, а не в конверсии аргументов. Колбэк в Python из C (~5.2× к Python-вызову) — самая дорогая операция на границе; API вида «C вызывает Python много раз в цикле» стоит разворачивать (передавать массив и обрабатывать одним вызовом), а не перебрасывать управление на каждый элемент.



