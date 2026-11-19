"""Anti-aliased SVG vector icon rendering powered by Tcl/Tk 9.0 native SVG support."""

import tkinter as tk
from dataclasses import dataclass


def render_svg(svg_markup: str, *, scale: float = 1.0) -> tk.PhotoImage:
    """Rasterize an SVG string into a crisp DPI-scaled ``tk.PhotoImage``."""
    safe_scale = max(1.0, scale)
    return tk.PhotoImage(data=svg_markup, format=f"svg -scale {safe_scale:.3f}")


def create_app_icon(*, scale: float = 1.0) -> tk.PhotoImage:
    """Create the high-resolution AegisKey shield-and-keyhole application icon."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect x="4" y="4" width="56" height="56" rx="14" fill="#1D4ED8"/>
  <path d="M32 13 L47 19.5 V31.5 C47 41.8 40.3 49.8 32 52.5 C23.7 49.8 17 41.8 17 31.5 V19.5 Z"
        fill="#0B0F17" stroke="#38BDF8" stroke-width="2.5" stroke-linejoin="round"/>
  <circle cx="32" cy="29.5" r="4.2" fill="#38BDF8"/>
  <rect x="30.2" y="32.5" width="3.6" height="8.5" rx="1.8" fill="#38BDF8"/>
</svg>"""
    return render_svg(svg, scale=scale)


@dataclass(frozen=True, slots=True)
class UiIconSet:
    """Collection of crisp UI icons bound to a specific theme foreground color."""

    generate: tk.PhotoImage
    copy: tk.PhotoImage
    eye_open: tk.PhotoImage
    eye_closed: tk.PhotoImage
    batch: tk.PhotoImage
    theme: tk.PhotoImage
    help_icon: tk.PhotoImage
    wipe: tk.PhotoImage


def build_ui_icons(
    *,
    primary_fg: str,
    secondary_fg: str,
    danger_fg: str,
    scale: float = 1.0,
) -> UiIconSet:
    """Build crisp 15x15 SVG button icons matching the active palette and display DPI."""
    # Scale gently relative to Tk scaling so icons stay crisp alongside 10pt fonts.
    icon_scale = max(1.0, scale * 0.95)

    def _wrap(paths: str) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" '
            f'viewBox="0 0 24 24" fill="none">{paths}</svg>'
        )

    generate_svg = _wrap(
        f'<path d="M21 12a9 9 0 1 1-2.64-6.36" stroke="{primary_fg}" '
        'stroke-width="2.2" stroke-linecap="round"/>'
        f'<path d="M21 3v6h-6" stroke="{primary_fg}" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    copy_svg = _wrap(
        f'<rect x="9" y="9" width="11" height="11" rx="2.2" stroke="{primary_fg}" '
        'stroke-width="2.1"/>'
        f'<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" '
        f'stroke="{primary_fg}" stroke-width="2.1" stroke-linecap="round"/>'
    )
    eye_open_svg = _wrap(
        f'<path d="M2 12s3.8-7 10-7 10 7 10 7-3.8 7-10 7-10-7-10-7Z" '
        f'stroke="{secondary_fg}" stroke-width="2.1" stroke-linejoin="round"/>'
        f'<circle cx="12" cy="12" r="3" stroke="{secondary_fg}" stroke-width="2.1"/>'
    )
    eye_closed_svg = _wrap(
        f'<path d="M3 3l18 18" stroke="{secondary_fg}" stroke-width="2.1" stroke-linecap="round"/>'
        f'<path d="M10.6 5.2A10.7 10.7 0 0 1 12 5c6.2 0 10 7 10 7a17.6 17.6 0 0 1-3.4 4.4" '
        f'stroke="{secondary_fg}" stroke-width="2.1" stroke-linecap="round"/>'
        f'<path d="M6.6 6.6C3.9 8.5 2 12 2 12s3.8 7 10 7c1.6 0 3.1-.4 4.4-1" '
        f'stroke="{secondary_fg}" stroke-width="2.1" stroke-linecap="round"/>'
    )
    batch_svg = _wrap(
        f'<rect x="3" y="4" width="18" height="4" rx="1.2" stroke="{secondary_fg}" '
        'stroke-width="2"/>'
        f'<rect x="3" y="10" width="18" height="4" rx="1.2" stroke="{secondary_fg}" '
        'stroke-width="2"/>'
        f'<rect x="3" y="16" width="18" height="4" rx="1.2" stroke="{secondary_fg}" '
        'stroke-width="2"/>'
    )
    theme_svg = _wrap(
        f'<circle cx="12" cy="12" r="4.5" stroke="{secondary_fg}" stroke-width="2.1"/>'
        f'<path d="M12 2v2.5M12 19.5V22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M2 12h2.5'
        f'M19.5 12H22M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" '
        f'stroke="{secondary_fg}" stroke-width="2" stroke-linecap="round"/>'
    )
    help_svg = _wrap(
        f'<circle cx="12" cy="12" r="9.5" stroke="{secondary_fg}" stroke-width="2"/>'
        f'<path d="M9.5 9.2a2.7 2.7 0 0 1 5.1.8c0 1.9-2.6 2.3-2.6 4.1" '
        f'stroke="{secondary_fg}" stroke-width="2" stroke-linecap="round"/>'
        f'<circle cx="12" cy="17.5" r="1.2" fill="{secondary_fg}"/>'
    )
    wipe_svg = _wrap(
        f'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" stroke="{danger_fg}" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    return UiIconSet(
        generate=render_svg(generate_svg, scale=icon_scale),
        copy=render_svg(copy_svg, scale=icon_scale),
        eye_open=render_svg(eye_open_svg, scale=icon_scale),
        eye_closed=render_svg(eye_closed_svg, scale=icon_scale),
        batch=render_svg(batch_svg, scale=icon_scale),
        theme=render_svg(theme_svg, scale=icon_scale),
        help_icon=render_svg(help_svg, scale=icon_scale),
        wipe=render_svg(wipe_svg, scale=icon_scale),
    )
