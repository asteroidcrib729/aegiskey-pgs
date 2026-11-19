"""High-DPI Tkinter GUI layer for the Password Generator application."""

from password_generator.ui.dpi import configure_tk_scaling, enable_high_dpi_awareness
from password_generator.ui.main_window import PasswordGeneratorWindow

__all__ = [
    "PasswordGeneratorWindow",
    "configure_tk_scaling",
    "enable_high_dpi_awareness",
]
