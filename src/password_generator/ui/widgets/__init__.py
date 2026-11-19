"""Custom high-DPI Tkinter canvas, SVG, and touchpad-scrollable composite widgets."""

from password_generator.ui.widgets.history_panel import SessionVaultPanel
from password_generator.ui.widgets.scrollable import TouchpadScrollableFrame, unpack_touchpad_deltas
from password_generator.ui.widgets.strength_meter import StrengthMeterCanvas
from password_generator.ui.widgets.toggle_switch import ToggleSwitch

__all__ = [
    "SessionVaultPanel",
    "StrengthMeterCanvas",
    "ToggleSwitch",
    "TouchpadScrollableFrame",
    "unpack_touchpad_deltas",
]
