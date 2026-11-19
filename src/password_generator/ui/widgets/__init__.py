"""Custom high-DPI Tkinter canvas and composite widgets."""

from password_generator.ui.widgets.history_panel import SessionVaultPanel
from password_generator.ui.widgets.strength_meter import StrengthMeterCanvas
from password_generator.ui.widgets.toggle_switch import ToggleSwitch

__all__ = [
    "SessionVaultPanel",
    "StrengthMeterCanvas",
    "ToggleSwitch",
]
