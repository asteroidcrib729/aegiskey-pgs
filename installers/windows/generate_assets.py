"""Generate crisp multi-resolution ICO and MSIX PNG assets from vector SVG artwork."""

import argparse
import struct
import tkinter as tk
from pathlib import Path

from password_generator.ui.icons import render_svg

_SHIELD_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 64 64">'
    '<rect x="4" y="4" width="56" height="56" rx="14" fill="#1D4ED8"/>'
    '<path d="M32 13 L47 19.5 V31.5 C47 41.8 40.3 49.8 32 52.5 '
    'C23.7 49.8 17 41.8 17 31.5 V19.5 Z" '
    'fill="#0B0F17" stroke="#38BDF8" stroke-width="2.5" stroke-linejoin="round"/>'
    '<circle cx="32" cy="29.5" r="4.2" fill="#38BDF8"/>'
    '<rect x="30.2" y="32.5" width="3.6" height="8.5" rx="1.8" fill="#38BDF8"/>'
    "</svg>"
)

_WIDE_TILE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="310" height="150" viewBox="0 0 310 150">'
    '<rect width="310" height="150" fill="#0B1120"/>'
    '<g transform="translate(107, 27) scale(1.5)">'
    '<rect x="4" y="4" width="56" height="56" rx="14" fill="#1D4ED8"/>'
    '<path d="M32 13 L47 19.5 V31.5 C47 41.8 40.3 49.8 32 52.5 '
    'C23.7 49.8 17 41.8 17 31.5 V19.5 Z" '
    'fill="#0B0F17" stroke="#38BDF8" stroke-width="2.5" stroke-linejoin="round"/>'
    '<circle cx="32" cy="29.5" r="4.2" fill="#38BDF8"/>'
    '<rect x="30.2" y="32.5" width="3.6" height="8.5" rx="1.8" fill="#38BDF8"/>'
    "</g>"
    "</svg>"
)

_ICO_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)

_MSIX_SQUARE_ASSETS: dict[str, int] = {
    "StoreLogo.png": 50,
    "Square44x44Logo.png": 44,
    "Square44x44Logo.scale-200.png": 88,
    "Square44x44Logo.targetsize-44.png": 44,
    "Square44x44Logo.targetsize-44_altform-unplated.png": 44,
    "Square44x44Logo.targetsize-256.png": 256,
    "Square44x44Logo.targetsize-256_altform-unplated.png": 256,
    "Square150x150Logo.png": 150,
    "Square150x150Logo.scale-200.png": 300,
}


def _render_png_bytes(svg_markup: str, out_path: Path) -> bytes:
    img = render_svg(svg_markup, scale=1.0)
    img.write(str(out_path), format="png")
    return out_path.read_bytes()


def _pack_png_ico(images: list[tuple[int, bytes]], ico_path: Path) -> None:
    """Write a multi-resolution Windows ICO container embedding PNG frames."""
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + count * 16
    entries: list[bytes] = []
    payload: list[bytes] = []

    for size, png_bytes in images:
        dim = 0 if size >= 256 else size
        entry = struct.pack(
            "<BBBBHHII",
            dim,
            dim,
            0,
            0,
            1,
            32,
            len(png_bytes),
            offset,
        )
        entries.append(entry)
        payload.append(png_bytes)
        offset += len(png_bytes)

    ico_path.write_bytes(header + b"".join(entries) + b"".join(payload))


def generate_windows_assets(output_dir: Path) -> Path:
    """Render ``AegisKey.ico`` and MSIX PNG tile assets into ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)
    msix_assets_dir = output_dir / "msix_assets"
    msix_assets_dir.mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    root.withdraw()
    try:
        ico_frames: list[tuple[int, bytes]] = []
        tmp_png = output_dir / "_tmp_ico.png"
        try:
            for size in _ICO_SIZES:
                svg = _SHIELD_SVG_TEMPLATE.format(w=size, h=size)
                png_bytes = _render_png_bytes(svg, tmp_png)
                ico_frames.append((size, png_bytes))
        finally:
            tmp_png.unlink(missing_ok=True)

        ico_path = output_dir / "AegisKey.ico"
        _pack_png_ico(ico_frames, ico_path)

        for filename, size in _MSIX_SQUARE_ASSETS.items():
            svg = _SHIELD_SVG_TEMPLATE.format(w=size, h=size)
            _render_png_bytes(svg, msix_assets_dir / filename)

        _render_png_bytes(_WIDE_TILE_SVG, msix_assets_dir / "Wide310x150Logo.png")
    finally:
        root.destroy()

    return output_dir


def main() -> int:
    """CLI entry point for asset generation."""
    parser = argparse.ArgumentParser(description="Generate Windows ICO and MSIX PNG assets.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/windows/assets"),
        help="Target directory for generated .ico and MSIX tile PNG assets.",
    )
    args = parser.parse_args()
    out = generate_windows_assets(args.output_dir)
    print(f"Generated Windows assets in: {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
