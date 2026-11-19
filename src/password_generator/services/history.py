"""RAM-only ephemeral session vault for recently generated secrets (never written to disk)."""

from dataclasses import dataclass
from datetime import datetime

from password_generator.core.models import GeneratedSecret, GenerationMode, SecurityTier


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """Single secret generated during the active application session."""

    value: str
    mode: GenerationMode
    entropy_bits: float
    tier: SecurityTier
    summary: str
    created_at: str


class SessionVaultService:
    """Bounded in-memory history of generated secrets that is wiped on clear or app exit."""

    def __init__(self, max_entries: int = 25) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1.")
        self._max_entries = max_entries
        self._entries: list[HistoryEntry] = []

    @property
    def count(self) -> int:
        """Number of secrets currently stored in RAM."""
        return len(self._entries)

    def entries(self) -> tuple[HistoryEntry, ...]:
        """Return session entries ordered newest-first."""
        return tuple(self._entries)

    def record(self, secret: GeneratedSecret) -> HistoryEntry:
        """Store a newly generated secret in memory, avoiding immediate duplicate rows."""
        if self._entries and self._entries[0].value == secret.value:
            return self._entries[0]

        entry = HistoryEntry(
            value=secret.value,
            mode=secret.mode,
            entropy_bits=secret.report.effective_bits,
            tier=secret.report.tier,
            summary=secret.summary,
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        self._entries.insert(0, entry)
        if len(self._entries) > self._max_entries:
            del self._entries[self._max_entries :]
        return entry

    def wipe(self) -> None:
        """Erase all stored session secrets from memory."""
        self._entries.clear()
