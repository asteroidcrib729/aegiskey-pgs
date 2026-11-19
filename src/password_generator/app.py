"""Application bootstrapper wiring DPI awareness, flicker-free startup, and window lifecycle."""

import tkinter as tk
from contextlib import suppress

from password_generator.services.settings_store import SettingsStore
from password_generator.ui.dpi import enable_high_dpi_awareness
from password_generator.ui.main_window import PasswordGeneratorWindow


def run_application(*, settings_store: SettingsStore | None = None) -> int:
    """Launch the high-DPI Tkinter Password Generator desktop application cleanly."""
    enable_high_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    with suppress(tk.TclError):
        root.attributes("-alpha", 0.0)

    window = PasswordGeneratorWindow(root, settings_store=settings_store)
    window.present()
    root.mainloop()
    return 0
