"""Ephemeral RAM-only Session Vault panel with smooth touchpad scrolling and masking."""

import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import ttk

from password_generator.services.history import HistoryEntry
from password_generator.ui.theme import FontSet, ThemePalette
from password_generator.ui.widgets.scrollable import TouchpadScrollableFrame


class SessionVaultPanel(ttk.Frame):
    """Scrollable session history table with default masking, copy, and instant RAM wipe."""

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
        self._revealed = tk.BooleanVar(value=False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, round(6 * self._scale)))
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
            style="Secondary.TButton",
            command=self._toggle_reveal,
        )
        self._reveal_btn.grid(row=0, column=0, padx=(0, round(5 * self._scale)))

        self._wipe_btn = ttk.Button(
            actions,
            text="Wipe Vault",
            style="Danger.TButton",
            command=self._on_wipe,
        )
        if wipe_icon is not None:
            self._wipe_btn.configure(image=wipe_icon, compound="left")
        self._wipe_btn.grid(row=0, column=1)

        self._scroll_area = TouchpadScrollableFrame(
            self,
            bg=palette.bg_surface,
            height=round(130 * self._scale),
        )
        self._scroll_area.grid(row=1, column=0, sticky="nsew")
        self._rows_frame = self._scroll_area.content
        self._rows_frame.columnconfigure(0, weight=1)

    def set_palette(self, palette: ThemePalette, *, wipe_icon: tk.PhotoImage | None = None) -> None:
        """Update canvas background on theme change and re-render rows."""
        self._palette = palette
        self._scroll_area.set_background(palette.bg_surface)
        if wipe_icon is not None:
            self._wipe_btn.configure(image=wipe_icon, compound="left")
        self._render_rows()

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

    def _render_rows(self) -> None:
        for child in self._rows_frame.winfo_children():
            child.destroy()

        if not self._entries:
            empty = ttk.Label(
                self._rows_frame,
                text="No secrets generated yet in this session.",
                style="CardMuted.TLabel",
            )
            empty.grid(row=0, column=0, sticky="w", pady=12)
            self._scroll_area.sync_scroll_region()
            return

        revealed = self._revealed.get()
        pad_x = round(9 * self._scale)
        pad_y = round(6 * self._scale)
        row_gap = round(5 * self._scale)
        for row_idx, entry in enumerate(self._entries):
            row_card = ttk.Frame(self._rows_frame, style="Elevated.TFrame", padding=(pad_x, pad_y))
            row_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, row_gap))
            row_card.columnconfigure(0, weight=1)

            display_text = entry.value if revealed else self._mask_secret(entry.value)
            if len(display_text) > 34:
                display_text = f"{display_text[:31]}..."

            secret_lbl = ttk.Label(row_card, text=display_text, style="Mono.TLabel")
            secret_lbl.grid(row=0, column=0, sticky="w")

            meta_text = f"{entry.created_at} · {entry.mode.upper()} · {entry.entropy_bits:.0f} bits"
            meta_lbl = ttk.Label(row_card, text=meta_text, style="ElevatedMuted.TLabel")
            meta_lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))

            btn_box = ttk.Frame(row_card, style="Elevated.TFrame")
            btn_box.grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 0))

            inspect_btn = ttk.Button(
                btn_box,
                text="Load",
                style="Secondary.TButton",
                command=partial(self._on_inspect_entry, entry.value),
            )
            inspect_btn.grid(row=0, column=0, padx=(0, 4))

            copy_btn = ttk.Button(
                btn_box,
                text="Copy",
                style="Secondary.TButton",
                command=partial(self._on_copy_entry, entry.value),
            )
            copy_btn.grid(row=0, column=1)

        self._scroll_area.sync_scroll_region()
