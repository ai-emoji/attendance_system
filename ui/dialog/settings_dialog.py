"""ui.dialog.settings_dialog

Dialog Cài đặt.

Yêu cầu hiện tại:
- Tạo button "Cài đặt bảng Nhân viên"; click sẽ mở dialog con
- Tách phần QGroupBox("Cài đặt bảng Nhân viên") sang file dialog mới
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout

from core.resource import CONTENT_FONT, FONT_WEIGHT_SEMIBOLD, UI_FONT
from ui.dialog.employee_table_settings_dialog import EmployeeTableSettingsDialog
from ui.dialog.download_attendance_settings_dialog import (
    DownloadAttendanceSettingsDialog,
)
from ui.dialog.shift_attendance_settings_dialog import ShiftAttendanceSettingsDialog


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open SettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt")
        self.setMinimumSize(420, 220)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        self.btn_employee_table = QPushButton("Cài đặt bảng Nhân viên", self)
        self.btn_employee_table.setFont(font_button)
        self.btn_employee_table.setFixedHeight(38)
        self.btn_employee_table.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_shift_attendance = QPushButton("Cài đặt chấm công theo ca", self)
        self.btn_shift_attendance.setFont(font_button)
        self.btn_shift_attendance.setFixedHeight(38)
        self.btn_shift_attendance.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_download_attendance = QPushButton(
            "Cài đặt tải dữ liệu chấm công", self
        )
        self.btn_download_attendance.setFont(font_button)
        self.btn_download_attendance.setFixedHeight(38)
        self.btn_download_attendance.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_close = QPushButton("Đóng", self)
        self.btn_close.setFont(font_button)
        self.btn_close.setFixedHeight(38)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)

        root.addWidget(self.btn_employee_table)
        root.addWidget(self.btn_shift_attendance)
        root.addWidget(self.btn_download_attendance)
        root.addStretch(1)
        root.addWidget(self.btn_close)

        self.btn_close.clicked.connect(self.reject)
        self.btn_employee_table.clicked.connect(self._open_employee_table_settings)
        self.btn_shift_attendance.clicked.connect(self._open_shift_attendance_settings)
        self.btn_download_attendance.clicked.connect(
            self._open_download_attendance_settings
        )

    def _open_employee_table_settings(self) -> None:
        dlg = EmployeeTableSettingsDialog(self)
        dlg.exec()

    def _open_shift_attendance_settings(self) -> None:
        dlg = ShiftAttendanceSettingsDialog(self)
        dlg.exec()

    def _open_download_attendance_settings(self) -> None:
        dlg = DownloadAttendanceSettingsDialog(self)
        dlg.exec()
