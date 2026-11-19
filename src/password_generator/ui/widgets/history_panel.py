"""Ephemeral RAM-only Session Vault panel displaying recently generated secrets safely."""

import tkinter as tk
from collections.abc import Callable
from functools import partial
from tkinter import ttk

from password_generator.services.history import HistoryEntry
from password_generator.ui.theme import FontSet, ThemePalette


class SessionVaultPanel(ttk.Frame):
    """Scrollable session history table with default masking, copy, and instant RAM wipe."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: ThemePalette,
        fonts: FontSet,
        on_copy_entry: Callable[[str], None],
        on_inspect_entry: Callable[[str], None],
        on_wipe: Callable[[], None],
    ) -> None:
        super().__init__(master, style="Card.TFrame")
        self._palette = palette
        self._fonts = fonts
        self._on_copy_entry = on_copy_entry
        self._on_inspect_entry = on_inspect_entry
        self._on_wipe = on_wipe
        self._entries: tuple[HistoryEntry, ...] = ()
        self._revealed = tk.BooleanVar(value=False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
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
        self._reveal_btn.grid(row=0, column=0, padx=(0, 6))

        self._wipe_btn = ttk.Button(
            actions,
            text="Wipe Vault",
            style="Danger.TButton",
            command=self._on_wipe,
        )
        self._wipe_btn.grid(row=0, column=1)

        # Canvas-based scrollable row container for clean custom row styling.
        list_wrap = ttk.Frame(self, style="Card.TFrame")
        list_wrap.grid(row=1, column=0, sticky="nsew")
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            list_wrap,
            bg=palette.bg_surface,
            highlightthickness=0,
            bd=0,
            height=180,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            list_wrap,
            orient="vertical",
            command=self._canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=scrollbar.set)

        self._rows_frame = ttk.Frame(self._canvas, style="Card.TFrame")
        self._window_id = self._canvas.create_window((0, 0), window=self._rows_frame, anchor="nw")

        self._rows_frame.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfigure(self._window_id, width=e.width),
        )

    def set_palette(self, palette: ThemePalette) -> None:
        """Update canvas background on theme change and re-render rows."""
        self._palette = palette
        self._canvas.configure(bg=palette.bg_surface)
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
            return

        revealed = self._revealed.get()
        for row_idx, entry in enumerate(self._entries):
            row_card = ttk.Frame(self._rows_frame, style="Elevated.TFrame", padding=(10, 7))
            row_card.grid(row=row_idx, column=0, sticky="ew", pady=(0, 6))
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
