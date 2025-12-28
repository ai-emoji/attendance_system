"""ui.dialog.loading_dialog

A lightweight loading/progress dialog used for long-running tasks.

Goals:
- Progress from 0..100 (no numeric text shown; color-filled bar instead).
- Smooth UI (does not block the event loop); task should run in a worker thread.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from core.resource import COLOR_BUTTON_PRIMARY, MAIN_CONTENT_BG_COLOR


class LoadingDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        title: str = "Đang tải",
        message: str = "Đang xử lý dữ liệu...",
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(str(title))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._label = QLabel(str(message))
        self._label.setWordWrap(True)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)  # "dùng màu thay số"

        # Style uses existing theme constants (no new hard-coded colors).
        self._bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid rgba(0,0,0,0.15);
                border-radius: 6px;
                background: rgba(0,0,0,0.06);
                height: 16px;
            }
            QProgressBar::chunk {
                background: %s;
                border-radius: 6px;
            }
            """
            % (COLOR_BUTTON_PRIMARY,)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)

        self.setStyleSheet(f"background: {MAIN_CONTENT_BG_COLOR};")

        self._anim = QPropertyAnimation(self._bar, b"value", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.setDuration(90)  # short smoothing; keeps UI responsive

        self._target_value: int = 0
        self._reported_value: int = 0
        self._done: bool = False

        # Count-based progress: ensures UI can show 1/5000..5000/5000 without skipping.
        self._total_count: int | None = None
        self._done_display: int = 0
        self._done_target: int = 0
        self._count_base_message: str = str(message)
        self._count_timer = QTimer(self)
        self._count_timer.setInterval(2)
        self._count_timer.timeout.connect(self._tick_count)

        # Minimum duration for the visual progress to reach 100%.
        # This is set by caller based on data size.
        self._min_duration_ms: int = 900
        self._elapsed = QElapsedTimer()
        self._elapsed.start()

        # Indeterminate/busy mode: show an infinite progress bar (no percent/count).
        self._indeterminate: bool = False
        self._saved_bar_range: tuple[int, int] = (0, 100)

    def set_indeterminate(
        self, enabled: bool = True, message: str | None = None
    ) -> None:
        """Enable/disable indeterminate (busy) mode.

        When enabled, the progress bar switches to an infinite indicator and ignores
        percent/count progress updates.
        """

        self._indeterminate = bool(enabled)

        if message is not None:
            self.set_message(str(message))

        if self._indeterminate:
            # Stop count-mode timer if running.
            try:
                if self._count_timer.isActive():
                    self._count_timer.stop()
            except Exception:
                pass
            self._total_count = None

            # Save current range and switch to infinite indicator.
            try:
                self._saved_bar_range = (
                    int(self._bar.minimum()),
                    int(self._bar.maximum()),
                )
            except Exception:
                self._saved_bar_range = (0, 100)

            try:
                self._bar.setRange(0, 0)
                self._bar.setValue(0)
            except Exception:
                pass
            return

        # Disable indeterminate: restore percent mode.
        lo, hi = self._saved_bar_range
        try:
            if int(hi) <= int(lo):
                lo, hi = 0, 100
        except Exception:
            lo, hi = 0, 100

        try:
            self._bar.setRange(int(lo), int(hi))
            if int(hi) == 100:
                self._bar.setValue(max(0, min(100, int(self._bar.value()))))
        except Exception:
            pass

    def set_message(self, message: str) -> None:
        self._label.setText(str(message))

    def set_progress(self, value: int, *, smooth: bool = True) -> None:
        # Percent-mode only (0..100). Count-mode uses set_count_target/_tick_count.
        v = max(0, min(100, int(value)))
        self._target_value = v

        if not smooth:
            self._bar.setValue(v)
            return

        cur = int(self._bar.value())
        if v == cur:
            return

        # Restart animation from current -> target.
        try:
            if self._anim.state() == QPropertyAnimation.State.Running:
                self._anim.stop()
        except Exception:
            pass
        self._anim.setStartValue(cur)
        self._anim.setEndValue(v)
        self._anim.start()

    def set_min_duration_ms(self, ms: int) -> None:
        self._min_duration_ms = max(250, int(ms))

        # Spread count increments across min duration when total is known.
        try:
            if self._total_count and int(self._total_count) > 0:
                interval = int(
                    max(2, min(15, self._min_duration_ms / int(self._total_count)))
                )
                self._count_timer.setInterval(interval)
        except Exception:
            pass

    def set_count_target(
        self,
        done: int,
        total: int,
        message: str | None = None,
    ) -> None:
        """Set desired done/total; UI will animate done by +1 each tick (no skipping)."""

        try:
            t = int(total)
        except Exception:
            t = 0
        if t <= 0:
            # Fallback to percent-based progress if total unknown.
            if message is not None:
                self.set_message(str(message))
            return

        try:
            d = int(done)
        except Exception:
            d = 0
        d = max(0, min(t, d))

        if message is not None:
            self._count_base_message = str(message)

        # Initialize total if first time or changed.
        if self._total_count != t:
            self._total_count = t
            self._done_display = 0
            self._done_target = 0

            # Switch progress bar to count-range so fill matches done/total across full width.
            try:
                self._bar.setRange(0, int(t))
                self._bar.setValue(0)
            except Exception:
                pass

            # Recompute interval to fit into min duration.
            interval = int(max(2, min(15, self._min_duration_ms / max(1, t))))
            self._count_timer.setInterval(interval)

        self._done_target = max(self._done_target, d)

        if not self._count_timer.isActive():
            self._count_timer.start()

    def _tick_count(self) -> None:
        if self._total_count is None or int(self._total_count) <= 0:
            try:
                self._count_timer.stop()
            except Exception:
                pass
            return

        if int(self._done_display) < int(self._done_target):
            self._done_display += 1

        # Update label with exact count.
        self.set_message(
            f"{self._count_base_message} ({self._done_display}/{self._total_count})"
        )

        # Update bar value based on count (full-width fill).
        try:
            self._bar.setValue(int(self._done_display))
        except Exception:
            pass

        # Stop timer when caught up and we're not expecting more.
        if int(self._done_display) >= int(self._done_target):
            if self._done:
                try:
                    self._count_timer.stop()
                except Exception:
                    pass
            else:
                # Keep running lightly in case target increases soon.
                pass

    def set_reported_progress(self, value: int, message: str | None = None) -> None:
        """Update progress reported by worker.

        Visual progress is clamped by elapsed time so it doesn't jump to 100% too fast.
        """

        if message is not None:
            self.set_message(str(message))

        # Indeterminate mode: keep busy indicator, ignore percent updates.
        if self._indeterminate:
            return

        v = max(0, min(100, int(value)))
        self._reported_value = v

        # If count-mode is active, ignore percent updates for the bar.
        # The bar is driven by done/total to avoid looking stuck at 1% for big totals.
        if self._total_count is not None and int(self._total_count) > 0:
            return

        if self._done:
            # When done, we allow finishing to 100.
            self.set_progress(v, smooth=True)
            return

        # Clamp by elapsed time (0..99) until done.
        try:
            elapsed = int(self._elapsed.elapsed())
        except Exception:
            elapsed = 0
        time_cap = int((elapsed / max(1, self._min_duration_ms)) * 99)
        time_cap = max(0, min(99, time_cap))
        visual = min(int(v), int(time_cap))
        self.set_progress(visual, smooth=True)

    def finish_and_close(self, *, delay_ms: int = 120) -> None:
        """Set to 100% and close shortly after (lets user see completion)."""

        self._done = True

        # If indeterminate, restore percent mode so users can see completion.
        if self._indeterminate:
            try:
                self.set_indeterminate(False)
            except Exception:
                pass

        # If worker finished quickly, wait until min duration is met.
        try:
            elapsed = int(self._elapsed.elapsed())
        except Exception:
            elapsed = 0
        remaining = max(0, int(self._min_duration_ms) - int(elapsed))

        # Ensure count reaches total before closing (if total is known).
        if self._total_count is not None and int(self._total_count) > 0:
            try:
                self._done_target = int(self._total_count)
                if not self._count_timer.isActive():
                    self._count_timer.start()
            except Exception:
                pass

        # In count-mode, set the bar to total (full width).
        if self._total_count is not None and int(self._total_count) > 0:
            try:
                self._bar.setRange(0, int(self._total_count))
                self._bar.setValue(int(self._total_count))
            except Exception:
                pass
        else:
            self.set_progress(100, smooth=True)

        def _close() -> None:
            try:
                self.accept()
            except Exception:
                try:
                    self.close()
                except Exception:
                    pass

        # If count is far behind, wait long enough for 1-by-1 animation.
        extra = 0
        try:
            if self._total_count is not None:
                interval = int(self._count_timer.interval() or 1)
                extra = int(
                    max(0, (int(self._done_target) - int(self._done_display)))
                    * interval
                )
        except Exception:
            extra = 0

        QTimer.singleShot(int(max(delay_ms, remaining, extra)), _close)

    @property
    def progress(self) -> int:
        try:
            return int(self._bar.value())
        except Exception:
            return 0

    @property
    def target_progress(self) -> int:
        return int(self._target_value)
