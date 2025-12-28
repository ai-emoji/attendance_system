"""ui.controllers.arrange_schedule_controllers

Controller cho màn "Sắp xếp ca theo lịch trình".

Trách nhiệm:
- Load danh sách lịch trình (bên trái)
- Lưu lịch trình vào DB
- Chọn lịch trình -> hiển thị thông tin bên phải
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt

from services.arrange_schedule_services import ArrangeScheduleService
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class ArrangeScheduleController:
    def __init__(
        self,
        parent_window,
        left=None,
        right=None,
        service: ArrangeScheduleService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._left = left
        self._right = right
        self._service = service or ArrangeScheduleService()
        self._current_schedule_id: int | None = None

    def bind(self) -> None:
        # Restore cached UI state (if any) BEFORE wiring signals to avoid
        # triggering selection-change loads.
        restored = False
        try:
            if self._left is not None and hasattr(
                self._left, "restore_cached_state_if_any"
            ):
                info = self._left.restore_cached_state_if_any()
                if isinstance(info, dict) and bool(info.get("restored")):
                    restored = True
                    sel = info.get("selected_id")
                    try:
                        self._current_schedule_id = (
                            int(sel) if sel and int(sel) > 0 else None
                        )
                    except Exception:
                        self._current_schedule_id = None
        except Exception:
            pass

        try:
            if self._right is not None and hasattr(
                self._right, "restore_cached_state_if_any"
            ):
                if bool(self._right.restore_cached_state_if_any()):
                    restored = True
        except Exception:
            pass

        # Fallback: if left selection wasn't restored, try restoring the current
        # schedule id from the right pane cache (prevents accidental create-new).
        try:
            if self._current_schedule_id is None and self._right is not None:
                sid = getattr(self._right, "current_schedule_id", None)
                if sid is not None and int(sid) > 0:
                    self._current_schedule_id = int(sid)
        except Exception:
            pass

        if self._right is not None:
            self._right.refresh_clicked.connect(self.on_refresh)
            self._right.save_clicked.connect(self.on_save)
            self._right.delete_clicked.connect(self.on_delete)

        if self._left is not None:
            self._left.schedule_selected.connect(self.on_selected)

        # If there was cached state, do not refresh (avoid losing the view state).
        if not restored:
            self.refresh()

    def on_refresh(self) -> None:
        """Reset các trường bên phải và bỏ chọn danh sách."""
        self._current_schedule_id = None
        if self._right is not None:
            try:
                if hasattr(self._right, "set_current_schedule_id"):
                    self._right.set_current_schedule_id(None)
                else:
                    setattr(self._right, "current_schedule_id", None)
            except Exception:
                pass
            self._clear_form()
        if self._left is not None:
            self._left.clear_selection()
        self.refresh()

    def refresh(self) -> None:
        """Reload danh sách lịch trình bên trái."""
        try:
            items = self._service.list_schedules()
            if self._left is not None:
                self._left.set_schedules(items)
            if self._right is not None:
                self._right.set_total(len(items))
        except Exception:
            logger.exception("Không thể tải danh sách lịch trình")
            if self._left is not None:
                self._left.set_schedules([])
            if self._right is not None:
                self._right.set_total(0)

    def on_selected(self) -> None:
        schedule_id = None
        if self._left is not None:
            schedule_id = self._left.get_selected_schedule_id()
        if schedule_id is None:
            return

        # Option "Chưa sắp xếp" (id=0): clear form and do not load any schedule
        try:
            if int(schedule_id) == 0:
                self._current_schedule_id = None
                if self._right is not None:
                    self._clear_form()
                return
        except Exception:
            pass

        if not schedule_id:
            return

        try:
            header, details = self._service.get_schedule(int(schedule_id))
            if header is None:
                return
            self._current_schedule_id = int(header.id)

            try:
                if hasattr(self._right, "set_current_schedule_id"):
                    self._right.set_current_schedule_id(int(header.id))
                else:
                    setattr(self._right, "current_schedule_id", int(header.id))
            except Exception:
                pass

            if self._right is None:
                return

            self._right.inp_schedule_name.setText(header.schedule_name)
            self._set_in_out_mode(header.in_out_mode)

            self._right.chk_ignore_sat.setChecked(bool(header.ignore_absent_sat))
            self._right.chk_ignore_sun.setChecked(bool(header.ignore_absent_sun))
            self._right.chk_ignore_holiday.setChecked(
                bool(header.ignore_absent_holiday)
            )
            self._right.chk_holiday_as_work.setChecked(
                bool(header.holiday_count_as_work)
            )
            self._right.chk_day_is_out.setChecked(bool(header.day_is_out_time))

            def _norm_day(s: str) -> str:
                return str(s or "").strip().casefold()

            # Build id->shift_code map for display
            all_shift_ids: list[int] = []
            for d in details:
                for v in (
                    d.shift1_id,
                    d.shift2_id,
                    d.shift3_id,
                    getattr(d, "shift4_id", None),
                    getattr(d, "shift5_id", None),
                ):
                    if v is not None:
                        try:
                            all_shift_ids.append(int(v))
                        except Exception:
                            pass
            id_to_code = self._service.get_work_shift_codes_by_ids(all_shift_ids)

            # Determine how many "Tên ca" columns needed (unlimited)
            max_cols = 0
            for d in details:
                try:
                    max_cols = max(
                        max_cols, len(list(getattr(d, "shift_ids", []) or []))
                    )
                except Exception:
                    pass

            # (Re)build table only when needed
            if hasattr(self._right, "build_table"):
                try:
                    self._right.build_table(max_cols)
                except Exception:
                    pass

            # Fill shifts into table by day_name
            day_name_to_detail = {_norm_day(d.day_name): d for d in details}
            table = self._right.table

            # Clear previous values
            for r in range(table.rowCount()):
                for c in (2, 3, 4, 5, 6):
                    it = table.item(r, c)
                    if it is not None:
                        it.setText("")
                        it.setData(Qt.ItemDataRole.UserRole, None)

            for r in range(table.rowCount()):
                day_item = table.item(r, 1)
                day_name = str(day_item.text() if day_item else "")
                d = day_name_to_detail.get(_norm_day(day_name))
                if not d:
                    continue

                shift_cols = list(range(2, table.columnCount()))
                items = [table.item(r, c) for c in shift_cols]

                def _set_shift_cell(it, shift_id: int | None) -> None:
                    if it is None:
                        return
                    if shift_id is None:
                        it.setText("")
                        it.setData(Qt.ItemDataRole.UserRole, None)
                        return
                    it.setData(Qt.ItemDataRole.UserRole, int(shift_id))
                    it.setText(str(id_to_code.get(int(shift_id), "")))

                values = [
                    *list(getattr(d, "shift_ids", []) or []),
                ]

                for idx, it in enumerate(items):
                    if idx >= len(values):
                        break
                    _set_shift_cell(it, values[idx])
        except Exception:
            logger.exception("Không thể load lịch trình")

    def on_save(self) -> None:
        if self._right is None:
            return

        # If left selection is missing (or UI restored from cache), fall back to
        # the right-pane cached schedule id to perform an update instead of creating
        # a duplicate schedule.
        try:
            if self._current_schedule_id is None:
                sid = getattr(self._right, "current_schedule_id", None)
                if sid is not None and int(sid) > 0:
                    self._current_schedule_id = int(sid)
        except Exception:
            pass

        schedule_name = self._right.inp_schedule_name.text()
        in_out_mode = self._right.cbo_in_out_mode.currentData()

        details_by_day_name: dict[str, list[int | None]] = {}
        table = self._right.table
        for r in range(table.rowCount()):
            day_item = table.item(r, 1)
            day_name = str(day_item.text() if day_item else "").strip()
            if not day_name:
                continue

            def _parse_int(cell_col: int) -> int | None:
                it = table.item(r, cell_col)
                if it is None:
                    return None
                # Prefer id stored in UserRole
                v = it.data(Qt.ItemDataRole.UserRole)
                if v is not None and str(v).strip() != "":
                    try:
                        return int(v)
                    except Exception:
                        pass
                raw = str(it.text() if it else "").strip()
                if not raw:
                    return None
                try:
                    return int(raw)
                except Exception:
                    return None

            shift_cols = list(range(2, table.columnCount()))
            slots: list[int | None] = []
            for col in shift_cols:
                slots.append(_parse_int(col))
            # Trim trailing None
            while slots and slots[-1] is None:
                slots.pop()
            details_by_day_name[day_name] = slots

        ok, msg, new_id = self._service.save_schedule(
            schedule_id=self._current_schedule_id,
            schedule_name=schedule_name,
            in_out_mode=str(in_out_mode) if in_out_mode is not None else None,
            ignore_absent_sat=self._right.chk_ignore_sat.isChecked(),
            ignore_absent_sun=self._right.chk_ignore_sun.isChecked(),
            ignore_absent_holiday=self._right.chk_ignore_holiday.isChecked(),
            holiday_count_as_work=self._right.chk_holiday_as_work.isChecked(),
            day_is_out_time=self._right.chk_day_is_out.isChecked(),
            details_by_day_name=details_by_day_name,
        )

        if not ok:
            MessageDialog.info(self._parent_window, "Không thể lưu", msg)
            return

        # Keep current id stable; for updates new_id should equal current id.
        self._current_schedule_id = int(new_id) if new_id else self._current_schedule_id
        try:
            if hasattr(self._right, "set_current_schedule_id"):
                self._right.set_current_schedule_id(self._current_schedule_id)
            else:
                setattr(self._right, "current_schedule_id", self._current_schedule_id)
        except Exception:
            pass
        self.refresh()
        if self._left is not None and new_id:
            self._left.select_schedule_id(int(new_id))
            self.on_selected()

    def on_delete(self) -> None:
        if self._left is None:
            return
        schedule_id = self._left.get_selected_schedule_id()
        if not schedule_id:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 lịch trình trong danh sách trước khi Xóa.",
            )
            return

        name = self._left.get_selected_schedule_name() or ""
        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa lịch trình: {name}?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_schedule(int(schedule_id))
        if not ok:
            MessageDialog.info(self._parent_window, "Không thể xóa", msg)
            return

        self._current_schedule_id = None
        self.refresh()
        if self._right is not None:
            self._clear_form()

    def _set_in_out_mode(self, mode: str | None) -> None:
        if self._right is None:
            return
        # New synced values: auto/device/first_last
        # Backward-compat: old values (in/out) map to device.
        if mode in ("in", "out"):
            target = "device"
        else:
            target = mode if mode in ("auto", "device", "first_last") else None
        cb = self._right.cbo_in_out_mode
        for i in range(cb.count()):
            if cb.itemData(i) == target:
                cb.setCurrentIndex(i)
                return
        cb.setCurrentIndex(0)

    def _clear_form(self) -> None:
        if self._right is None:
            return
        self._right.inp_schedule_name.clear()
        self._right.cbo_in_out_mode.setCurrentIndex(0)
        self._right.chk_ignore_sat.setChecked(False)
        self._right.chk_ignore_sun.setChecked(False)
        self._right.chk_ignore_holiday.setChecked(False)
        self._right.chk_holiday_as_work.setChecked(False)
        self._right.chk_day_is_out.setChecked(False)

        table = self._right.table
        for r in range(table.rowCount()):
            for c in range(2, table.columnCount()):
                it = table.item(r, c)
                if it is not None:
                    it.setText("")
                    it.setData(Qt.ItemDataRole.UserRole, None)
