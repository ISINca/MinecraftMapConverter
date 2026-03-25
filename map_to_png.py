#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Minecraft Java Edition map_*.dat (gzipped NBT) to a PNG preview.

Usage:
  python map_to_png.py path/to/map_0.dat
  python map_to_png.py map_a.dat map_b.dat
  python map_to_png.py map_a.dat map_b.dat --layout combined --out mosaic.png
  python map_to_png.py path/to/maps_folder/ --layout combined
  python map_to_png.py --maps-dir path/to/data --layout combined --out mosaic.png
  python map_to_png.py path/to/map_0.dat --out preview.png --scale 4 --grid

Dependencies: pip install nbtlib pillow

Base RGB values match the Java map color table (Minecraft Wiki, Java Edition).
Shading uses multipliers (0.71, 0.86, 1.0, 0.53) per map color byte shade index.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence

from PIL import Image, ImageDraw

import nbtlib

# --- Map geometry (vanilla fixed map item size) ---
MAP_DIMENSION: Final[int] = 128
EXPECTED_COLOR_COUNT: Final[int] = MAP_DIMENSION * MAP_DIMENSION

# --- Shading (same ordering as MapColor modifiers in vanilla Java) ---
SHADE_MULTIPLIERS: Final[tuple[float, float, float, float]] = (
    0.71,
    0.86,
    1.0,
    0.53,
)

# --- Grid overlay ---
GRID_ALPHA: Final[int] = 60

# --- Full vanilla base palette: index = baseColor, RGB at full brightness (shade 2). ---
# Index 0 (NONE / unexplored): treated as fully transparent for all shades.
# Sources: https://minecraft.wiki/w/Map_item_format (Java, base colors), DataChecked 1.21.5.
MAP_BASE_RGB: Final[tuple[tuple[int, int, int], ...]] = (
    (0, 0, 0),
    (127, 178, 56),
    (247, 233, 163),
    (199, 199, 199),
    (255, 0, 0),
    (160, 160, 255),
    (167, 167, 167),
    (0, 124, 0),
    (255, 255, 255),
    (164, 168, 184),
    (151, 109, 77),
    (112, 112, 112),
    (64, 64, 255),
    (143, 119, 72),
    (255, 252, 245),
    (216, 127, 51),
    (178, 76, 216),
    (102, 153, 216),
    (229, 229, 51),
    (127, 204, 25),
    (242, 127, 165),
    (76, 76, 76),
    (153, 153, 153),
    (76, 127, 153),
    (127, 63, 178),
    (51, 76, 178),
    (102, 76, 51),
    (102, 127, 51),
    (153, 51, 51),
    (25, 25, 25),
    (250, 238, 77),
    (92, 219, 213),
    (74, 128, 255),
    (0, 217, 58),
    (129, 86, 49),
    (112, 2, 0),
    (209, 177, 161),
    (159, 82, 36),
    (149, 87, 108),
    (112, 108, 138),
    (186, 133, 36),
    (103, 117, 53),
    (160, 77, 78),
    (57, 41, 35),
    (135, 107, 98),
    (87, 92, 92),
    (122, 73, 88),
    (76, 62, 92),
    (76, 50, 35),
    (76, 82, 42),
    (142, 60, 46),
    (37, 22, 16),
    (189, 48, 49),
    (148, 63, 97),
    (92, 25, 29),
    (22, 126, 134),
    (58, 142, 140),
    (86, 44, 62),
    (20, 180, 133),
    (100, 100, 100),
    (216, 175, 147),
    (127, 167, 150),
)

NUM_BASE_COLORS: Final[int] = len(MAP_BASE_RGB)
_MAX_BASE_INDEX: Final[int] = NUM_BASE_COLORS - 1

# Vanilla map scale is 0..4; allow slightly higher for forward compatibility.
_MAX_MAP_SCALE: Final[int] = 8


@dataclass(frozen=True)
class MapRecord:
    """One map file: color buffer and placement metadata from NBT."""

    path: Path
    colors: bytes
    x_center: int
    z_center: int
    scale: int
    dimension: str


def _as_int(tag: object, default: int = 0) -> int:
    if tag is None:
        return default
    return int(tag)  # type: ignore[arg-type]


def _dimension_key(raw: object) -> str:
    """Normalize dimension for equality checks (legacy byte or 1.16+ resource id)."""
    if raw is None:
        return "minecraft:overworld"
    if isinstance(raw, str):
        return raw
    # nbtlib String or numeric legacy dimension
    try:
        i = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        s = str(raw)
        if len(s) >= 2 and s[0] == s[-1] == "'":
            return s[1:-1]
        return s
    legacy = {
        0: "minecraft:overworld",
        -1: "minecraft:the_nether",
        1: "minecraft:the_end",
    }
    return legacy.get(i, f"legacy:{i}")


def blocks_per_pixel(scale: int) -> int:
    """Blocks covered by one map pixel: 2**scale (vanilla Java)."""
    if scale < 0:
        raise ValueError("map scale must be non-negative")
    return 1 << scale


def load_map_record(path: Path) -> MapRecord:
    """
    Load map.dat: colors (16384 bytes) plus xCenter, zCenter, scale, dimension.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Not a file or does not exist: {path}")

    nbt_file: nbtlib.File | None = None
    last_error: Exception | None = None
    for gzipped in (True, False):
        try:
            nbt_file = nbtlib.load(str(path), gzipped=gzipped)
            last_error = None
            break
        except OSError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc
    if nbt_file is None:
        assert last_error is not None
        raise RuntimeError(f"Failed to read NBT from {path}: {last_error}") from last_error

    root = getattr(nbt_file, "root", nbt_file)
    if "data" not in root:
        raise ValueError(f"{path}: NBT root has no 'data' compound")
    data = root["data"]
    if "colors" not in data:
        raise ValueError(f"{path}: 'data' has no 'colors' byte array")

    colors_tag = data["colors"]
    raw_values: Sequence[int] = colors_tag  # type: ignore[assignment]
    normalized = bytes(int(v) & 0xFF for v in raw_values)

    if len(normalized) != EXPECTED_COLOR_COUNT:
        raise ValueError(
            f"{path}: data.colors must have length {EXPECTED_COLOR_COUNT}, "
            f"got {len(normalized)}"
        )

    x_center = _as_int(data.get("xCenter"), 0)
    z_center = _as_int(data.get("zCenter"), 0)
    scale = _as_int(data.get("scale"), 0)
    if scale > _MAX_MAP_SCALE:
        raise ValueError(f"{path}: map scale {scale} is out of supported range (0..{_MAX_MAP_SCALE})")
    dimension = _dimension_key(data.get("dimension"))

    return MapRecord(
        path=path,
        colors=normalized,
        x_center=x_center,
        z_center=z_center,
        scale=scale,
        dimension=dimension,
    )


def load_map(path: Path) -> bytes:
    """
    Load and validate map.dat; return raw color bytes (length EXPECTED_COLOR_COUNT).
    """
    return load_map_record(path).colors


def decode_color(value: int) -> tuple[int, int, int, int]:
    """
    Decode one map color byte to RGBA.
    colorIndex = value & 0xFF; baseColor = colorIndex // 4; shade = colorIndex % 4.
    """
    color_index = value & 0xFF
    base_color = color_index // 4
    shade = color_index % 4
    multiplier = SHADE_MULTIPLIERS[shade]

    if base_color == 0:
        return (0, 0, 0, 0)

    if base_color > _MAX_BASE_INDEX:
        base_color = _MAX_BASE_INDEX

    r, g, b = MAP_BASE_RGB[base_color]
    r_out = max(0, min(255, int(round(r * multiplier))))
    g_out = max(0, min(255, int(round(g * multiplier))))
    b_out = max(0, min(255, int(round(b * multiplier))))
    return (r_out, g_out, b_out, 255)


def render_image(colors: bytes) -> Image.Image:
    """Build 128x128 RGBA image; index i maps to pixel (i % 128, i // 128), top-left origin."""
    if len(colors) != EXPECTED_COLOR_COUNT:
        raise ValueError(
            f"colors length must be {EXPECTED_COLOR_COUNT}, got {len(colors)}"
        )
    pixel_bytes = bytearray(EXPECTED_COLOR_COUNT * 4)
    offset = 0
    for byte in colors:
        rgba = decode_color(byte)
        pixel_bytes[offset : offset + 4] = rgba
        offset += 4
    return Image.frombytes(
        "RGBA", (MAP_DIMENSION, MAP_DIMENSION), bytes(pixel_bytes)
    )


def stitch_maps(records: Sequence[MapRecord]) -> Image.Image:
    """
    Place 128x128 map tiles on one RGBA canvas using xCenter, zCenter, scale, dimension.
    World NW corner of each map tile: (xCenter - 64*bpp, zCenter - 64*bpp).
    Image X = world X, image Y = world Z (south = down).
    """
    recs = list(records)
    if not recs:
        raise ValueError("no maps to stitch")

    ref_dim = recs[0].dimension
    ref_scale = recs[0].scale
    bpp = blocks_per_pixel(ref_scale)
    half_px = MAP_DIMENSION // 2

    for r in recs:
        if r.dimension != ref_dim:
            raise ValueError(
                f"dimension mismatch for stitch: {r.path.name} is {r.dimension!r}, "
                f"expected {ref_dim!r} (all maps must be the same dimension)."
            )
        if r.scale != ref_scale:
            raise ValueError(
                f"scale mismatch for stitch: {r.path.name} has scale {r.scale}, "
                f"expected {ref_scale} (all maps must use the same scale / zoom)."
            )

    world_x_mins: list[int] = []
    world_z_mins: list[int] = []
    world_x_maxs: list[int] = []
    world_z_maxs: list[int] = []

    for r in recs:
        wx0 = r.x_center - half_px * bpp
        wz0 = r.z_center - half_px * bpp
        wx1 = wx0 + MAP_DIMENSION * bpp
        wz1 = wz0 + MAP_DIMENSION * bpp
        world_x_mins.append(wx0)
        world_z_mins.append(wz0)
        world_x_maxs.append(wx1)
        world_z_maxs.append(wz1)

    gx0 = min(world_x_mins)
    gz0 = min(world_z_mins)
    gx1 = max(world_x_maxs)
    gz1 = max(world_z_maxs)

    extent_x = gx1 - gx0
    extent_z = gz1 - gz0
    if extent_x % bpp != 0 or extent_z % bpp != 0:
        raise ValueError(
            f"combined extent ({extent_x}x{extent_z} blocks) is not a multiple of "
            f"blocks-per-pixel ({bpp}); maps may not tile cleanly."
        )

    width_px = extent_x // bpp
    height_px = extent_z // bpp

    for r in recs:
        wx0 = r.x_center - half_px * bpp
        wz0 = r.z_center - half_px * bpp
        if (wx0 - gx0) % bpp != 0 or (wz0 - gz0) % bpp != 0:
            raise ValueError(
                f"{r.path.name}: map is not aligned to the combined pixel grid "
                f"(bpp={bpp}). Centers may not belong to a single stitched layout."
            )

    canvas = Image.new("RGBA", (width_px, height_px), (0, 0, 0, 0))
    for r in sorted(recs, key=lambda t: str(t.path)):
        wx0 = r.x_center - half_px * bpp
        wz0 = r.z_center - half_px * bpp
        ox = (wx0 - gx0) // bpp
        oy = (wz0 - gz0) // bpp
        tile = render_image(r.colors)
        canvas.paste(tile, (ox, oy), tile)

    return canvas


def apply_upscale(image: Image.Image, scale: int) -> Image.Image:
    """Nearest-neighbor upscale; scale must be >= 1."""
    if scale < 1:
        raise ValueError("scale must be >= 1")
    if scale == 1:
        return image
    w, h = image.size
    return image.resize((w * scale, h * scale), resample=Image.Resampling.NEAREST)


def draw_grid_cells(image: Image.Image, scale: int) -> Image.Image:
    """
    Draw 1px semi-transparent grid every `scale` pixels (after upscale).
    Works for single 128x128-based images and larger stitched mosaics.
    """
    if scale <= 1:
        return image
    rgba = image.convert("RGBA")
    w, h = rgba.size
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    grid_color = (0, 0, 0, GRID_ALPHA)

    for k in range(w // scale + 1):
        x = min(k * scale, w - 1)
        draw.line([(x, 0), (x, h - 1)], fill=grid_color, width=1)
    for k in range(h // scale + 1):
        y = min(k * scale, h - 1)
        draw.line([(0, y), (w - 1, y)], fill=grid_color, width=1)

    return Image.alpha_composite(rgba, overlay)


def draw_grid(image: Image.Image, scale: int) -> Image.Image:
    """Same as draw_grid_cells (128x128 maps upscale to multiples of scale)."""
    return draw_grid_cells(image, scale)


def _default_output_path(map_dat: Path) -> Path:
    return map_dat.with_suffix(".png")


def _collect_dat_files(directory: Path) -> list[Path]:
    """Non-recursive: only *.dat in the given directory (Java map files)."""
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".dat")


def _resolve_map_paths(
    inputs: Sequence[Path],
    maps_dirs: Sequence[Path],
) -> list[Path]:
    """
    Build a deduplicated list of map paths: every *.dat from listed folders
    plus any explicit files. Folders from positional args behave like --maps-dir.
    """
    chunks: list[Path] = []
    for p in inputs:
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f"path does not exist: {p}")
        if p.is_dir():
            chunks.extend(_collect_dat_files(p))
        else:
            chunks.append(p)

    for d in maps_dirs:
        d = Path(d)
        if not d.exists():
            raise FileNotFoundError(f"--maps-dir path does not exist: {d}")
        if not d.is_dir():
            raise NotADirectoryError(f"--maps-dir is not a directory: {d}")
        chunks.extend(_collect_dat_files(d))

    seen: set[str] = set()
    unique: list[Path] = []
    for p in chunks:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return sorted(unique, key=lambda x: str(x).lower())


def _finalize_image(img: Image.Image, scale: int, grid: bool, label: str) -> Image.Image:
    img = apply_upscale(img, scale)
    if grid:
        if scale <= 1:
            print(
                f"Note: --grid ignored for {label} (requires --scale > 1)",
                file=sys.stderr,
            )
        else:
            img = draw_grid_cells(img, scale)
    return img


def _save_png(img: Image.Image, out_path: Path, verbose: bool) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    if verbose:
        print(f"Wrote {out_path} ({img.size[0]}x{img.size[1]})")


def _process_one(
    map_path: Path,
    out_path: Path,
    scale: int,
    grid: bool,
    verbose: bool,
) -> None:
    record = load_map_record(map_path)
    img = render_image(record.colors)
    img = _finalize_image(img, scale, grid, map_path.name)
    _save_png(img, out_path, verbose)


def _process_combined(
    records: Sequence[MapRecord],
    out_path: Path,
    scale: int,
    grid: bool,
    verbose: bool,
) -> None:
    img = stitch_maps(records)
    img = _finalize_image(img, scale, grid, "combined output")
    _save_png(img, out_path, verbose)


DEFAULT_COMBINED_OUT: Final[Path] = Path("stitched.png")


def _is_explicit_png_file(path: Path) -> bool:
    """True if --out should be treated as a single PNG file path."""
    if path.exists():
        return path.is_file()
    return path.suffix.lower() == ".png"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Minecraft map.dat (Java, gzipped NBT) to PNG (128x128 map colors)."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Optional map_*.dat file(s) and/or folders of .dat files (same as --maps-dir)",
    )
    parser.add_argument(
        "--maps-dir",
        "-d",
        action="append",
        default=None,
        dest="maps_dirs",
        type=Path,
        metavar="DIR",
        help=(
            "Folder containing Java map_*.dat files (only *.dat names are used). "
            "Repeat -d for multiple folders."
        ),
    )
    parser.add_argument(
        "--layout",
        choices=("separate", "combined"),
        default="separate",
        help=(
            "separate: one PNG per map. combined: one mosaic using xCenter/zCenter/scale/dimension from NBT "
            "(all maps must share the same dimension and scale)."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Output: PNG file for single map or for --layout combined; directory for multiple maps with "
            "--layout separate. Default: beside each .dat, or stitched.png for combined."
        ),
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Integer scale factor (nearest neighbor). Default: 1",
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Draw pixel grid (only effective with --scale > 1)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress success messages",
    )
    args = parser.parse_args(argv)

    inputs: list[Path] = list(args.inputs or [])
    maps_dirs: list[Path] = list(args.maps_dirs or [])
    layout: str = args.layout
    scale: int = args.scale
    grid: bool = args.grid
    verbose = not args.quiet
    out_opt: Path | None = args.out

    if scale < 1:
        print("error: --scale must be at least 1", file=sys.stderr)
        return 2

    if not inputs and not maps_dirs:
        print(
            "error: pass at least one input: map .dat path(s), a folder, and/or --maps-dir / -d <folder>",
            file=sys.stderr,
        )
        return 2

    try:
        dat_paths = _resolve_map_paths(inputs, maps_dirs)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not dat_paths:
        print(
            "error: no *.dat files found. Java map files are named map_<id>.dat in the world's data folder.",
            file=sys.stderr,
        )
        return 1

    if verbose:
        print(f"Using {len(dat_paths)} map file(s) (*.dat).")

    try:
        records = [load_map_record(p) for p in dat_paths]

        if layout == "combined":
            if out_opt is not None and out_opt.exists() and out_opt.is_dir():
                print(
                    "error: --layout combined requires --out to be a PNG file path, not a directory",
                    file=sys.stderr,
                )
                return 2
            out_path = out_opt if out_opt is not None else DEFAULT_COMBINED_OUT
            if verbose and len(records) > 1:
                print(
                    f"Stitching {len(records)} maps → {out_path} "
                    f"(positions from xCenter/zCenter; same dimension & scale required)"
                )
            _process_combined(records, out_path, scale, grid, verbose)
            return 0

        # --layout separate
        if len(dat_paths) >= 2 and out_opt is not None and _is_explicit_png_file(out_opt):
            print(
                "error: multiple maps + --layout separate: use --out <directory> or omit --out "
                "(writes .png next to each .dat)",
                file=sys.stderr,
            )
            return 2

        out_dir_sep: Path | None = None
        if len(dat_paths) >= 2 and out_opt is not None:
            out_dir_sep = out_opt

        if len(dat_paths) == 1:
            p0 = dat_paths[0]
            if out_opt is not None and out_opt.exists() and out_opt.is_dir():
                print(
                    "error: single map: --out must be a PNG file path, not a directory",
                    file=sys.stderr,
                )
                return 2
            target = out_opt if out_opt is not None else _default_output_path(p0)
            _process_one(p0, target, scale, grid, verbose)
            return 0

        for p in dat_paths:
            target = (
                out_dir_sep / p.with_suffix(".png").name
                if out_dir_sep is not None
                else _default_output_path(p)
            )
            _process_one(p, target, scale, grid, verbose)

    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
