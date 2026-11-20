"""Tkinter UI smoke and integration tests for SVG rendering, touchpad scroll, and lifecycle."""

import tkinter as tk
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from password_generator.core.models import GenerationMode
from password_generator.services.settings_store import SettingsStore
from password_generator.ui.main_window import PasswordGeneratorWindow
from password_generator.ui.widgets.scrollable import (
    TouchpadScrollableFrame,
    unpack_touchpad_deltas,
)


def test_unpack_touchpad_deltas_decodes_signed_dx_and_dy() -> None:
    # Positive dy = 24, dx = 0
    assert unpack_touchpad_deltas(24) == (0, 24)
    # Negative dy = -18 (16-bit two's complement 0xFFEE)
    assert unpack_touchpad_deltas(0xFFEE) == (0, -18)
    # Combined dx = -10 (0xFFF6 << 16), dy = 12
    packed = (0xFFF6 << 16) | 12
    assert unpack_touchpad_deltas(packed) == (-10, 12)


def test_touchpad_scrollable_frame_scrolls_smoothly_on_small_deltas() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        frame = TouchpadScrollableFrame(root, bg="#111827", height=120)
        frame.pack(fill="both", expand=True)
        for i in range(25):
            tk.Label(frame.content, text=f"Row {i}").pack(pady=4)

        root.geometry("300x120")
        root.update()
        assert frame.can_scroll() is True

        initial_top = frame.canvas.yview()[0]
        # Dispatch Tk 9.0 TouchpadScroll downward swipe (negative dy = -30 -> +30 px down)
        fake_event = cast(
            Any,
            SimpleNamespace(widget=frame.content.winfo_children()[0], delta=0xFFE2),
        )
        res = TouchpadScrollableFrame._dispatch_touchpad(fake_event)
        assert res == "break"
        assert frame.canvas.yview()[0] > initial_top

        # Dispatch small MouseWheel fractional deltas (multiple -15 precision ticks)
        after_touchpad = frame.canvas.yview()[0]
        small_wheel = cast(
            Any,
            SimpleNamespace(widget=frame.content.winfo_children()[0], delta=-15),
        )
        TouchpadScrollableFrame._dispatch_mousewheel(small_wheel)
        TouchpadScrollableFrame._dispatch_mousewheel(small_wheel)
        assert frame.canvas.yview()[0] > after_touchpad
    finally:
        with suppress(tk.TclError):
            if root.winfo_exists():
                root.destroy()


def test_main_window_lifecycle_interactions_and_error_handling(tmp_path: Path) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        store = SettingsStore(tmp_path / "ui_prefs.json")
        window = PasswordGeneratorWindow(root, settings_store=store)
        root.update()

        initial_secret = window._secret_var.get()
        assert len(initial_secret) == 24
        assert window._vault.count >= 1
        assert len(window._batch_items) == 4
        assert len(window._strength_meter.find_all()) == 6

        # Switch through every generation mode and verify output
        window.switch_mode(GenerationMode.PASSPHRASE)
        assert "-" in window._secret_var.get()

        window.switch_mode(GenerationMode.TOKEN)
        assert window._secret_var.get().startswith("ak_live_")

        window.switch_mode(GenerationMode.PIN)
        assert window._secret_var.get().isdigit()

        window.switch_mode(GenerationMode.PASSWORD)
        assert window._secret_var.get()

        # Verify manual editing triggers live analyzer without overwriting input
        window._secret_var.set("qwerty1234")
        assert "Manual" in window._summary_var.get()
        assert "WEAK" in window._tier_badge.cget("text") or "CRITICAL" in window._tier_badge.cget(
            "text"
        )

        # Verify invalid policy updates error banner instead of crashing
        window._pwd_upper_var.set(False)
        window._pwd_lower_var.set(False)
        window._pwd_digits_var.set(False)
        window._pwd_symbols_var.set(False)
        window.generate_current()
        assert window._error_var.get()

        # Re-enable classes, test batch load, clipboard copy/clear, mask, theme, and vault wipe
        window._pwd_upper_var.set(True)
        window._pwd_lower_var.set(True)
        window.generate_current()
        assert window._error_var.get() == ""

        window.generate_batch_candidates()
        assert len(window._batch_items) == 4
        window._copy_and_load_batch(window._batch_items[0])
        assert window._secret_var.get() == window._batch_items[0].value

        # Verify SessionVaultPanel TouchpadScroll & MouseWheel handlers return cleanly
        for _ in range(8):
            window.generate_current()
        assert window._vault.count >= 6
        fake_tp = cast(Any, SimpleNamespace(delta=0xFFE4))
        assert window._vault_panel._on_touchpad_scroll(fake_tp) == "break"
        fake_mw = cast(Any, SimpleNamespace(delta=-120))
        assert window._vault_panel._on_mousewheel(fake_mw) == "break"

        window.clear_clipboard_now()
        window.toggle_mask()
        assert window._masked_var.get() is True

        window.toggle_theme()
        assert window._theme_mode == "light"
        root.update()

        window._wipe_vault()
        assert window._vault.count == 0

        window._on_close()
        assert store.load().theme == "light"
        assert store.load().mask_secret_display is True
    finally:
        with suppress(tk.TclError):
            if root.winfo_exists():
                root.destroy()


def test_window_present_and_resize_cycle(tmp_path: Path) -> None:
    root = tk.Tk()
    root.withdraw()
    with suppress(tk.TclError):
        root.attributes("-alpha", 0.0)
    try:
        store = SettingsStore(tmp_path / "present_prefs.json")
        window = PasswordGeneratorWindow(root, settings_store=store)
        window.present()
        root.geometry("980x640")
        root.update()
        root.geometry("1220x780")
        root.update()
        assert window._audit_notes_label.cget("wraplength") >= 200

        # Populate vault above viewport height and verify TouchpadScroll moves Treeview yview
        for _ in range(15):
            window.generate_current()
        root.update()
        initial_y = window._vault_panel.tree.yview()[0]
        fake_tp_down = cast(Any, SimpleNamespace(delta=0xFFE4))
        for _ in range(6):
            assert window._vault_panel._on_touchpad_scroll(fake_tp_down) == "break"
        root.update()
        scrolled_y = window._vault_panel.tree.yview()[0]
        assert scrolled_y > initial_y

        fake_tp_up = cast(Any, SimpleNamespace(delta=0x001C))
        for _ in range(6):
            assert window._vault_panel._on_touchpad_scroll(fake_tp_up) == "break"
        root.update()
        assert window._vault_panel.tree.yview()[0] < scrolled_y

        window._on_close()
    finally:
        with suppress(tk.TclError):
            if root.winfo_exists():
                root.destroy()
