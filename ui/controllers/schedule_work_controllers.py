"""ui.controllers.schedule_work_controllers

Controller cho màn "Sắp xếp lịch Làm việc".

Hiện tại (theo spec UI-only):
- Load cây Phòng ban/Chức danh (bên trái)
- Wire buttons ở TitleBar2: Tìm kiếm / Làm mới / Xóa lịch NV
- Bên phải đang là placeholder table (chưa render dữ liệu)

Không dùng QMessageBox; dùng MessageDialog.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QDate, QTimer

from core.threads import BackgroundTaskRunner

from services.schedule_work_services import ScheduleWorkService
from ui.dialog.title_dialog import MessageDialog
from ui.dialog.schedule_work_settings import ScheduleWorkSettingsDialog


logger = logging.getLogger(__name__)


class ScheduleWorkController:
    def __init__(
        self,
        parent_window,
        view,
        service: ScheduleWorkService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._view = view
        self._service = service or ScheduleWorkService()

        # Cache search result (UI table will be implemented later)
        self._employees_cache = []

        # Current selected employee context for TempScheduleContent
        self._selected_employee: dict | None = None

        # Watch date change (midnight) to refresh default schedule column
        self._day_watch_timer: QTimer | None = None
        self._last_day_iso: str | None = None
        self._search_runner = BackgroundTaskRunner(self._parent_window, name="schedule_work_search")

    def bind(self) -> None:
        try:
            self._view.title2.search_clicked.connect(self.on_search)
            self._view.title2.refresh_clicked.connect(self.on_refresh)
            self._view.title2.delete_clicked.connect(self.on_delete)
            self._view.title2.settings_clicked.connect(self.on_open_settings)
        except Exception:
            pass

        # Auto-apply filter when clicking the department/title tree
        try:
            self._view.content.left.selection_changed.connect(self.on_search)
        except Exception:
            pass

        try:
            self._view.content.right.btn_apply.clicked.connect(self.on_apply)
        except Exception:
            pass

        # Temp schedule (Lịch trình tạm)
        try:
            self._view.content.right.table.itemSelectionChanged.connect(
                self.on_employee_selected
            )
        except Exception:
            pass
        try:
            self._view.content.temp.add_clicked.connect(self.on_temp_add)
            self._view.content.temp.delete_clicked.connect(self.on_temp_delete)
        except Exception:
            pass

        # Defer heavy initial loads so UI can paint first.
        try:
            QTimer.singleShot(0, self.refresh_tree)
            QTimer.singleShot(0, self.refresh_schedules)
            QTimer.singleShot(0, self.on_search)
        except Exception:
            self.refresh_tree()
            self.refresh_schedules()
            self.on_search()

        # Auto-refresh schedule names when day changes (00:00).
        # Requirement: when passing 23:59 -> 00:00 of next day, expired ranges should no longer show.
        self._start_day_watch()

    def on_open_settings(self) -> None:
        try:
            dlg = ScheduleWorkSettingsDialog(self._parent_window)
            dlg.exec()
        except Exception:
            logger.exception("Không thể mở cài đặt sắp xếp lịch làm việc")
            try:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Không thể mở cửa sổ Cài đặt sắp xếp lịch làm việc.",
                )
            except Exception:
                pass

    def _start_day_watch(self) -> None:
        try:
            today_iso = QDate.currentDate().toString("yyyy-MM-dd")
        except Exception:
            today_iso = None
        self._last_day_iso = today_iso

        if self._day_watch_timer is None:
            self._day_watch_timer = QTimer(self._view)
            self._day_watch_timer.setInterval(30 * 1000)  # 30s
            self._day_watch_timer.timeout.connect(self._on_day_watch_tick)

        try:
            if not self._day_watch_timer.isActive():
                self._day_watch_timer.start()
        except Exception:
            pass

    def _on_day_watch_tick(self) -> None:
        try:
            cur = QDate.currentDate().toString("yyyy-MM-dd")
        except Exception:
            return

        if not cur or cur == self._last_day_iso:
            return

        self._last_day_iso = cur
        # Day changed -> refresh UI mapping for new day
        try:
            self.refresh_default_schedule_column()
        except Exception:
            pass
        try:
            # Preserve current search filter when the day changes
            self.refresh_temp_table(self._get_selected_filters())
        except Exception:
            pass

    def refresh_temp_table(self, filters: dict | None = None) -> None:
        """Load global temp schedule assignments into TempScheduleContent.

        Spec: bảng 'Lịch trình tạm' hiển thị nhiều người trong 1 bảng,
        không phụ thuộc vào nhân viên đang chọn ở bảng 'Lịch trình mặc định'.

        Khi user tìm kiếm ở TitleBar2, bảng temp cũng được lọc theo cùng input.
        """

        def _norm(x) -> str:
            return str(x or "").strip().casefold()

        try:
            rows = list(self._service.list_temp_schedule_assignments() or [])

            try:
                search_text = _norm((filters or {}).get("search_text"))
                search_by = _norm((filters or {}).get("search_by"))
            except Exception:
                search_text = ""
                search_by = ""

            if search_text:
                filtered: list[dict] = []
                for r in rows:
                    code = _norm((r or {}).get("employee_code"))
                    name = _norm((r or {}).get("full_name"))

                    if search_by == "employee_code":
                        ok = search_text in code
                    elif search_by == "employee_name":
                        ok = search_text in name
                    else:
                        ok = (search_text in code) or (search_text in name)

                    if ok:
                        filtered.append(r)
                rows = filtered

            try:
                self._view.content.temp.set_rows_chunked(rows)
            except Exception:
                self._view.content.temp.set_rows(rows)
        except Exception:
            logger.exception("Không thể tải danh sách lịch trình tạm")
            try:
                self._view.content.temp.clear_rows()
            except Exception:
                pass

    def _qdate_from_iso(self, iso: str | None) -> QDate | None:
        s = str(iso or "").strip()
        if not s:
            return None
        try:
            qd = QDate.fromString(s, "yyyy-MM-dd")
            return qd if qd.isValid() else None
        except Exception:
            return None

    def _select_combo_by_data(self, combo, data) -> None:
        try:
            for i in range(int(combo.count())):
                if combo.itemData(i) == data:
                    combo.setCurrentIndex(i)
                    return
        except Exception:
            return

    def _get_selected_employee_from_table(self) -> dict | None:
        table = getattr(self._view.content.right, "table", None)
        if table is None:
            return None

        try:
            row = int(table.currentRow())
        except Exception:
            row = -1
        if row < 0:
            return None

        try:
            it_id = table.item(row, self._view.content.right.COL_ID)
            it_code = table.item(row, self._view.content.right.COL_EMP_CODE)
            it_name = table.item(row, self._view.content.right.COL_FULL_NAME)
        except Exception:
            return None

        if it_id is None:
            return None
        raw = str(it_id.text() or "").strip()
        if not raw:
            return None

        try:
            emp_id = int(raw)
        except Exception:
            return None
        if emp_id <= 0:
            return None

        return {
            "id": emp_id,
            "employee_code": str(it_code.text() or "").strip() if it_code else "",
            "full_name": str(it_name.text() or "").strip() if it_name else "",
        }

    def _get_current_employee_ids_in_table(self) -> list[int]:
        """Return employee IDs currently shown in the default schedule table."""

        ids: list[int] = []

        # Prefer cache built by on_search (fast, stable)
        for x in self._employees_cache or []:
            try:
                if isinstance(x, dict):
                    v = int(x.get("id") or 0)
                else:
                    v = int(getattr(x, "id", None) or 0)
            except Exception:
                continue
            if v > 0:
                ids.append(v)

        if ids:
            return list(dict.fromkeys(ids))

        # Fallback: read from UI table
        table = getattr(self._view.content.right, "table", None)
        if table is None:
            return []
        for r in range(int(table.rowCount())):
            it_id = table.item(r, self._view.content.right.COL_ID)
            if it_id is None:
                continue
            raw = str(it_id.text() or "").strip()
            if not raw:
                continue
            try:
                v = int(raw)
            except Exception:
                continue
            if v > 0:
                ids.append(v)

        return list(dict.fromkeys(ids))

    def refresh_default_schedule_column(
        self, employee_ids: list[int] | None = None
    ) -> None:
        """Refresh schedule names shown in the default schedule table."""

        ids = (
            employee_ids
            if employee_ids is not None
            else self._get_current_employee_ids_in_table()
        )
        ids = [int(x) for x in (ids or []) if int(x) > 0]
        if not ids:
            return
        try:
            schedule_map = self._service.get_employee_schedule_name_map(ids)
            self._view.content.right.apply_schedule_name_map(schedule_map)
        except Exception:
            logger.exception("Không thể tải lịch làm việc đã gán")

    def _get_employee_ids_by_temp_assignment_ids(
        self, assignment_ids: list[int]
    ) -> list[int]:
        if not assignment_ids:
            return []

        want = set()
        for x in assignment_ids:
            try:
                v = int(x)
            except Exception:
                continue
            if v > 0:
                want.add(v)
        if not want:
            return []

        # Query current temp list and map id -> employee_id
        try:
            rows = self._service.list_temp_schedule_assignments()
        except Exception:
            return []

        emp_ids: list[int] = []
        for r in rows or []:
            try:
                aid = int(r.get("id") or 0)
                if aid not in want:
                    continue
                eid = int(r.get("employee_id") or 0)
            except Exception:
                continue
            if eid > 0:
                emp_ids.append(eid)

        return list(dict.fromkeys(emp_ids))

    def on_employee_selected(self) -> None:
        """When selecting an employee in default schedule table, auto-bind TempScheduleContent."""

        emp = self._get_selected_employee_from_table()
        self._selected_employee = emp
        if not emp:
            # Do not clear the temp table; it's global.
            return

        # Default: today -> today
        try:
            today = QDate.currentDate()
            self._view.content.temp.inp_from.setDate(today)
            self._view.content.temp.inp_to.setDate(today)
        except Exception:
            pass

        # Auto-select active schedule (if any) and auto-fill range
        try:
            active = self._service.get_employee_active_schedule_assignment(
                employee_id=int(emp["id"])
            )
            if active:
                q_from = self._qdate_from_iso(active.get("effective_from"))
                q_to = self._qdate_from_iso(active.get("effective_to"))
                if q_from is not None:
                    self._view.content.temp.inp_from.setDate(q_from)
                if q_to is not None:
                    self._view.content.temp.inp_to.setDate(q_to)
                self._select_combo_by_data(
                    self._view.content.temp.cbo_schedule,
                    int(active.get("schedule_id") or 0),
                )
            else:
                # Placeholder
                try:
                    self._view.content.temp.cbo_schedule.setCurrentIndex(0)
                except Exception:
                    pass
        except Exception:
            logger.exception("Không thể auto-fill lịch trình tạm")

    def on_temp_add(self) -> None:
        temp = self._view.content.temp

        # Mode:
        # - If checkbox in TempScheduleContent is ✅: apply to all ✅ employees in default schedule table
        # - If ❌: apply only to the currently selected employee row
        apply_to_checked = False
        try:
            apply_to_checked = bool(temp.chk_update_by_selected.isChecked())
        except Exception:
            apply_to_checked = False

        target_employee_ids: list[int] = []
        if apply_to_checked:
            try:
                target_employee_ids = (
                    self._view.content.right.get_checked_employee_ids()
                )
            except Exception:
                target_employee_ids = []

            target_employee_ids = [
                int(x) for x in (target_employee_ids or []) if int(x) > 0
            ]
            target_employee_ids = list(dict.fromkeys(target_employee_ids))

            if not target_employee_ids:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng tick ✅ nhân viên ở bảng Lịch trình mặc định (hoặc bỏ chọn checkbox để thêm theo dòng đang chọn).",
                )
                return
        else:
            emp = self._selected_employee or self._get_selected_employee_from_table()
            if not emp:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng chọn nhân viên trên Lịch trình mặc định trước khi Thêm mới.",
                )
                return
            target_employee_ids = [int(emp["id"])]

        try:
            from_q = temp.inp_from.date()
            to_q = temp.inp_to.date()
        except Exception:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Vui lòng chọn Từ ngày / Đến ngày.",
            )
            return

        if to_q < from_q:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Đến ngày phải lớn hơn hoặc bằng Từ ngày.",
            )
            return

        schedule_id = None
        schedule_name = ""
        try:
            schedule_id = temp.cbo_schedule.currentData()
            schedule_name = str(temp.cbo_schedule.currentText() or "").strip()
        except Exception:
            schedule_id = None

        # Placeholder / clear option is not allowed for temp schedule
        try:
            if schedule_id is None or int(schedule_id) <= 0:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng chọn Lịch làm việc trước khi Thêm mới.",
                )
                return
        except Exception:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Vui lòng chọn Lịch làm việc trước khi Thêm mới.",
            )
            return

        effective_from = from_q.toString("yyyy-MM-dd")
        effective_to = to_q.toString("yyyy-MM-dd")

        failed_ids: list[int] = []
        last_msg = None
        for emp_id in target_employee_ids:
            ok, msg, _ = self._service.upsert_employee_schedule_assignment_with_range(
                employee_id=int(emp_id),
                schedule_id=int(schedule_id),
                effective_from=str(effective_from),
                effective_to=str(effective_to),
                note=None,
            )
            if not ok:
                failed_ids.append(int(emp_id))
                last_msg = msg

        if failed_ids:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                f"Có {len(failed_ids)} nhân viên không thể lưu lịch trình tạm. {str(last_msg or '')}".strip(),
            )
            # Continue to refresh tables for any successful rows.

        # Refresh global temp table (do not filter to one employee)
        try:
            self.refresh_temp_table(self._get_selected_filters())
        except Exception:
            self.refresh_temp_table()

        # Update default schedule table immediately (no manual Refresh required).
        # 1) If the range covers today, update UI immediately.
        try:
            today = QDate.currentDate()
            if from_q <= today <= to_q:
                if apply_to_checked:
                    # Apply label to all checked rows quickly
                    try:
                        self._view.content.right.apply_schedule_to_checked(
                            schedule_name
                        )
                    except Exception:
                        pass
                else:
                    # Apply label to current selected row
                    table = getattr(self._view.content.right, "table", None)
                    if table is not None:
                        cur_row = int(table.currentRow())
                        if cur_row >= 0:
                            it_sched = table.item(
                                cur_row, self._view.content.right.COL_SCHEDULE
                            )
                            if it_sched is not None:
                                it_sched.setText(str(schedule_name or "").strip())
        except Exception:
            pass

        # 2) Refresh schedule map from DB for affected employees (fallback: whole table)
        try:
            self.refresh_default_schedule_column(target_employee_ids)
        except Exception:
            self.refresh_default_schedule_column()

        # Keep the selected schedule visible
        try:
            self._select_combo_by_data(temp.cbo_schedule, int(schedule_id))
        except Exception:
            pass

        # Optional: keep label updated in UI table (for active range)
        try:
            _ = schedule_name
        except Exception:
            pass

    def on_temp_delete(self) -> None:
        temp = self._view.content.temp

        # Bulk delete if user checked ✅ rows; otherwise delete current selected row.
        checked_ids: list[int] = []
        try:
            checked_ids = temp.get_checked_assignment_ids()
        except Exception:
            checked_ids = []

        if checked_ids:
            affected_emp_ids = self._get_employee_ids_by_temp_assignment_ids(
                checked_ids
            )
            any_failed = False
            for aid in checked_ids:
                ok, _msg, _ = self._service.delete_assignment_by_id(int(aid))
                if not ok:
                    any_failed = True
            if any_failed:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Có dòng không thể xóa. Vui lòng thử lại.",
                )
        else:
            assignment_id = None
            try:
                assignment_id = temp.get_selected_assignment_id()
            except Exception:
                assignment_id = None

            if not assignment_id:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng tick ✅ hoặc chọn dòng trong bảng Lịch trình tạm để Xóa bỏ.",
                )
                return

            affected_emp_ids = self._get_employee_ids_by_temp_assignment_ids(
                [int(assignment_id)]
            )

            ok, msg, _ = self._service.delete_assignment_by_id(int(assignment_id))
            if not ok:
                MessageDialog.info(self._parent_window, "Thông báo", str(msg))
                return

        # Refresh global temp table (do not filter to one employee)
        try:
            self.refresh_temp_table(self._get_selected_filters())
        except Exception:
            self.refresh_temp_table()

        # Refresh default schedule column for impacted employees (or whole table if unknown)
        try:
            if affected_emp_ids:
                self.refresh_default_schedule_column(affected_emp_ids)
            else:
                self.refresh_default_schedule_column()
        except Exception:
            pass

    def refresh_tree(self) -> None:
        try:
            dept_rows = self._service.list_departments_tree_rows()
            title_rows = self._service.list_titles_tree_rows()
            self._view.content.left.set_departments(dept_rows, titles=title_rows)
        except Exception:
            logger.exception("Không thể tải cây phòng ban/chức danh")
            try:
                self._view.content.left.set_departments([], titles=[])
            except Exception:
                pass

    def refresh_schedules(self) -> None:
        try:
            items = self._service.list_schedules()
            self._view.content.right.set_schedules(items)
            try:
                self._view.content.temp.set_schedules(items)
            except Exception:
                pass
        except Exception:
            logger.exception("Không thể tải danh sách lịch làm việc")
            try:
                self._view.content.right.set_schedules([])
                try:
                    self._view.content.temp.set_schedules([])
                except Exception:
                    pass
            except Exception:
                pass

    def on_refresh(self) -> None:
        # Spec: Làm mới phải hiển thị lại đầy đủ nhân viên (không để bảng rỗng).
        self._employees_cache = []
        self._selected_employee = None

        # Reset search inputs
        try:
            self._view.title2.inp_search.setText("")
        except Exception:
            pass
        try:
            self._view.title2.cbo_search_by.setCurrentIndex(0)
        except Exception:
            pass

        # Reset left tree selection (bỏ filter phòng ban/chức danh)
        try:
            self._view.content.left.tree.setCurrentItem(None)
            self._view.content.left.tree.clearSelection()
        except Exception:
            pass

        # Reload global temp table
        self.refresh_temp_table()

        # Reload data sources then refresh the employee table
        self.refresh_tree()
        self.refresh_schedules()
        self.on_search()

    def _get_selected_filters(self) -> dict:
        filters: dict = {
            "search_by": None,
            "search_text": None,
            "department_id": None,
            "title_id": None,
        }

        try:
            filters["search_by"] = self._view.title2.cbo_search_by.currentData()
            filters["search_text"] = self._view.title2.inp_search.text()
        except Exception:
            pass

        # Auto-detect search mode when user chooses "Tự động" (or when missing).
        try:
            sb_raw = str(filters.get("search_by") or "").strip().lower()
            st = str(filters.get("search_text") or "").strip()

            if sb_raw in ("", "auto"):
                if not st:
                    filters["search_by"] = None
                else:
                    # Heuristic:
                    # - If there is whitespace => likely a name
                    # - If contains any non-alnum (except common code separators) => likely a name
                    # - Otherwise => employee_code
                    has_space = any(ch.isspace() for ch in st)
                    if has_space:
                        filters["search_by"] = "employee_name"
                    else:
                        allowed = set("-_./")
                        has_weird = any(
                            (not ch.isalnum()) and (ch not in allowed) for ch in st
                        )
                        filters["search_by"] = (
                            "employee_name" if has_weird else "employee_code"
                        )
        except Exception:
            pass

        # Left tree selection
        try:
            ctx = self._view.content.left.get_selected_node_context() or {}
            if ctx.get("type") == "dept":
                filters["department_id"] = ctx.get("id")
            elif ctx.get("type") == "title":
                filters["title_id"] = ctx.get("id")
                filters["department_id"] = ctx.get("department_id")
        except Exception:
            pass

        return filters

    def on_search(self) -> None:
        # Defer + async: avoid UI freeze when DB or tables are large.
        try:
            QTimer.singleShot(0, self._on_search_async)
        except Exception:
            self._on_search_async()

    def _on_search_async(self) -> None:
        try:
            filters = self._get_selected_filters()
        except Exception:
            filters = {}

        def _fn() -> object:
            def _norm(x) -> str:
                return str(x or "").strip().casefold()

            employees = list(self._service.search_employees(filters) or [])

            emp_ids: list[int] = []
            for x in employees:
                try:
                    if isinstance(x, dict):
                        emp_ids.append(int(x.get("id") or 0))
                    else:
                        emp_ids.append(int(getattr(x, "id", None) or 0))
                except Exception:
                    continue
            emp_ids = [i for i in emp_ids if i > 0]

            schedule_map: dict[int, str] = {}
            try:
                if emp_ids:
                    schedule_map = dict(self._service.get_employee_schedule_name_map(emp_ids) or {})
            except Exception:
                schedule_map = {}

            temp_rows = list(self._service.list_temp_schedule_assignments() or [])
            try:
                search_text = _norm((filters or {}).get("search_text"))
                search_by = _norm((filters or {}).get("search_by"))
            except Exception:
                search_text = ""
                search_by = ""

            if search_text:
                filtered: list[dict] = []
                for r in temp_rows:
                    code = _norm((r or {}).get("employee_code"))
                    name = _norm((r or {}).get("full_name"))
                    if search_by == "employee_code":
                        ok = search_text in code
                    elif search_by == "employee_name":
                        ok = search_text in name
                    else:
                        ok = (search_text in code) or (search_text in name)
                    if ok:
                        filtered.append(r)
                temp_rows = filtered

            return {
                "employees": employees,
                "schedule_map": schedule_map,
                "temp_rows": temp_rows,
            }

        def _ok(payload: object) -> None:
            try:
                data = payload if isinstance(payload, dict) else {}
                employees = list(data.get("employees") or [])
                schedule_map = data.get("schedule_map") or {}
                temp_rows = list(data.get("temp_rows") or [])

                self._employees_cache = employees
                self._view.title2.set_total(len(employees))

                try:
                    self._view.content.right.set_employees_chunked(
                        employees,
                        schedule_by_employee_id=schedule_map,
                    )
                except Exception:
                    self._view.content.right.set_employees(employees)
                    try:
                        self._view.content.right.apply_schedule_name_map(schedule_map)
                    except Exception:
                        pass

                try:
                    self._view.content.temp.set_rows_chunked(temp_rows)
                except Exception:
                    self._view.content.temp.set_rows(temp_rows)
            except Exception:
                logger.exception("Không thể tìm nhân viên")
                try:
                    self._view.title2.set_total(0)
                    self._view.content.right.clear_employees()
                except Exception:
                    pass

        def _err(_msg: str) -> None:
            logger.exception("Không thể tìm nhân viên")
            try:
                self._employees_cache = []
                self._view.title2.set_total(0)
                self._view.content.right.clear_employees()
            except Exception:
                pass
            try:
                self._view.content.temp.clear_rows()
            except Exception:
                pass

        self._search_runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def on_apply(self) -> None:
        try:
            cbo = self._view.content.right.cbo_schedule
            schedule_name = str(cbo.currentText() or "").strip()
            schedule_id = cbo.currentData()

            # Index 0 is placeholder: must choose an action/schedule
            try:
                if int(cbo.currentIndex()) == 0:
                    MessageDialog.info(
                        self._parent_window,
                        "Thông báo",
                        "Vui lòng chọn Lịch làm việc trước khi Áp dụng.",
                    )
                    return
            except Exception:
                pass

            checked_ids = self._view.content.right.get_checked_employee_ids()
            if not checked_ids:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng chọn nhân viên trước khi Áp dụng.",
                )
                return

            # Option "Chưa sắp xếp ca" (data=0): clear assignments
            try:
                if int(schedule_id or 0) == 0:
                    for emp_id in checked_ids:
                        try:
                            self._service.delete_employee_schedule(int(emp_id))
                        except Exception:
                            pass
                    self._view.content.right.apply_schedule_to_checked("")
                    self._view.title2.set_total(
                        self._view.content.right.table.rowCount()
                    )
                    return
            except Exception:
                pass

            # Persist to DB (effective from today) then reflect in UI.
            try:
                processed = self._service.apply_schedule_to_employees(
                    employee_ids=[int(x) for x in checked_ids],
                    schedule_id=int(schedule_id),
                )
                if int(processed or 0) <= 0:
                    MessageDialog.info(
                        self._parent_window,
                        "Thông báo",
                        "Không thể cập nhật Lịch làm việc vào DB. Vui lòng kiểm tra cấu hình DB và thử lại.",
                    )
                    return
            except Exception:
                logger.exception("Không thể cập nhật lịch làm việc vào DB")
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Không thể cập nhật Lịch làm việc vào DB. Vui lòng kiểm tra cấu hình DB và thử lại.",
                )
                return

            applied = self._view.content.right.apply_schedule_to_checked(schedule_name)
            self._view.title2.set_total(self._view.content.right.table.rowCount())
            if applied <= 0:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Không có nhân viên nào được áp dụng.",
                )
        except Exception:
            logger.exception("Không thể áp dụng lịch làm việc")

    def on_delete(self) -> None:
        try:
            checked_ids = self._view.content.right.get_checked_employee_ids()
            if not checked_ids:
                MessageDialog.info(
                    self._parent_window,
                    "Thông báo",
                    "Vui lòng chọn nhân viên trước khi Xóa lịch NV.",
                )
                return

            # Best-effort delete in DB; UI schedule column will be cleared.
            for emp_id in checked_ids:
                try:
                    self._service.delete_employee_schedule(int(emp_id))
                except Exception:
                    pass

            # Clear schedule column for checked rows
            self._view.content.right.apply_schedule_to_checked("")
        except Exception:
            logger.exception("Không thể xóa lịch NV")
