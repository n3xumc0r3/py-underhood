# Часть XV. Тестирование: от assert до тестов самого CPython

До сих пор тесты в этой книге мелькали только мимоходом — как источник примеров или сосед по CLI. Эта часть смотрит на тестирование так, как смотрит вся книга: что происходит под капотом. Каждый тестовый инструмент сидит на конкретном крючке интерпретатора: `assert` — это скомпилированный байт-код с отдельным `LOAD_ASSERTION_ERROR`; `unittest.mock` — дисциплина над `setattr`/`__getattribute__`; `coverage.py` — счётчики на line-событиях трейсера; отладчики и профайлеры в 3.12+ — уже не `sys.settrace`, а новый API `sys.monitoring` (PEP 669). А «тесты самого CPython» — это вообще исполняемая спецификация языка (14.1). Разделы идут от простого к сложному: сначала то, что есть в любом тесте (`assert`, `unittest`, mock), затем фреймворки (`doctest`, `pytest`, coverage), затем интерпретаторная кухня (трассировка, monitoring, regrtest, диагностические режимы).

## 15.1. `assert` под капотом: байт-код, `-O` и тонкие локации ошибок { #15.1 }

Базовая единица любого теста — `assert`. В 1.15 разобраны ловушки синтаксиса и флаг `-O`; здесь — как assert живёт в байт-коде и почему трейсбеки в 3.11+ стали такими точными.

Компиляция `assert x > 0, "bad"` на 3.12 (8.9):

```python
import dis

def f(x):
    assert x > 0, "bad"

dis.dis(f)
#   2           LOAD_FAST                0 (x)
#               LOAD_CONST               1 (0)
#               COMPARE_OP              40 (>)
#               POP_JUMP_IF_TRUE         7 (to 26)   # если условие ИСТИННО —
#                                                         прыгаем мимо raise-блока
#               LOAD_ASSERTION_ERROR                 # иначе готовим исключение
#               LOAD_CONST               2 ('bad')   # и его сообщение
#               RAISE_VARARGS            1
```

Три детали, которые видно прямо в выводе. Первая — компилятор переворачивает условие: вместо «если ложно — падай» он генерирует «если истинно — прыгай дальше», потому что happy-path (тест прошёл) должен быть прямым путём без прыжка. Вторая — у исключения есть собственный опкод загрузки `LOAD_ASSERTION_ERROR`: так интерпретатор не ищет `AssertionError` в ваших глобалах — подмена `builtins.AssertionError` не изменит поведение `assert`. Третья — сообщение `"bad"` — это обычная константа или выражение: f-string в сообщении вычисляется **только при падении** assert, в счастливом пути её нет.

С `-O` и `-OO` всё исчезает ещё на этапе компиляции (1.15): можно убедиться без перезапуска интерпретатора:

```python
src = "def f(x):\n    assert x > 0, 'bad'\n"
plain = compile(src, "<t>", "exec")
optimized = compile(src, "<t>", "exec", optimize=2)

import dis
ops = {i.opname for i in dis.get_instructions(optimized)}
print("RAISE_VARARGS в -O-версии:", "RAISE_VARARGS" in ops)
# RAISE_VARARGS в -O-версии: False
```

Отсюда правило из 1.15 на языке байт-кода: `-O` не «выключает» assert'ы — она **не компилирует их вовсе**, вместе с сообщением и любыми побочными эффектами в нём.

### PEP 657: тонкие локации ошибок в трейсбеках (3.11+) { #15.1-pep-657 }

До 3.11 traceback показывал только строку, где что-то пошло не так. PEP 657 добавил в кодовые объекты точные колонки начала и конца каждого выражения (`co_positions()`), и теперь каретки `^` в трейсбеке указывают на конкретный фрагмент выражения:

```python
# t.py
d = {"a": {"b": 1}}
print(d["a"]["c"]["d"])
```

```text
Traceback (most recent call last):
  File "t.py", line 2, in <module>
    print(d["a"]["c"]["d"])
          ~~~~~~^^^^^
KeyError: 'c'
```

Каретка указывает ровно на `["c"]` — ключ, которого нет, а не на весь `print` и не на всю цепочку индексации. Тильды показывают успешно вычисленную часть (`d["a"]`), каретки — сбойную. Для assert'ов это работает так:

```python
# t2.py
x = 0
assert x == 1 and x > 3, "fail"
```

```text
Traceback (most recent call last):
  File "t2.py", line 2, in <module>
    assert x == 1 and x > 3, "fail"
           ^^^^^^^^^^^^^^^^
AssertionError: fail
```

⚠️ Предел точности задаёт байт-код: у `and`-цепочки нет отдельной инструкции на каждый операнд, поэтому каретки накрывают всё условие. Чем «плоско» выражение, тем точнее прицел. Именно это улучшение сделало сообщения тестов читаемыми без отладчика: видно **что именно** в строке упало. А pytest идёт дальше и переписывает сами assert'ы (15.6) — уже не локация, а интерпретация.

## 15.2. `unittest` изнутри: loader → suite → runner → result { #15.2 }

`unittest` — xUnit-порт из Java (за авторством Steve'а Purcell'а, в stdlib с 2.1), и его архитектура — конвейер из четырёх ролей:

| Роль | Класс | Что делает |
|---|---|---|
| Хранение | `unittest.TestCase` | один тест-класс; методы `test_*` — тесты |
| Поиск | `unittest.TestLoader` | находит тесты → собирает `TestSuite` |
| Контейнер | `unittest.TestSuite` | просто список тестов и итерация по нему |
| Исполнение | `unittest.TextTestRunner` | гоняет suite, копит события в `TestResult` |
| Протокол | `unittest.TestResult` | счётчики: `testsRun`, `failures`, `errors`, `skipped` |

Ключ к пониманию — что `TestCase` — это **не** «тест». Это класс-фабрика: `TestLoader.loadTestsFromTestCase(T)` создаёт по одному экземпляру `T` на каждый метод `test_*`. Каждый экземпляр — самостоятельный тест со своим `setUp`/`tearDown`: изоляция достигается тем, что каждый тест живёт в свежем объекте, а не тем, что состояние «чистится» после.

Запуск через `python -m unittest` — это тот же runpy-механизм, что у `python -m json.tool` (11.31): интерпретатор импортирует пакет `unittest` как `__main__`, тот подхватывает `unittest.main()` и дальше — loader/runner. Живой вывод:

```text
$ python -m unittest -v
test_add (test_demo.TD.test_add) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.000s

OK
```

### Порядок тестов и discovery { #15.2-poryadok }

Первое, что удивляет тех, кто ждёт «порядок объявления»: тесты исполняются **в алфавитном порядке** имён. Это свойство лоадера — `TestLoader.sortTestMethodsUsing` (по умолчанию `three_way_cmp`):

```python
import unittest

class T(unittest.TestCase):
    def test_b(self): pass
    def test_a(self): pass
    def test_c(self): pass

suite = unittest.TestLoader().loadTestsFromTestCase(T)
print([t._testMethodName for t in suite])
# ['test_a', 'test_b', 'test_c']  — не порядок объявления!
```

Следствие для практики: `test_1`…`test_10` упорядочатся как `test_1, test_10, test_2, …` — если порядок важен, тесты делают **зависимыми от данных, а не от имён**, либо используют `subTest`. Присвоить `sortTestMethodsUsing = None` можно (порядок станет порядком обнаружения), но полагаться на это — значит строить тесты на хрупком крючке.

`discover` ищет файлы по шаблону `test*.py` (настраивается) и — важный момент — собирает **только `TestCase`-подклассы** и модули с `load_tests`. Голая функция `def test_ok(): ...` для unittest не существует:

```python
# pkg/test_x.py
import unittest
class TX(unittest.TestCase):
    def test_ok(self): self.assertTrue(True)

# pkg/test_y.py
def test_bare(): pass          # unittest это НЕ увидит
```

```python
import unittest
tests = unittest.defaultTestLoader.discover("pkg")
print(tests.countTestCases())
# 1   — test_y.py просканирован, но голой функции там нет
```

Это самое заметное отличие от pytest, который собирает голые функции `test_*` как полноценные тесты (15.6).

### TestResult: куда деваются skip, xfail и subTest { #15.2-result }

Runner ничего не решает — он передаёт события в `TestResult`. Отсюда механика всех «статусов»:

- `skipTest()` / `@unittest.skip(...)`: тест бросает `unittest.SkipTest`, лоадер/раннер ловит его отдельно → `result.skipped` — список пар `(тест, причина)`;
- `@unittest.expectedFailure`: если тест упал — фиксируется в `result.expectedFailures`; если **внезапно прошёл** — в `result.unexpectedSuccesses` (это тоже не успех: сюрприз требует разбирательства);
- `subTest`: провал одного подтеста **не останавливает** остальные подтесты этого метода, а в отчёт пишется конкретный случай.

```python
import unittest

r = unittest.TestResult()

class T2(unittest.TestCase):
    def test_ok(self): pass
    def test_skip(self): self.skipTest("потом")
    @unittest.expectedFailure
    def test_xfail(self): self.assertEqual(1, 2)
    def test_fail(self): self.assertEqual(1, 2)

unittest.TestLoader().loadTestsFromTestCase(T2).run(r)
print(r.testsRun, len(r.failures), r.skipped, len(r.expectedFailures))
# 4 1 [(<T2 testMethod=test_skip>, 'потом')] 1
```

`subTest` при этом честно считается одним тестом, но провал конкретного подтеста попадает в отчёт с его параметрами:

```python
class T3(unittest.TestCase):
    def test_many(self):
        for i in range(5):
            with self.subTest(i=i):
                self.assertNotEqual(i, 3)

# testsRun = 1, но в result.failures — падение именно подтеста i=3
# AssertionError: 3 == 3
```

⚠️ `assertNotEqual(i, 3)` падает с сообщением `3 == 3`, а не `3 != 3`: сообщение assert-методов показывает **аргументы**, из которых видно равенство. Не пугайтесь формулировки.

Ещё одна деталь механики, о которой мало кто знает: у `TestCase` с 3.11+ есть `enterContext(cm)` — программный эквивалент `with` внутри теста, удобный для общих setup-ов; у `IsolatedAsyncioTestCase` — парный `enterAsyncContext` (4.9):

```python
class WithTempdir(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())  # 3.11+
        self.tmp = tmp
```

Выход менеджера при этом будет выполнен **после** `tearDown` — контекстные менеджеры, зарегистрированные через `enterContext`, стекуются в `ExitStack` теста (2.4).

## 15.3. `unittest.mock` изнутри: анатомия подмены { #15.3 }

`unittest.mock` кажется магией: объект, который «умеет всё» и помнит все вызовы. Под капотом — только три механизма: `__getattr__` создаёт дочерние моки на лету, `__call__` записывает вызовы, а `patch` — это `setattr` с откатом.

### Авто-атрибуты и запись вызовов { #15.3-zapis-vyzovov }

```python
from unittest import mock

m = mock.Mock()
m.anything.deeper(42)          # ← ни один из атрибутов не существовал
print(m.anything.deeper.call_args)
# call(42)

m.f(1, x=2)
ca = m.f.call_args
print(ca.args, ca.kwargs)      # (1,) {'x': 2}   — кортежи с 3.8+
print(m.f.call_args == mock.call(1, x=2))   # True
```

Обращение к любому атрибуту мока возвращает (и запоминает) новый `Mock` — поэтому цепочки `m.anything.deeper` работают без подготовки. Запись вызовов — список `_mock_call_args_list`; методы `assert_called_with`/`assert_called_once_with` — просто сравнения с этим списком, поэтому их «умение» не выходит за рамки `==` на `call(...)`.

`side_effect` даёт три поведения сразу (проверяются в порядке: исключение → iterable → значение):

```python
m_err = mock.Mock(side_effect=ValueError("бум"))
m_err(1)                       # ValueError: бум — исключение бросается

m_seq = mock.Mock(side_effect=[1, 2, 3])
m_seq(); m_seq(); m_seq()      # 1, 2, 3 — по значению на вызов, потом StopIteration

m_mix = mock.Mock(return_value=42, side_effect=[9])
print(m_mix())
# 9  — side_effect (как iterable) имеет приоритет над return_value
```

`MagicMock` — то же самое, но с **заранее настроенными dunder-методами** (5.17): `len(MagicMock()) == 0`, `iter()` отдаёт пустой итератор, сравнения работают. Голый `Mock` dunder-ы не настраивает — `len(Mock())` упадёт `TypeError`. Правило: почти всегда берите `MagicMock` (он и есть значение по умолчанию у `patch`).

### spec и autospec: мок, который не врёт { #15.3-spec-i-autospec }

Авто-атрибуты — и главная дыра моков: опечатка в имени метода делает тест, который проверяет **несуществующий** API. Лечится `spec`:

```python
mi = mock.Mock(spec=int)
mi.no_such
# AttributeError: Mock object has no attribute 'no_such'
isinstance(mi, int)
# True — мок подменяет __class__ под spec
```

`spec` ограничивает набор атрибутов реальным объектом (и `isinstance` начинает работать — мок выдаёт себя за указанный класс). `create_autospec` идёт дальше — переносит **сигнатуру** функции:

```python
import inspect
as_py = mock.create_autospec(lambda a, b=0: None)
print(inspect.signature(as_py))
# (a, b=0)  — сигнатура сохранена

as_py()
# TypeError: missing a required argument: 'a'  — вызов проверяется как настоящий
```

⚠️ `autospec` полагается на интроспекцию, а она у C-функций ограничена: `create_autospec(len)` даёт мок с сигнатурой `(*args, **kwargs)` — проверка аргументов **не включается**, и `len(1, 2)` на моке не падает. Для C-API мок с autospec — не гарантия совместимости, а просто замещающий объект.

### `patch`: setattr с откатом — и классическая ловушка { #15.3-lovushka-from-import }

`mock.patch("os.getcwd", return_value="/stub")` механически делает вот что: разрезает строку-цель по точкам, импортирует корневой модуль, спускается по цепочке `getattr` до родителя, запоминает старое значение атрибута и делает `setattr(parent, "getcwd", Mock(return_value="/stub"))`. На выходе из блока — `setattr` обратно. Всё. Никакой интерпретаторной магии — потому и работает одинаково с чем угодно, к чему применим `setattr`.

```python
with mock.patch("os.getcwd", return_value="/stub"):
    print(os.getcwd())
# /stub
print(os.getcwd())
# /home/user/proj — после выхода атрибут восстановлен
```

Отсюда — самая знаменитая ловушка mock: **`patch` подменяет атрибут модуля, а не объект**. Имя, связанное через `from math import sqrt` до патча, продолжает указывать на старую функцию:

```python
import math
from math import sqrt as direct_sqrt

with mock.patch("math.sqrt", return_value=-1):
    print(math.sqrt(9))     # -1.0   — подменён атрибут модуля math
    print(direct_sqrt(9))   # 3.0    — локальное имя связано СТАРОЙ функцией
```

❌ Патчить «то, как импортировал сосед». ✅ Патчить то место, **где имя используется**: если тестируемый модуль сделал `from mymod import sqrt`, патчить `mymodule.sqrt`, а не `mymod.sqrt`.

Пара ручек, которые дополняют картину:

- `patch("os.definitely_not_here", create=True)` — патчит даже несуществующий атрибут (иначе `patch` честно падает `AttributeError` — это защита от опечаток в цели, отключать осознанно);
- `mock.sentinel.obj` — уникальный объект-маркер: `sentinel.a is sentinel.a`, но `sentinel.a != sentinel.b` — вместо строковых «магических значений» в проверках;
- `mock.seal(m)` — «замораживает» дерево моков: существующие атрибуты работают, новые создать нельзя (`AttributeError: Cannot set mock.new_attr`) — страховка от случайных обращений к несуществующему API, аналог `spec` для моков, собранных руками.

Производительность моков — отдельная тема: вызов `Mock` в десятки раз дороже обычного вызова функции (54× у `Mock`, 81× у autospec — бенчмарк в конце части). В горячих путях тестов это складывается в минуты.

## 15.4. Подмена времени и окружения в тестах { #15.4 }

«Сейчас» — самый неприятный фактор недетерминизма в тестах: код смотрит на `datetime.now()`, `time.time()`, `time.monotonic()`. Инструменты заморозки времени различаются глубиной, на которой живут.

Уровень один — тот же `patch` из 15.3:

```python
from unittest import mock
import time

with mock.patch("time.time", return_value=1_577_880_000):
    print(int(time.time()))
# 1577880000
```

Работает только для имён, которые вызываются **через атрибут модуля** (`time.time()`), и только для питоновского уровня: C-расширения, вызывающие `time()` напрямую из C, мок не увидят.

Уровень два — `freezegun` (чистый Python): обходит десятки модулей (`datetime`, `time`, `calendar`…) и патчит их атрибуты. Замораживается всё, включая `time.monotonic`, а `time.sleep` становится **no-op**:

```python
import time, datetime
from freezegun import freeze_time

with freeze_time("2020-01-01 12:00:00"):
    print(datetime.datetime.now())        # 2020-01-01 12:00:00
    print(int(time.time()))               # 1577880000
    t0 = time.monotonic(); time.sleep(3); t1 = time.monotonic()
    print(round(t1 - t0, 1), datetime.datetime.now())
    # 0.0 2020-01-01 12:00:00 — sleep ничего не ждал и время не сдвинул
print(datetime.datetime.now())            # настоящее время
```

Уровень три — `time-machine` (C-расширение): патчит C-уровень функций времени, поэтому и вход/выход дешевле на три порядка, и поведение тоньше настраивается. `tick=False` — стоп-кадр: настенные часы стоят, но `sleep` реально спит и `monotonic` идёт; `tick=True` — часы идут от заданной точки:

```python
import time, datetime, time_machine

with time_machine.travel("2020-01-01 12:00:00", tick=False):
    print(datetime.datetime.now())        # 2020-01-01 12:00:00
    t0 = time.monotonic(); time.sleep(0.2); t1 = time.monotonic()
    print(round(t1 - t0, 2), datetime.datetime.now())
    # 0.2 2020-01-01 12:00:00 — спал по-настоящему, часы стоят

with time_machine.travel(datetime.datetime(2020, 1, 1), tick=True):
    t0 = time.time(); time.sleep(0.2); t1 = time.time()
    print(round(t1 - t0, 2))
    # 0.2 — время течёт от заданной точки
```

Выбор: точечные проверки — `patch`; «остановить всё время» для интеграционных тестов — `freezegun` (дороже на входе/выходе, но тащит за собой `datetime` и сдвигает время при `sleep`-ах сторонних библиотек через свои настройки); частая заморозка в перфоманс-чувствительных тестах — `time-machine` (≈1500× быстрее freezegun на входе/выходе — бенчмарк в конце части).

Часовые пояса подменяются окружением: `os.environ["TZ"] = "UTC"; time.tzset()` — POSIX-only (на Windows `tzset` нет), поэтому в кросс-платформенных тестах это делают через `monkeypatch`/`patch.dict` (2.4, 15.3) и пропускают тест на Windows (`@unittest.skipIf(sys.platform == "win32", ...)`).

## 15.5. `doctest` изнутри { #15.5 }

Директивы doctest разобраны в 12.4; здесь — как модуль устроен. `doctest` — конвейер из двух компонентов: `DocTestParser` вырезает из текста примеры (`>>> ...` в начале строки + ожидаемый вывод до пустой строки или следующего `>>>`), а `DocTestRunner` исполняет их и сравнивает вывод.

```python
import doctest, types

mod_src = '''\
def double(x):
    """Удваивает.
    >>> double(4)
    8
    >>> double('ab')
    'abab'
    """
    return x * 2
'''
fm = types.ModuleType("fake")
exec(mod_src, fm.__dict__)
print(doctest.testmod(fm))
# TestResults(failed=0, attempted=2)
print(len(doctest.DocTestParser().get_examples(mod_src)))
# 2
```

Три детали механики, которые объясняют почти все «почему» doctest'а.

**Сравнение — посимвольное сравнение строк stdout с ожидаемым текстом.** Никакого repr-протокола: если функция печатает `'abab'` с кавычками, ожидание должно быть `'abab'`, а если бы вывод шёл через `print` — без кавычек. Отсюда же требование «пустая строка в ожидаемом выводе = конец примера»: парсер просто не знает, где вывод заканчивается.

**Пространство имён примера — globals модуля (копия).** Примеры из docstring'а функции исполняются в её модуле, поэтому `double` в примере выше видна без импортов. Нюанс уровня исходников: `DocTestFinder` привязывает docstring к модулю проверкой `module.__dict__ is func.__globals__` — функция, созданная в одном пространстве имён и вставленная в другой (как в паттерне `exec` выше, где важно исполнить код именно в `fm.__dict__`), examples теряет.

**Код возврата и CLI.** `doctest.testmod()` возвращает именованный кортеж `TestResults(failed, attempted)`, а `python -m doctest file.py` выходит с кодом 1 при провале — удобно для CI:

```text
$ python -m doctest dt_fail2.py ; echo $?
**********************************************************************
File "dt_fail2.py", line 2, in dt_fail2
Failed example:
    1 + 1
Expected:
    3
Got:
    2
**********************************************************************
1 items had failures:
   1 of   1 in dt_fail2
***Test Failed*** 1 failures.
1
```

Traceback-примеры матчатся по типу исключения и сообщению, а `# doctest: +IGNORE_EXCEPTION_DETAIL` (12.4) ослабляет проверку до одного типа. Там же — таблица директив (`+ELLIPSIS`, `+SKIP`, `+NORMALIZE_WHITESPACE`), здесь повторять её не будем.

⚠️ Границы применимости: doctest — это **документация с гарантией свежести**, а не набор тестов. Он идеален там, где пример и есть спецификация (README, docstring чистых функций), и плох там, где нужны фикстуры, изоляция состояния и проверка побочных эффектов — это уже территория 15.2/15.6.

## 15.6. `pytest` изнутри { #15.6 }

`pytest` — не stdlib (`pip install pytest`), но де-факто стандарт индустрии, и его «магия» — собирать голые функции, показывать умные diff'ы, раздавать фикстуры по имени аргумента — стоит на трёх конкретных механизмах: свой протокол сбора, переписывание assert'ов через импорт-хук и ленивая dependency-injection фикстур.

### Сбор: голые функции, TestCase, parametrize { #15.6-sbor }

Коллектор pytest обходит дерево от rootdir, импортирует файлы `test_*.py`/`*_test.py` и собирает всё, что похоже на тест: голые функции `test_*`, методы `test_*` в классах `Test*` (без `__init__`) — и заодно полноценные `unittest.TestCase` (15.2) в режиме совместимости:

```python
# test_flat.py
import unittest, pytest

def test_bare():                     # голая функция — pytest соберёт,
    assert 1 + 1 == 2                # unittest.discover — нет (15.2)

class TC(unittest.TestCase):         # unittest-стиль — тоже соберёт
    def test_case(self):
        self.assertEqual(2, 2)

@pytest.mark.parametrize("n,expected", [(2, 4), (3, 9), (4, 16)])
def test_square(n, expected):
    assert n ** 2 == expected

@pytest.mark.skip(reason="не готово")
def test_skip(): pass

@pytest.mark.xfail
def test_xfail(): assert False

def test_rich_fail():
    a, b = [1, 2, 3], [1, 2, 4]
    assert a == b
```

```text
$ pytest -v
...
test_flat.py::test_bare PASSED                     [ 12%]
test_flat.py::TC::test_case PASSED                 [ 25%]
test_flat.py::test_square[2-4] PASSED              [ 37%]
test_flat.py::test_square[3-9] PASSED              [ 50%]
test_flat.py::test_square[4-16] PASSED             [ 62%]
test_flat.py::test_skip SKIPPED (не готово)        [ 75%]
test_flat.py::test_xfail XFAIL                     [ 87%]
test_flat.py::test_rich_fail FAILED                [100%]
...
============== 1 failed, 5 passed, 1 skipped, 1 xfailed ==============
```

`parametrize` — это генерация тестов **на этапе сбора**: из одного определения делается три теста с идентификаторами `[2-4]`, `[3-9]`, `[4-16]` (значения параметров в имени). Статусы совпадают с unittest-овскими по смыслу, но есть важная разница в сборе: pytest собирает голые функции, unittest — нет (15.2).

### Assertion rewriting: почему assert pytest'а такой умный { #15.6-assertion-rewriting }

Обычный `assert a == b` в падении говорит только «assert failed» — выражение уже вычислено и потеряно (15.1). pytest перед импортом каждого тестового модуля **переписывает его AST**: каждый `assert` заменяется на код, который вычисляет подвыражения, сохраняет их в служебные переменные `@py_assert*` и в случае падения собирает из них человекочитаемое сообщение. Механику видно напрямую — тот же трансформер, что крутится в импорт-хуке:

```python
import ast, dis
from _pytest.assertion import rewrite

src = b"def f(a, b):\n    assert a == b\n"
tree = ast.parse(src)
rewrite.rewrite_asserts(tree, src, "t.py", None)   # тот же шаг, что делает pytest
code = compile(tree, "t.py", "exec")

body = [c for c in code.co_consts if getattr(c, "co_name", None) == "f"][0]
print([n for n in body.co_names if n.startswith("@")])
# ['@py_builtins', '@pytest_ar']  — служебные модули rewriting'а

dis.dis(body)
#   2           LOAD_FAST                0 (a)
#               LOAD_FAST                1 (b)
#               COMPARE_OP              40 (==)
#               STORE_FAST               2 (@py_assert1)   # ← результат сохранён
#               LOAD_FAST                2 (@py_assert1)
#               POP_JUMP_IF_TRUE ...                        # упали? собираем repr
#               LOAD_GLOBAL              (@pytest_ar)
#               LOAD_ATTR                (_call_reprcompare)
#               ...
```

Служебные имена `@py_builtins` (защищённые встроенные функции) и `@pytest_ar` (`_pytest.assertion.util`) с `@`-префиксом не конфликтуют с вашими именами. Побочный эффект: переписанный assert вычисляет подвыражения **заранее** — в сообщении видно не только «равно или нет», но и что с чем сравнивали:

```text
E   AssertionError: assert [1, 2, 3] == [1, 2, 4]
E     At index 2 diff: 3 != 4
```

Проверки строятся из того же сравнения `==`, что и обычный assert, но с сохранёнными operand'ами. Переписывание можно выключить (`--assert=plain`) — и вы сразу вернётесь к сухим сообщениям из 15.1.

### Фикстуры: dependency injection по имени { #15.6-fikstury }

Фикстура — функция под `@pytest.fixture`, которую pytest вызывает сам, когда тест объявляет её имя параметром. Это DI-контейнер: тест запрашивает зависимости по имени, pytest резолвит их рекурсивно (фикстура может зависеть от фикстуры), кэширует результат в рамках scope и гарантированно выполняет teardown после.

```python
import pytest
events = []

@pytest.fixture
def one():
    events.append("setup:one"); yield 1
    events.append("teardown:one")

@pytest.fixture
def two(one):                       # зависит от one
    events.append("setup:two"); yield 2
    events.append("teardown:two")

def test_both(two, one):
    print("EVENTS :", events)
```

```text
EVENTS : ['setup:one', 'setup:two']        # setup по зависимостям
# после теста: ['setup:one', 'setup:two', 'teardown:two', 'teardown:one']
#                                            ← teardown в ОБРАТНОМ порядке (LIFO)
```

Три факта механики. **Setup идёт по цепочке зависимостей** (`one` прежде `two`), независимо от порядка параметров теста. **Teardown — стек в обратном порядке** (`two` прежде `one`): код после `yield` исполняется как финализаторы в `ExitStack` (2.4). **Scope по умолчанию — `"function"`**: на следующий тест фикстура пересоздаётся целиком; `"module"`/`"session"` кэшируют результат между тестами — и тогда порядок teardown'ов между тестами становится важным наблюдаемым поведением.

`yield`-фикстура — это `@contextmanager` (2.3) в миниатюре: код до `yield` — setup, после — teardown. Если setup упал, teardown не вызывается; если упал teardown — pytest сообщит об ошибке фикстуры отдельно от результата теста.

### Плагины и кэш { #15.6-plaginy }

Вся внешняя логика pytest — хуки. Заголовок сессии показывает, что реально подгружено (в нашем прогоне выше: `plugins: time-machine-3.5.1` — плагин time-machine объявил себя через entry points и загрузился **автоматически**, без конфига). Система хуков — `pluggy`, та же библиотека, что питает хуки в setuptools; точка расширения — entry points группы `pytest.plugins` (7.9) или `conftest.py`. Кэш сессии — каталог `.pytest_cache` (последние провалы для `--lf`, nodeids); его можно отключить флагом `-p no:cacheprovider` — `-p` загружает/блокирует плагины по имени, и кэш — тоже плагин.

⚠️ Порядок импорта при сборе не случайность, а контракты: `conftest.py`-файлы импортируются до тестовых модулей, а сам pytest предлагает три import-режима (`--import-mode=prepend|append|importlib`, дефолт `prepend`). В `prepend` каталог теста вставляется в `sys.path[0]` — отсюда классические «два файла с одинаковым именем не собираются вместе»: pytest видит один и тот же модуль. Лечится `__init__.py`-пакетами или `--import-mode=importlib`.
## 15.7. `coverage.py`: измерение покрытия { #15.7 }

Coverage отвечает на вопрос «какие строки исполнились», и это тоже интерпретаторный крючок: чтобы узнать, на каких строках побежал код, нужно получать line-события трейсера (15.8). `coverage.py` — эталонная реализация, под капотом которой два переключаемых движка (ниже).

```python
# mod.py
def classify(n):
    if n % 2 == 0:
        return "even"
    return "odd"

def dead():
    return "никогда"

def skip_me():  # pragma: no cover
    return "исключено"
```

```text
$ coverage run use.py          # use.py: from mod import classify; print(classify(4))
even
$ coverage report -m
Name     Stmts   Miss  Cover   Missing
--------------------------------------
mod.py       6      2    67%   4, 7
use.py       2      0   100%
--------------------------------------
TOTAL        8      2    75%
```

Читается мгновенно: не исполнены строка 4 (`return "even"` — условие было ложным) и строка 7 (`dead()`), а `skip_me` целиком исключён директивой `# pragma: no cover` — потому у него нет строки в отчёте. `Stmts` считает исполняемые statements, а не все строки файла.

### Ветвное покрытие { #15.7-vetvnoe-pokrytie }

Строчное покрытие обманчиво: строка `if n % 2 == 0:` исполнилась — но **оба ли** исхода условия проверены? Флаг `--branch` переводит coverage на arc-модель: единица измерения — не строка, а **переход** (дуга) между строками, как в graph-представлении кода:

```text
$ coverage run --branch use.py && coverage report -m
Name     Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------
mod.py       6      2      2      1    62%   4, 7
use.py       2      0      0      0   100%
----------------------------------------------------
TOTAL        8      2      2      1    70%
```

Появились колонки `Branch` (всего дуг) и `BrPart` (частично покрытые ветвления) — покрытие стало ниже (62% против 67%) при том же коде, потому что теперь честно учитывается непроверенный исход `if`. Для тестов, ориентированных на «100%», имеет смысл именно ветвное — строчное достигается почти случайно.

### Внутри: SQLite и движки трассировки { #15.7-dvizhki }

Результат `coverage run` — файл `.coverage`, и это обычная SQLite-база:

```python
import sqlite3
con = sqlite3.connect(".coverage")
print(sorted(r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")))
# ['arc', 'context', 'coverage_schema', 'file', 'line_bits', 'meta', 'tracer']
```

Ключевая таблица — `line_bits`: номера исполненных строк, упакованные в блобы схемой RLE (пары «сколько строк пропустить — сколько закрасить»); при `--branch` рядом лежит `arc` — пары переходов. `context` хранит контексты (`coverage run --context=название` — размечать замеры, например по тест-группам), `meta` — версию формата. `coverage combine` сливает параллельные `.coverage.<хост>.<pid>`-файлы в один — потому CI-джобы пишут в отдельные файлы, а не в общий.

Движки трассировки переключаются переменной окружения `COVERAGE_CORE`:

- `ctrace` (по умолчанию на 3.12) — C-трассировщик `CTracer`, собственной механикой повторяющий `sys.settrace` (15.8), но целиком в C: события line/call/return снимаются с минимальной питоновской обвязки;
- `sysmon` — `sys.monitoring` (PEP 669, 15.9): `COVERAGE_CORE=sysmon coverage run …`; неверное значение бракуется сразу: `Unknown core value: 'bogus'`.

⚠️ Движки дают одинаковые данные, но не идентичную скорость: на нашем workload'е ctrace замедлил запуск в 4.3 раза, sysmon — в 3.4 (бенчмарк в конце части). Порог перехода на sysmon — 3.12+ и тип нагрузки: чем больше line-событий, тем заметнее преимущество monitoring-механики.

## 15.8. `sys.settrace`/`sys.setprofile`: крючки отладчика и профайлера { #15.8 }

`pdb` (1.16), `bdb` (11.30), `profile` (11.30) и line-события coverage (15.7) сидят на одном и том же крючке — `sys.settrace`. Это функция-трейсер, которую интерпретатор вызывает при трёх классах событий:

| Событие | Когда | Кого вызывают | arg |
|---|---|---|---|
| `call` | начался новый кадр | **глобальный** трейсер | `None` |
| `line` | следующая строка кода | **локальный** трейсер кадра | `None` |
| `return` | кадр завершается | локальный трейсер | возвращаемое значение |
| `exception` | исключение в кадре | локальный трейсер | `(exc, value, tb)` |
| `opcode` | следующая инструкция | локальный трейсер | `None` |

Ключевая слово — **двухуровневость**: глобальный трейсер получает только `call` и своим **возвращаемым значением** назначает локальный трейсер для кадра:

```python
import sys

events = []

def tracer(frame, event, arg):
    if frame.f_code.co_name == "work":
        events.append(event)
        return tracer          # ← возвращаем локальный трейсер
    return tracer

def work():
    a = 1
    b = 2
    return a + b

sys.settrace(tracer)
work()
sys.settrace(None)
print(events)
# ['call', 'line', 'line', 'line', 'return']
```

Три `line`-события — по одному на присваивание и на `return`. Именно на этом уровне живёт отладчик: на `line` — проверять breakpoints и отдавать управление пользователю; на `call`/`return` — строить стек-визуализацию. Цена — тоже здесь: событие на каждую строку питоновского кода, поэтому трассировка «всего подряд» замедляет программу на порядок (бенчмарк в конце части) — 1.16 недаром предупреждает, что `settrace` медленный.

`sys.setprofile` — парный, но иной крючок: событие на **границах** функций (`call`/`return`) и на границах с C (`c_call`/`c_return`/`c_raise`), без line-событий:

```python
profevents = []
def prof(frame, event, arg):
    if event in ("c_call", "c_return"):
        profevents.append(event)

sys.setprofile(prof)
sum([1, 2, 3])
sys.setprofile(None)
print(profevents)
# ['c_call', 'c_return']
```

Экономнее на порядки — потому профайлеры (`cProfile`, 11.30) используют именно `setprofile`, а отладчики — `settrace`.

### Что изменилось в 3.12: settrace теперь эмуляция { #15.8-izmeneniya-3-12 }

В 3.12 `settrace`/`setprofile` внутренне **переписаны поверх `sys.monitoring`** (15.9): это уже не прямой механизм eval loop, а адаптер (в исходниках CPython — `Python/legacy_tracing.c`). Появились поведенческие отличия, каждое из которых проверено на 3.12.14 и 3.13.5:

- **`return None` из локального трейсера больше не гасит трассировку кадра.** В документации до 3.11 было: «локальный трейсер должен вернуть себя… или `None`, чтобы отключить трассировку в этой области». В 3.12 формулировка заменена на «возвращаемое значение задаёт новый локальный трейсер» — и на практике `None` просто сохраняет текущий:

  ```python
  def local(frame, event, arg):
      events.append(event)
      if event == "line":
          return None            # раньше: отключить line-события
      return local

  sys.settrace(lambda f, e, a: local)
  work()                          # всё равно ['line', 'line', 'line', 'return']
  ```

- **Отключить line-события теперь нужно через `frame.f_trace_lines = False`** — и это работает как заявлено: line-события кадра гаснут, `return` приходит:

  ```python
  def local2(frame, event, arg):
      events.append(event)
      if frame.f_lineno == frame.f_code.co_firstlineno + 1:
          frame.f_trace_lines = False
      return local2
  # ['line', 'return']
  ```

- **Исключение в трейсере прокидывается в трассируемый код.** Документация по-прежнему обещает «ошибка в трейсере снимает его, как `settrace(None)`» — трейсер действительно снимается, но исключение в 3.12+ больше не глотается: `RuntimeError("boom")` из трейсера доезжает до исполняемого кода и обрывает его. Отладчику теперь обязательно оборачивать собственные колбэки в `try/except`.

- **`opcode`-события через `frame.f_trace_opcodes = True`: на 3.12 не приходят** (эмуляция не раздаёт opcode-события из `settrace`-адаптера), на 3.13.5 — приходят. Если нужны инструкции — надёжнее `sys.monitoring` с `INSTRUCTION` (15.9).

⚠️ Код, который трассирует другие процессы/потоки через `settrace` и опирается на старые тонкости (гашение через `None`, тихие исключения), после миграции на 3.12+ меняет поведение молча — проверяйте трейсеры тестами (благо для этого теперь есть `sys.monitoring`-детект: `sys.gettrace()` возвращает трейсер, но события могут не совпадать со старой семантикой).

Параноидальное дополнение из 11.30 остаётся в силе: если ваш код исполняет чужой Python и разрешает `breakpoint()`/`sys.settrace` — вы дали чужому коду полный контроль над выполнением. Песочницы перезаписывают `sys.settrace` первым делом.

## 15.9. `sys.monitoring` (PEP 669, 3.12+): один API для отладчиков, профайлеров и coverage { #15.9 }

PEP 669 — главный интерпретаторный подарок тестово-отладочной экосистеме в 3.12. Идея: вместо двух старых крючков (`settrace` для отладчиков, `setprofile` для профайлеров) с их ценой на каждое событие — единый API `sys.monitoring`, где инструмент **регистрируется** под фиксированным ID и подписывается только на нужные события. Цена неподписанных событий — ноль: компилятор генерирует соответствующие проверки только при активных инструментах.

Инструментальные ID фиксированы стандартом — одновременно могут работать несколько инструментов (у `settrace` был один глобальный трейсер):

```python
import sys
mon = sys.monitoring
print(mon.DEBUGGER_ID, mon.COVERAGE_ID, mon.PROFILER_ID, mon.OPTIMIZER_ID)
# 0 1 2 5
```

(`OPTIMIZER_ID=5` зарезервирован — в 3.13 на него встал экспериментальный tier-2 оптимизатор из 13.5.)

Набор событий (17 на 3.12):

| Событие | Что это |
|---|---|
| `PY_START` / `PY_RETURN` | начало и обычный конец вызова python-функции |
| `PY_RESUME` / `PY_YIELD` / `PY_UNWIND` / `PY_THROW` | возобновление корутины, выдача из генератора, выход по исключению, бросок в корутину (4.8) |
| `RAISE` / `RERAISE` / `EXCEPTION_HANDLED` / `STOP_ITERATION` | механика исключений |
| `CALL` / `C_RETURN` / `C_RAISE` | вызовы встроенных/C-функций |
| `LINE` / `INSTRUCTION` / `JUMP` / `BRANCH` | строка, инструкция, безусловный и условный переход |

Минимальный рабочий инструмент — считаем вызовы функции:

```python
import sys

mon = sys.monitoring
calls = []

def cb(code, instruction_offset):
    if code.co_name == "hot":
        calls.append(code.co_name)

mon.use_tool_id(mon.PROFILER_ID, "book-demo")     # занять ID 2
mon.set_events(mon.PROFILER_ID, mon.events.PY_START)   # подписка
mon.register_callback(mon.PROFILER_ID, mon.events.PY_START, cb)

def hot(): return 42
for _ in range(3):
    hot()

mon.register_callback(mon.PROFILER_ID, mon.events.PY_START, None)  # снять колбэк
mon.set_events(mon.PROFILER_ID, 0)                # снять подписку
mon.free_tool_id(mon.PROFILER_ID)                 # освободить ID
print(calls.count("hot"), mon.get_tool(mon.PROFILER_ID))
# 3 None
```

Протокол — пары «подписка → колбэк» на каждый тип события; `get_tool(id)` подтверждает, что после `free_tool_id` слот свободен. В реальных инструментах в колбэках сразу фильтруют по `code.co_filename` — событие приходит на **каждый** вызов любой функции, и тривиальный счётчик без фильтра сам станет просадкой.

### Локальные события: подписка на один код-объект { #15.9-lokalnye-sobytiya }

`set_events` действует глобально, а `set_local_events` — на **один** код-объект (8.7). Это API для точечного инструментария: «трассируй только эту функцию» без цены на весь процесс:

```python
mon.use_tool_id(mon.COVERAGE_ID, "local-demo")
code_obj = compile("def h(x):\n    return x * 2\n\nresult = h(21)\n", "<t>", "exec")
mon.set_local_events(mon.COVERAGE_ID, code_obj, mon.events.CALL)

seen = []
def cb_call(*args):                    # CALL передаёт 4 аргумента
    seen.append(args)

mon.register_callback(mon.COVERAGE_ID, mon.events.CALL, cb_call)
g = {}
exec(code_obj, g)
mon.set_local_events(mon.COVERAGE_ID, code_obj, 0)
mon.free_tool_id(mon.COVERAGE_ID)
print(len(seen), g["result"])
# 1 42      — один CALL (вызов h), глобальные события не взводились
print(len(seen[0]))
# 4         — (code, instruction_offset, callable, arg0)
```

Обратите внимание на арность: у большинства событий колбэк — `(code, instruction_offset)`, но `CALL` дополнительно передаёт callable и первый аргумент (4 аргумента), `RAISE` — исключение. Главное — **локальные события работают автономно**: глобальная подписка для них не нужна (в прогоне выше `get_events` вернул 0).

Кто уже сидит на PEP 669: coverage.py — опционально через `COVERAGE_CORE=sysmon` (15.7), фреймворки отладчиков (`debugpy` и наследники pdb) мигрируют постепенно, а в 3.14 на этот же API легла remote-отладка (PEP 768 — подключение отладчика к работающему процессу; его CLI-ручка `-X disable_remote_debug` разобрана в 10.3). Старый `settrace` (15.8) теперь — обёртка над этим же механизмом, так что у интерпретатора остался один системный крючок вместо трёх.

## 15.10. Тесты самого CPython: `python -m test` { #15.10 }

Внутри каждого CPython лежит `test` — пакет с ~сотнями тестовых модулей, и это не «какие-то тесты»: для альтернативных реализаций они играют роль исполняемой спецификации языка (14.1) — «прошёл test suite» — главное заявление о совместимости. Запускаются они тем же интерпретатором через regrtest (regression test runner):

```text
$ python -m test test_support
== Tests result: SUCCESS ==

1 test OK.

Total duration: 1.1 sec
Total tests: run=50 skipped=3
Total test files: run=1/1
Result: SUCCESS
```

Тот же runpy-механизм, что и у `-m unittest` (15.2): `test` — обычный пакет, `__main__` которого вызывает `test.libregrtest`. Полезные ручки (из `python -m test --help`):

| Флаг | Что делает |
|---|---|
| `-j N` | параллельный запуск в N процессов — suite большой, так и в CPython CI гоняют |
| `-m ШАБЛОН` | фильтр тестов по имени (`-m test_dict` → только тесты с dict в имени) |
| `-u all` / `-u сетевые` | какие **ресурсы** разрешить: сеть, аудио, большие файлы; по умолчанию часть выключена |
| `-r`, `--randseed=N` | случайный порядок тестов (ловля скрытых зависимостей между тестами) |
| `--list-tests` | не запускать, только показать, что будет запускаться |
| `-f`, `-M`, `-T`, `-p` | список тестов из файла, memorylimit, покрытие trace-модулем, альтернативный интерпретатор для подпроцессов |

### Охота на рефлаки: debug-сборка { #15.10-refleaki }

Самый интересный режим regrtest — `-R` (hunt reference leaks): интерпретатор гоняет каждый тест несколько раз подряд и сравнивает суммарный refcount объектов между прогонами. Утечка рефлаков — рост счётчика от прогона к прогону — сигнал «модуль держит объекты дольше, чем нужно». Механика требует `sys.gettotalrefcount`, который существует **только в debug-сборках** CPython (`./configure --with-pydebug`):

```python
import sys
print(hasattr(sys, "gettotalrefcount"))
# False  — релизная сборка (как в стандартных дистрибутивах)
```

На debug-сборке `-R 3:3` означает «три прогрева и три контрольных прогона»: сначала несколько раз подряд исполняется тест (сборка мусора и прогрев кэшей — 8.6), затем замеряется `sys.gettotalrefcount()` после каждого прогона; рост счётчика от прогона к прогону печатается как leaked references, и regrtest возвращает провал. Отсюда же термин «refleak test» в changelog'ах CPython: правки перед релизом прогоняют именно на debug-сборке с `-R`, потому что утечка рефлаков в stdlib — это утечка памяти во всех приложениях на CPython.

Второй слой — `test.support` (и подмодули `os_helper`, `import_helper`, `script_helper`, `warnings_helper`): утилиты, которыми пользуются тесты CPython, доступные и вам:

```python
from test import support, os_helper
print(hasattr(support, "captured_stdout"),      # перехват stdout как контекст-менеджер
      hasattr(support, "run_in_subinterp"),     # код в суб-интерпретаторе
      hasattr(os_helper, "temp_dir"))           # временные каталоги с уборкой
# True True True
```

⚠️ `test.support` — приватная территория: API меняется между версиями без предупреждений. Для продуктовых тестов — `tempfile`, `contextlib.redirect_stdout` (2.7) и `subprocess`; `test.support` — для тестов, живущих внутри CPython, или инструментов, осознанно привязанных к версии интерпретатора.

## 15.11. Тестовые режимы интерпретатора: шпаргалка { #15.11 }

Книга уже разобрала по одному все диагностические ручки CPython (10.1–10.3, 11.6, 9.1, 4.3, 10.8). Здесь они собраны вместе под тем углом, ради которого их чаще всего и включают: **поймать проблему в тестах/CI, пока она не дошла до продакшена**.

| Ручка | Что даёт в тестах | Подробно |
|---|---|---|
| `-X dev` / `PYTHONDEVMODE` | «dev-режим»: видны `DeprecationWarning` и `ResourceWarning` (`unclosed file` и соседи), включается asyncio-debug, строже фильтры предупреждений | 10.2 |
| `-W error::DeprecationWarning` | упреждающий провал тестов на устаревших вызовах — deprecated API превращается в ошибку | 11.6 |
| `-X warn_default_encoding` / `PYTHONWARNDEFAULTENCODING` | `EncodingWarning` на вызовах `open()` без явной кодировки — перед переходом на `-X utf8`-стратегию | 9.1 |
| `PYTHONHASHSEED=0` | воспроизводимость: хэши (и порядок множеств/dict-ключей, зависящий от них) одинаковы между прогонами | 10.3 |
| `PYTHONASYNCIODEBUG` / `asyncio.run(debug=True)` | лог «Executing … took 0.200 seconds» по «медленным» колбэкам, диагностика незавершённых корутин | 4.3 |
| `-X faulthandler` / `faulthandler.enable()` | на segfault — не молчаливый «Segmentation fault», а `Fatal Python error` с питоновским стеком | 10.8 |
| `PYTHONMALLOC=debug` | отлов ошибок работы с памятью в C-расширениях (запись за границу буфера, use-after-free) | 10.3 |
| `-X utf8` / `PYTHONUTF8` | фиксированная кодировка IO в CI — тесты не зависят от локали машины | 10.3 |

Пара живых прогонов, чтобы ручки перестали быть аббревиатурами. `PYTHONHASHSEED` управляет рандомизацией хэшей str/bytes (SipHash с рандомным ключом — защитой от hash-flooding):

```text
$ PYTHONHASHSEED=0 python -c "print(hash('спам'))"
-4792541503203960822
$ PYTHONHASHSEED=0 python -c "print(hash('спам'))"
-4792541503203960822          # то же самое — детерминизм
$ PYTHONHASHSEED=random python -c "print(hash('спам'))"
-7698640846738831484          # каждый запуск — новый ключ
```

`-X dev` делает видимой то, что по умолчанию спит:

```text
$ python -c "open('/tmp/z.txt', 'w')"          # файл забыли закрыть — тишина
$ python -X dev -c "open('/tmp/z.txt', 'w')"
<string>:1: ResourceWarning: unclosed file <_io.TextIOWrapper name='/tmp/z.txt' mode='w' encoding='UTF-8'>
```

А `-X faulthandler` превращает segfault из «rc=-11 и ноль информации» в трейсбек:

```text
$ python -c "import ctypes; ctypes.string_at(0)"
Segmentation fault
$ python -X faulthandler -c "import ctypes; ctypes.string_at(0)"
Fatal Python error: Segmentation fault
...
Current thread 0x00007f… (most recent call first):
  File "<string>", line 1 in <module>
```

Для CI типовой сборкой становится комбинация:

```bash
PYTHONHASHSEED=0 PYTHONDEVMODE=1 \
PYTHONWARNDEFAULTENCODING=1 \
python -X faulthandler -W error::DeprecationWarning -m pytest tests/
```

Мораль шпаргалки: интерпретатор уже содержит датчики почти всех классов проблем — невидимых предупреждений, локальной зависимости, порчи памяти, «тихих» падений. Тесты, запущенные с включёнными датчиками, ловят их за один прогон; продакшн — за инцидент.

### Бенчмарки к Части XV { #15.11-benchmarki }

Замеры на CPython 3.12.14 (Linux, x86_64); абсолютные числа зависят от машины, отношения — устойчивы.

**1. Цена трассировки вызовов: `sys.monitoring` против старых крючков.**
Считаем вызовы пустой функции 200 000 раз четырьмя способами: без трассировки, `sys.monitoring` (PY_START), `sys.setprofile`, `sys.settrace`:

```text
none         0.0225 с   — baseline
monitoring   0.0447 с   — 2.0×  к baseline
setprofile   0.0710 с   — 3.2×
settrace     0.0776 с   — 3.4×
```

Уже на голых call-событиях monitoring быстрее обоих старых крючков; разрыв растёт на line-событиях (замер 2). Важная деталь методики: у monitoring каждый вызов — python-колбэк на `PY_START`; если колбэк тяжёлый, вы тормозите сами.

**2. LINE-события: где выгода monitoring становится видимой.**
~2 003 000 line-событий (1000 вызовов функции со 1000-итерационным циклом): baseline 0.040 с, `sys.monitoring` (LINE) 0.283 с ≈ **7.1×**, `sys.settrace` (line через локальный трейсер) 0.420 с ≈ **10.6×**. Отношение monitoring/settrace ≈ 1.5× — не «порядки», но на горячей трассировке это разница между «терпимо» и «мешает». Напоминание из 8.4: точную экономию меряйте на своём workload.

**3. Цена вызова мока.**
300 000 вызовов `f(i)` на обычной функции и на моках:

```text
plain       0.0338 с   — baseline
Mock        1.8420 с   — 54×
MagicMock   1.8671 с   — 55×
autospec    2.7501 с   — 81×
```

Каждый вызов мока — питоновский `__call__` с записью `call_args`, проверкой `side_effect` и наложением `spec`. Отсюда практическое правило: в тестах производительности и в тестах с миллионами итераций моки не мокают, а считают.

**4. Цена coverage-прогона.**
Один и тот же workload (функция с ветвлениями, ~0.05 с чистого прогона) под `coverage run` с разными движками:

```text
plain                0.046 с
coverage (ctrace)    0.196 с   — 4.3×
coverage (sysmon)    0.157 с   — 3.4×
```

Покрытие — это трассировка всего кода, поэтому замедление в разы — норма; экономия sysmon (15.7, 15.9) на 3.12+ уже заметна и растёт на ветвистом коде.

**5. Цена входа/выхода в «замороженное время».**
300 циклов входа/выхода из контекста заморозки:

```text
freezegun      0.738 с   — чистый Python, патч множества модулей
time-machine   0.0005 с  — C-расширение, патч C-уровня   ≈ 1500×
```

Для теста, замораживающего время один раз, безразлично; для фикстуры-автозамены времени на каждый тест (function-scope, сотни тестов) — разница между минутами и мгновением (15.4).


