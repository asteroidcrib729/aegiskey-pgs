"""Obsidian Dark and Studio Light design tokens, font resolution, and ttk styling."""

import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from tkinter import ttk
from typing import Literal

ThemeMode = Literal["dark", "light"]


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Semantic color palette for the desktop workstation interface."""

    mode: ThemeMode
    bg_app: str
    bg_surface: str
    bg_elevated: str
    bg_input: str
    border: str
    border_focus: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_fg: str
    success: str
    warning: str
    danger: str
    quantum: str
    switch_off: str
    switch_knob: str


DARK_PALETTE = ThemePalette(
    mode="dark",
    bg_app="#0B0F17",
    bg_surface="#121826",
    bg_elevated="#1A2234",
    bg_input="#0E1420",
    border="#26334D",
    border_focus="#38BDF8",
    text_primary="#F8FAFC",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    accent="#2563EB",
    accent_hover="#3B82F6",
    accent_fg="#FFFFFF",
    success="#10B981",
    warning="#F59E0B",
    danger="#F43F5E",
    quantum="#22D3EE",
    switch_off="#334155",
    switch_knob="#F8FAFC",
)

LIGHT_PALETTE = ThemePalette(
    mode="light",
    bg_app="#F1F5F9",
    bg_surface="#FFFFFF",
    bg_elevated="#F8FAFC",
    bg_input="#FFFFFF",
    border="#CBD5E1",
    border_focus="#0284C7",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#64748B",
    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_fg="#FFFFFF",
    success="#059669",
    warning="#D97706",
    danger="#E11D48",
    quantum="#0891B2",
    switch_off="#CBD5E1",
    switch_knob="#FFFFFF",
)


def get_palette(mode: ThemeMode) -> ThemePalette:
    """Return the ``ThemePalette`` corresponding to ``mode``."""
    return DARK_PALETTE if mode == "dark" else LIGHT_PALETTE


@dataclass(frozen=True, slots=True)
class FontSet:
    """Resolved cross-platform font families optimized for Windows 11 and HiDPI screens."""

    ui_family: str
    display_family: str
    mono_family: str

    @property
    def title(self) -> tuple[str, int, str]:
        return (self.display_family, 15, "bold")

    @property
    def subtitle(self) -> tuple[str, int]:
        return (self.ui_family, 9)

    @property
    def card_heading(self) -> tuple[str, int, str]:
        return (self.ui_family, 10, "bold")

    @property
    def body(self) -> tuple[str, int]:
        return (self.ui_family, 10)

    @property
    def body_bold(self) -> tuple[str, int, str]:
        return (self.ui_family, 10, "bold")

    @property
    def caption(self) -> tuple[str, int]:
        return (self.ui_family, 9)

    @property
    def caption_bold(self) -> tuple[str, int, str]:
        return (self.ui_family, 9, "bold")

    @property
    def secret_hero(self) -> tuple[str, int, str]:
        return (self.mono_family, 14, "bold")

    @property
    def mono_small(self) -> tuple[str, int]:
        return (self.mono_family, 9)


def _pick_font(available: set[str], candidates: tuple[str, ...], fallback: str) -> str:
    for name in candidates:
        if name in available:
            return name
    return fallback


def resolve_fonts(root: tk.Misc) -> FontSet:
    """Choose crisp installed fonts with clean fallbacks."""
    available = set(tkfont.families(root))
    ui_family = _pick_font(
        available,
        ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text"),
        "TkDefaultFont",
    )
    display_family = _pick_font(
        available,
        ("Segoe UI Variable Display", "Segoe UI", "Inter", "SF Pro Display"),
        ui_family,
    )
    mono_family = _pick_font(
        available,
        ("Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Consolas", "Courier New"),
        "TkFixedFont",
    )
    return FontSet(
        ui_family=ui_family,
        display_family=display_family,
        mono_family=mono_family,
    )


def apply_ttk_theme(style: ttk.Style, palette: ThemePalette, fonts: FontSet) -> None:
    """Apply cohesive modern widget styling on top of the ``clam`` ttk theme."""
    style.theme_use("clam")

    style.configure(
        ".",
        background=palette.bg_surface,
        foreground=palette.text_primary,
        bordercolor=palette.border,
        focuscolor=palette.border_focus,
        font=fonts.body,
    )

    style.configure("App.TFrame", background=palette.bg_app)
    style.configure("Card.TFrame", background=palette.bg_surface)
    style.configure("Elevated.TFrame", background=palette.bg_elevated)

    style.configure("App.TLabel", background=palette.bg_app, foreground=palette.text_primary)
    style.configure(
        "AppMuted.TLabel",
        background=palette.bg_app,
        foreground=palette.text_secondary,
        font=fonts.subtitle,
    )
    style.configure("Title.TLabel", background=palette.bg_app, font=fonts.title)

    style.configure("Card.TLabel", background=palette.bg_surface, foreground=palette.text_primary)
    style.configure(
        "CardHeading.TLabel",
        background=palette.bg_surface,
        foreground=palette.text_primary,
        font=fonts.card_heading,
    )
    style.configure(
        "CardMuted.TLabel",
        background=palette.bg_surface,
        foreground=palette.text_secondary,
        font=fonts.caption,
    )
    style.configure(
        "Elevated.TLabel",
        background=palette.bg_elevated,
        foreground=palette.text_primary,
        font=fonts.caption,
    )
    style.configure(
        "ElevatedMuted.TLabel",
        background=palette.bg_elevated,
        foreground=palette.text_secondary,
        font=fonts.caption,
    )
    style.configure(
        "Mono.TLabel",
        background=palette.bg_elevated,
        foreground=palette.text_primary,
        font=fonts.mono_small,
    )

    # Buttons
    style.configure(
        "Primary.TButton",
        background=palette.accent,
        foreground=palette.accent_fg,
        bordercolor=palette.accent,
        focusthickness=1,
        padding=(14, 8),
        font=fonts.body_bold,
        relief="flat",
    )
    style.map(
        "Primary.TButton",
        background=[("active", palette.accent_hover), ("pressed", palette.accent_hover)],
        bordercolor=[("active", palette.accent_hover)],
    )

    style.configure(
        "Secondary.TButton",
        background=palette.bg_elevated,
        foreground=palette.text_primary,
        bordercolor=palette.border,
        padding=(12, 8),
        font=fonts.caption_bold,
        relief="flat",
    )
    style.map(
        "Secondary.TButton",
        background=[("active", palette.border), ("pressed", palette.border)],
        bordercolor=[("focus", palette.border_focus)],
    )

    style.configure(
        "Danger.TButton",
        background=palette.bg_elevated,
        foreground=palette.danger,
        bordercolor=palette.border,
        padding=(10, 6),
        font=fonts.caption_bold,
        relief="flat",
    )
    style.map(
        "Danger.TButton",
        background=[("active", palette.danger), ("pressed", palette.danger)],
        foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
    )

    style.configure(
        "ModeActive.TButton",
        background=palette.accent,
        foreground=palette.accent_fg,
        bordercolor=palette.accent,
        padding=(10, 7),
        font=fonts.caption_bold,
        relief="flat",
    )
    style.map(
        "ModeActive.TButton",
        background=[("active", palette.accent_hover)],
    )

    style.configure(
        "ModeInactive.TButton",
        background=palette.bg_elevated,
        foreground=palette.text_secondary,
        bordercolor=palette.border,
        padding=(10, 7),
        font=fonts.caption_bold,
        relief="flat",
    )
    style.map(
        "ModeInactive.TButton",
        background=[("active", palette.border)],
        foreground=[("active", palette.text_primary)],
    )

    # Inputs
    style.configure(
        "App.TEntry",
        fieldbackground=palette.bg_input,
        foreground=palette.text_primary,
        insertcolor=palette.text_primary,
        bordercolor=palette.border,
        lightcolor=palette.border,
        darkcolor=palette.border,
        padding=(8, 6),
    )
    style.map(
        "App.TEntry",
        bordercolor=[("focus", palette.border_focus)],
        lightcolor=[("focus", palette.border_focus)],
    )

    style.configure(
        "App.TSpinbox",
        fieldbackground=palette.bg_input,
        foreground=palette.text_primary,
        background=palette.bg_elevated,
        arrowcolor=palette.text_primary,
        bordercolor=palette.border,
        padding=(6, 4),
    )

    style.configure(
        "App.TCombobox",
        fieldbackground=palette.bg_input,
        foreground=palette.text_primary,
        background=palette.bg_elevated,
        arrowcolor=palette.text_primary,
        bordercolor=palette.border,
        padding=(8, 5),
    )
    style.map(
        "App.TCombobox",
        fieldbackground=[("readonly", palette.bg_input)],
        foreground=[("readonly", palette.text_primary)],
        selectbackground=[("readonly", palette.bg_input)],
        selectforeground=[("readonly", palette.text_primary)],
    )

    style.configure(
        "App.Horizontal.TScale",
        background=palette.bg_surface,
        troughcolor=palette.bg_elevated,
        bordercolor=palette.border,
        sliderlength=18,
        sliderrelief="flat",
    )

    style.configure(
        "App.Vertical.TScrollbar",
        background=palette.bg_elevated,
        troughcolor=palette.bg_surface,
        bordercolor=palette.bg_surface,
        arrowcolor=palette.text_secondary,
    )
