"""Ephemeral RAM-only Session Vault panel backed by native Treeview and touchpad gestures."""

import tkinter as tk
from collections.abc import Callable
from contextlib import suppress
from tkinter import ttk

from password_generator.services.history import HistoryEntry
from password_generator.ui.theme import FontSet, ThemePalette
from password_generator.ui.widgets.scrollable import unpack_touchpad_deltas


class SessionVaultPanel(ttk.Frame):
    """Native tabular session history with masking, touchpad scrolling, copy, and RAM wipe."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: ThemePalette,
        fonts: FontSet,
        scale: float = 1.0,
        on_copy_entry: Callable[[str], None],
        on_inspect_entry: Callable[[str], None],
        on_wipe: Callable[[], None],
        wipe_icon: tk.PhotoImage | None = None,
    ) -> None:
        super().__init__(master, style="Card.TFrame")
        self._palette = palette
        self._fonts = fonts
        self._scale = max(1.0, scale)
        self._on_copy_entry = on_copy_entry
        self._on_inspect_entry = on_inspect_entry
        self._on_wipe = on_wipe
        self._entries: tuple[HistoryEntry, ...] = ()
        self._iid_to_value: dict[str, str] = {}
        self._revealed = tk.BooleanVar(value=False)
        self._scroll_accum: float = 0.0

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, round(5 * self._scale)))
        header.columnconfigure(0, weight=1)

        self._title_label = ttk.Label(
            header,
            text="Session Vault (RAM-Only · 0)",
            style="CardHeading.TLabel",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        actions = ttk.Frame(header, style="Card.TFrame")
        actions.grid(row=0, column=1, sticky="e")

        self._reveal_btn = ttk.Button(
            actions,
            text="Reveal",
            style="BatchPill.TButton",
            command=self._toggle_reveal,
        )
        self._reveal_btn.grid(row=0, column=0, padx=(0, round(4 * self._scale)))

        ttk.Button(
            actions,
            text="Load",
            style="BatchPill.TButton",
            command=self._inspect_selected,
        ).grid(row=0, column=1, padx=(0, round(4 * self._scale)))

        ttk.Button(
            actions,
            text="Copy",
            style="BatchPill.TButton",
            command=self._copy_selected,
        ).grid(row=0, column=2, padx=(0, round(4 * self._scale)))

        self._wipe_btn = ttk.Button(
            actions,
            text="Wipe",
            style="Danger.TButton",
            command=self._on_wipe,
        )
        if wipe_icon is not None:
            self._wipe_btn.configure(image=wipe_icon, compound="left")
        self._wipe_btn.grid(row=0, column=3)

        self.tree = ttk.Treeview(
            self,
            columns=("secret", "mode", "bits", "time"),
            show="headings",
            selectmode="browse",
            height=2,
            style="Vault.Treeview",
        )
        self.tree.heading("secret", text="Secret", anchor="w")
        self.tree.heading("mode", text="Mode", anchor="w")
        self.tree.heading("bits", text="Entropy", anchor="e")
        self.tree.heading("time", text="Time", anchor="e")

        s = self._scale
        self.tree.column(
            "secret", width=round(170 * s), minwidth=round(96 * s), stretch=True, anchor="w"
        )
        self.tree.column(
            "mode", width=round(82 * s), minwidth=round(64 * s), stretch=False, anchor="w"
        )
        self.tree.column(
            "bits", width=round(60 * s), minwidth=round(48 * s), stretch=False, anchor="e"
        )
        self.tree.column(
            "time", width=round(60 * s), minwidth=round(48 * s), stretch=False, anchor="e"
        )

        self.tree.grid(row=1, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview,
            style="App.Vertical.TScrollbar",
        )
        self.scrollbar.grid(row=1, column=1, sticky="ns", padx=(round(4 * s), 0))
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.bind("<Double-1>", lambda _e: self._copy_selected())
        self.tree.bind("<Return>", lambda _e: self._inspect_selected())
        for widget in (self, self._title_label, self.tree, self.scrollbar):
            with suppress(tk.TclError):
                widget.bind("<TouchpadScroll>", self._on_touchpad_scroll)
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", lambda _e: self._scroll_units(-1))
            widget.bind("<Button-5>", lambda _e: self._scroll_units(1))

    def set_palette(self, palette: ThemePalette, *, wipe_icon: tk.PhotoImage | None = None) -> None:
        """Update icon styling on theme change."""
        self._palette = palette
        if wipe_icon is not None:
            self._wipe_btn.configure(image=wipe_icon, compound="left")

    def set_entries(self, entries: tuple[HistoryEntry, ...]) -> None:
        """Replace displayed entries and update vault header count."""
        self._entries = entries
        self._title_label.configure(text=f"Session Vault (RAM-Only · {len(entries)})")
        self._render_rows()

    def _toggle_reveal(self) -> None:
        self._revealed.set(not self._revealed.get())
        self._reveal_btn.configure(text="Mask" if self._revealed.get() else "Reveal")
        self._render_rows()

    @staticmethod
    def _mask_secret(secret: str) -> str:
        if len(secret) <= 4:
            return "•" * len(secret)
        preview = "•" * min(14, len(secret) - 2)
        return f"{preview}{secret[-2:]}"

    def _selected_value(self) -> str | None:
        selection = self.tree.selection()
        if selection and selection[0] in self._iid_to_value:
            return self._iid_to_value[selection[0]]
        if self._entries:
            return self._entries[0].value
        return None

    def _copy_selected(self) -> None:
        val = self._selected_value()
        if val is not None:
            self._on_copy_entry(val)

    def _inspect_selected(self) -> None:
        val = self._selected_value()
        if val is not None:
            self._on_inspect_entry(val)

    def _scroll_units(self, units: int) -> str:
        if units != 0:
            self.tree.yview_scroll(units, "units")
        return "break"

    def _on_touchpad_scroll(self, event: tk.Event[tk.Misc]) -> str:
        _dx, dy = unpack_touchpad_deltas(event.delta)
        if dy != 0:
            step_px = max(18.0, 26.0 * self._scale)
            self._scroll_accum += -dy / step_px
            whole = int(self._scroll_accum)
            if whole != 0:
                self._scroll_accum -= whole
                self.tree.yview_scroll(whole, "units")
        return "break"

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> str:
        self._scroll_accum += -(event.delta / 120.0) * 2.0
        whole = int(self._scroll_accum)
        if whole != 0:
            self._scroll_accum -= whole
            self.tree.yview_scroll(whole, "units")
        return "break"

    def _render_rows(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._iid_to_value.clear()

        revealed = self._revealed.get()
        for idx, entry in enumerate(self._entries):
            display_text = entry.value if revealed else self._mask_secret(entry.value)
            if len(display_text) > 34:
                display_text = f"{display_text[:31]}..."
            iid = f"entry-{idx}"
            self._iid_to_value[iid] = entry.value
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    display_text,
                    entry.mode.upper(),
                    f"{entry.entropy_bits:.0f} bits",
                    entry.created_at,
                ),
            )
