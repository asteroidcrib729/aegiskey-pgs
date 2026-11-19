"""Anti-aliased segmented SVG meter visualizing cryptographic strength with flicker-free resize."""

import tkinter as tk
from contextlib import suppress

from password_generator.core.models import SecurityTier, StrengthReport
from password_generator.ui.theme import ThemePalette

_SEGMENTS: int = 6


class StrengthMeterCanvas(tk.Label):
    """Six-segment rounded cryptographic entropy gauge rendered crisply via Tk 9.0 SVG."""

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
        self._meter_image: tk.PhotoImage | None = None
        self._last_width: int = 0
        self._redraw_after_id: str | None = None
        self._height_px = max(10, round(10 * self._scale))

        super().__init__(
            master,
            bg=palette.bg_surface,
            bd=0,
            highlightthickness=0,
            anchor="w",
        )
        self.bind("<Configure>", self._on_configure)
        self.bind("<Destroy>", self._on_destroy)

    def set_palette(self, palette: ThemePalette) -> None:
        """Apply updated theme colors and schedule a smooth repaint."""
        self._palette = palette
        self.configure(bg=palette.bg_surface)
        self._schedule_redraw()

    def update_report(self, report: StrengthReport) -> None:
        """Bind a new ``StrengthReport`` and repaint segments."""
        self._report = report
        self._schedule_redraw()

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
        new_w = event.width
        if new_w > 20 and new_w != self._last_width:
            self._last_width = new_w
            self._schedule_redraw()

    def _schedule_redraw(self) -> None:
        if self._redraw_after_id is None:
            self._redraw_after_id = self.after_idle(self._redraw)

    def _redraw(self) -> None:
        self._redraw_after_id = None
        width = max(self._last_width, self.winfo_width(), round(360 * self._scale))
        height = self._height_px
        gap = max(4, round(6 * self._scale))
        seg_w = max(10.0, (width - gap * (_SEGMENTS - 1)) / _SEGMENTS)
        rx = min(height / 2.0, 4.0 * self._scale)

        active = self._active_segments(self._report)
        active_color = (
            self.tier_color(self._report.tier)
            if self._report is not None
            else self._palette.switch_off
        )

        rects: list[str] = []
        for idx in range(_SEGMENTS):
            x0 = idx * (seg_w + gap)
            fill = active_color if idx < active else self._palette.switch_off
            rects.append(
                f'<rect x="{x0:.2f}" y="0" width="{seg_w:.2f}" height="{height}" '
                f'rx="{rx:.2f}" fill="{fill}"/>'
            )

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">{"".join(rects)}</svg>'
        )
        self._meter_image = tk.PhotoImage(data=svg, format="svg")
        self.configure(image=self._meter_image)

    def _on_destroy(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is self:
            if self._redraw_after_id is not None:
                with suppress(tk.TclError):
                    self.after_cancel(self._redraw_after_id)
                self._redraw_after_id = None
            self._meter_image = None
