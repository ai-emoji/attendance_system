"""ui.dialog.arrange_schedule_settings_dialog

Dialog cài đặt giao diện bảng "Khai báo lịch trình" (Arrange Schedule).

Áp dụng cho 2 bảng trong arrange_schedule_widgets:
- Danh sách lịch trình (bên trái)
- Bảng chi tiết ngày/ca (bên phải)

Cho phép chỉnh:
- Kích thước chữ bảng (body)
- Đậm/nhạt bảng
- Kích thước chữ header
- Đậm/nhạt header
- Căn lề + đậm/nhạt theo từng cột (theo key)

Lưu/đọc từ core.ui_settings và phát signal để các bảng đang mở cập nhật ngay.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.resource import (
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    UI_FONT,
)
from core.ui_settings import (
    get_arrange_schedule_table_ui,
    update_arrange_schedule_table_ui,
)


def _norm_text(s: str) -> str:
    return " ".join(str(s or "").strip().split())


class ArrangeScheduleSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open ArrangeScheduleSettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt khai báo lịch trình")
        self.setMinimumSize(660, 400)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        group = QGroupBox("Cài đặt bảng khai báo lịch trình", self)
        group.setFont(font_normal)

        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._ui = get_arrange_schedule_table_ui()

        self.spin_font_size = QSpinBox(group)
        self.spin_font_size.setRange(8, 24)
        self.spin_font_size.setValue(int(self._ui.font_size))
        self.spin_font_size.setFont(font_normal)

        self.cbo_table_weight = QComboBox(group)
        self.cbo_table_weight.setFont(font_normal)
        self.cbo_table_weight.addItem("Nhạt", "normal")
        self.cbo_table_weight.addItem("Đậm", "bold")
        idx_w = self.cbo_table_weight.findData(self._ui.font_weight)
        self.cbo_table_weight.setCurrentIndex(idx_w if idx_w >= 0 else 0)

        self.spin_header_font_size = QSpinBox(group)
        self.spin_header_font_size.setRange(8, 24)
        self.spin_header_font_size.setValue(int(self._ui.header_font_size))
        self.spin_header_font_size.setFont(font_normal)

        self.cbo_header_weight = QComboBox(group)
        self.cbo_header_weight.setFont(font_normal)
        self.cbo_header_weight.addItem("Nhạt", "normal")
        self.cbo_header_weight.addItem("Đậm", "bold")
        idx_hw = self.cbo_header_weight.findData(self._ui.header_font_weight)
        self.cbo_header_weight.setCurrentIndex(idx_hw if idx_hw >= 0 else 1)

        self.cbo_column = QComboBox(group)
        self.cbo_column.setFont(font_normal)

        # Keys are used by arrange_schedule_widgets.py when applying.
        columns = [
            ("list_schedule_name", "Danh sách lịch trình: Lịch trình"),
            ("detail_day", "Bảng chi tiết: Ngày"),
            ("detail_shift_1", "Bảng chi tiết: Tên ca 1"),
            ("detail_shift_2", "Bảng chi tiết: Tên ca 2"),
            ("detail_shift_3", "Bảng chi tiết: Tên ca 3"),
            ("detail_shift_4", "Bảng chi tiết: Tên ca 4"),
            ("detail_shift_5", "Bảng chi tiết: Tên ca 5"),
        ]
        for key, label in columns:
            self.cbo_column.addItem(label, key)

        self.cbo_align = QComboBox(group)
        self.cbo_align.setFont(font_normal)
        self.cbo_align.addItem("Căn trái", "left")
        self.cbo_align.addItem("Căn giữa", "center")
        self.cbo_align.addItem("Căn phải", "right")

        self.cbo_column_weight = QComboBox(group)
        self.cbo_column_weight.setFont(font_normal)
        self.cbo_column_weight.addItem("Theo bảng", "inherit")
        self.cbo_column_weight.addItem("Nhạt", "normal")
        self.cbo_column_weight.addItem("Đậm", "bold")

        def _refresh_column_defaults() -> None:
            key = str(self.cbo_column.currentData() or "").strip()
            a = (self._ui.column_align or {}).get(key, "center")
            idx_a = self.cbo_align.findData(a)
            self.cbo_align.setCurrentIndex(idx_a if idx_a >= 0 else 1)

            if key in (self._ui.column_bold or {}):
                self.cbo_column_weight.setCurrentIndex(
                    self.cbo_column_weight.findData(
                        "bold" if self._ui.column_bold.get(key) else "normal"
                    )
                )
            else:
                self.cbo_column_weight.setCurrentIndex(
                    self.cbo_column_weight.findData("inherit")
                )

        self.cbo_column.currentIndexChanged.connect(
            lambda _i: _refresh_column_defaults()
        )
        _refresh_column_defaults()

        form.addRow("Kích thước chữ", self.spin_font_size)
        form.addRow("Chữ đậm/nhạt (toàn bảng)", self.cbo_table_weight)
        form.addRow("Kích thước chữ (header)", self.spin_header_font_size)
        form.addRow("Chữ đậm/nhạt (header)", self.cbo_header_weight)
        form.addRow("Chọn cột", self.cbo_column)
        form.addRow("Căn lề cột", self.cbo_align)
        form.addRow("Đậm/nhạt cột", self.cbo_column_weight)

        self.label_status = QLabel("", self)
        self.label_status.setFont(font_normal)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(10)

        self.btn_apply = QPushButton("Áp dụng", self)
        self.btn_apply.setFont(font_button)
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_close = QPushButton("Đóng", self)
        self.btn_close.setFont(font_button)
        self.btn_close.setFixedHeight(34)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(self.btn_apply, 1)
        btn_row.addWidget(self.btn_close, 1)

        root.addWidget(group, 0)
        root.addWidget(self.label_status, 0)
        root.addLayout(btn_row)
        root.addStretch(1)

        self.btn_close.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self._on_apply)

    def _on_apply(self) -> None:
        try:
            fs = int(self.spin_font_size.value())
            fw = str(self.cbo_table_weight.currentData() or "normal").strip()
            hfs = int(self.spin_header_font_size.value())
            hfw = str(self.cbo_header_weight.currentData() or "bold").strip()
            col_key = str(self.cbo_column.currentData() or "").strip()
            align = str(self.cbo_align.currentData() or "center").strip()
            col_weight = str(self.cbo_column_weight.currentData() or "inherit").strip()

            update_arrange_schedule_table_ui(
                font_size=fs,
                font_weight=fw,
                header_font_size=hfs,
                header_font_weight=hfw,
                column_key=col_key,
                column_align=align,
                column_bold=col_weight,
            )
            self._ui = get_arrange_schedule_table_ui()
            self.label_status.setText("Đã áp dụng.")
        except Exception as exc:
            self.label_status.setText(_norm_text(str(exc)))
