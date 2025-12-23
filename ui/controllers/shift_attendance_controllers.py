"""ui.controllers.shift_attendance_controllers

Controller cho màn "Chấm công Theo ca".

Hiện tại:
- Load phòng ban vào combobox
- Load danh sách nhân viên (lọc có mcc_code) vào bảng MainContent1
- Nút "Làm mới" reset toàn bộ field của MainContent1
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QTableWidgetItem

from services.shift_attendance_services import ShiftAttendanceService


logger = logging.getLogger(__name__)


class ShiftAttendanceController:
    def __init__(
        self,
        parent_window,
        content1,
        content2=None,
        service: ShiftAttendanceService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._content1 = content1
        self._content2 = content2
        self._service = service or ShiftAttendanceService()
        self._audit_mode: str = (
            "default"  # 'default' (dept/title) | 'selected' (checked)
        )

    def bind(self) -> None:
        self._content1.refresh_clicked.connect(self.on_refresh_clicked)
        self._content1.department_changed.connect(self.refresh)
        try:
            self._content1.title_changed.connect(self.refresh)
        except Exception:
            pass
        self._content1.search_changed.connect(self.refresh)
        if self._content2 is not None:
            self._content1.view_clicked.connect(self.on_view_clicked)

        # Initial
        self._load_departments()
        self._load_titles()
        self._reset_fields(clear_table=False)
        self.refresh()
        # Default: show ALL audit rows for current date range when opening.
        if self._content2 is not None:
            self._audit_mode = "default"
            self._load_audit_for_current_range(
                employee_ids=None,
                attendance_codes=None,
                department_id=None,
                title_id=None,
            )

    def _current_date_range(self) -> tuple[str | None, str | None]:
        try:
            from_qdate: QDate = self._content1.date_from.date()
            to_qdate: QDate = self._content1.date_to.date()
            return (
                from_qdate.toString("yyyy-MM-dd"),
                to_qdate.toString("yyyy-MM-dd"),
            )
        except Exception:
            return (None, None)

    def _load_audit_for_current_range(
        self,
        *,
        employee_ids: list[int] | None,
        attendance_codes: list[str] | None,
        department_id: int | None,
        title_id: int | None,
    ) -> None:
        if self._content2 is None:
            return

        from_date, to_date = self._current_date_range()
        try:
            rows = self._service.list_attendance_audit(
                from_date=from_date,
                to_date=to_date,
                employee_ids=employee_ids,
                attendance_codes=attendance_codes,
                department_id=department_id,
                title_id=title_id,
            )
            self._render_audit_table(rows)
        except Exception:
            logger.exception("Không thể tải attendance_audit")
            try:
                self._content2.table.setRowCount(0)
            except Exception:
                pass

    def _load_departments(self) -> None:
        try:
            items = self._service.list_departments_dropdown() or []
        except Exception:
            logger.exception("Không thể tải danh sách phòng ban")
            items = []

        cb = self._content1.cbo_department
        old = cb.blockSignals(True)
        try:
            cb.clear()
            cb.addItem("Tất cả phòng ban", None)
            for dept_id, dept_name in items:
                # Hiển thị kèm ID để dễ đối soát
                cb.addItem(f"{dept_id} - {dept_name}", int(dept_id))
        finally:
            cb.blockSignals(old)

    def _load_titles(self) -> None:
        cb = getattr(self._content1, "cbo_title", None)
        if cb is None:
            return

        try:
            items = self._service.list_titles_dropdown() or []
        except Exception:
            logger.exception("Không thể tải danh sách chức vụ")
            items = []

        old = cb.blockSignals(True)
        try:
            cb.clear()
            cb.addItem("Tất cả chức vụ", None)
            for title_id, title_name in items:
                cb.addItem(f"{title_id} - {title_name}", int(title_id))
        finally:
            cb.blockSignals(old)

    def _selected_department_id(self) -> int | None:
        try:
            dept_id = self._content1.cbo_department.currentData()
            return int(dept_id) if dept_id else None
        except Exception:
            return None

    def _selected_title_id(self) -> int | None:
        try:
            cb = getattr(self._content1, "cbo_title", None)
            if cb is None:
                return None
            title_id = cb.currentData()
            return int(title_id) if title_id else None
        except Exception:
            return None

    def _build_filters(self) -> dict[str, Any]:
        filters: dict[str, Any] = {}

        filters["department_id"] = self._selected_department_id()
        filters["title_id"] = self._selected_title_id()

        search_by = self._content1.cbo_search_by.currentData()
        search_text = str(self._content1.inp_search_text.text() or "").strip()

        if search_by and search_text:
            filters["search_by"] = str(search_by)
            filters["search_text"] = search_text
        else:
            filters["search_by"] = None
            filters["search_text"] = None

        return filters

    def _reset_fields(self, *, clear_table: bool) -> None:
        # Reset inputs
        try:
            self._content1.cbo_department.setCurrentIndex(0)
        except Exception:
            pass
        try:
            self._content1.cbo_search_by.setCurrentIndex(0)
        except Exception:
            pass
        try:
            self._content1.inp_search_text.setText("")
        except Exception:
            pass

        # Reset dates
        today = QDate.currentDate()
        try:
            self._content1.date_from.setDate(today)
            self._content1.date_to.setDate(today)
        except Exception:
            pass

        # Reset counter/total + table
        try:
            self._content1.set_total(0)
        except Exception:
            pass
        if clear_table:
            try:
                self._content1.table.setRowCount(0)
            except Exception:
                pass

    def on_refresh_clicked(self) -> None:
        self._load_departments()
        self._load_titles()
        self._reset_fields(clear_table=True)
        self.refresh()
        # Default: show ALL audit rows for current date range after refresh.
        if self._content2 is not None:
            self._audit_mode = "default"
            self._load_audit_for_current_range(
                employee_ids=None,
                attendance_codes=None,
                department_id=None,
                title_id=None,
            )

    def refresh(self) -> None:
        try:
            rows = self._service.list_employees(self._build_filters())
            self._render_main_table(rows)
            self._content1.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách nhân viên")
            try:
                self._content1.table.setRowCount(0)
            except Exception:
                pass
            try:
                self._content1.set_total(0)
            except Exception:
                pass

    def _render_main_table(self, rows: list[dict[str, Any]]) -> None:
        table = self._content1.table
        table.setRowCount(0)
        if not rows:
            return

        # Columns: [✓] | STT | Mã NV | Tên nhân viên | Mã chấm công | Lịch trình | Chức vụ | Phòng Ban | Ngày vào làm
        table.setRowCount(len(rows))
        for r_idx, r in enumerate(rows):
            emp_id = r.get("id")
            dept_id = r.get("department_id")
            title_id = r.get("title_id")

            mcc_code = r.get("mcc_code")
            attendance_code = (
                str(mcc_code or "").strip() or str(r.get("employee_code") or "").strip()
            )

            chk = QTableWidgetItem("❌")
            chk.setFlags(chk.flags() & ~Qt.ItemFlag.ItemIsEditable)
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            chk.setData(Qt.ItemDataRole.UserRole, emp_id)
            chk.setData(Qt.ItemDataRole.UserRole + 1, attendance_code)
            chk.setData(Qt.ItemDataRole.UserRole + 2, dept_id)
            chk.setData(Qt.ItemDataRole.UserRole + 3, title_id)
            table.setItem(r_idx, 0, chk)

            stt_val = r.get("stt")
            if stt_val is None or str(stt_val).strip() == "":
                stt_val = r_idx + 1
            stt_item = QTableWidgetItem(str(stt_val))
            stt_item.setFlags(stt_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r_idx, 1, stt_item)

            values = [
                r.get("employee_code"),
                r.get("full_name"),
                r.get("mcc_code"),
                "",  # Lịch trình: xử lý sau
                r.get("title_name"),
                r.get("department_name"),
                r.get("start_date"),
            ]

            for c_idx, v in enumerate(values, start=2):
                item = QTableWidgetItem(str(v or ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c_idx == 2:
                    item.setData(Qt.ItemDataRole.UserRole, emp_id)
                    item.setData(Qt.ItemDataRole.UserRole + 1, dept_id)
                    item.setData(Qt.ItemDataRole.UserRole + 2, title_id)
                table.setItem(r_idx, c_idx, item)

        # Ensure per-column UI settings (align/bold/visible) apply to created items.
        try:
            self._content1.apply_ui_settings()
        except Exception:
            pass

    def _selected_employee_id(self) -> int | None:
        try:
            table = self._content1.table
            row = int(table.currentRow())
            if row < 0:
                return None
            item = table.item(row, 0)
            if item is None:
                return None
            emp_id = item.data(Qt.ItemDataRole.UserRole)
            return int(emp_id) if emp_id is not None else None
        except Exception:
            return None

    def _selected_attendance_code(self) -> str | None:
        """Returns selected employee attendance code (mcc_code) from MainContent1 table."""
        try:
            table = self._content1.table
            row = int(table.currentRow())
            if row < 0:
                return None
            # Column order in MainContent1: [✓], STT, employee_code, full_name, mcc_code, ...
            item = table.item(row, 4)
            if item is None:
                return None
            code = str(item.text() or "").strip()
            return code or None
        except Exception:
            return None

    def on_view_clicked(self) -> None:
        if self._content2 is None:
            return

        checked_ids: list[int] = []
        checked_codes: list[str] = []
        try:
            checked_ids, checked_codes = self._content1.get_checked_employee_keys()
        except Exception:
            checked_ids, checked_codes = ([], [])

        if checked_ids or checked_codes:
            self._audit_mode = "selected"
            self._load_audit_for_current_range(
                employee_ids=checked_ids,
                attendance_codes=checked_codes,
                department_id=None,
                title_id=None,
            )
            return

        # No checkbox selection: apply department/title filters.
        self._audit_mode = "default"
        self._load_audit_for_current_range(
            employee_ids=None,
            attendance_codes=None,
            department_id=self._selected_department_id(),
            title_id=self._selected_title_id(),
        )

    def _render_audit_table(self, rows: list[dict[str, Any]]) -> None:
        if self._content2 is None:
            return

        table = self._content2.table
        table.setRowCount(0)
        if not rows:
            return

        cols = [k for (k, _label) in getattr(self._content2, "_COLUMNS", [])]
        if not cols:
            return

        table.setRowCount(len(rows))
        for r_idx, r in enumerate(rows):
            for c_idx, key in enumerate(cols):
                # Virtual columns
                if key == "__check":
                    item = QTableWidgetItem("❌")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    try:
                        item.setData(Qt.ItemDataRole.UserRole, r.get("id"))
                    except Exception:
                        pass
                elif key == "stt":
                    stt_val = r.get("stt")
                    if stt_val is None or str(stt_val).strip() == "":
                        stt_val = r_idx + 1
                    item = QTableWidgetItem(str(stt_val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    v = r.get(key)

                    # Allow MainContent2 to toggle HH:MM / HH:MM:SS for in/out columns.
                    if key in {"in_1", "out_1", "in_2", "out_2", "in_3", "out_3"}:
                        raw = "" if v is None else str(v)
                        try:
                            txt = self._content2._format_time_value(raw)  # type: ignore[attr-defined]
                        except Exception:
                            txt = raw
                        item = QTableWidgetItem(str(txt))
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw)
                        except Exception:
                            pass
                    else:
                        item = QTableWidgetItem("" if v is None else str(v))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(r_idx, c_idx, item)

        # Ensure per-column UI settings apply to created items.
        try:
            self._content2.apply_ui_settings()
        except Exception:
            pass
