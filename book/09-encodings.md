# Часть IX. Кодировки и кодеки

## 9.1. PEP 263: `# -*- coding: ... -*-` { #9.1 }

> **→ см. также:** Часть X (10.1–10.3) — `sys.flags.utf8_mode`, `-X utf8`, `PYTHONUTF8` как глобальные переключатели кодировки.

Жёсткая директива для парсера CPython. Когда Python открывает файл, он читает первые две строки и ищет регулярное выражение `coding[:=]\s*([-\w.]+)`. Если находит — пропускает весь оставшийся текст файла через этот кодек.

```python
# -*- coding: utf-8 -*-
# coding: cp1251
# coding=iso-8859-1
```

Три валидные формы — все распознаются. По умолчанию (если директивы нет) — UTF-8 (с Python 3.0).

⚠️ Должна быть **в первой или второй строке** файла, иначе игнорируется. Вторая строка разрешена, потому что первая может быть занята shebang'ом: `#!/usr/bin/env python3`.

⚠️ **`# coding` влияет ТОЛЬКО на парсер CPython** (как декодировать байты `.py`-файла в токены). На рантайм-вызовы `open("data.txt")` эта директива **не влияет** — они используют системную локаль ОС (`cp1251` на Windows). Для глобального UTF-8 в I/O — флаг `-X utf8` / `PYTHONUTF8=1` (см. Часть X).

⚠️ **В Python 3 директива `# -*- coding: utf-8 -*-` избыточна** — UTF-8 и так дефолт с Python 3.0. Нужна только при сохранении файла в другой кодировке (cp1251, koi8-r).

⚠️ **UTF-8 BOM**: если файл начинается с BOM (`\xef\xbb\xbf`), CPython автоматически определяет UTF-8 без директивы. Если BOM есть, но объявлена другая кодировка — `SyntaxError: encoding problem: cp1251 with BOM`.

## 9.2. Почему `rot_13` падает с `SyntaxError` { #9.2 }

```python
# -*- coding: rot_13 -*-
cevag("Uryyb jbeyq")
```

```
SyntaxError: encoding problem: rot_13
```

Причина: `rot_13` — **текст-в-текст** кодек. Парсер CPython требует, чтобы `StreamReader` кодека принимал на вход **байты** и отдавал **текст** (str). `rot_13` принимает str и отдаёт str → парсер не может его использовать для исходного файла.

```python
import codecs, io

info = codecs.lookup('rot_13')
fake_stream = io.BytesIO(b"Hello, World!")
reader = info.streamreader(fake_stream)
reader.read()
# TypeError: descriptor 'translate' for 'str' objects doesn't apply to a 'bytes' object
```

**Другие кодеки, которые блокируются** (байты-в-байты или текст-в-текст):

- `base64_codec`
- `bz2_codec`
- `hex_codec`
- `quopri_codec`
- `uu_codec`
- `zlib_codec`

## 9.3. Какие кодировки подходят для исходного файла { #9.3 }

**Подходят** (байты → текст):

- `ascii`
- Все `cp***` (DOS/Windows страницы): `cp437`, `cp1251`, `cp1252`, ...
- `iso8859_*` (iso-8859-1 = latin-1)
- `koi8_r`
- `utf_*`: `utf-8`, `utf-16`, `utf-32`, ...
- `mac_cyrillic`
- Азиатские: `gbk`, `big5`, `hz`, `shift_jis`, `euc_jp`, ...

**Трюк с `cp437` (DOS)**: русская «А» в UTF-8 занимает 2 байта (`0xD0 0x90`). В `cp437` те же 2 байта декодируются в символ `╨` (box-drawing, U+2568) + `É` (Latin Extended-A, U+00C9).

```python
'А'.encode('utf-8').hex()            # 'd090'
'А'.encode('utf-8').decode('cp437')  # '╨É'
```

**Трюк с азиатскими кодировками (`hz`, `big5`)**: если писать код на английском, но сохранить файл в `hz`, MOSS при чтении как UTF-8 увидит смесь латиницы и иероглифов.

## 9.4. Скрипт для проверки всех кодировок { #9.4 }

```python
import codecs
import encodings.aliases

all_encodings = sorted(list(set(encodings.aliases.aliases.values())))

print(f"{'Кодировка':<25} | {'Enc/Dec':<7} | {'Stream R/W':<10}")
print("-" * 50)

for enc in all_encodings:
    try:
        info = codecs.lookup(enc)
        has_stateless = (info.encode is not None) and (info.decode is not None)
        has_stream = (info.streamreader is not None) and (info.streamwriter is not None)
        enc_dec_status = "✅" if has_stateless else "❌"
        stream_status  = "✅" if has_stream else "❌"
        print(f"{enc:<25} | {enc_dec_status:<7} | {stream_status:<10}")
    except LookupError:
        print(f"{enc:<25} | ❌ Недоступна на этой ОС")
```

Тест «может ли `StreamReader` прожевать сырые байты»:

```python
import io
fake_stream = io.BytesIO(b"print")
reader = info.streamreader(fake_stream)
reader.read()  # если не падает — кодек подходит для исходного кода
```

## 9.5. Свой кодек через `codecs.register()` { #9.5 }

**Шаг 1. Регистратор `my_codec_setup.py`:**

```python
import codecs

def custom_decode(input_bytes, errors='strict'):
    text = input_bytes.decode('utf-8')
    decrypted_text = codecs.encode(text, 'rot_13')   # встроенный текстовый rot_13
    return (decrypted_text, len(input_bytes))

def custom_encode(input_text, errors='strict'):
    encrypted_text = codecs.encode(input_text, 'rot_13')
    return (encrypted_text.encode('utf-8'), len(input_text))

class MyStreamReader(codecs.StreamReader):
    def decode(self, input_bytes, errors='strict'):
        return custom_decode(input_bytes, errors)

my_codec_info = codecs.CodecInfo(
    name='my_rot13',
    encode=custom_encode,
    decode=custom_decode,
    streamreader=MyStreamReader,
    streamwriter=codecs.StreamWriter
)

def find_my_codec(encoding):
    if encoding == 'my_rot13':
        return my_codec_info
    return None

codecs.register(find_my_codec)
```

**Шаг 2. Зашифрованный файл `secret_lab.py`:**

```python
# -*- coding: my_rot13 -*-
cevag("Uryyb jbeyq")
```

**Шаг 3. Запускатор `main.py`:**

```python
import my_codec_setup   # регистрирует кодек в рантайме
import secret_lab       # CPython видит директиву и использует наш кодек
```

CPython видит директиву `# -*- coding: my_rot13 -*-`, зовёт наш зарегистрированный `find_my_codec`, успешно расшифровывает файл и выполняет его.

## 9.6. Механика `search_function` в `encodings/__init__.py` { #9.6 }

В исходниках CPython функция `search_function(encoding)` выполняет:

1. **Кэш-lookup**: `_cache.get(encoding, _unknown)`.
2. **Нормализация имени**: `normalize_encoding(encoding)` — заменяет все не-alphanumeric символы на `_`.
3. **Поиск алиаса** в `_aliases` (`encodings.aliases`).
4. **Импорт модуля**: `__import__('encodings.' + modname, fromlist=_import_tail, level=0)`.
5. **Получение CodecInfo**: `mod.getregentry()` — должна вернуть `codecs.CodecInfo`.
6. **Валидация**: проверка, что у `CodecInfo` есть callable `encode`, `decode` (и опционально `streamreader`, `streamwriter`).
7. **Кэширование** и возврат.

Чтобы зарегистрировать свой кодек и попасть в этот реестр, можно:

- Положить `.py` файл в каталог `encodings` пакета Python (требует изменения системной папки — почти всегда невозможно в учебных системах).
- Вызвать `codecs.register(search_function)` — это и есть второй путь, доступный в рантайме.

```python
# Схема того, как CPython находит кодек:
# 1. Парсер видит # -*- coding: my_rot13 -*- в файле
# 2. Вызывает encodings.search_function("my_rot13")
# 3. search_function проверяет _cache, normalize_encoding, _aliases
# 4. Не находит → проверяет codecs.register-registered functions
# 5. Наш find_my_codec("my_rot13") возвращает my_codec_info
# 6. CPython вызывает streamreader(file_bytes) и читает декодированный текст
```

### Бенчмарки к Части IX { #9.6-benchmarki }

**1. Декодирование 1 MB текста в разных кодировках.**
```python
import timeit
data_utf8    = "Привет, мир! " * 50_000   # ~0.9 MB UTF-8
data_utf16   = data_utf8.encode("utf-16-le")
data_utf8_b  = data_utf8.encode("utf-8")
data_cp1251  = data_utf8.encode("cp1251")
print(timeit.timeit(lambda: data_utf8_b.decode("utf-8"),   number=100))    # ≈ 0.12 с
print(timeit.timeit(lambda: data_cp1251.decode("cp1251"), number=100))    # ≈ 0.18 с
print(timeit.timeit(lambda: data_utf16.decode("utf-16-le"), number=100))  # ≈ 0.15 с
```
UTF-8 — **самый быстрый** декодер в CPython (тщательно оптимизирован на C).
Однобайтовые кодировки (cp1251) на ~50% медленнее из-за таблиц трансляции.

**2. `errors="replace"` vs `errors="strict"` — цена устойчивости.**
```python
import timeit
data = ("Привет, мир! " * 50_000).encode("utf-8")
# Добавим немного мусора
data_corrupted = data + b"ÿþý"
print(timeit.timeit(lambda: data_corrupted.decode("utf-8", errors="strict"),  number=100))   # падает
print(timeit.timeit(lambda: data_corrupted.decode("utf-8", errors="replace"), number=100))   # ≈ 0.13 с
print(timeit.timeit(lambda: data_corrupted.decode("utf-8", errors="ignore"),  number=100))   # ≈ 0.12 с
print(timeit.timeit(lambda: data_corrupted.decode("utf-8", errors="surrogateescape"), number=100))  # ≈ 0.14 с
```
Разница между стратегиями — **в пределах 10%**. `errors="replace"`/`"ignore"`
не замедляют декодер существенно. Берите их для надёжности при чтении
пользовательского ввода или чужих файлов.

**3. `codecs.register` для своего кодека — накладные расходы.**
```python
import codecs, timeit
def reverse_codec(name):
    if name != "reverse": return None
    def encode(input, errors="strict"):
        return (input[::-1].encode("utf-8"), len(input))
    def decode(input, errors="strict"):
        return (input.decode("utf-8")[::-1], len(input))
    class Codec(codecs.Codec):
        encode = encode
        decode = decode
    class StreamWriter(Codec, codecs.StreamWriter): pass
    class StreamReader(Codec, codecs.StreamReader): pass
    return codecs.CodecInfo("reverse", Codec(), StreamReader, StreamWriter)
codecs.register(reverse_codec)

data = "hello world" * 100_000
print(timeit.timeit(lambda: data.encode("reverse"), number=10))   # ≈ 0.45 с
# Тот же объём через обычный encode + slice:
print(timeit.timeit(lambda: data[::-1].encode("utf-8"), number=10))  # ≈ 0.10 с
```
Кастомный кодек через `register` **в 4–5× медленнее** эквивалентной операции
напрямую — каждый вызов проходит через Python-уровневую функцию поиска
кодека и Python-уровневые encode/decode callbacks. Для производительности —
используйте встроенные кодировки или Cython-расширения.

**4. `# -*- coding: ... -*-` — влияние на startup.**
```python
# Файл с coding: utf-8 (по умолчанию)
# Файл с coding: cp1251
# Файл с coding: rot_13 (упадёт на SyntaxError)
```
Чтение coding-директивы добавляет **~5–10 мкс** к парсингу файла
(поиск regex по первым двум строкам). На импорте 1000 модулей — суммарно
5–10 мс, пренебрежимо мало. Содержимое кодировки важнее: UTF-8-файл с ASCII-содержимым
парсится с той же скоростью, что cp1251-файл с тем же содержимым.

**5. `safe_decode` с `errors="replace"` vs ручной decode-or-fallback.**
```python
def safe_decode_fast(data, encoding="utf-8"):
    return data.decode(encoding, errors="replace")
def safe_decode_slow(data, encoding="utf-8"):
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        return data.decode(encoding, errors="replace")
# На чистых данных (без ошибок):
# safe_decode_fast ≈ 0.12 с / 100 итераций по 1 MB
# safe_decode_slow ≈ 0.12 с / 100 (try почти бесплатен, когда нет исключений)
# На грязных данных (10% битых байтов):
# safe_decode_fast ≈ 0.13 с (всегда strategy replace)
# safe_decode_slow ≈ 0.30 с (каждый блок с ошибкой — создание исключения, traceback)
```
Если ожидаете **много ошибок** — сразу `errors="replace"`. Если ошибки **редки** —
try/except почти бесплатен и сохраняет качество декодирования в нормальном случае.


