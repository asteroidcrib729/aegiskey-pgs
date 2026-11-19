"""Tkinter UI smoke and integration tests verifying rendering, modes, errors, and teardown."""

import tkinter as tk
from contextlib import suppress
from pathlib import Path

from password_generator.core.models import GenerationMode
from password_generator.services.settings_store import SettingsStore
from password_generator.ui.main_window import PasswordGeneratorWindow


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
        assert len(window._batch_items) == 5

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
        assert len(window._batch_items) == 5
        window._copy_and_load_batch(window._batch_items[0])
        assert window._secret_var.get() == window._batch_items[0].value

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
