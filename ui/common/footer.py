"""ui.common.footer

Footer của ứng dụng.

Yêu cầu:
- Min width theo MIN_MAINWINDOW_WIDTH
- Chiều cao cố định 30px
- Tách riêng phần nền (bg) và nội dung
- Nền COLOR_BG_FOOTER chiếm 100% kích thước
- Nội dung overlay trên nền, margin trái/phải 20px
- Trái: thứ + ngày/tháng/năm + giờ:phút:giây (tiếng Việt)
- Phải: thông tin và phiên bản
- Áp dụng font đậm (FONT_WEIGHT_SEMIBOLD)
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from core.resource import (
    APP_INFO,
    APP_VERSION,
    COLOR_BG_FOOTER,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    FONT_WEIGHT_SEMIBOLD,
    MIN_MAINWINDOW_WIDTH,
    UI_FONT,
)


class Footer(QWidget):
    """Footer hiển thị thời gian và thông tin phiên bản."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._timer: QTimer | None = None
        self._label_datetime: QLabel | None = None
        self._label_info_version: QLabel | None = None
        self._bg: QWidget | None = None
        self._content: QWidget | None = None
        self._init_ui()
        self._start_clock()

    def _init_ui(self) -> None:
        self.setObjectName("Footer")
        self.setMinimumWidth(MIN_MAINWINDOW_WIDTH)
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Tách riêng nền (bg) và nội dung (content)
        self._bg = QWidget(self)
        self._bg.setObjectName("FooterBg")
        self._bg.setStyleSheet(f"#FooterBg {{ background-color: {COLOR_BG_FOOTER}; }}")

        self._content = QWidget(self)
        self._content.setObjectName("FooterContent")
        self._content.setStyleSheet("#FooterContent { background: transparent; }")

        content_layout = QHBoxLayout(self._content)
        content_layout.setContentsMargins(20, 0, 20, 0)
        content_layout.setSpacing(0)

        font_bold = QFont(UI_FONT, CONTENT_FONT)
        # FONT_WEIGHT_* trong resource.py đang theo thang CSS (400/500/600).
        # Qt dùng thang 0..99, nên map về Bold/Normal để hiển thị đúng.
        if FONT_WEIGHT_SEMIBOLD >= 600:
            font_bold.setWeight(QFont.Weight.Bold)
        else:
            font_bold.setWeight(QFont.Weight.Normal)

        self._label_datetime = QLabel("")
        self._label_datetime.setFont(font_bold)
        self._label_datetime.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self._label_datetime.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self._label_info_version = QLabel(f"{APP_INFO} | Phiên bản {APP_VERSION}")
        self._label_info_version.setFont(font_bold)
        self._label_info_version.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self._label_info_version.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self._label_info_version.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

        content_layout.addWidget(self._label_datetime, 1)
        content_layout.addWidget(self._label_info_version, 0)

    def resizeEvent(self, event) -> None:
        """Đảm bảo bg phủ 100% kích thước và content nằm đè lên trên."""
        rect = self.rect()
        if self._bg is not None:
            self._bg.setGeometry(rect)
        if self._content is not None:
            self._content.setGeometry(rect)
        super().resizeEvent(event)

    def _start_clock(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_datetime)
        self._update_datetime()
        self._timer.start()

    def _update_datetime(self) -> None:
        if self._label_datetime is None:
            return

        now = datetime.now()
        # Hiển thị tiếng Việt chắc chắn (không phụ thuộc locale hệ điều hành)
        weekday_map = {
            0: "Thứ Hai",
            1: "Thứ Ba",
            2: "Thứ Tư",
            3: "Thứ Năm",
            4: "Thứ Sáu",
            5: "Thứ Bảy",
            6: "Chủ Nhật",
        }
        weekday = weekday_map.get(now.weekday(), "")
        text = f"{weekday} | {now:%d-%m-%Y %H:%M:%S}"
        self._label_datetime.setText(text)
