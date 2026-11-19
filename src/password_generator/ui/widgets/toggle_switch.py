"""High-DPI crisp Canvas pill toggle switch widget bound to a ``tk.BooleanVar``."""

import tkinter as tk
from collections.abc import Callable

from password_generator.ui.theme import ThemePalette


class ToggleSwitch(tk.Canvas):
    """Accessible pill toggle switch with keyboard support and theme adaptation."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        variable: tk.BooleanVar,
        palette: ThemePalette,
        scale: float = 1.0,
        command: Callable[[], None] | None = None,
    ) -> None:
        self._scale = max(1.0, scale)
        self._width = round(42 * self._scale)
        self._height = round(22 * self._scale)
        super().__init__(
            master,
            width=self._width,
            height=self._height,
            bg=palette.bg_surface,
            highlightthickness=1,
            highlightbackground=palette.bg_surface,
            highlightcolor=palette.border_focus,
            bd=0,
            cursor="hand2",
            takefocus=1,
        )
        self._variable = variable
        self._palette = palette
        self._command = command

        self.bind("<Button-1>", self._on_toggle)
        self.bind("<space>", self._on_toggle)
        self.bind("<Return>", self._on_toggle)
        self._trace_name = self._variable.trace_add("write", lambda *_: self._redraw())
        self.bind("<Destroy>", self._on_destroy)
        self._redraw()

    def set_palette(self, palette: ThemePalette) -> None:
        """Update surface colors when the application theme changes."""
        self._palette = palette
        self.configure(
            bg=palette.bg_surface,
            highlightbackground=palette.bg_surface,
            highlightcolor=palette.border_focus,
        )
        self._redraw()

    def _on_toggle(self, _event: tk.Event[tk.Misc] | None = None) -> str:
        self._variable.set(not self._variable.get())
        if self._command is not None:
            self._command()
        return "break"

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self:
            self._variable.trace_remove("write", self._trace_name)

    def _redraw(self) -> None:
        self.delete("all")
        checked = self._variable.get()
        track_color = self._palette.accent if checked else self._palette.switch_off
        pad = round(2 * self._scale)
        w = self._width
        h = self._height
        r = h - pad * 2

        # Pill background constructed from two end circles and center rectangle for crisp edges.
        self.create_oval(pad, pad, pad + r, pad + r, fill=track_color, outline=track_color)
        self.create_oval(w - pad - r, pad, w - pad, pad + r, fill=track_color, outline=track_color)
        self.create_rectangle(
            pad + r / 2,
            pad,
            w - pad - r / 2,
            pad + r,
            fill=track_color,
            outline=track_color,
        )

        knob_pad = round(4 * self._scale)
        knob_d = h - knob_pad * 2
        knob_x = (w - knob_pad - knob_d) if checked else knob_pad
        self.create_oval(
            knob_x,
            knob_pad,
            knob_x + knob_d,
            knob_pad + knob_d,
            fill=self._palette.switch_knob,
            outline=self._palette.switch_knob,
        )
