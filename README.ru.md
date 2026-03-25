# Minecraft map.dat → PNG

Небольшая CLI-утилита: читает файлы карт **Minecraft Java Edition** `map_*.dat` (NBT, обычно gzip) и сохраняет **128×128** PNG с ванильной палитрой и затенением карты.

*English version: [README.md](README.md)*

---

## Что нужно

- **Python 3.10+** (лучше 3.12+).
- Пакеты **nbtlib** и **pillow** (через pip).

Поддерживаются только карты **Java Edition** из папки `data` сохранения. Форматы **Bedrock** не читаются.

---

## 1. Установка Python

### Windows

1. Скачай установщик с **[python.org/downloads](https://www.python.org/downloads/)** (официальный установщик; одной только «заглушки» из Microsoft Store может быть недостаточно).

2. В мастере установки включи **«Add python.exe to PATH»** (добавить Python в PATH).

3. Заверши установку и **открой новое** окно терминала (PowerShell или cmd).

4. **По желанию:** если команда `python` открывает Store или почти ничего не делает — в **Параметры → Приложения → Дополнительные компоненты → Псевдонимы выполнения приложений** отключи псевдонимы для **python.exe** и **python3.exe**, либо проверь `where python` — должен быть путь вида `...\Python3xx\python.exe`.

5. Проверка:

   ```text
   python --version
   ```

   Должна отобразиться версия, например `Python 3.12.x`.

### macOS / Linux

Поставь Python 3 из пакетного менеджера или с [python.org](https://www.python.org/downloads/). Проверка:

```text
python3 --version
```

Если в системе команда называется `python3`, используй её во всех примерах вместо `python`.

---

## 2. Файлы проекта

Скопируй `map_to_png.py` в любую папку (например `C:\Work\MinecraftMapExporter`). Для работы **достаточно одного** этого файла.

---

## 3. Зависимости

Если команда `pip` не находится, ставь так (на чистой установке Python это надёжный способ):

```text
python -m pip install nbtlib pillow
```

На macOS/Linux при интерпретаторе `python3`:

```text
python3 -m pip install nbtlib pillow
```

Вместе с **nbtlib** может поставиться **numpy** — это нормально.

**Совет (Windows):** если pip предупреждает, что `Scripts` не в PATH, всегда можно вызывать `python -m pip`. При желании добавь папку `Scripts` в PATH пользователя.

---

## 4. Где лежат файлы карт

В **Java Edition** данные карт в сохранении:

```text
<папка saves>/<ИмяМира>/data/map_<номер>.dat
```

Пример для лаунчера по умолчанию (Windows):

```text
%appdata%\.minecraft\saves\<ИмяМира>\data\map_0.dat
```

Можно скопировать `map_0.dat` рядом со скриптом или указать **полный путь** к файлу в команде.

---

## 5. Использование

В терминале перейди в каталог с `map_to_png.py` и запускай:

### Базовый режим — PNG рядом с `.dat`

```text
python map_to_png.py map_0.dat
```

### Свой путь к PNG

```text
python map_to_png.py map_0.dat --out preview.png
```

### Масштаб (nearest-neighbor, без сглаживания)

Например `--scale 4` даёт **512×512**:

```text
python map_to_png.py map_0.dat --scale 4 --out map_512.png
```

**`--scale`** работает и с папкой, и с `--maps-dir`, и с `--layout combined` — масштабируется уже готовое изображение.

### Сетка по пикселям карты (удобно для построек; имеет смысл при `--scale` > 1)

```text
python map_to_png.py map_0.dat --scale 4 --grid --out map_grid.png
```

### Пакетно — все `*.dat` в папке

Берутся **только** файлы с расширением **`.dat`** (`map_0.dat`, `map_1.dat`, …). Остальное игнорируется. **Подпапки не обходятся** — только верхний уровень указанной папки.

Отдельный PNG на каждую карту (рядом с `.dat`, если не задан `--out`):

```text
python map_to_png.py "C:\path\to\world\data"
```

То же через флаг (удобно, когда много карт):

```text
python map_to_png.py --maps-dir "C:\path\to\world\data"
python map_to_png.py -d "C:\path\to\world\data" -d "C:\path\to\other\data"
```

Все PNG в **одну папку** (`--out` — каталог, не файл `.png`):

```text
python map_to_png.py "C:\path\to\world\data" --out "C:\path\to\output_pngs"
python map_to_png.py --maps-dir "C:\path\to\world\data" --out "C:\path\to\output_pngs"
```

### Несколько файлов — отдельные PNG (режим по умолчанию)

```text
python map_to_png.py map_0.dat map_1.dat map_2.dat
python map_to_png.py map_0.dat map_1.dat --out "C:\path\to\png_folder"
```

### Одна мозаика из нескольких карт (`--layout combined`)

Позиции тайлов берутся из NBT: **`xCenter`**, **`zCenter`**, **`scale`**, **`dimension`**. Ось **X** мира → **X** картинки, **Z** мира → **Y** вниз (как на карте в игре). У всех карт должны совпадать **измерение** и **масштаб** (zoom); иначе утилита завершится с ошибкой.

```text
python map_to_png.py map_0.dat map_1.dat map_2.dat --layout combined --out mosaic.png
```

Без `--out` имя по умолчанию — **`stitched.png`** в текущей папке.

Склейка **всех** `*.dat` из каталога:

```text
python map_to_png.py "C:\path\to\world\data" --layout combined --out full_map.png
python map_to_png.py --maps-dir "C:\path\to\world\data" --layout combined --out full_map.png
```

К мозаике тоже применимы **`--scale`** и **`--grid`**.

### Тихий режим

```text
python map_to_png.py map_0.dat -q
```

### Справка по аргументам

```text
python map_to_png.py --help
```

---

## 6. Частые проблемы

| Сообщение / ситуация | Что сделать |
|---------------------|-------------|
| `path does not exist` | Файла нет в **текущей** папке — укажи полный путь или сделай `cd` в каталог с `.dat`. |
| `pip` не распознан | Используй `python -m pip install nbtlib pillow`. |
| `python` только пишет `Python` или открывает Store | Поставь Python с **python.org**, включи PATH, отключи псевдонимы Store, открой новый терминал. |
| `data.colors must have length 16384` | Не карта Java или битый файл. |
| `NBT root has no 'data'` | Не тот тип файла. |
| `dimension mismatch` / `scale mismatch` | Для `--layout combined` нужны карты из одного измерения и с одним zoom. |
| `not aligned to the combined pixel grid` | Нестандартные центры карт в NBT. |
| Несколько карт + `--layout separate` + `--out файл.png` | Для нескольких карт `--out` должен быть **папкой** или не указывай его; для одного общего PNG используй `--layout combined`. |

---

## 7. Кратко о реализации

- Читается массив `data.colors` — **16384** байта (128×128).
- Каждый байт — индекс цвета и вариант затенения; множители **0.71, 0.86, 1.0, 0.53**.
- Поддерживаются **nbtlib 1.x и 2.x**.
- Сначала пробуется **gzip**, затем несжатый NBT.

---

## Лицензия

Скрипт распространяется как есть, для личного и свободного использования. При перепубликации удобно приложить README — так проще установить Python и зависимости.
