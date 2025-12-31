"""ui.dialog.start_dialog

Dialog khởi tạo ứng dụng.

Yêu cầu:
- Hiển thị tiến trình khởi tạo 0..100%.
- Có thanh nền (bg) bên dưới và thanh tiến trình chạy phía trên.
- Khi khởi tạo xong (100%) tự đóng để chuyển sang MainWindow.

Ghi chú:
- Dialog này chỉ mô phỏng tiến trình khởi tạo ở phía UI.
  Nếu cần gắn vào các bước init thật (kết nối DB, preload settings...),
  có thể cập nhật các mốc trong _tick().
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QElapsedTimer, QSize, QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from core.resource import (
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    MAIN_CONTENT_BG_COLOR,
    UI_FONT,
    get_app_icon,
    resource_path,
    set_window_icon,
)


class StartDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        title: str = "Đang khởi tạo ứng dụng...",
        create_main_window: Callable[[], object] | None = None,
    ) -> None:
        super().__init__(parent)
        self._min_visible_ms = 2000
        self._text_before_50 = str(title or "")
        self._text_after_50 = "Đang chuyển vào ứng dụng..."
        self._step_idx = 0
        self._started = False
        self._finish_scheduled = False
        self._work_done = False
        self._elapsed = QElapsedTimer()
        self._create_main_window = create_main_window
        self._main_window: object | None = None

        self.setModal(True)
        self.setWindowTitle("Khởi tạo")
        self.setFixedWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(f"background: {MAIN_CONTENT_BG_COLOR};")

        # App/window icon
        try:
            set_window_icon(self)
        except Exception:
            pass

        font_title = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_title.setWeight(QFont.Weight.DemiBold)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        # Logo (use existing packaged asset)
        self._logo = QLabel("")
        try:
            self._logo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        try:
            self._logo.setPixmap(get_app_icon().pixmap(QSize(72, 72)))
        except Exception:
            # Best-effort: skip showing logo.
            self._logo.setText("")

        self._label = QLabel(self._text_before_50)
        self._label.setFont(font_title)
        self._label.setWordWrap(True)

        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)

        # Use existing theme constants; avoid introducing new colors.
        # Keep a visible "bg" with a border, and a primary chunk.
        self._bar.setStyleSheet(
            "\n".join(
                [
                    f"QProgressBar {{ border: 1px solid {COLOR_BORDER}; border-radius: 6px; background: {MAIN_CONTENT_BG_COLOR}; height: 16px; }}",
                    f"QProgressBar::chunk {{ background: {COLOR_BUTTON_PRIMARY}; border-radius: 6px; }}",
                ]
            )
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self._logo)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._run_next_step)

        # Progress animation: drive the bar by elapsed time so it fills in 2s.
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(16)
        self._progress_timer.timeout.connect(self._tick_progress)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._started:
            return
        self._started = True
        self._finish_scheduled = False
        self._work_done = False
        try:
            self._elapsed.restart()
        except Exception:
            pass
        self._step_idx = 0
        self._bar.setValue(0)
        try:
            self._label.setText(self._text_before_50)
        except Exception:
            pass
        self._progress_timer.start()
        self._timer.start(0)

    def _accept_and_stop(self) -> None:
        try:
            self._progress_timer.stop()
        except Exception:
            pass
        self.accept()

    def _maybe_close(self) -> None:
        if not self._work_done:
            return
        if self._finish_scheduled:
            return

        try:
            elapsed = int(self._elapsed.elapsed())
        except Exception:
            elapsed = self._min_visible_ms

        remaining = max(0, int(self._min_visible_ms) - int(elapsed))
        if remaining <= 0:
            self._finish_scheduled = True
            self._accept_and_stop()
            return

        self._finish_scheduled = True
        QTimer.singleShot(remaining, self._accept_and_stop)

    def _finish(self) -> None:
        self._work_done = True
        self._maybe_close()

    def get_main_window(self) -> object | None:
        return self._main_window

    def _set_progress(self, value: int, message: str) -> None:
        # Progress bar is time-driven; step values are used only as semantic hints.
        if str(message or "").strip() == "Hoàn tất":
            try:
                self._label.setText("Hoàn tất")
            except Exception:
                pass

    def _tick_progress(self) -> None:
        try:
            elapsed = int(self._elapsed.elapsed())
        except Exception:
            elapsed = 0

        if self._min_visible_ms <= 0:
            pct = 100
        else:
            pct = int(min(100, (elapsed * 100) / int(self._min_visible_ms)))

        try:
            current = int(self._bar.value())
        except Exception:
            current = 0

        if pct > current:
            try:
                self._bar.setValue(pct)
            except Exception:
                pass

        # Update status text based on progress threshold.
        if not self._work_done:
            target_text = self._text_after_50 if pct >= 50 else self._text_before_50
            try:
                if self._label.text() != target_text:
                    self._label.setText(target_text)
            except Exception:
                pass

        # If work finishes early, close right at (or after) the 2s mark.
        if self._work_done:
            self._maybe_close()

    def _preload_ui_settings(self) -> None:
        from core.ui_settings import load_ui_settings

        # Ensure user ui_settings.json is initialized/loaded.
        load_ui_settings()

    def _preload_header_icons(self) -> None:
        # Preload icons used by Header ribbon so switching tabs feels instant.
        from ui.controllers.header_controllers import HeaderController

        ctrl = HeaderController(
            view=type("_", (), {})()
        )  # dummy view, we only use actions list
        tabs = [
            HeaderController.TAB_KHAI_BAO,
            HeaderController.TAB_KET_NOI,
            HeaderController.TAB_CHAM_CONG,
            HeaderController.TAB_CONG_CU,
        ]

        paths: set[str] = set()
        for t in tabs:
            for a in ctrl._get_actions_for_tab(t):
                s = str(a.svg or "").strip()
                if not s:
                    continue
                if "/" in s or "\\" in s:
                    paths.add(resource_path(s))
                else:
                    paths.add(resource_path(f"assets/images/{s}"))

        # Force SVG parse by requesting a pixmap.
        for p in sorted(paths):
            try:
                QIcon(p).pixmap(QSize(32, 32))
            except Exception:
                continue

    def _create_window(self) -> None:
        if self._create_main_window is None:
            return
        self._main_window = self._create_main_window()

    def _run_next_step(self) -> None:
        # Step-based progress: only advances when a real init step completes.
        steps: list[tuple[int, str, Callable[[], None]]] = [
            (10, "Đang tải cấu hình giao diện...", self._preload_ui_settings),
            (45, "Đang nạp biểu tượng và tài nguyên...", self._preload_header_icons),
            (100, "Đang khởi tạo cửa sổ chính...", self._create_window),
        ]

        if self._step_idx >= len(steps):
            self._finish()
            return

        pct, msg, fn = steps[self._step_idx]
        self._set_progress(pct, msg)

        try:
            fn()
        except Exception:
            # Best-effort: still allow app to proceed.
            pass

        self._step_idx += 1
        if self._step_idx >= len(steps):
            self._set_progress(100, "Hoàn tất")
            self._finish()
            return

        # Continue on next event-loop tick to keep UI responsive.
        self._timer.start(0)
