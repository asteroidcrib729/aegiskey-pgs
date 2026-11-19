"""Segmented high-DPI Canvas meter visualizing cryptographic strength and entropy."""

import tkinter as tk

from password_generator.core.models import SecurityTier, StrengthReport
from password_generator.ui.theme import ThemePalette

_SEGMENTS: int = 6


class StrengthMeterCanvas(tk.Canvas):
    """Six-segment cryptographic entropy gauge adapting cleanly to HiDPI and theme changes."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: ThemePalette,
        scale: float = 1.0,
    ) -> None:
        self._scale = max(1.0, scale)
        height = round(14 * self._scale)
        super().__init__(
            master,
            height=height,
            bg=palette.bg_surface,
            highlightthickness=0,
            bd=0,
        )
        self._palette = palette
        self._report: StrengthReport | None = None
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_palette(self, palette: ThemePalette) -> None:
        """Apply updated theme colors and redraw immediately."""
        self._palette = palette
        self.configure(bg=palette.bg_surface)
        self._redraw()

    def update_report(self, report: StrengthReport) -> None:
        """Bind a new ``StrengthReport`` and repaint segments."""
        self._report = report
        self._redraw()

    def tier_color(self, tier: SecurityTier) -> str:
        """Return the semantic accent color representing ``tier``."""
        if tier in (SecurityTier.CRITICAL, SecurityTier.WEAK):
            return self._palette.danger
        if tier == SecurityTier.FAIR:
            return self._palette.warning
        if tier in (SecurityTier.STRONG, SecurityTier.NEAR_UNBREAKABLE):
            return self._palette.success
        return self._palette.quantum

    def _active_segments(self, report: StrengthReport | None) -> int:
        if report is None or report.length == 0:
            return 0
        tier_map = {
            SecurityTier.CRITICAL: 1,
            SecurityTier.WEAK: 2,
            SecurityTier.FAIR: 3,
            SecurityTier.STRONG: 4,
            SecurityTier.NEAR_UNBREAKABLE: 5,
            SecurityTier.QUANTUM_RESISTANT: 6,
        }
        return tier_map[report.tier]

    def _redraw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), round(200 * self._scale))
        height = max(self.winfo_height(), round(14 * self._scale))
        gap = round(6 * self._scale)
        bar_h = round(8 * self._scale)
        top = max(0, (height - bar_h) // 2)
        seg_w = max(8.0, (width - gap * (_SEGMENTS - 1)) / _SEGMENTS)

        active = self._active_segments(self._report)
        active_color = (
            self.tier_color(self._report.tier)
            if self._report is not None
            else self._palette.switch_off
        )

        for idx in range(_SEGMENTS):
            x0 = idx * (seg_w + gap)
            x1 = x0 + seg_w
            fill = active_color if idx < active else self._palette.switch_off
            self.create_rectangle(x0, top, x1, top + bar_h, fill=fill, outline=fill)
