"""ui.dialog.employee_table_settings_dialog

Dialog cài đặt giao diện bảng Nhân viên (EmployeeTable).

Yêu cầu:
- Tất cả control nằm trong 1 group + có button "Áp dụng"
- Click "Áp dụng" sẽ áp dụng ngay cho các bảng đang mở
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
from core.ui_settings import get_employee_table_ui, update_employee_table_ui
from ui.dialog.download_attendance_settings_dialog import (
    DownloadAttendanceSettingsDialog,
)


def _norm_text(s: str) -> str:
    return " ".join(str(s or "").strip().split())


class EmployeeTableSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open EmployeeTableSettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt bảng Nhân viên")
        self.setMinimumSize(620, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        group = QGroupBox("Cài đặt bảng Nhân viên", self)
        group.setFont(font_normal)
        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._ui = get_employee_table_ui()

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

        self.cbo_column = QComboBox(group)
        self.cbo_column.setFont(font_normal)
        # Column list: keep in sync with employee_widgets.py keys.
        columns = [
            ("stt", "STT"),
            ("employee_code", "MÃ NV"),
            ("full_name", "HỌ VÀ TÊN"),
            ("start_date", "Ngày vào làm"),
            ("title_name", "Chức Vụ"),
            ("department_name", "Phòng Ban"),
            ("date_of_birth", "Ngày Sinh"),
            ("gender", "Giới tính"),
            ("national_id", "CCCD/CMND"),
            ("id_issue_date", "Ngày Cấp"),
            ("id_issue_place", "Nơi Cấp"),
            ("address", "Địa chỉ"),
            ("phone", "Số điện thoại"),
            ("insurance_no", "Số Bảo Hiểm"),
            ("tax_code", "Mã số Thuế TNCN"),
            ("degree", "Bằng cấp"),
            ("major", "Chuyên ngành"),
            ("contract1_term", "HĐLĐ (ký lần 1)"),
            ("contract1_no", "Số HĐLĐ (lần 1)"),
            ("contract1_sign_date", "Ngày ký (lần 1)"),
            ("contract1_expire_date", "Ngày hết hạn (lần 1)"),
            ("contract2_indefinite", "HĐLĐ ký không thời hạn"),
            ("contract2_no", "Số HĐLĐ (không thời hạn)"),
            ("contract2_sign_date", "Ngày ký (không thời hạn)"),
            ("children_count", "Số con"),
            ("child_dob_1", "Ngày sinh con 1"),
            ("child_dob_2", "Ngày sinh con 2"),
            ("child_dob_3", "Ngày sinh con 3"),
            ("child_dob_4", "Ngày sinh con 4"),
            ("employment_status", "Hiện trạng"),
            ("note", "Ghi chú"),
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

        form.addRow("Kích thước chữ", self.spin_font_size)
        form.addRow("Chữ đậm/nhạt (toàn bảng)", self.cbo_table_weight)
        form.addRow("Chọn cột", self.cbo_column)
        form.addRow("Căn lề cột", self.cbo_align)
        form.addRow("Đậm/nhạt cột", self.cbo_column_weight)

        self.label_status = QLabel("", self)
        self.label_status.setFont(font_normal)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(10)

        self.btn_download_attendance = QPushButton(
            "Cài đặt tải dữ liệu chấm công", self
        )
        self.btn_download_attendance.setFont(font_button)
        self.btn_download_attendance.setFixedHeight(34)
        self.btn_download_attendance.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_apply = QPushButton("Áp dụng", self)
        self.btn_apply.setFont(font_button)
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_close = QPushButton("Đóng", self)
        self.btn_close.setFont(font_button)
        self.btn_close.setFixedHeight(34)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(self.btn_download_attendance, 1)
        btn_row.addWidget(self.btn_apply, 1)
        btn_row.addWidget(self.btn_close, 1)

        root.addWidget(group, 0)
        root.addWidget(self.label_status, 0)
        root.addLayout(btn_row)
        root.addStretch(1)

        self.btn_close.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_download_attendance.clicked.connect(self._open_download_attendance)

    def _open_download_attendance(self) -> None:
        dlg = DownloadAttendanceSettingsDialog(self)
        dlg.exec()

    def _on_apply(self) -> None:
        try:
            fs = int(self.spin_font_size.value())
            fw = str(self.cbo_table_weight.currentData() or "normal").strip()
            col_key = str(self.cbo_column.currentData() or "").strip()
            align = str(self.cbo_align.currentData() or "left").strip()
            col_weight = str(self.cbo_column_weight.currentData() or "inherit").strip()

            update_employee_table_ui(
                font_size=fs,
                font_weight=fw,
                column_key=col_key,
                column_align=align,
                column_bold=col_weight,
            )
            self._ui = get_employee_table_ui()
            self.label_status.setText("Đã áp dụng.")
        except Exception as exc:
            self.label_status.setText(_norm_text(str(exc)))
