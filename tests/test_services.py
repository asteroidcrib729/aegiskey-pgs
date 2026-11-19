"""Tests for clipboard auto-wipe service, RAM-only session vault, and preferences store."""

from collections.abc import Callable
from pathlib import Path

from password_generator.core.generator import generate_password
from password_generator.core.models import PasswordPolicy
from password_generator.services.clipboard import ClipboardService
from password_generator.services.history import SessionVaultService
from password_generator.services.settings_store import AppPreferences, SettingsStore


class FakeClipboardBackend:
    """In-memory mock of Tkinter's clipboard and ``after`` timer API."""

    def __init__(self) -> None:
        self.clipboard_content: str = ""
        self.scheduled: dict[str, Callable[[], object]] = {}
        self._counter = 0

    def clipboard_clear(self) -> None:
        self.clipboard_content = ""

    def clipboard_append(self, string: str, /) -> None:
        self.clipboard_content += string

    def clipboard_get(self) -> str:
        return self.clipboard_content

    def after(self, ms: int, func: Callable[[], object], /) -> str:
        del ms
        self._counter += 1
        timer_id = f"timer-{self._counter}"
        self.scheduled[timer_id] = func
        return timer_id

    def after_cancel(self, id: str) -> None:
        self.scheduled.pop(id, None)

    def fire_next(self) -> None:
        assert self.scheduled
        timer_id, func = next(iter(self.scheduled.items()))
        self.scheduled.pop(timer_id)
        func()


def test_clipboard_auto_clears_when_secret_unchanged() -> None:
    backend = FakeClipboardBackend()
    svc = ClipboardService(backend)
    ticks: list[int] = []
    cleared_states: list[bool] = []

    svc.copy_secret(
        "MySecret!99",
        timeout_seconds=2,
        on_tick=ticks.append,
        on_cleared=cleared_states.append,
    )
    assert backend.clipboard_content == "MySecret!99"
    assert ticks == [2]

    backend.fire_next()
    assert ticks == [2, 1]
    assert backend.clipboard_content == "MySecret!99"

    backend.fire_next()
    assert cleared_states == [True]
    assert backend.clipboard_content == ""


def test_clipboard_preserves_external_data_copied_later() -> None:
    backend = FakeClipboardBackend()
    svc = ClipboardService(backend)
    cleared_states: list[bool] = []

    svc.copy_secret("OriginalSecret", timeout_seconds=1, on_cleared=cleared_states.append)
    backend.clipboard_content = "User copied something else"

    backend.fire_next()
    assert cleared_states == [False]
    assert backend.clipboard_content == "User copied something else"


def test_session_vault_records_caps_and_wipes() -> None:
    vault = SessionVaultService(max_entries=3)
    secrets = [generate_password(PasswordPolicy(length=16)) for _ in range(4)]

    for item in secrets:
        vault.record(item)
    # Re-recording newest does not duplicate
    vault.record(secrets[-1])

    entries = vault.entries()
    assert len(entries) == 3
    assert entries[0].value == secrets[-1].value

    vault.wipe()
    assert vault.count == 0
    assert vault.entries() == ()


def test_settings_store_roundtrip_and_corrupt_fallback(tmp_path: Path) -> None:
    cfg = tmp_path / "prefs.json"
    store = SettingsStore(cfg)

    assert store.load() == AppPreferences()

    custom = AppPreferences(
        theme="light",
        clipboard_clear_seconds=60,
        mask_secret_display=True,
        last_preset_key="memorable_passphrase",
    )
    assert store.save(custom) is True
    assert store.load() == custom

    cfg.write_text("{corrupt-json", encoding="utf-8")
    assert store.load() == AppPreferences()
