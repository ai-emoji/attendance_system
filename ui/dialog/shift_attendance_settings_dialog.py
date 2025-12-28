"""ui.dialog.shift_attendance_settings_dialog

Dialog cài đặt giao diện bảng "Chấm công Theo ca" (Shift Attendance).

Yêu cầu:
- Tất cả control nằm trong 1 group + có button "Áp dụng"
- Có thể chọn để thay đổi từng cột: Ẩn/Hiện, Căn lề, Đậm/Nhạt
- Có thể chỉnh kích thước chữ + đậm/nhạt toàn bảng
- Mở dialog phải đọc setting hiện tại (xem trước), sau đó cài đặt

Ghi chú:
- Lưu/đọc từ core.ui_settings và phát signal để các bảng đang mở cập nhật ngay.
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
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    CONTENT_FONT,
    COLOR_TEXT_LIGHT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    UI_FONT,
)
from core.ui_settings import (
    get_shift_attendance_table_ui,
    update_shift_attendance_table_ui,
)


def _norm_text(s: str) -> str:
    return " ".join(str(s or "").strip().split())


class ShiftAttendanceSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open ShiftAttendanceSettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt bảng Chấm công Theo ca")
        self.setMinimumSize(640, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        group = QGroupBox("Cài đặt bảng Chấm công Theo ca", self)
        group.setFont(font_normal)

        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._ui = get_shift_attendance_table_ui()

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

        # Keep in sync with ui.widgets.shift_attendance_widgets.MainContent1/_COLUMNS
        # and ui.widgets.shift_attendance_widgets.MainContent2/_COLUMNS.
        columns = [
            # Shared columns
            ("employee_code", "Mã nhân viên"),
            ("full_name", "Tên nhân viên"),
            # MainContent1 (employee list)
            ("mcc_code", "Mã chấm công"),
            ("schedule", "Lịch làm việc"),
            ("title_name", "Chức vụ"),
            ("department_name", "Phòng Ban"),
            ("start_date", "Ngày vào làm"),
            # MainContent2 (attendance grid)
            ("date", "Ngày"),
            ("weekday", "Thứ"),
            ("in_1", "Vào 1"),
            ("out_1", "Ra 1"),
            ("in_2", "Vào 2"),
            ("out_2", "Ra 2"),
            ("in_3", "Vào 3"),
            ("out_3", "Ra 3"),
            ("late", "Trễ"),
            ("early", "Sớm"),
            ("hours", "Giờ"),
            ("work", "Công"),
            ("kh", "KH"),
            ("hours_plus", "Giờ +"),
            ("work_plus", "Công +"),
            ("leave_plus", "KH +"),
            ("tc1", "TC1"),
            ("tc2", "TC2"),
            ("tc3", "TC3"),
            ("total", "Tổng"),
            ("shift_code", "Ca"),
        ]
        for key, label in columns:
            self.cbo_column.addItem(label, key)

        # Visible toggle (emoji) - replaces old checkbox/combobox UI
        self.btn_visible = QPushButton(group)
        self.btn_visible.setFont(font_normal)
        self.btn_visible.setCheckable(True)
        self.btn_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_visible.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 6px 10px; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:hover {{ color: {COLOR_TEXT_LIGHT}; }}",
                    # Checked = show
                    f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:checked:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                    # Unchecked = hide
                    f"QPushButton:!checked {{ background: {COLOR_BUTTON_CANCEL}; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:!checked:hover {{ background: {COLOR_BUTTON_CANCEL_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                ]
            )
        )

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

        def _set_visible_button(is_visible: bool) -> None:
            self.btn_visible.blockSignals(True)
            try:
                self.btn_visible.setChecked(bool(is_visible))
                self.btn_visible.setText("✅ Hiển thị" if bool(is_visible) else "❌ Ẩn")
            finally:
                self.btn_visible.blockSignals(False)

        self.btn_visible.toggled.connect(lambda v: _set_visible_button(bool(v)))

        def _refresh_column_defaults() -> None:
            key = str(self.cbo_column.currentData() or "").strip()

            vis = bool((self._ui.column_visible or {}).get(key, True))
            _set_visible_button(bool(vis))

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

        form.addRow("Kích thước chữ", self.spin_font_size)
        form.addRow("Chữ đậm/nhạt (toàn bảng)", self.cbo_table_weight)
        form.addRow("Kích thước chữ (header)", self.spin_header_font_size)
        form.addRow("Chữ đậm/nhạt (header)", self.cbo_header_weight)
        form.addRow("Chọn cột", self.cbo_column)
        form.addRow("Hiển thị cột", self.btn_visible)
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
            visible = "show" if bool(self.btn_visible.isChecked()) else "hide"
            align = str(self.cbo_align.currentData() or "left").strip()
            col_weight = str(self.cbo_column_weight.currentData() or "inherit").strip()

            update_shift_attendance_table_ui(
                font_size=fs,
                font_weight=fw,
                header_font_size=hfs,
                header_font_weight=hfw,
                column_key=col_key,
                column_visible=visible,
                column_align=align,
                column_bold=col_weight,
            )
            self._ui = get_shift_attendance_table_ui()
            self.label_status.setText("Đã áp dụng.")
        except Exception as exc:
            self.label_status.setText(_norm_text(str(exc)))
