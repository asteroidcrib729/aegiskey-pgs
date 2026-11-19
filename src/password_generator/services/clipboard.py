"""Auto-clearing clipboard service to prevent secrets from lingering in the OS clipboard."""

from collections.abc import Callable
from contextlib import suppress
from typing import Protocol


class ClipboardBackend(Protocol):
    """Minimal Tkinter-compatible clipboard & timer interface for testability."""

    def clipboard_clear(self) -> None: ...
    def clipboard_append(self, string: str, /) -> None: ...
    def clipboard_get(self) -> str: ...
    def after(self, ms: int, func: Callable[[], object], /) -> str: ...
    def after_cancel(self, id: str) -> None: ...


class ClipboardService:
    """Manages secure clipboard copies with countdown ticks and conditional auto-wipe."""

    def __init__(self, backend: ClipboardBackend) -> None:
        self._backend = backend
        self._active_secret: str | None = None
        self._timer_id: str | None = None
        self._remaining_seconds: int = 0
        self._on_tick: Callable[[int], None] | None = None
        self._on_cleared: Callable[[bool], None] | None = None

    @property
    def remaining_seconds(self) -> int:
        """Seconds remaining before the active secret is wiped from the clipboard."""
        return self._remaining_seconds

    @property
    def has_active_secret(self) -> bool:
        """Whether an auto-clear timer is currently guarding a copied secret."""
        return self._active_secret is not None

    def copy_secret(
        self,
        secret: str,
        *,
        timeout_seconds: int = 30,
        on_tick: Callable[[int], None] | None = None,
        on_cleared: Callable[[bool], None] | None = None,
    ) -> None:
        """Copy ``secret`` to the clipboard and optionally schedule automatic clearing."""
        if not secret:
            return

        self.cancel_timer()
        self._backend.clipboard_clear()
        self._backend.clipboard_append(secret)

        self._active_secret = secret
        self._on_tick = on_tick
        self._on_cleared = on_cleared

        if timeout_seconds > 0:
            self._remaining_seconds = timeout_seconds
            if self._on_tick is not None:
                self._on_tick(self._remaining_seconds)
            self._schedule_next_tick()
        else:
            self._remaining_seconds = 0

    def clear_now(self, *, force: bool = True) -> bool:
        """Immediately clear the clipboard if it holds our secret (or always if ``force=True``).

        Returns:
            True if the clipboard was cleared, False if external clipboard data was preserved.
        """
        self.cancel_timer()
        expected = self._active_secret
        self._active_secret = None
        self._remaining_seconds = 0

        should_clear = force
        if not force and expected is not None:
            try:
                should_clear = self._backend.clipboard_get() == expected
            except Exception:
                should_clear = False

        if should_clear:
            try:
                self._backend.clipboard_clear()
                # Overwrite with "" to reduce Windows clipboard history artifact risk.
                self._backend.clipboard_append("")
                self._backend.clipboard_clear()
            except Exception:
                should_clear = False

        if self._on_cleared is not None:
            self._on_cleared(should_clear)
        return should_clear

    def cancel_timer(self) -> None:
        """Cancel any scheduled countdown callback without altering clipboard contents."""
        if self._timer_id is not None:
            with suppress(Exception):
                self._backend.after_cancel(self._timer_id)
            self._timer_id = None

    def _schedule_next_tick(self) -> None:
        self._timer_id = self._backend.after(1000, self._handle_tick)

    def _handle_tick(self) -> None:
        self._timer_id = None
        if self._active_secret is None:
            return

        self._remaining_seconds = max(0, self._remaining_seconds - 1)
        if self._remaining_seconds > 0:
            if self._on_tick is not None:
                self._on_tick(self._remaining_seconds)
            self._schedule_next_tick()
            return

        self.clear_now(force=False)
