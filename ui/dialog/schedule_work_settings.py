"""ui.dialog.schedule_work_settings

Dialog cài đặt cho màn "Sắp xếp lịch Làm việc".

Yêu cầu:
- Click button "Cài đặt" ở TitleBar2 thì mở dialog này
- Dialog hiển thị ở giữa màn hình (ưu tiên giữa parent)
- Set kích thước cho cửa sổ

Cài đặt hiện có:
- Kích thước chữ bảng (body)
- Đậm/nhạt bảng (body)
- Kích thước chữ header
- Đậm/nhạt header
- Chọn cột để căn lề + đậm/nhạt

Lưu/đọc: core.ui_settings (database/ui_settings.json)
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer
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
    MAIN_CONTENT_BG_COLOR,
    UI_FONT,
)

from core.ui_settings import get_schedule_work_table_ui, update_schedule_work_table_ui


def _norm_text(s: str) -> str:
    return " ".join(str(s or "").strip().split())


class ScheduleWorkSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open ScheduleWorkSettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt sắp xếp lịch làm việc")
        self.setFixedSize(640, 420)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        self._ui = get_schedule_work_table_ui()

        group = QGroupBox("Cài đặt bảng Sắp xếp lịch làm việc", self)
        group.setFont(font_normal)

        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

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
        # Shared keys across both tables in schedule_work_widgets.py
        columns = [
            ("check", "Cột chọn"),
            ("employee_code", "Mã NV"),
            ("mcc_code", "Mã chấm công"),
            ("full_name", "Tên nhân viên"),
            ("department_name", "Phòng ban"),
            ("title_name", "Chức danh"),
            ("from_date", "Từ ngày"),
            ("to_date", "Đến ngày"),
            ("schedule_name", "Lịch làm việc"),
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
            a = (self._ui.column_align or {}).get(key, "left")
            idx_a = self.cbo_align.findData(a)
            self.cbo_align.setCurrentIndex(idx_a if idx_a >= 0 else 0)

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

        form.addRow("Kích thước chữ (bảng)", self.spin_font_size)
        form.addRow("Chữ đậm/nhạt (bảng)", self.cbo_table_weight)
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
            align = str(self.cbo_align.currentData() or "left").strip()
            col_weight = str(self.cbo_column_weight.currentData() or "inherit").strip()

            update_schedule_work_table_ui(
                font_size=fs,
                font_weight=fw,
                header_font_size=hfs,
                header_font_weight=hfw,
                column_key=col_key,
                column_align=align,
                column_bold=col_weight,
            )
            self._ui = get_schedule_work_table_ui()
            self.label_status.setText("Đã áp dụng.")
        except Exception as exc:
            self.label_status.setText(_norm_text(str(exc)))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._center_dialog)

    def _center_dialog(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            try:
                pg = parent.frameGeometry()
                center = pg.center()
                fg = self.frameGeometry()
                fg.moveCenter(center)
                self.move(fg.topLeft())
                return
            except Exception:
                pass

        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        fg = self.frameGeometry()
        fg.moveCenter(geo.center())
        self.move(fg.topLeft())
