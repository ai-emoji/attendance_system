"""ui.dialog.employee_list_dialog

Dialog hiển thị danh sách nhân viên (đầy đủ cột, ẩn ID).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout

from core.resource import ICON_EXCEL, resource_path
from core.ui_settings import get_last_save_dir, set_last_save_dir
from services.employee_services import EmployeeService
from ui.dialog.title_dialog import MessageDialog
from ui.widgets.employee_widgets import EmployeeTable


logger = logging.getLogger(__name__)


class EmployeeListDialog(QDialog):
    def __init__(
        self,
        service: EmployeeService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service or EmployeeService()

        self.setWindowTitle("Danh sách nhân viên")
        self.setFixedSize(1336, 768)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        self.cbo_search_by = QComboBox()
        self.cbo_search_by.setFixedHeight(32)
        self.cbo_search_by.setStyleSheet(
            "border-radius: 0px; border: 1px solid black; padding: 0 10px;"
        )
        self.cbo_search_by.addItem("STT", "stt")
        self.cbo_search_by.addItem("Mã NV", "employee_code")
        self.cbo_search_by.addItem("Họ và tên", "full_name")
        self.cbo_search_by.setCurrentIndex(1)

        self.inp_search_text = QLineEdit()
        self.inp_search_text.setPlaceholderText("Tìm kiếm...")
        self.inp_search_text.setFixedHeight(32)
        self.inp_search_text.setStyleSheet(
            "border-radius: 0px; border: 1px solid black; padding: 0 10px;"
        )

        # icon tìm kiếm (leading icon trong QLineEdit)
        try:
            self.inp_search_text.addAction(
                QIcon(resource_path("assets/images/search.svg")),
                QLineEdit.ActionPosition.LeadingPosition,
            )
        except Exception:
            pass

        self.cbo_employment_status = QComboBox()
        self.cbo_employment_status.setFixedHeight(32)
        self.cbo_employment_status.setStyleSheet(
            "border-radius: 0px; border: 1px solid black; padding: 0 10px;"
        )
        self.cbo_employment_status.addItem("Hiện trạng", "")
        self.cbo_employment_status.setFixedHeight(30)
        self.cbo_employment_status.addItem("Đi làm", "1")
        self.cbo_employment_status.addItem("Nghỉ thai sản", "2")
        self.cbo_employment_status.addItem("Đã nghỉ việc", "3")
        self.cbo_employment_status.setCurrentIndex(0)

        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.setStyleSheet(
            "background-color: white; border-radius: 0px; border: 1px solid black; padding: 0 10px;"
        )
        try:
            self.btn_refresh.setIcon(QIcon(resource_path("assets/images/refresh.svg")))
            self.btn_refresh.setIconSize(QSize(18, 18))
        except Exception:
            pass

        self.btn_export = QPushButton("Xuất danh sách")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(32)
        self.btn_export.setStyleSheet(
            "background-color: white; border-radius: 0px; border: 1px solid black; padding: 0 10px;"
        )
        self.btn_export.setIcon(QIcon(resource_path(ICON_EXCEL)))
        self.btn_export.setIconSize(QSize(18, 18))

        self.label_total = QLabel("Tổng: 0")
        self.label_total.setStyleSheet("border-radius: 0px;")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        header.addWidget(self.cbo_search_by, 0)
        header.addWidget(self.inp_search_text, 1)
        header.addWidget(self.btn_refresh, 0)
        header.addWidget(self.cbo_employment_status, 0)
        header.addWidget(self.btn_export, 0)
        header.addWidget(self.label_total, 0)

        self.table = EmployeeTable(self)
        self.table.show_all_columns()  # show full columns but keep ID hidden

        root.addLayout(header, 0)
        root.addWidget(self.table, 1)

        self.cbo_search_by.currentIndexChanged.connect(self.refresh)
        self.inp_search_text.textChanged.connect(self.refresh)
        self.cbo_employment_status.currentIndexChanged.connect(self.refresh)
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_export.clicked.connect(self.on_export)

        self.refresh()

    def _get_filters(self) -> dict:
        search_by = self.cbo_search_by.currentData()
        search_by = str(search_by).strip() if search_by is not None else ""

        status = self.cbo_employment_status.currentData()
        status = str(status).strip() if status is not None else ""
        return {
            "search_by": search_by,
            "search_text": self.inp_search_text.text().strip(),
            "employment_status": status,
            "department_id": None,
        }

    def refresh(self) -> None:
        try:
            rows = self._service.list_employees(self._get_filters())
            self.table.set_rows(rows)
            try:
                self.label_total.setText(f"Tổng: {len(rows)}")
            except Exception:
                pass
        except Exception:
            logger.exception("Không thể tải danh sách nhân viên")
            self.table.clear()
            try:
                self.label_total.setText("Tổng: 0")
            except Exception:
                pass

    def on_refresh(self) -> None:
        try:
            self.table.clear_column_filters()
        except Exception:
            pass

        try:
            self.inp_search_text.blockSignals(True)
            self.inp_search_text.setText("")
        finally:
            try:
                self.inp_search_text.blockSignals(False)
            except Exception:
                pass

        try:
            self.cbo_search_by.blockSignals(True)
            self.cbo_search_by.setCurrentIndex(1)
        finally:
            try:
                self.cbo_search_by.blockSignals(False)
            except Exception:
                pass

        try:
            self.cbo_employment_status.blockSignals(True)
            self.cbo_employment_status.setCurrentIndex(0)
        finally:
            try:
                self.cbo_employment_status.blockSignals(False)
            except Exception:
                pass

        self.refresh()

    def on_export(self) -> None:
        selected_rows = []
        try:
            selected_rows = self.table.get_selected_row_dicts()
        except Exception:
            selected_rows = []

            default_name = "Danh sách nhân viên.xlsx"
            initial = str(Path(get_last_save_dir()) / default_name)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Xuất danh sách nhân viên",
                initial,
                "Excel (*.xlsx)",
            )
        if not file_path:
            return
            try:
                set_last_save_dir(str(Path(file_path).parent))
            except Exception:
                pass

        if selected_rows:
            ok, msg = self._service.export_xlsx_rows(file_path, selected_rows)
        else:
            filters = self._get_filters()
            ok, msg = self._service.export_xlsx(file_path, filters)
        MessageDialog.info(self, "Xuất danh sách", msg)
