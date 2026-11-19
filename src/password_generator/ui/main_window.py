"""Main high-DPI Tkinter workstation window for cryptographic secret generation and auditing."""

import tkinter as tk
from functools import partial
from tkinter import ttk

from password_generator.core.entropy import evaluate_secret
from password_generator.core.generator import (
    MAX_PASSPHRASE_WORDS,
    MAX_PIN_LENGTH,
    MIN_PASSPHRASE_WORDS,
    MIN_PIN_LENGTH,
    generate_batch,
    generate_passphrase,
    generate_password,
    generate_pin,
    generate_token,
)
from password_generator.core.models import (
    GeneratedSecret,
    GenerationMode,
    PassphrasePolicy,
    PasswordPolicy,
    PinPolicy,
    PolicyValidationError,
    PresetProfile,
    StrengthReport,
    TokenFormat,
    TokenPolicy,
    WordCase,
)
from password_generator.core.presets import SECURITY_PRESETS, get_preset_by_key
from password_generator.services.clipboard import ClipboardService
from password_generator.services.history import SessionVaultService
from password_generator.services.settings_store import AppPreferences, SettingsStore
from password_generator.ui.dpi import apply_windows_titlebar_theme, configure_tk_scaling
from password_generator.ui.theme import (
    FontSet,
    ThemeMode,
    ThemePalette,
    apply_ttk_theme,
    get_palette,
    resolve_fonts,
)
from password_generator.ui.widgets import SessionVaultPanel, StrengthMeterCanvas, ToggleSwitch

_SEPARATOR_OPTIONS: dict[str, str] = {
    "Hyphen (-)": "-",
    "Dot (.)": ".",
    "Underscore (_)": "_",
    "Space ( )": " ",
    "Slash (/)": "/",
}

_CASE_OPTIONS: dict[str, WordCase] = {
    "Title Case": WordCase.TITLE,
    "lowercase": WordCase.LOWER,
    "UPPERCASE": WordCase.UPPER,
    "Random Word Case": WordCase.RANDOM_WORD,
}

_TOKEN_FORMAT_OPTIONS: dict[str, TokenFormat] = {
    "URL-Safe Base64": TokenFormat.URLSAFE_B64,
    "Hexadecimal": TokenFormat.HEX,
    "Base62 Alphanumeric": TokenFormat.BASE62,
}

_CLIPBOARD_TIMEOUT_LABELS: dict[str, int] = {
    "15 sec": 15,
    "30 sec": 30,
    "60 sec": 60,
    "120 sec": 120,
    "Manual only": 0,
}


class PasswordGeneratorWindow:
    """Orchestrates the responsive high-DPI GUI, policies, live strength audit, and vault."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        settings_store: SettingsStore | None = None,
        vault: SessionVaultService | None = None,
    ) -> None:
        self.root = root
        self._settings_store = settings_store or SettingsStore()
        self._prefs = self._settings_store.load()
        self._vault = vault or SessionVaultService(max_entries=25)
        self._clipboard = ClipboardService(root)

        self._scale = configure_tk_scaling(root)
        self._theme_mode: ThemeMode = self._prefs.theme
        self._palette: ThemePalette = get_palette(self._theme_mode)
        self._fonts: FontSet = resolve_fonts(root)
        self._style = ttk.Style(root)

        self._suppress_edit_trace = False
        self._suppress_policy_regeneration = False
        self._vault_record_after_id: str | None = None
        self._last_generated: GeneratedSecret | None = None
        self._batch_items: list[GeneratedSecret] = []

        # Registered theme-aware surfaces & widgets updated dynamically on theme toggle.
        self._bordered_cards: list[tk.Frame] = []
        self._toggle_switches: list[ToggleSwitch] = []
        self._mode_buttons: dict[GenerationMode, ttk.Button] = {}
        self._mode_frames: dict[GenerationMode, ttk.Frame] = {}

        self._init_variables()
        self._configure_root_window()
        self._build_layout()
        self._bind_shortcuts()
        self._apply_theme()

        initial_preset = get_preset_by_key(self._prefs.last_preset_key) or SECURITY_PRESETS[0]
        self._apply_preset(initial_preset, generate=True)

    def _init_variables(self) -> None:
        self._active_mode = GenerationMode.PASSWORD
        self._preset_var = tk.StringVar(value=SECURITY_PRESETS[0].name)
        self._secret_var = tk.StringVar(value="")
        self._summary_var = tk.StringVar(value="CSPRNG Ready")
        self._clipboard_status_var = tk.StringVar(value="Clipboard idle")
        self._clipboard_timeout_var = tk.StringVar(
            value=self._timeout_to_label(self._prefs.clipboard_clear_seconds)
        )
        self._masked_var = tk.BooleanVar(value=self._prefs.mask_secret_display)
        self._error_var = tk.StringVar(value="")

        # Password policy vars
        self._pwd_length_var = tk.IntVar(value=24)
        self._pwd_upper_var = tk.BooleanVar(value=True)
        self._pwd_lower_var = tk.BooleanVar(value=True)
        self._pwd_digits_var = tk.BooleanVar(value=True)
        self._pwd_symbols_var = tk.BooleanVar(value=True)
        self._pwd_no_ambig_var = tk.BooleanVar(value=False)
        self._pwd_no_repeats_var = tk.BooleanVar(value=False)
        self._pwd_start_letter_var = tk.BooleanVar(value=False)
        self._pwd_custom_symbols_var = tk.StringVar(value="")
        self._pwd_excluded_var = tk.StringVar(value="")

        # Passphrase policy vars
        self._phrase_words_var = tk.IntVar(value=7)
        self._phrase_sep_var = tk.StringVar(value="Hyphen (-)")
        self._phrase_case_var = tk.StringVar(value="Title Case")
        self._phrase_digit_var = tk.BooleanVar(value=True)
        self._phrase_symbol_var = tk.BooleanVar(value=False)

        # Token policy vars
        self._token_bits_var = tk.IntVar(value=256)
        self._token_format_var = tk.StringVar(value="URL-Safe Base64")
        self._token_prefix_var = tk.StringVar(value="ak_live_")

        # PIN policy vars
        self._pin_length_var = tk.IntVar(value=6)
        self._pin_no_seq_var = tk.BooleanVar(value=True)
        self._pin_no_rep_var = tk.BooleanVar(value=True)

        self._secret_var.trace_add("write", self._on_secret_edited)

    @staticmethod
    def _timeout_to_label(seconds: int) -> str:
        for label, sec in _CLIPBOARD_TIMEOUT_LABELS.items():
            if sec == seconds:
                return label
        return "30 sec"

    def _configure_root_window(self) -> None:
        self.root.title("AegisKey · Secure Password Generator Studio")
        width = round(1140 * min(self._scale, 1.35))
        height = round(790 * min(self._scale, 1.35))
        min_w = round(940 * min(self._scale, 1.25))
        min_h = round(680 * min(self._scale, 1.25))

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(width, max(min_w, screen_w - 80))
        height = min(height, max(min_h, screen_h - 90))
        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 2)

        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        self.root.minsize(min_w, min_h)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._outer = ttk.Frame(self.root, style="App.TFrame", padding=(18, 14, 18, 16))
        self._outer.grid(row=0, column=0, sticky="nsew")
        self._outer.columnconfigure(0, weight=1)
        self._outer.rowconfigure(2, weight=1)

        self._build_header(self._outer)
        self._build_hero_card(self._outer)

        body = ttk.Frame(self._outer, style="App.TFrame")
        body.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        body.columnconfigure(0, weight=5, uniform="cols")
        body.columnconfigure(1, weight=6, uniform="cols")
        body.rowconfigure(0, weight=1)

        self._build_policy_studio(body)
        self._build_right_column(body)

    def _create_card(
        self,
        parent: tk.Misc,
        *,
        padding: tuple[int, int] = (14, 12),
    ) -> tuple[tk.Frame, ttk.Frame]:
        border_frame = tk.Frame(
            parent,
            bg=self._palette.border,
            highlightthickness=1,
            highlightbackground=self._palette.border,
            bd=0,
        )
        border_frame.columnconfigure(0, weight=1)
        border_frame.rowconfigure(0, weight=1)
        self._bordered_cards.append(border_frame)

        inner = ttk.Frame(border_frame, style="Card.TFrame", padding=padding)
        inner.grid(row=0, column=0, sticky="nsew")
        return border_frame, inner

    def _build_header(self, parent: ttk.Frame) -> None:
        header = ttk.Frame(parent, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        left = ttk.Frame(header, style="App.TFrame")
        left.grid(row=0, column=0, sticky="w")

        ttk.Label(left, text="AegisKey · Password Generator Studio", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            left,
            text="CSPRNG (secrets) · Zero Disk Secrets · Live Entropy & Attack Auditor",
            style="AppMuted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))

        right = ttk.Frame(header, style="App.TFrame")
        right.grid(row=0, column=1, sticky="e")

        ttk.Label(right, text="Preset:", style="AppMuted.TLabel").grid(row=0, column=0, padx=(0, 6))
        self._preset_combo = ttk.Combobox(
            right,
            textvariable=self._preset_var,
            values=[p.name for p in SECURITY_PRESETS],
            state="readonly",
            width=27,
            style="App.TCombobox",
        )
        self._preset_combo.grid(row=0, column=1, padx=(0, 8))
        self._preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        self._theme_btn = ttk.Button(
            right,
            text="Light Mode" if self._theme_mode == "dark" else "Dark Mode",
            style="Secondary.TButton",
            command=self.toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=(0, 6))

        ttk.Button(
            right,
            text="Shortcuts (F1)",
            style="Secondary.TButton",
            command=self._show_help_dialog,
        ).grid(row=0, column=3)

    def _build_hero_card(self, parent: ttk.Frame) -> None:
        card_border, card = self._create_card(parent, padding=(16, 14))
        card_border.grid(row=1, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)

        # Top info row
        top_bar = ttk.Frame(card, style="Card.TFrame")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_bar.columnconfigure(0, weight=1)

        ttk.Label(top_bar, textvariable=self._summary_var, style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        clip_box = ttk.Frame(top_bar, style="Card.TFrame")
        clip_box.grid(row=0, column=1, sticky="e")

        self._clipboard_label = ttk.Label(
            clip_box,
            textvariable=self._clipboard_status_var,
            style="CardMuted.TLabel",
        )
        self._clipboard_label.grid(row=0, column=0, padx=(0, 8))

        self._clear_clip_btn = ttk.Button(
            clip_box,
            text="Clear Clipboard",
            style="Secondary.TButton",
            command=self.clear_clipboard_now,
        )
        self._clear_clip_btn.grid(row=0, column=1)

        # Secret display + actions
        secret_row = ttk.Frame(card, style="Card.TFrame")
        secret_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        secret_row.columnconfigure(0, weight=1)

        self._secret_entry_border = tk.Frame(
            secret_row,
            bg=self._palette.border,
            highlightthickness=1,
            highlightbackground=self._palette.border,
            bd=0,
        )
        self._secret_entry_border.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._secret_entry_border.columnconfigure(0, weight=1)

        self._secret_entry = tk.Entry(
            self._secret_entry_border,
            textvariable=self._secret_var,
            font=self._fonts.secret_hero,
            bg=self._palette.bg_input,
            fg=self._palette.text_primary,
            insertbackground=self._palette.text_primary,
            relief="flat",
            bd=8,
            show="•" if self._masked_var.get() else "",
        )
        self._secret_entry.grid(row=0, column=0, sticky="ew")
        self._secret_entry.bind("<FocusIn>", lambda _e: self._set_entry_focus(focused=True))
        self._secret_entry.bind("<FocusOut>", lambda _e: self._set_entry_focus(focused=False))

        actions = ttk.Frame(secret_row, style="Card.TFrame")
        actions.grid(row=0, column=1, sticky="e")

        ttk.Button(
            actions,
            text="Generate",
            style="Primary.TButton",
            command=self.generate_current,
        ).grid(row=0, column=0, padx=(0, 6))

        ttk.Button(
            actions,
            text="Copy",
            style="Primary.TButton",
            command=self.copy_current_secret,
        ).grid(row=0, column=1, padx=(0, 6))

        self._mask_btn = ttk.Button(
            actions,
            text="Show" if self._masked_var.get() else "Hide",
            style="Secondary.TButton",
            command=self.toggle_mask,
        )
        self._mask_btn.grid(row=0, column=2, padx=(0, 6))

        ttk.Button(
            actions,
            text="5x Batch",
            style="Secondary.TButton",
            command=self.generate_batch_candidates,
        ).grid(row=0, column=3)

        # Strength meter + metrics strip
        self._strength_meter = StrengthMeterCanvas(
            card,
            palette=self._palette,
            scale=self._scale,
        )
        self._strength_meter.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        metrics_row = ttk.Frame(card, style="Card.TFrame")
        metrics_row.grid(row=3, column=0, sticky="ew")
        metrics_row.columnconfigure(1, weight=1)

        self._tier_badge = tk.Label(
            metrics_row,
            text="STRENGTH",
            font=self._fonts.caption_bold,
            padx=8,
            pady=2,
            bg=self._palette.bg_elevated,
            fg=self._palette.quantum,
        )
        self._tier_badge.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self._metrics_label = ttk.Label(metrics_row, text="", style="CardMuted.TLabel")
        self._metrics_label.grid(row=0, column=1, sticky="w")

        self._error_label = tk.Label(
            metrics_row,
            textvariable=self._error_var,
            font=self._fonts.caption_bold,
            bg=self._palette.bg_surface,
            fg=self._palette.danger,
        )
        self._error_label.grid(row=0, column=2, sticky="e")

    def _build_policy_studio(self, parent: ttk.Frame) -> None:
        card_border, card = self._create_card(parent, padding=(14, 12))
        card_border.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        ttk.Label(card, text="Generation Policy Studio", style="CardHeading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 8)
        )

        # Mode switcher row
        mode_bar = ttk.Frame(card, style="Card.TFrame")
        mode_bar.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        modes = (
            (GenerationMode.PASSWORD, "Password"),
            (GenerationMode.PASSPHRASE, "Passphrase"),
            (GenerationMode.TOKEN, "API Token"),
            (GenerationMode.PIN, "PIN"),
        )
        for col, (mode, label) in enumerate(modes):
            mode_bar.columnconfigure(col, weight=1)
            btn = ttk.Button(
                mode_bar,
                text=label,
                style="ModeActive.TButton" if mode == self._active_mode else "ModeInactive.TButton",
                command=partial(self.switch_mode, mode),
            )
            btn.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 4, 0))
            self._mode_buttons[mode] = btn

        # Stacked mode container
        stack = ttk.Frame(card, style="Card.TFrame")
        stack.grid(row=2, column=0, sticky="nsew")
        stack.columnconfigure(0, weight=1)
        stack.rowconfigure(0, weight=1)

        self._mode_frames[GenerationMode.PASSWORD] = self._build_password_panel(stack)
        self._mode_frames[GenerationMode.PASSPHRASE] = self._build_passphrase_panel(stack)
        self._mode_frames[GenerationMode.TOKEN] = self._build_token_panel(stack)
        self._mode_frames[GenerationMode.PIN] = self._build_pin_panel(stack)

        for frame in self._mode_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")
        self._mode_frames[self._active_mode].tkraise()

        # Footer clipboard auto-clear hygiene setting
        footer = ttk.Frame(card, style="Card.TFrame")
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, text="Auto-Clear Clipboard After Copy:", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        timeout_combo = ttk.Combobox(
            footer,
            textvariable=self._clipboard_timeout_var,
            values=list(_CLIPBOARD_TIMEOUT_LABELS),
            state="readonly",
            width=14,
            style="App.TCombobox",
        )
        timeout_combo.grid(row=0, column=1, sticky="e")
        timeout_combo.bind("<<ComboboxSelected>>", self._on_timeout_changed)

    def _add_toggle_row(
        self,
        parent: ttk.Frame,
        row: int,
        col: int,
        label: str,
        variable: tk.BooleanVar,
    ) -> None:
        cell = ttk.Frame(parent, style="Card.TFrame")
        cell.grid(row=row, column=col, sticky="ew", padx=(0, 8), pady=5)
        cell.columnconfigure(1, weight=1)

        switch = ToggleSwitch(
            cell,
            variable=variable,
            palette=self._palette,
            scale=self._scale,
            command=self._on_policy_changed,
        )
        switch.grid(row=0, column=0, padx=(0, 8))
        self._toggle_switches.append(switch)

        lbl = ttk.Label(cell, text=label, style="Card.TLabel", cursor="hand2")
        lbl.grid(row=0, column=1, sticky="w")
        lbl.bind("<Button-1>", lambda _e: self._flip_bool_var(variable))

    def _flip_bool_var(self, variable: tk.BooleanVar) -> None:
        variable.set(not variable.get())
        self._on_policy_changed()

    def _add_quick_length_buttons(
        self,
        parent: ttk.Frame,
        values: tuple[int, ...],
        var: tk.IntVar,
    ) -> ttk.Frame:
        row = ttk.Frame(parent, style="Card.TFrame")
        for idx, val in enumerate(values):
            ttk.Button(
                row,
                text=str(val),
                style="Secondary.TButton",
                command=partial(self._set_int_var, var, val),
            ).grid(row=0, column=idx, padx=(0 if idx == 0 else 4, 0))
        return row

    def _set_int_var(self, var: tk.IntVar, value: int) -> None:
        var.set(value)
        self._on_policy_changed()

    def _build_password_panel(self, parent: ttk.Frame) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)

        # Length header + spinbox
        len_head = ttk.Frame(panel, style="Card.TFrame")
        len_head.grid(row=0, column=0, sticky="ew")
        len_head.columnconfigure(0, weight=1)
        ttk.Label(len_head, text="Password Length", style="Card.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        spin = ttk.Spinbox(
            len_head,
            from_=4,
            to=128,
            textvariable=self._pwd_length_var,
            width=5,
            style="App.TSpinbox",
            command=self._on_policy_changed,
        )
        spin.grid(row=0, column=1, sticky="e")
        spin.bind("<Return>", lambda _e: self._on_policy_changed())
        spin.bind("<FocusOut>", lambda _e: self._on_policy_changed())

        scale = ttk.Scale(
            panel,
            from_=4,
            to=128,
            orient="horizontal",
            variable=self._pwd_length_var,
            style="App.Horizontal.TScale",
            command=lambda raw: self._on_scale_drag(self._pwd_length_var, raw),
        )
        scale.grid(row=1, column=0, sticky="ew", pady=(6, 6))

        quick = self._add_quick_length_buttons(
            panel, (12, 16, 20, 24, 32, 64), self._pwd_length_var
        )
        quick.grid(row=2, column=0, sticky="w", pady=(0, 12))

        # Character class & hygiene switches
        switches = ttk.Frame(panel, style="Card.TFrame")
        switches.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        switches.columnconfigure(0, weight=1)
        switches.columnconfigure(1, weight=1)

        self._add_toggle_row(switches, 0, 0, "Uppercase (A-Z)", self._pwd_upper_var)
        self._add_toggle_row(switches, 0, 1, "Lowercase (a-z)", self._pwd_lower_var)
        self._add_toggle_row(switches, 1, 0, "Digits (0-9)", self._pwd_digits_var)
        self._add_toggle_row(switches, 1, 1, "Symbols (!@#...)", self._pwd_symbols_var)
        self._add_toggle_row(switches, 2, 0, "Exclude Ambiguous (0O1lI)", self._pwd_no_ambig_var)
        self._add_toggle_row(switches, 2, 1, "No Adjacent Repeats", self._pwd_no_repeats_var)
        self._add_toggle_row(switches, 3, 0, "Start With Letter", self._pwd_start_letter_var)

        # Custom symbol & exclusion inputs
        inputs = ttk.Frame(panel, style="Card.TFrame")
        inputs.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        inputs.columnconfigure(1, weight=1)

        ttk.Label(inputs, text="Custom Symbols:", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        sym_entry = ttk.Entry(
            inputs,
            textvariable=self._pwd_custom_symbols_var,
            style="App.TEntry",
        )
        sym_entry.grid(row=0, column=1, sticky="ew", pady=4)
        sym_entry.bind("<FocusOut>", lambda _e: self._on_policy_changed())
        sym_entry.bind("<Return>", lambda _e: self._on_policy_changed())

        ttk.Label(inputs, text="Exclude Characters:", style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        excl_entry = ttk.Entry(
            inputs,
            textvariable=self._pwd_excluded_var,
            style="App.TEntry",
        )
        excl_entry.grid(row=1, column=1, sticky="ew", pady=4)
        excl_entry.bind("<FocusOut>", lambda _e: self._on_policy_changed())
        excl_entry.bind("<Return>", lambda _e: self._on_policy_changed())

        return panel

    def _build_passphrase_panel(self, parent: ttk.Frame) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)

        head = ttk.Frame(panel, style="Card.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        ttk.Label(
            head, text="Word Count (4,096-Word Dictionary · 12 bits/word)", style="Card.TLabel"
        ).grid(row=0, column=0, sticky="w")
        spin = ttk.Spinbox(
            head,
            from_=MIN_PASSPHRASE_WORDS,
            to=MAX_PASSPHRASE_WORDS,
            textvariable=self._phrase_words_var,
            width=5,
            style="App.TSpinbox",
            command=self._on_policy_changed,
        )
        spin.grid(row=0, column=1, sticky="e")

        ttk.Scale(
            panel,
            from_=MIN_PASSPHRASE_WORDS,
            to=MAX_PASSPHRASE_WORDS,
            orient="horizontal",
            variable=self._phrase_words_var,
            style="App.Horizontal.TScale",
            command=lambda raw: self._on_scale_drag(self._phrase_words_var, raw),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 6))

        self._add_quick_length_buttons(panel, (4, 6, 7, 8, 10, 12), self._phrase_words_var).grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )

        opts = ttk.Frame(panel, style="Card.TFrame")
        opts.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        opts.columnconfigure(1, weight=1)

        ttk.Label(opts, text="Separator:", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        sep_combo = ttk.Combobox(
            opts,
            textvariable=self._phrase_sep_var,
            values=list(_SEPARATOR_OPTIONS),
            state="readonly",
            style="App.TCombobox",
        )
        sep_combo.grid(row=0, column=1, sticky="ew", pady=5)
        sep_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_policy_changed())

        ttk.Label(opts, text="Word Casing:", style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        case_combo = ttk.Combobox(
            opts,
            textvariable=self._phrase_case_var,
            values=list(_CASE_OPTIONS),
            state="readonly",
            style="App.TCombobox",
        )
        case_combo.grid(row=1, column=1, sticky="ew", pady=5)
        case_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_policy_changed())

        switches = ttk.Frame(panel, style="Card.TFrame")
        switches.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        switches.columnconfigure(0, weight=1)
        switches.columnconfigure(1, weight=1)
        self._add_toggle_row(switches, 0, 0, "Append Random Digit", self._phrase_digit_var)
        self._add_toggle_row(switches, 0, 1, "Append Random Symbol", self._phrase_symbol_var)

        return panel

    def _build_token_panel(self, parent: ttk.Frame) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)

        ttk.Label(panel, text="Cryptographic Bit Strength", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self._add_quick_length_buttons(panel, (128, 192, 256, 384, 512), self._token_bits_var).grid(
            row=1, column=0, sticky="w", pady=(0, 14)
        )

        opts = ttk.Frame(panel, style="Card.TFrame")
        opts.grid(row=2, column=0, sticky="ew")
        opts.columnconfigure(1, weight=1)

        ttk.Label(opts, text="Encoding Format:", style="CardMuted.TLabel").grid(
            row=0, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        fmt_combo = ttk.Combobox(
            opts,
            textvariable=self._token_format_var,
            values=list(_TOKEN_FORMAT_OPTIONS),
            state="readonly",
            style="App.TCombobox",
        )
        fmt_combo.grid(row=0, column=1, sticky="ew", pady=5)
        fmt_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_policy_changed())

        ttk.Label(opts, text="Optional Prefix:", style="CardMuted.TLabel").grid(
            row=1, column=0, sticky="w", pady=5, padx=(0, 10)
        )
        prefix_entry = ttk.Entry(opts, textvariable=self._token_prefix_var, style="App.TEntry")
        prefix_entry.grid(row=1, column=1, sticky="ew", pady=5)
        prefix_entry.bind("<FocusOut>", lambda _e: self._on_policy_changed())
        prefix_entry.bind("<Return>", lambda _e: self._on_policy_changed())

        return panel

    def _build_pin_panel(self, parent: ttk.Frame) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Card.TFrame")
        panel.columnconfigure(0, weight=1)

        head = ttk.Frame(panel, style="Card.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text="PIN Digits", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            head,
            from_=MIN_PIN_LENGTH,
            to=MAX_PIN_LENGTH,
            textvariable=self._pin_length_var,
            width=5,
            style="App.TSpinbox",
            command=self._on_policy_changed,
        ).grid(row=0, column=1, sticky="e")

        ttk.Scale(
            panel,
            from_=MIN_PIN_LENGTH,
            to=MAX_PIN_LENGTH,
            orient="horizontal",
            variable=self._pin_length_var,
            style="App.Horizontal.TScale",
            command=lambda raw: self._on_scale_drag(self._pin_length_var, raw),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 6))

        self._add_quick_length_buttons(panel, (4, 6, 8, 10, 12, 16), self._pin_length_var).grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )

        switches = ttk.Frame(panel, style="Card.TFrame")
        switches.grid(row=3, column=0, sticky="ew")
        switches.columnconfigure(0, weight=1)
        self._add_toggle_row(switches, 0, 0, "Block Sequences (123, 987)", self._pin_no_seq_var)
        self._add_toggle_row(switches, 1, 0, "Block Repeated Digits", self._pin_no_rep_var)

        return panel

    def _build_right_column(self, parent: ttk.Frame) -> None:
        right = ttk.Frame(parent, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        self._build_audit_card(right)
        self._build_batch_card(right)
        self._build_vault_card(right)

    def _build_audit_card(self, parent: ttk.Frame) -> None:
        border, card = self._create_card(parent, padding=(14, 10))
        border.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        ttk.Label(
            card, text="2026 Brute-Force Resistance & Audit", style="CardHeading.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self._attack_rows_frame = ttk.Frame(card, style="Card.TFrame")
        self._attack_rows_frame.grid(row=1, column=0, sticky="ew")
        self._attack_rows_frame.columnconfigure(0, weight=1)

        self._attack_value_labels: list[tuple[ttk.Label, ttk.Label]] = []
        for idx in range(3):
            lbl_left = ttk.Label(self._attack_rows_frame, text="", style="CardMuted.TLabel")
            lbl_right = ttk.Label(self._attack_rows_frame, text="", style="Card.TLabel")
            lbl_left.grid(row=idx, column=0, sticky="w", pady=2)
            lbl_right.grid(row=idx, column=1, sticky="e", pady=2)
            self._attack_value_labels.append((lbl_left, lbl_right))

        self._audit_notes_label = tk.Label(
            card,
            text="",
            justify="left",
            anchor="w",
            wraplength=440,
            font=self._fonts.caption,
            bg=self._palette.bg_surface,
            fg=self._palette.text_secondary,
        )
        self._audit_notes_label.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _build_batch_card(self, parent: ttk.Frame) -> None:
        border, card = self._create_card(parent, padding=(14, 10))
        border.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        card.columnconfigure(0, weight=1)

        header = ttk.Frame(card, style="Card.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Quick Batch Candidates", style="CardHeading.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Button(
            header,
            text="Refresh 5x",
            style="Secondary.TButton",
            command=self.generate_batch_candidates,
        ).grid(row=0, column=1, sticky="e")

        self._batch_rows_frame = ttk.Frame(card, style="Card.TFrame")
        self._batch_rows_frame.grid(row=1, column=0, sticky="ew")
        self._batch_rows_frame.columnconfigure(0, weight=1)

    def _build_vault_card(self, parent: ttk.Frame) -> None:
        border, card = self._create_card(parent, padding=(14, 10))
        border.grid(row=2, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self._vault_panel = SessionVaultPanel(
            card,
            palette=self._palette,
            fonts=self._fonts,
            on_copy_entry=self._copy_value,
            on_inspect_entry=self._load_secret_into_analyzer,
            on_wipe=self._wipe_vault,
        )
        self._vault_panel.grid(row=0, column=0, sticky="nsew")

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-g>", lambda _e: self.generate_current())
        self.root.bind("<Control-G>", lambda _e: self.generate_current())
        self.root.bind("<Control-Shift-C>", lambda _e: self.copy_current_secret())
        self.root.bind("<Control-Shift-c>", lambda _e: self.copy_current_secret())
        self.root.bind("<Control-b>", lambda _e: self.generate_batch_candidates())
        self.root.bind("<Control-B>", lambda _e: self.generate_batch_candidates())
        self.root.bind("<Control-t>", lambda _e: self.toggle_theme())
        self.root.bind("<Control-T>", lambda _e: self.toggle_theme())
        self.root.bind("<Control-m>", lambda _e: self.toggle_mask())
        self.root.bind("<Control-M>", lambda _e: self.toggle_mask())
        self.root.bind("<Control-l>", lambda _e: self.clear_clipboard_now())
        self.root.bind("<Control-L>", lambda _e: self.clear_clipboard_now())
        self.root.bind("<F1>", lambda _e: self._show_help_dialog())

    def _apply_theme(self) -> None:
        self._palette = get_palette(self._theme_mode)
        p = self._palette

        apply_ttk_theme(self._style, p, self._fonts)
        self.root.configure(bg=p.bg_app)
        self.root.option_add("*TCombobox*Listbox.background", p.bg_surface)
        self.root.option_add("*TCombobox*Listbox.foreground", p.text_primary)
        self.root.option_add("*TCombobox*Listbox.selectBackground", p.accent)
        self.root.option_add("*TCombobox*Listbox.selectForeground", p.accent_fg)

        for frame in self._bordered_cards:
            frame.configure(bg=p.border, highlightbackground=p.border)
        for switch in self._toggle_switches:
            switch.set_palette(p)

        self._secret_entry_border.configure(bg=p.border, highlightbackground=p.border)
        self._secret_entry.configure(
            bg=p.bg_input,
            fg=p.text_primary,
            insertbackground=p.text_primary,
        )
        self._strength_meter.set_palette(p)
        self._vault_panel.set_palette(p)
        self._error_label.configure(bg=p.bg_surface, fg=p.danger)
        self._audit_notes_label.configure(bg=p.bg_surface, fg=p.text_secondary)
        self._theme_btn.configure(text="Light Mode" if self._theme_mode == "dark" else "Dark Mode")

        if self._last_generated is not None:
            self._update_report_view(self._last_generated.report)

        apply_windows_titlebar_theme(self.root, dark=(self._theme_mode == "dark"))

    def toggle_theme(self) -> None:
        """Switch between Obsidian Dark and Studio Light themes and persist preference."""
        self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
        self._apply_theme()
        self._save_preferences()

    def _set_entry_focus(self, *, focused: bool) -> None:
        color = self._palette.border_focus if focused else self._palette.border
        self._secret_entry_border.configure(bg=color, highlightbackground=color)

    def toggle_mask(self) -> None:
        """Toggle visibility of the active secret display."""
        masked = not self._masked_var.get()
        self._masked_var.set(masked)
        self._secret_entry.configure(show="•" if masked else "")
        self._mask_btn.configure(text="Show" if masked else "Hide")
        self._render_batch_rows()
        self._save_preferences()

    def switch_mode(self, mode: GenerationMode) -> None:
        """Activate a generation mode panel and immediately produce a matching secret."""
        self._active_mode = mode
        for item_mode, btn in self._mode_buttons.items():
            btn.configure(
                style="ModeActive.TButton" if item_mode == mode else "ModeInactive.TButton"
            )
        self._mode_frames[mode].tkraise()
        self.generate_current()

    def _on_preset_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        chosen_name = self._preset_var.get()
        for preset in SECURITY_PRESETS:
            if preset.name == chosen_name:
                self._apply_preset(preset, generate=True)
                self._save_preferences(preset_key=preset.key)
                return

    def _apply_preset(self, preset: PresetProfile, *, generate: bool) -> None:
        self._suppress_policy_regeneration = True
        try:
            self._preset_var.set(preset.name)
            self._active_mode = preset.mode
            for item_mode, btn in self._mode_buttons.items():
                btn.configure(
                    style="ModeActive.TButton"
                    if item_mode == preset.mode
                    else "ModeInactive.TButton"
                )
            self._mode_frames[preset.mode].tkraise()

            if preset.password_policy is not None:
                p = preset.password_policy
                self._pwd_length_var.set(p.length)
                self._pwd_upper_var.set(p.use_uppercase)
                self._pwd_lower_var.set(p.use_lowercase)
                self._pwd_digits_var.set(p.use_digits)
                self._pwd_symbols_var.set(p.use_symbols)
                self._pwd_no_ambig_var.set(p.exclude_ambiguous)
                self._pwd_no_repeats_var.set(p.no_adjacent_repeats)
                self._pwd_start_letter_var.set(p.start_with_letter)
                self._pwd_custom_symbols_var.set(p.custom_symbols)
                self._pwd_excluded_var.set(p.excluded_chars)

            if preset.passphrase_policy is not None:
                pp = preset.passphrase_policy
                self._phrase_words_var.set(pp.word_count)
                self._phrase_digit_var.set(pp.append_digit)
                self._phrase_symbol_var.set(pp.append_symbol)
                for label, sep in _SEPARATOR_OPTIONS.items():
                    if sep == pp.separator:
                        self._phrase_sep_var.set(label)
                        break
                for label, case in _CASE_OPTIONS.items():
                    if case == pp.word_case:
                        self._phrase_case_var.set(label)
                        break

            if preset.token_policy is not None:
                tp = preset.token_policy
                self._token_bits_var.set(tp.bit_strength)
                self._token_prefix_var.set(tp.prefix)
                for label, fmt in _TOKEN_FORMAT_OPTIONS.items():
                    if fmt == tp.token_format:
                        self._token_format_var.set(label)
                        break

            if preset.pin_policy is not None:
                pin = preset.pin_policy
                self._pin_length_var.set(pin.length)
                self._pin_no_seq_var.set(pin.disallow_sequences)
                self._pin_no_rep_var.set(pin.disallow_repeated_digits)
        finally:
            self._suppress_policy_regeneration = False

        if generate:
            self.generate_current()

    def _on_scale_drag(self, var: tk.IntVar, raw_value: str) -> None:
        rounded = round(float(raw_value))
        if var.get() != rounded:
            var.set(rounded)
        self._on_policy_changed(debounce_vault=True)

    def _on_policy_changed(self, *, debounce_vault: bool = False) -> None:
        if self._suppress_policy_regeneration:
            return
        self.generate_current(record_immediately=not debounce_vault)

    def _current_password_policy(self) -> PasswordPolicy:
        return PasswordPolicy(
            length=self._pwd_length_var.get(),
            use_uppercase=self._pwd_upper_var.get(),
            use_lowercase=self._pwd_lower_var.get(),
            use_digits=self._pwd_digits_var.get(),
            use_symbols=self._pwd_symbols_var.get(),
            exclude_ambiguous=self._pwd_no_ambig_var.get(),
            no_adjacent_repeats=self._pwd_no_repeats_var.get(),
            start_with_letter=self._pwd_start_letter_var.get(),
            custom_symbols=self._pwd_custom_symbols_var.get(),
            excluded_chars=self._pwd_excluded_var.get(),
        )

    def _current_passphrase_policy(self) -> PassphrasePolicy:
        return PassphrasePolicy(
            word_count=self._phrase_words_var.get(),
            separator=_SEPARATOR_OPTIONS.get(self._phrase_sep_var.get(), "-"),
            word_case=_CASE_OPTIONS.get(self._phrase_case_var.get(), WordCase.TITLE),
            append_digit=self._phrase_digit_var.get(),
            append_symbol=self._phrase_symbol_var.get(),
        )

    def _current_token_policy(self) -> TokenPolicy:
        return TokenPolicy(
            bit_strength=self._token_bits_var.get(),
            token_format=_TOKEN_FORMAT_OPTIONS.get(
                self._token_format_var.get(),
                TokenFormat.URLSAFE_B64,
            ),
            prefix=self._token_prefix_var.get(),
        )

    def _current_pin_policy(self) -> PinPolicy:
        return PinPolicy(
            length=self._pin_length_var.get(),
            disallow_sequences=self._pin_no_seq_var.get(),
            disallow_repeated_digits=self._pin_no_rep_var.get(),
        )

    def _generate_one(self) -> GeneratedSecret:
        if self._active_mode == GenerationMode.PASSWORD:
            return generate_password(self._current_password_policy())
        if self._active_mode == GenerationMode.PASSPHRASE:
            return generate_passphrase(self._current_passphrase_policy())
        if self._active_mode == GenerationMode.TOKEN:
            return generate_token(self._current_token_policy())
        return generate_pin(self._current_pin_policy())

    def generate_current(self, *, record_immediately: bool = True) -> None:
        """Generate a new CSPRNG secret for the active mode and refresh all analytics."""
        try:
            generated = self._generate_one()
        except (PolicyValidationError, ValueError, tk.TclError) as exc:
            self._error_var.set(str(exc))
            return

        self._error_var.set("")
        self._last_generated = generated
        self._summary_var.set(generated.summary)

        self._suppress_edit_trace = True
        try:
            self._secret_var.set(generated.value)
        finally:
            self._suppress_edit_trace = False

        self._update_report_view(generated.report)
        self._schedule_vault_record(generated, immediate=record_immediately)
        self.generate_batch_candidates()

    def _schedule_vault_record(self, secret: GeneratedSecret, *, immediate: bool) -> None:
        if self._vault_record_after_id is not None:
            self.root.after_cancel(self._vault_record_after_id)
            self._vault_record_after_id = None

        if immediate:
            self._vault.record(secret)
            self._vault_panel.set_entries(self._vault.entries())
            return

        def _commit() -> None:
            self._vault_record_after_id = None
            self._vault.record(secret)
            self._vault_panel.set_entries(self._vault.entries())

        self._vault_record_after_id = self.root.after(400, _commit)

    def generate_batch_candidates(self) -> None:
        """Generate 5 distinct candidates for the active policy and update the batch list."""
        try:
            items = generate_batch(
                self._active_mode,
                5,
                password_policy=self._current_password_policy()
                if self._active_mode == GenerationMode.PASSWORD
                else None,
                passphrase_policy=self._current_passphrase_policy()
                if self._active_mode == GenerationMode.PASSPHRASE
                else None,
                token_policy=self._current_token_policy()
                if self._active_mode == GenerationMode.TOKEN
                else None,
                pin_policy=self._current_pin_policy()
                if self._active_mode == GenerationMode.PIN
                else None,
            )
        except (PolicyValidationError, ValueError, tk.TclError) as exc:
            self._error_var.set(str(exc))
            return

        self._batch_items = items
        self._render_batch_rows()

    def _render_batch_rows(self) -> None:
        for child in self._batch_rows_frame.winfo_children():
            child.destroy()

        masked = self._masked_var.get()
        for idx, item in enumerate(self._batch_items):
            row = ttk.Frame(self._batch_rows_frame, style="Elevated.TFrame", padding=(8, 4))
            row.grid(row=idx, column=0, sticky="ew", pady=(0, 4))
            row.columnconfigure(0, weight=1)

            preview = "•" * min(16, len(item.value)) if masked else item.value
            if len(preview) > 36:
                preview = f"{preview[:33]}..."

            ttk.Label(row, text=preview, style="Mono.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(
                row,
                text=f"{item.report.effective_bits:.0f} bits",
                style="ElevatedMuted.TLabel",
            ).grid(row=0, column=1, padx=(8, 8), sticky="e")
            ttk.Button(
                row,
                text="Copy",
                style="Secondary.TButton",
                command=partial(self._copy_and_load_batch, item),
            ).grid(row=0, column=2, sticky="e")

    def _copy_and_load_batch(self, item: GeneratedSecret) -> None:
        self._last_generated = item
        self._summary_var.set(item.summary)
        self._suppress_edit_trace = True
        try:
            self._secret_var.set(item.value)
        finally:
            self._suppress_edit_trace = False
        self._update_report_view(item.report)
        self._vault.record(item)
        self._vault_panel.set_entries(self._vault.entries())
        self._copy_value(item.value)

    def _on_secret_edited(self, *_args: object) -> None:
        if self._suppress_edit_trace:
            return
        text = self._secret_var.get()
        self._last_generated = None
        self._summary_var.set("Manual / Custom Secret Audit (live pattern & entropy check)")
        self._error_var.set("")
        report = evaluate_secret(text)
        self._update_report_view(report)

    def _load_secret_into_analyzer(self, value: str) -> None:
        self._secret_var.set(value)

    def _update_report_view(self, report: StrengthReport) -> None:
        self._strength_meter.update_report(report)
        tier_color = self._strength_meter.tier_color(report.tier)
        self._tier_badge.configure(
            text=report.tier.upper(),
            bg=self._palette.bg_elevated,
            fg=tier_color,
        )
        self._metrics_label.configure(
            text=(
                f"Effective Entropy: {report.effective_bits:.1f} bits  ·  "
                f"Score: {report.score}/100  ·  "
                f"Length: {report.length}  ·  "
                f"Alphabet: {report.charset_size}"
            )
        )

        for idx, (lbl_left, lbl_right) in enumerate(self._attack_value_labels):
            if idx < len(report.attack_estimates):
                est = report.attack_estimates[idx]
                lbl_left.configure(text=est.label)
                lbl_right.configure(text=est.human_duration)

        notes: list[str] = [f"! {w}" for w in report.warnings]
        notes.extend(f"• {rec}" for rec in report.recommendations)
        if not notes:
            notes.append("✓ Passes 2026 entropy & pattern checks with zero detected weaknesses.")
        self._audit_notes_label.configure(
            text="\n".join(notes),
            fg=self._palette.warning if report.warnings else self._palette.text_secondary,
        )

    def copy_current_secret(self) -> None:
        """Copy the currently displayed secret to the clipboard with auto-clear protection."""
        value = self._secret_var.get()
        if not value:
            return
        if self._last_generated is not None:
            self._vault.record(self._last_generated)
            self._vault_panel.set_entries(self._vault.entries())
        self._copy_value(value)

    def _copy_value(self, secret: str) -> None:
        timeout = _CLIPBOARD_TIMEOUT_LABELS.get(self._clipboard_timeout_var.get(), 30)
        self._clipboard.copy_secret(
            secret,
            timeout_seconds=timeout,
            on_tick=self._on_clipboard_tick,
            on_cleared=self._on_clipboard_cleared,
        )
        if timeout == 0:
            self._clipboard_status_var.set("Copied to clipboard (manual clear)")

    def _on_clipboard_tick(self, remaining: int) -> None:
        self._clipboard_status_var.set(f"Copied · auto-clear in {remaining}s")

    def _on_clipboard_cleared(self, was_wiped: bool) -> None:
        if was_wiped:
            self._clipboard_status_var.set("Clipboard securely wiped")
        else:
            self._clipboard_status_var.set("External clipboard data preserved")

    def clear_clipboard_now(self) -> None:
        """Immediately wipe the OS clipboard."""
        self._clipboard.clear_now(force=True)

    def _on_timeout_changed(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._save_preferences()

    def _wipe_vault(self) -> None:
        self._vault.wipe()
        self._vault_panel.set_entries(())

    def _save_preferences(self, *, preset_key: str | None = None) -> None:
        timeout = _CLIPBOARD_TIMEOUT_LABELS.get(self._clipboard_timeout_var.get(), 30)
        active_preset_key = preset_key or self._prefs.last_preset_key
        prefs = AppPreferences(
            theme=self._theme_mode,
            clipboard_clear_seconds=timeout,
            mask_secret_display=self._masked_var.get(),
            last_preset_key=active_preset_key,
        )
        self._prefs = prefs
        self._settings_store.save(prefs)

    def _show_help_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("AegisKey Shortcuts & Security Model")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self._palette.bg_surface)

        frame = ttk.Frame(dialog, style="Card.TFrame", padding=(18, 16))
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            frame, text="Keyboard Shortcuts & Security Guarantees", style="CardHeading.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        help_text = (
            "Ctrl+G         Generate new CSPRNG secret\n"
            "Ctrl+Shift+C   Copy active secret & start auto-wipe timer\n"
            "Ctrl+B         Refresh 5x batch candidates\n"
            "Ctrl+M         Toggle secret masking (Show / Hide)\n"
            "Ctrl+L         Clear OS clipboard immediately\n"
            "Ctrl+T         Switch Obsidian Dark / Studio Light theme\n"
            "F1             Open this reference dialog\n\n"
            "Security Architecture (2026):\n"
            "• Uses OS CSPRNG via Python `secrets` (never Mersenne Twister `random`).\n"
            "• Uniform sampling with Fisher-Yates CSPRNG shuffle after class guarantees.\n"
            "• Session Vault lives strictly in RAM and is wiped on exit.\n"
            "• Clipboard auto-wipe verifies content before clearing so external copies stay safe."
        )
        tk.Label(
            frame,
            text=help_text,
            justify="left",
            font=self._fonts.mono_small,
            bg=self._palette.bg_surface,
            fg=self._palette.text_secondary,
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        ttk.Button(frame, text="Close", style="Primary.TButton", command=dialog.destroy).grid(
            row=2, column=0, sticky="e"
        )
        apply_windows_titlebar_theme(dialog, dark=(self._theme_mode == "dark"))

    def _on_close(self) -> None:
        if self._vault_record_after_id is not None:
            self.root.after_cancel(self._vault_record_after_id)
            self._vault_record_after_id = None
        self._clipboard.cancel_timer()
        self._vault.wipe()
        self._save_preferences()
        self.root.destroy()
