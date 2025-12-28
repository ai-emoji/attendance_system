"""ui.controllers.employee_controllers

Controller cho màn "Thông tin Nhân viên".
"""

from __future__ import annotations

import logging
from pathlib import Path
import unicodedata

from core.ui_settings import get_last_save_dir, set_last_save_dir
from core.threads import BackgroundTaskRunner

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QProgressDialog

from services.employee_services import EmployeeService
from services.title_services import TitleService
from ui.dialog.employee_dialog import EmployeeDialog
from ui.dialog.employee_list_dialog import EmployeeListDialog
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

        self._tree_runner = BackgroundTaskRunner(self._parent_window, name="employee_tree")
        self._list_runner = BackgroundTaskRunner(self._parent_window, name="employee_list")

    def bind(self) -> None:
        # Wire signals first (fast), then load data in background.

        # Restore cached UI/table state (if any) before the first refresh.
        restored = False
        try:
            restored = bool(self._content.restore_cached_state_if_any())
        except Exception:
            restored = False

        self._content.search_changed.connect(self.refresh)
        self._content.export_clicked.connect(self.on_export)
        self._content.import_clicked.connect(self.on_import)
        self._content.view_list_clicked.connect(self.on_view_list)
        self._content.add_clicked.connect(self.on_add)
        self._content.edit_clicked.connect(self.on_edit)
        self._content.delete_clicked.connect(self.on_delete)
        self._content.refresh_clicked.connect(self.on_refresh_clicked)

        # Load tree async so the view can paint first.
        try:
            QTimer.singleShot(0, self._load_tree_async)
        except Exception:
            self._load_tree_async()

        if not restored:
            # Defer refresh so UI shows immediately.
            try:
                QTimer.singleShot(0, self.refresh)
            except Exception:
                self.refresh()

    def _load_tree_async(self) -> None:
        def _fn() -> object:
            dept_rows = self._service.list_departments_tree_rows()
            title_rows = []
            try:
                title_models = TitleService().list_titles()
                title_rows = [(t.id, t.department_id, t.title_name) for t in title_models]
            except Exception:
                title_rows = []
            return (list(dept_rows or []), list(title_rows or []))

        def _ok(result: object) -> None:
            try:
                dept_rows, title_rows = result if isinstance(result, tuple) else ([], [])
                d = list(dept_rows or []) if isinstance(dept_rows, list) else []
                t = list(title_rows or []) if isinstance(title_rows, list) else []
                self._content.department_tree.set_departments(d, titles=t)
            except Exception:
                logger.exception("Không thể tải cây phòng ban")

        def _err(_msg: str) -> None:
            try:
                self._content.department_tree.set_departments([], titles=[])
            except Exception:
                pass

        self._tree_runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def on_refresh_clicked(self) -> None:
        # User intent: refresh should clear department filtering.
        try:
            self._content.department_tree.clear_selection()
        except Exception:
            try:
                # Fallback in case the widget doesn't expose helper.
                self._content.department_tree.tree.clearSelection()
                self._content.department_tree.tree.setCurrentItem(None)
            except Exception:
                pass
        self.refresh()

    def _get_selected(self) -> tuple[int, str, str] | None:
        return self._content.table.get_selected_employee()

    @staticmethod
    def _norm_text(s: str) -> str:
        s0 = " ".join(str(s or "").strip().split()).lower()
        return "".join(
            ch
            for ch in unicodedata.normalize("NFKD", s0)
            if not unicodedata.combining(ch)
        )

    def _apply_tree_filters(self, filters: dict) -> dict:
        """Apply tree selection to filters.

        - Department node -> department_id
        - Title node -> title_id
        """

        filters = dict(filters or {})
        filters.setdefault("department_id", None)
        filters.setdefault("title_id", None)

        ctx = None
        try:
            ctx = self._content.department_tree.get_selected_node_context()
        except Exception:
            ctx = None

        if not ctx:
            return filters

        if ctx.get("type") == "title":
            filters["department_id"] = None
            filters["title_id"] = ctx.get("id")
        else:
            filters["department_id"] = ctx.get("id")
            filters["title_id"] = None

        return filters

    def refresh(self) -> None:
        # Debounce to keep UI responsive when typing.
        try:
            QTimer.singleShot(0, self._refresh_async)
        except Exception:
            self._refresh_async()

    def _refresh_async(self) -> None:
        try:
            filters = self._apply_tree_filters(self._content.get_filters())
        except Exception:
            filters = {}

        def _fn() -> object:
            rows = self._service.list_employees(filters)
            return list(rows or [])

        def _ok(result: object) -> None:
            try:
                data = list(result or []) if isinstance(result, list) else []
                self._content.table.set_rows(data)
                self._content.set_total(len(data))
            except Exception:
                logger.exception("Không thể tải danh sách nhân viên")
                try:
                    self._content.table.clear()
                except Exception:
                    pass
                try:
                    self._content.set_total(0)
                except Exception:
                    pass

        def _err(_msg: str) -> None:
            try:
                self._content.table.clear()
            except Exception:
                pass
            try:
                self._content.set_total(0)
            except Exception:
                pass

        self._list_runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def on_export(self) -> None:
        default_name = "Danh sách nhân viên.xlsx"
        initial = str(Path(get_last_save_dir()) / default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self._parent_window,
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

        selected_rows: list[dict] = []
        try:
            selected_rows = self._content.table.get_selected_row_dicts() or []
        except Exception:
            selected_rows = []

        if selected_rows:
            ok, msg = self._service.export_xlsx_rows(file_path, selected_rows)
        else:
            filters = self._apply_tree_filters(self._content.get_filters())
            ok, msg = self._service.export_xlsx(file_path, filters)
        MessageDialog.info(self._parent_window, "Xuất danh sách", msg)

    def on_import(self) -> None:
        dlg = ImportEmployeeDialog(service=self._service, parent=self._parent_window)
        if dlg.exec() == ImportEmployeeDialog.Accepted:
            self.refresh()

    def on_view_list(self) -> None:
        dlg = EmployeeListDialog(service=self._service, parent=self._parent_window)
        dlg.exec()

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
        selected_many = self._content.table.get_selected_employees()
        if not selected_many:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn ít nhất 1 dòng trong bảng trước khi Xóa.",
            )
            return

        # Bulk delete
        if len(selected_many) > 1:
            count = len(selected_many)
            sample_codes = [c for (_id, c, _n) in selected_many[:5] if str(c).strip()]
            sample_text = (
                ("\nVí dụ mã: " + ", ".join(sample_codes)) if sample_codes else ""
            )

            if not MessageDialog.confirm(
                self._parent_window,
                "Xác nhận xóa",
                f"Bạn có chắc muốn xóa {count} nhân viên?{sample_text}",
                ok_text="Xóa",
                cancel_text="Hủy",
                destructive=True,
            ):
                return

            progress = QProgressDialog(
                "Đang xóa nhân viên...",
                "Hủy",
                0,
                count,
                self._parent_window,
            )
            progress.setWindowTitle("Xóa nhân viên")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)

            ids = [int(i) for (i, _c, _n) in selected_many]

            canceled = False
            deleted = 0
            first_fail_msg: str | None = None

            def on_bulk_progress(done: int, total: int) -> None:
                progress.setValue(done)
                progress.setLabelText(f"{done}/{total} - Đang xóa...")
                if progress.wasCanceled():
                    raise RuntimeError("Đã hủy.")

            try:
                deleted, total_req = self._service.delete_employees_bulk(
                    ids, progress_cb=on_bulk_progress
                )
            except Exception as exc:
                canceled = "hủy" in str(exc).lower()
                first_fail_msg = str(exc)
                deleted = deleted or 0
                total_req = count

            try:
                progress.setValue(count)
            except Exception:
                pass
            try:
                progress.close()
            except Exception:
                pass

            self.refresh()

            if canceled:
                MessageDialog.info(
                    self._parent_window,
                    "Xóa nhân viên",
                    f"Đã xóa {deleted}/{count} nhân viên. (Đã hủy thao tác)",
                )
                return

            fail_count = max(0, int(count) - int(deleted))
            if fail_count == 0:
                MessageDialog.info(
                    self._parent_window,
                    "Xóa nhân viên",
                    f"Đã xóa {deleted}/{count} nhân viên.",
                )
            else:
                MessageDialog.info(
                    self._parent_window,
                    "Xóa nhân viên",
                    f"Đã xóa {deleted}/{count} nhân viên. Thất bại: {fail_count}.\n{first_fail_msg or ''}",
                )
            return

        # Single delete keeps existing dialog
        emp_id, _code, _name = selected_many[0]

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
