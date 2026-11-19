"""Windows Per-Monitor DPI awareness, Tk scaling synchronization, and native dark titlebar."""

import ctypes
import sys
import tkinter as tk
from contextlib import suppress

_DEFAULT_DPI: float = 96.0
_DWMWA_USE_IMMERSIVE_DARK_MODE: int = 20


def enable_high_dpi_awareness() -> None:
    """Enable Per-Monitor v2 DPI awareness on Windows before creating the Tk root window."""
    if sys.platform != "win32":
        return

    windll = getattr(ctypes, "windll", None)
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
    if sys.platform == "win32":
        windll = getattr(ctypes, "windll", None)
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


def apply_windows_titlebar_theme(window: tk.Wm, *, dark: bool) -> None:
    """Ask Windows DWM to render an immersive dark or light native titlebar."""
    if sys.platform != "win32":
        return

    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return

    with suppress(AttributeError, OSError, tk.TclError, ValueError):
        if isinstance(window, tk.Misc):
            window.update_idletasks()
            target_id = window.winfo_id()
            # For top-level Tk windows on Windows, GetParent resolves the outer frame HWND.
            hwnd = int(windll.user32.GetParent(target_id)) or target_id
            value = ctypes.c_int(1 if dark else 0)
            windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(_DWMWA_USE_IMMERSIVE_DARK_MODE),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
