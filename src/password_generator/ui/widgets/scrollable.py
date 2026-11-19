"""Smooth, flicker-free scrollable frame supporting Tk 9.0 touchpad two-finger gestures."""

import tkinter as tk
from contextlib import suppress
from tkinter import ttk
from typing import ClassVar


def unpack_touchpad_deltas(packed_delta: int) -> tuple[int, int]:
    """Decode Tk 9.0 ``<TouchpadScroll>`` packed 32-bit delta into signed ``(dx, dy)`` pixels."""
    dx_raw = (packed_delta >> 16) & 0xFFFF
    dy_raw = packed_delta & 0xFFFF
    dx = dx_raw if dx_raw < 0x8000 else dx_raw - 0x10000
    dy = dy_raw if dy_raw < 0x8000 else dy_raw - 0x10000
    return (dx, dy)


def _is_descendant(widget: tk.Misc | None, ancestor: tk.Misc) -> bool:
    current = widget
    while current is not None:
        if current is ancestor:
            return True
        parent_name = current.winfo_parent()
        if not parent_name:
            return False
        with suppress(KeyError, tk.TclError):
            current = current.nametowidget(parent_name)
            continue
        return False
    return False


class TouchpadScrollableFrame(ttk.Frame):
    """Scrollable viewport with pixel-accurate touchpad scrolling and coalesced resize sync."""

    _registered_roots: ClassVar[set[int]] = set()
    _instances: ClassVar[list[TouchpadScrollableFrame]] = []

    def __init__(
        self,
        master: tk.Misc,
        *,
        bg: str,
        height: int | None = None,
        scrollbar_style: str = "App.Vertical.TScrollbar",
    ) -> None:
        super().__init__(master, style="Card.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=bg,
            highlightthickness=0,
            bd=0,
            yscrollincrement=1,
        )
        if height is not None:
            self.canvas.configure(height=height)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            style=scrollbar_style,
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content = ttk.Frame(self.canvas, style="Card.TFrame")
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self._last_canvas_width: int = 0
        self._sync_after_id: str | None = None
        self._wheel_remainder: float = 0.0

        self.content.bind("<Configure>", self._schedule_layout_sync)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind("<Destroy>", self._on_destroy)

        TouchpadScrollableFrame._instances.append(self)
        self._ensure_root_scroll_bindings()

    def set_background(self, bg: str) -> None:
        """Update canvas background color to match the active theme surface."""
        self.canvas.configure(bg=bg)

    def _ensure_root_scroll_bindings(self) -> None:
        toplevel = self.winfo_toplevel()
        root_key = toplevel.winfo_id()
        if root_key in TouchpadScrollableFrame._registered_roots:
            return
        TouchpadScrollableFrame._registered_roots.add(root_key)

        with suppress(tk.TclError):
            toplevel.bind_all("<TouchpadScroll>", TouchpadScrollableFrame._dispatch_touchpad)
        toplevel.bind_all("<MouseWheel>", TouchpadScrollableFrame._dispatch_mousewheel)
        toplevel.bind_all("<Button-4>", TouchpadScrollableFrame._dispatch_linux_up)
        toplevel.bind_all("<Button-5>", TouchpadScrollableFrame._dispatch_linux_down)

    @classmethod
    def _find_target(cls, event: tk.Event[tk.Misc]) -> TouchpadScrollableFrame | None:
        widget: tk.Misc | None = event.widget if isinstance(event.widget, tk.Misc) else None
        if widget is None or isinstance(widget, ttk.Scrollbar):
            return None

        # Choose the innermost scrollable frame whose content actually overflows.
        candidates: list[TouchpadScrollableFrame] = []
        for inst in list(cls._instances):
            try:
                if not inst.winfo_exists():
                    continue
            except tk.TclError:
                continue
            if _is_descendant(widget, inst):
                candidates.append(inst)

        # Reverse order checks innermost nested container first.
        for inst in reversed(candidates):
            if inst.can_scroll():
                return inst
        return candidates[-1] if candidates else None

    @classmethod
    def _dispatch_touchpad(cls, event: tk.Event[tk.Misc]) -> str | None:
        target = cls._find_target(event)
        if target is None:
            return None
        _dx, dy = unpack_touchpad_deltas(event.delta)
        if dy != 0 and target.can_scroll():
            target.scroll_pixels(-dy)
            return "break"
        return None

    @classmethod
    def _dispatch_mousewheel(cls, event: tk.Event[tk.Misc]) -> str | None:
        target = cls._find_target(event)
        if target is None or not target.can_scroll():
            return None
        target.scroll_wheel_delta(event.delta)
        return "break"

    @classmethod
    def _dispatch_linux_up(cls, event: tk.Event[tk.Misc]) -> str | None:
        target = cls._find_target(event)
        if target is None or not target.can_scroll():
            return None
        target.scroll_pixels(-42)
        return "break"

    @classmethod
    def _dispatch_linux_down(cls, event: tk.Event[tk.Misc]) -> str | None:
        target = cls._find_target(event)
        if target is None or not target.can_scroll():
            return None
        target.scroll_pixels(42)
        return "break"

    def can_scroll(self) -> bool:
        """Return True when the inner content is taller than the visible viewport."""
        return self.content.winfo_reqheight() > max(self.canvas.winfo_height(), 1)

    def scroll_pixels(self, pixels: int) -> None:
        """Scroll vertically by exact pixel count, clamped cleanly inside content bounds."""
        if not self.can_scroll() or pixels == 0:
            return
        self.canvas.yview_scroll(pixels, "units")

    def scroll_wheel_delta(self, delta: int) -> None:
        """Accumulate mouse-wheel or precision wheel deltas so small increments never drop."""
        # Standard mouse notch = 120 -> 48 px; fractional touchpad wheel deltas accumulate cleanly.
        self._wheel_remainder += -(delta / 120.0) * 48.0
        whole_pixels = int(self._wheel_remainder)
        if whole_pixels != 0:
            self._wheel_remainder -= whole_pixels
            self.scroll_pixels(whole_pixels)

    def sync_scroll_region(self) -> None:
        """Refresh canvas scrollregion and reset scroll position when content fits viewport."""
        self._sync_after_id = None
        with suppress(tk.TclError):
            bbox = self.canvas.bbox("all")
            if bbox is not None:
                self.canvas.configure(scrollregion=bbox)
            if not self.can_scroll():
                self.canvas.yview_moveto(0.0)

    def _schedule_layout_sync(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._sync_after_id is None:
            self._sync_after_id = self.after_idle(self.sync_scroll_region)

    def _on_canvas_configure(self, event: tk.Event[tk.Misc]) -> None:
        new_width = event.width
        if new_width > 1 and new_width != self._last_canvas_width:
            self._last_canvas_width = new_width
            self.canvas.itemconfigure(self._window_id, width=new_width)
        self._schedule_layout_sync()

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is not self:
            return
        if self._sync_after_id is not None:
            with suppress(tk.TclError):
                self.after_cancel(self._sync_after_id)
            self._sync_after_id = None
        if self in TouchpadScrollableFrame._instances:
            TouchpadScrollableFrame._instances.remove(self)
