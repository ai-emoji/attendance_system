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
from ui.dialog.arrange_schedule_settings_dialog import ArrangeScheduleSettingsDialog
from ui.dialog.declare_work_shift_settings_dialog import (
    DeclareWorkShiftSettingsDialog,
)
from ui.dialog.schedule_work_settings import ScheduleWorkSettingsDialog
from ui.dialog.shift_attendance_settings_dialog import ShiftAttendanceSettingsDialog


class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open SettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt")
        self.setMinimumSize(420, 280)

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

        self.btn_schedule_work = QPushButton("Cài đặt sắp xếp lịch làm việc", self)
        self.btn_schedule_work.setFont(font_button)
        self.btn_schedule_work.setFixedHeight(38)
        self.btn_schedule_work.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_arrange_schedule = QPushButton("Cài đặt khai báo lịch trình", self)
        self.btn_arrange_schedule.setFont(font_button)
        self.btn_arrange_schedule.setFixedHeight(38)
        self.btn_arrange_schedule.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_declare_work_shift = QPushButton("Cài đặt khai báo ca làm việc", self)
        self.btn_declare_work_shift.setFont(font_button)
        self.btn_declare_work_shift.setFixedHeight(38)
        self.btn_declare_work_shift.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_import_employee = QPushButton("Cài đặt import nhân viên", self)
        self.btn_import_employee.setFont(font_button)
        self.btn_import_employee.setFixedHeight(38)
        self.btn_import_employee.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_import_shift_attendance = QPushButton(
            "Cài đặt import chấm công theo ca", self
        )
        self.btn_import_shift_attendance.setFont(font_button)
        self.btn_import_shift_attendance.setFixedHeight(38)
        self.btn_import_shift_attendance.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_close = QPushButton("Đóng", self)
        self.btn_close.setFont(font_button)
        self.btn_close.setFixedHeight(38)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)

        root.addWidget(self.btn_employee_table)
        root.addWidget(self.btn_shift_attendance)
        root.addWidget(self.btn_download_attendance)
        root.addWidget(self.btn_schedule_work)
        root.addWidget(self.btn_import_employee)
        root.addWidget(self.btn_import_shift_attendance)
        root.addWidget(self.btn_arrange_schedule)
        root.addWidget(self.btn_declare_work_shift)
        root.addStretch(1)
        root.addWidget(self.btn_close)

        self.btn_close.clicked.connect(self.reject)
        self.btn_employee_table.clicked.connect(self._open_employee_table_settings)
        self.btn_shift_attendance.clicked.connect(self._open_shift_attendance_settings)
        self.btn_download_attendance.clicked.connect(
            self._open_download_attendance_settings
        )
        self.btn_schedule_work.clicked.connect(self._open_schedule_work_settings)
        self.btn_import_employee.clicked.connect(self._open_import_employee_settings)
        self.btn_import_shift_attendance.clicked.connect(
            self._open_import_shift_attendance_settings
        )
        self.btn_arrange_schedule.clicked.connect(self._open_arrange_schedule_settings)
        self.btn_declare_work_shift.clicked.connect(
            self._open_declare_work_shift_settings
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

    def _open_schedule_work_settings(self) -> None:
        dlg = ScheduleWorkSettingsDialog(self)
        dlg.exec()

    def _open_import_employee_settings(self) -> None:
        # ImportEmployeeDialog uses EmployeeTable, so reuse Employee table UI settings.
        dlg = EmployeeTableSettingsDialog(self)
        dlg.exec()

    def _open_import_shift_attendance_settings(self) -> None:
        # ImportShiftAttendanceDialog preview table reuses Shift Attendance UI settings.
        dlg = ShiftAttendanceSettingsDialog(self)
        dlg.exec()

    def _open_arrange_schedule_settings(self) -> None:
        dlg = ArrangeScheduleSettingsDialog(self)
        dlg.exec()

    def _open_declare_work_shift_settings(self) -> None:
        dlg = DeclareWorkShiftSettingsDialog(self)
        dlg.exec()
