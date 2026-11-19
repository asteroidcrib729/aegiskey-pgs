"""Application bootstrapper wiring DPI awareness, root Tk lifecycle, and window controller."""

import tkinter as tk

from password_generator.services.settings_store import SettingsStore
from password_generator.ui.dpi import enable_high_dpi_awareness
from password_generator.ui.main_window import PasswordGeneratorWindow


def run_application(*, settings_store: SettingsStore | None = None) -> int:
    """Launch the high-DPI Tkinter Password Generator desktop application."""
    enable_high_dpi_awareness()
    root = tk.Tk()
    PasswordGeneratorWindow(root, settings_store=settings_store)
    root.mainloop()
    return 0
