"""Fast, flicker-free segmented meter visualizing cryptographic strength on HiDPI displays."""

import tkinter as tk

from password_generator.core.models import SecurityTier, StrengthReport
from password_generator.ui.theme import ThemePalette

_SEGMENTS: int = 6


class StrengthMeterCanvas(tk.Canvas):
    """Six-segment rounded cryptographic entropy gauge with synchronous zero-lag resize."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        palette: ThemePalette,
        scale: float = 1.0,
    ) -> None:
        self._scale = max(1.0, scale)
        self._palette = palette
        self._report: StrengthReport | None = None
        self._bar_h = max(8, round(8 * self._scale))
        self._canvas_h = self._bar_h + max(2, round(2 * self._scale))
        self._last_width: int = 0

        super().__init__(
            master,
            height=self._canvas_h,
            bg=palette.bg_surface,
            bd=0,
            highlightthickness=0,
        )
        self.bind("<Configure>", self._on_configure)

    def set_palette(self, palette: ThemePalette) -> None:
        """Apply updated theme colors and repaint segments immediately."""
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

    @staticmethod
    def _active_segments(report: StrengthReport | None) -> int:
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

    def _on_configure(self, event: tk.Event[tk.Misc]) -> None:
        if event.width > 20 and event.width != self._last_width:
            self._last_width = event.width
            self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        width = max(self._last_width, self.winfo_width(), round(360 * self._scale))
        gap = max(4, round(6 * self._scale))
        seg_w = max(14.0, (width - gap * (_SEGMENTS - 1)) / _SEGMENTS)
        cy = self._canvas_h / 2.0
        cap_r = self._bar_h / 2.0

        active = self._active_segments(self._report)
        active_color = (
            self.tier_color(self._report.tier)
            if self._report is not None
            else self._palette.switch_off
        )

        for idx in range(_SEGMENTS):
            x0 = idx * (seg_w + gap) + cap_r
            x1 = max(x0 + 1.0, idx * (seg_w + gap) + seg_w - cap_r)
            fill = active_color if idx < active else self._palette.switch_off
            self.create_line(
                x0,
                cy,
                x1,
                cy,
                width=self._bar_h,
                capstyle=tk.ROUND,
                fill=fill,
            )
