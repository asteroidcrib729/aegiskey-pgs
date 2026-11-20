"""Windows Per-Monitor DPI awareness, Tk scaling synchronization, and native DWM polish."""

import ctypes
import sys
import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from ctypes import wintypes
from typing import Any

_DEFAULT_DPI: float = 96.0
_DWMWA_USE_IMMERSIVE_DARK_MODE: int = 20
_GCLP_HBRBACKGROUND: int = -10
_GWL_EXSTYLE: int = -20
_WS_EX_LAYERED: int = 0x00080000
_SWP_NOSIZE: int = 0x0001
_SWP_NOMOVE: int = 0x0002
_SWP_NOZORDER: int = 0x0004
_SWP_NOACTIVATE: int = 0x0010
_SWP_FRAMECHANGED: int = 0x0020
_WM_SETREDRAW: int = 0x000B
_RDW_INVALIDATE: int = 0x0001
_RDW_ERASE: int = 0x0004
_RDW_ALLCHILDREN: int = 0x0080
_RDW_UPDATENOW: int = 0x0100
_RDW_FRAME: int = 0x0400

_ACTIVE_BRUSHES: dict[int, int] = {}


def _win_dll() -> Any:
    """Return ``ctypes.windll`` on Windows, or ``None`` on non-Windows platforms."""
    if sys.platform != "win32":
        return None
    return getattr(ctypes, "windll", None)


def enable_high_dpi_awareness() -> None:
    """Enable Per-Monitor v2 DPI awareness on Windows before creating the Tk root window."""
    windll = _win_dll()
    if windll is None:
        return

    with suppress(AttributeError, OSError):
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        user32 = windll.user32
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return

    with suppress(AttributeError, OSError):
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        windll.shcore.SetProcessDpiAwareness(2)
        return

    with suppress(AttributeError, OSError):
        windll.user32.SetProcessDPIAware()


def query_window_dpi(window: tk.Misc) -> float:
    """Return the active display DPI for ``window``, defaulting to 96.0 if unavailable."""
    windll = _win_dll()
    if windll is not None:
        with suppress(AttributeError, OSError, tk.TclError):
            hwnd = window.winfo_id()
            dpi = float(windll.user32.GetDpiForWindow(hwnd))
            if dpi >= 72.0:
                return dpi

    with suppress(tk.TclError):
        measured = float(window.winfo_fpixels("1i"))
        if measured >= 72.0:
            return measured

    return _DEFAULT_DPI


def configure_tk_scaling(root: tk.Misc) -> float:
    """Synchronize Tcl/Tk scaling to monitor DPI and return the logical scale multiplier."""
    dpi = query_window_dpi(root)
    with suppress(tk.TclError):
        root.tk.call("tk", "scaling", dpi / 72.0)
    return max(1.0, dpi / _DEFAULT_DPI)


def _resolve_outer_hwnd(window: tk.Misc) -> int:
    windll = _win_dll()
    if windll is None:
        return 0
    target_id = window.winfo_id()
    parent_hwnd = int(windll.user32.GetParent(target_id))
    return parent_hwnd or target_id


def _hex_to_colorref(hex_color: str) -> int:
    cleaned = hex_color.lstrip("#")
    if len(cleaned) != 6:
        return 0x00170E0A
    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)
    return (b << 16) | (g << 8) | r


def apply_windows_surface_polish(
    window: tk.Wm,
    *,
    bg_hex: str,
    child_bg_hex: str | None = None,
    dark: bool,
) -> None:
    """Configure DWM titlebar and class background brushes to prevent white erase flashes."""
    if not isinstance(window, tk.Misc):
        return

    windll = _win_dll()
    if windll is None:
        return

    with suppress(AttributeError, OSError, tk.TclError, ValueError):
        window.update_idletasks()
        inner_hwnd = window.winfo_id()
        outer_hwnd = _resolve_outer_hwnd(window)

        targets = [(outer_hwnd, bg_hex)]
        if inner_hwnd and inner_hwnd != outer_hwnd:
            targets.append((inner_hwnd, child_bg_hex or bg_hex))

        create_brush = windll.gdi32.CreateSolidBrush
        create_brush.argtypes = [wintypes.DWORD]
        create_brush.restype = ctypes.c_void_p

        delete_obj = windll.gdi32.DeleteObject
        delete_obj.argtypes = [ctypes.c_void_p]
        delete_obj.restype = ctypes.c_int

        set_class_long = windll.user32.SetClassLongPtrW
        set_class_long.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        set_class_long.restype = ctypes.c_void_p

        for hwnd, hex_val in targets:
            colorref = _hex_to_colorref(hex_val)
            old_brush = _ACTIVE_BRUSHES.pop(hwnd, 0)
            new_brush = int(create_brush(colorref) or 0)
            if new_brush:
                set_class_long(hwnd, _GCLP_HBRBACKGROUND, new_brush)
                _ACTIVE_BRUSHES[hwnd] = new_brush
            if old_brush:
                delete_obj(old_brush)

        value = ctypes.c_int(1 if dark else 0)
        windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(outer_hwnd),
            ctypes.c_uint(_DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )


def strip_layered_window_flag(window: tk.Misc) -> None:
    """Remove ``WS_EX_LAYERED`` after startup reveal so Win32 resize compositing stays native."""
    windll = _win_dll()
    if windll is None:
        return
    with suppress(AttributeError, OSError, tk.TclError):
        outer_hwnd = _resolve_outer_hwnd(window)
        exstyle = int(windll.user32.GetWindowLongW(outer_hwnd, _GWL_EXSTYLE))
        if exstyle & _WS_EX_LAYERED:
            windll.user32.SetWindowLongW(
                outer_hwnd,
                _GWL_EXSTYLE,
                exstyle & ~_WS_EX_LAYERED,
            )
            windll.user32.SetWindowPos(
                ctypes.c_void_p(outer_hwnd),
                None,
                0,
                0,
                0,
                0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
            )


def atomic_resize_redraw(window: tk.Misc, layout_callback: Callable[[], None]) -> None:
    """Suppress intermediate child repaints during layout, then paint atomically once."""
    windll = _win_dll()
    if windll is None:
        layout_callback()
        return

    outer_hwnd = 0
    with suppress(AttributeError, OSError, tk.TclError):
        outer_hwnd = _resolve_outer_hwnd(window)

    if not outer_hwnd:
        layout_callback()
        return

    user32 = windll.user32
    hwnd_ptr = ctypes.c_void_p(outer_hwnd)
    user32.SendMessageW(hwnd_ptr, _WM_SETREDRAW, 0, 0)
    try:
        layout_callback()
    finally:
        user32.SendMessageW(hwnd_ptr, _WM_SETREDRAW, 1, 0)
        flags = _RDW_INVALIDATE | _RDW_ERASE | _RDW_ALLCHILDREN | _RDW_UPDATENOW | _RDW_FRAME
        user32.RedrawWindow(hwnd_ptr, None, None, ctypes.c_uint(flags))


def release_window_brushes(window: tk.Misc) -> None:
    """Clean up GDI solid brushes allocated for ``window`` on teardown."""
    windll = _win_dll()
    if windll is None:
        return
    with suppress(AttributeError, OSError, tk.TclError):
        inner_hwnd = window.winfo_id()
        outer_hwnd = _resolve_outer_hwnd(window)
        for hwnd in {outer_hwnd, inner_hwnd}:
            brush = _ACTIVE_BRUSHES.pop(hwnd, 0)
            if brush:
                windll.gdi32.DeleteObject(ctypes.c_void_p(brush))
