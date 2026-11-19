"""Persistence for non-secret user interface preferences only."""

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

ThemeName = Literal["dark", "light"]


@dataclass(frozen=True, slots=True)
class AppPreferences:
    """Non-sensitive UI and workflow preferences persisted across sessions."""

    theme: ThemeName = "dark"
    clipboard_clear_seconds: int = 30
    mask_secret_display: bool = False
    last_preset_key: str = "near_unbreakable"


def default_config_path() -> Path:
    """Return the OS-appropriate user configuration file path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "PasswordGeneratorApp" / "preferences.json"
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base_unix = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base_unix / "password-generator-app" / "preferences.json"


class SettingsStore:
    """Loads and saves ``AppPreferences`` safely as UTF-8 JSON without touching secrets."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or default_config_path()

    @property
    def path(self) -> Path:
        """File path used for preference persistence."""
        return self._path

    def load(self) -> AppPreferences:
        """Load persisted preferences, falling back to safe defaults on missing or invalid JSON."""
        try:
            raw_text = self._path.read_text(encoding="utf-8")
            raw_data = json.loads(raw_text)
        except OSError, ValueError:
            return AppPreferences()

        if not isinstance(raw_data, dict):
            return AppPreferences()

        raw_theme = raw_data.get("theme", "dark")
        theme: ThemeName = "light" if raw_theme == "light" else "dark"

        raw_timeout = raw_data.get("clipboard_clear_seconds", 30)
        timeout = (
            raw_timeout
            if isinstance(raw_timeout, int) and raw_timeout in {0, 15, 30, 60, 120}
            else 30
        )

        mask_display = bool(raw_data.get("mask_secret_display", False))
        preset_key = raw_data.get("last_preset_key", "near_unbreakable")
        if not isinstance(preset_key, str) or not preset_key:
            preset_key = "near_unbreakable"

        return AppPreferences(
            theme=theme,
            clipboard_clear_seconds=timeout,
            mask_secret_display=mask_display,
            last_preset_key=preset_key,
        )

    def save(self, prefs: AppPreferences) -> bool:
        """Write ``prefs`` to disk; returns False if the filesystem is read-only or unavailable."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(asdict(prefs), indent=2)
            self._path.write_text(f"{payload}\n", encoding="utf-8")
        except OSError:
            return False
        return True
