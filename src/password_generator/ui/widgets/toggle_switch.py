"""High-DPI anti-aliased SVG pill toggle switch widget bound to a ``tk.BooleanVar``."""

import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from tkinter import ttk

from password_generator.ui.icons import render_svg
from password_generator.ui.theme import ThemePalette


class ToggleSwitch(ttk.Label):
    """Crisp anti-aliased pill toggle switch with keyboard support and theme adaptation."""

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
        self._variable = variable
        self._palette = palette
        self._command = command

        self._img_on: tk.PhotoImage | None = None
        self._img_off: tk.PhotoImage | None = None

        super().__init__(
            master,
            style="Card.TLabel",
            cursor="hand2",
            takefocus=True,
        )

        self.bind("<Button-1>", self._on_toggle)
        self.bind("<space>", self._on_toggle)
        self.bind("<Return>", self._on_toggle)
        self._trace_name = self._variable.trace_add("write", lambda *_: self._refresh_image())
        self.bind("<Destroy>", self._on_destroy)

        self._rebuild_images()
        self._refresh_image()

    def set_palette(self, palette: ThemePalette) -> None:
        """Update surface colors and re-rasterize anti-aliased switch SVGs on theme change."""
        self._palette = palette
        self.configure(style="Card.TLabel")
        self._rebuild_images()
        self._refresh_image()

    def _rebuild_images(self) -> None:
        p = self._palette
        # 40x22 logical viewBox rasterized smoothly via Tk 9.0 SVG engine.
        svg_on = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="22" viewBox="0 0 40 22">'
            f'<rect x="1" y="1" width="38" height="20" rx="10" fill="{p.accent}" '
            f'stroke="{p.accent}" stroke-width="1"/>'
            f'<circle cx="29" cy="11" r="7.2" fill="{p.switch_knob}"/>'
            "</svg>"
        )
        svg_off = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="22" viewBox="0 0 40 22">'
            f'<rect x="1" y="1" width="38" height="20" rx="10" fill="{p.switch_off}" '
            f'stroke="{p.border}" stroke-width="1"/>'
            f'<circle cx="11" cy="11" r="7.2" fill="{p.switch_knob}"/>'
            "</svg>"
        )
        self._img_on = render_svg(svg_on, scale=self._scale)
        self._img_off = render_svg(svg_off, scale=self._scale)

    def _refresh_image(self) -> None:
        img = self._img_on if self._variable.get() else self._img_off
        if img is not None:
            self.configure(image=img)

    def _on_toggle(self, _event: tk.Event[tk.Misc] | None = None) -> str:
        self._variable.set(not self._variable.get())
        if self._command is not None:
            self._command()
        return "break"

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self:
            with suppress(tk.TclError):
                self._variable.trace_remove("write", self._trace_name)
            self._img_on = None
            self._img_off = None
