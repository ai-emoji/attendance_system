"""ui.controllers.employee_controllers

Controller cho màn "Thông tin Nhân viên".
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import QFileDialog

from services.employee_services import EmployeeService
from ui.dialog.employee_dialog import EmployeeDialog
from ui.dialog.import_employee_dialog import ImportEmployeeDialog
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class EmployeeController:
    def __init__(
        self, parent_window, content, service: EmployeeService | None = None
    ) -> None:
        self._parent_window = parent_window
        self._content = content
        self._service = service or EmployeeService()

    def bind(self) -> None:
        # Load department tree
        try:
            dept_rows = self._service.list_departments_tree_rows()
            self._content.department_tree.set_departments(dept_rows)
        except Exception:
            logger.exception("Không thể tải cây phòng ban")

        self._content.search_changed.connect(self.refresh)
        self._content.export_clicked.connect(self.on_export)
        self._content.import_clicked.connect(self.on_import)
        self._content.add_clicked.connect(self.on_add)
        self._content.edit_clicked.connect(self.on_edit)
        self._content.delete_clicked.connect(self.on_delete)
        self._content.refresh_clicked.connect(self.refresh)

        self.refresh()

    def _get_selected(self) -> tuple[int, str, str] | None:
        return self._content.table.get_selected_employee()

    def refresh(self) -> None:
        try:
            filters = self._content.get_filters()
            rows = self._service.list_employees(filters)
            self._content.table.set_rows(rows)
            self._content.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách nhân viên")
            self._content.table.clear()
            self._content.set_total(0)

    def on_export(self) -> None:
        filters = self._content.get_filters()
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent_window,
            "Xuất danh sách nhân viên",
            "employees.xlsx",
            "Excel (*.xlsx)",
        )
        if not file_path:
            return
        ok, msg = self._service.export_xlsx(file_path, filters)
        MessageDialog.info(self._parent_window, "Xuất danh sách", msg)

    def on_import(self) -> None:
        dlg = ImportEmployeeDialog(service=self._service, parent=self._parent_window)
        if dlg.exec() == ImportEmployeeDialog.Accepted:
            self.refresh()

    def on_add(self) -> None:
        departments = self._service.list_departments_dropdown()
        titles = self._service.list_titles_dropdown()
        issue_places = self._service.list_issue_places_dropdown()
        dlg = EmployeeDialog(
            mode="add",
            departments=departments,
            titles=titles,
            issue_places=issue_places,
            parent=self._parent_window,
        )

        def _save() -> None:
            ok, msg, _new_id = self._service.create_employee(dlg.get_data())
            dlg.set_status(msg, ok=ok)
            if ok:
                dlg.accept()

        dlg.btn_save.clicked.connect(_save)
        if dlg.exec() == EmployeeDialog.Accepted:
            self.refresh()

    def on_edit(self) -> None:
        selected = self._get_selected()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Sửa thông tin.",
            )
            return

        emp_id, _code, _name = selected

        employee = self._service.get_employee(emp_id)
        if not employee:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Không tìm thấy nhân viên để sửa.",
            )
            return

        departments = self._service.list_departments_dropdown()
        titles = self._service.list_titles_dropdown()
        issue_places = self._service.list_issue_places_dropdown()
        dlg = EmployeeDialog(
            mode="edit",
            employee=employee,
            departments=departments,
            titles=titles,
            issue_places=issue_places,
            parent=self._parent_window,
        )

        def _save() -> None:
            ok, msg = self._service.update_employee(emp_id, dlg.get_data())
            dlg.set_status(msg, ok=ok)
            if ok:
                dlg.accept()

        dlg.btn_save.clicked.connect(_save)
        if dlg.exec() == EmployeeDialog.Accepted:
            self.refresh()

    def on_delete(self) -> None:
        selected = self._get_selected()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Xóa.",
            )
            return

        emp_id, _code, _name = selected

        employee = self._service.get_employee(emp_id)
        if not employee:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Không tìm thấy nhân viên để xóa.",
            )
            return

        departments = self._service.list_departments_dropdown()
        titles = self._service.list_titles_dropdown()
        issue_places = self._service.list_issue_places_dropdown()
        dlg = EmployeeDialog(
            mode="delete",
            employee=employee,
            departments=departments,
            titles=titles,
            issue_places=issue_places,
            parent=self._parent_window,
        )

        def _do_delete() -> None:
            ok, msg = self._service.delete_employee(emp_id)
            dlg.set_status(msg, ok=ok)
            if ok:
                dlg.accept()

        dlg.btn_save.clicked.connect(_do_delete)
        if dlg.exec() == EmployeeDialog.Accepted:
            self.refresh()
