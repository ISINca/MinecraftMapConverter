# Minecraft map.dat → PNG

Small CLI tool that reads **Minecraft Java Edition** `map_*.dat` files (NBT, usually gzip-compressed) and exports a **128×128** PNG using the vanilla map color palette and shading.

*Русская версия: [README.ru.md](README.ru.md)*

---

## What you need

- **Python 3.10+** (3.12+ recommended; the tool runs on current stable releases).
- Two Python packages: **nbtlib** and **pillow** (installed via pip).

This tool is for **Java Edition** map files under your world’s `data` folder. It does not read Bedrock map formats.

---

## 1. Install Python

### Windows

1. Download the installer from **[python.org/downloads](https://www.python.org/downloads/)** (official installer — avoid relying only on the Microsoft Store shortcut).

2. During setup, enable **“Add python.exe to PATH”** (or “Add Python to environment variables”).

3. Finish the installation and **open a new** terminal (PowerShell or Command Prompt).

4. **Optional but helpful:** Windows may register a **Microsoft Store stub** for `python` that does not run scripts properly. If commands only print `Python` or nothing useful:
   - Open **Settings → Apps → Advanced app settings → App execution aliases** and turn **off** the aliases for **python.exe** and **python3.exe**, **or**
   - Ensure `python` resolves to the install under `...\Python3xx\` (check with `where python` in PowerShell).

5. Verify:

   ```text
   python --version
   ```

   You should see something like `Python 3.12.x` or `Python 3.14.x`.

### macOS / Linux

Install Python 3 from your package manager or [python.org](https://www.python.org/downloads/). Then confirm:

```text
python3 --version
```

On some systems the command is `python3` instead of `python`; use the same name in all commands below.

---

## 2. Get this project

Download `map_to_png.py` (and optionally this `README.md`) into a folder of your choice, for example:

```text
C:\Work\MinecraftMapExporter
```

You only **need** `map_to_png.py` to run the tool.

---

## 3. Install dependencies

**Do not worry if the `pip` command is not found** — use Python’s module flag instead (works on a fresh Python install):

```text
python -m pip install nbtlib pillow
```

On macOS/Linux, if your interpreter is `python3`:

```text
python3 -m pip install nbtlib pillow
```

`nbtlib` may pull in **numpy** as a dependency; that is normal.

**Tip (Windows):** If the installer warns that scripts are not on `PATH`, you can still use `python -m pip` forever. Optionally add Python’s `Scripts` folder to your user `PATH` if you want the `pip` command and other tools available directly.

---

## 4. Where are the map files?

For **Minecraft Java Edition**, map data files live inside your save:

```text
<saves folder>/<YourWorldName>/data/map_<id>.dat
```

Examples:

- Windows (default launcher):  
  `%appdata%\.minecraft\saves\<WorldName>\data\map_0.dat`
- Copy `map_0.dat` (or any `map_<number>.dat`) to your working folder, **or** pass the **full path** to the script.

---

## 5. Usage

Open a terminal, go to the folder that contains `map_to_png.py`, then run:

### Basic — PNG next to the `.dat` (same name, `.png` extension)

```text
python map_to_png.py map_0.dat
```

### Custom output path

```text
python map_to_png.py map_0.dat --out preview.png
```

### Upscale (nearest-neighbor, pixel-perfect)

Scale `4` → **512×512** image:

```text
python map_to_png.py map_0.dat --scale 4 --out map_512.png
```

### Grid overlay (useful for building; only meaningful with `--scale` > 1)

```text
python map_to_png.py map_0.dat --scale 4 --grid --out map_grid.png
```

### Batch — all `.dat` files in a folder

Only files whose names end in **`.dat`** are used (typical Java map files: `map_0.dat`, `map_1.dat`, …). Other files in the folder are ignored. The scan is **not recursive** (only that folder’s top level).

Writes one PNG per map next to each file (unless `--out` is set to a directory):

```text
python map_to_png.py "C:\path\to\world\data"
```

Same thing with an explicit flag (handy when you have many maps and no other positional args):

```text
python map_to_png.py --maps-dir "C:\path\to\world\data"
python map_to_png.py -d "C:\path\to\world\data" -d "C:\path\to\other\data"
```

Output into a specific **directory** (must be a folder, not a `.png` filename):

```text
python map_to_png.py "C:\path\to\world\data" --out "C:\path\to\output_pngs"
python map_to_png.py --maps-dir "C:\path\to\world\data" --out "C:\path\to\output_pngs"
```

### Several maps by path — separate PNGs (default)

List any number of `.dat` files; each becomes its own image next to the source (or under `--out` if it is a **directory**):

```text
python map_to_png.py map_0.dat map_1.dat map_2.dat
python map_to_png.py map_0.dat map_1.dat --out "C:\path\to\png_folder"
```

### One mosaic from several maps (`--layout combined`)

Uses **NBT fields** `xCenter`, `zCenter`, `scale`, and `dimension` so tiles are placed like in the world: image **X** = world **X**, image **Y** = world **Z** (south downward). All maps must share the **same dimension** and **same scale** (zoom); otherwise the tool exits with an error.

```text
python map_to_png.py map_0.dat map_1.dat map_2.dat --layout combined --out mosaic.png
```

If you omit `--out`, the default file name is **`stitched.png`** in the current working directory.

Stitch **every** `*.dat` in a folder into one image:

```text
python map_to_png.py "C:\path\to\world\data" --layout combined --out full_map.png
python map_to_png.py --maps-dir "C:\path\to\world\data" --layout combined --out full_map.png
```

You can still use `--scale` and `--grid` on the final (possibly large) image.

### Quiet mode (no success messages)

```text
python map_to_png.py map_0.dat -q
```

### Full help

```text
python map_to_png.py --help
```

---

## 6. Troubleshooting

| Problem | What to do |
|--------|------------|
| `path does not exist: map_0.dat` | The file is not in the **current working directory**. Use the full path to `map_<id>.dat`, or `cd` to the folder that contains it. |
| `pip` is not recognized | Use `python -m pip install nbtlib pillow` instead of `pip install ...`. |
| `python` opens the Store or prints only `Python` | Install Python from **python.org**, enable PATH, disable **App execution aliases** for Python (Windows), open a new terminal. |
| `data.colors must have length 16384` | The file is not a standard Java map, or it is corrupted. |
| `NBT root has no 'data'` | Wrong file type or not a Java `map_*.dat`. |
| `dimension mismatch` / `scale mismatch` (combined layout) | Maps are from different dimensions or zoom levels; use only maps that belong to one grid. |
| `not aligned to the combined pixel grid` | Map centers do not line up on the usual map grid (unusual or edited NBT). |
| `multiple maps + --layout separate` + `--out file.png` | With several files, `--out` must be a **folder** or omitted; use `--layout combined` for a single PNG. |

---

## 7. Technical notes (short)

- Reads `data.colors` as **16384** bytes (128×128).
- Decodes each byte as vanilla map color index and shade; uses the Java map base-color table and shading multipliers **0.71, 0.86, 1.0, 0.53**.
- Supports **nbtlib 1.x and 2.x** (the script resolves the root compound in a version-tolerant way).
- Tries **gzip** first, then uncompressed NBT, for unusual files.

---

## License

The script is provided as-is for personal and shared use. If you redistribute it, keeping this README with the script helps others install Python and dependencies correctly.
