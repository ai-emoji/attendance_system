"""ui.controllers.declare_work_shift_controllers

Controller cho màn "Khai báo Ca làm việc".

Trách nhiệm:
- Load danh sách ca vào bảng
- Làm mới (reload + clear form)
- Lưu (thêm mới nếu chưa chọn dòng; cập nhật nếu đang chọn)
- Xóa (xóa theo dòng đang chọn)

Không dùng QMessageBox; dùng MessageDialog.
"""

from __future__ import annotations

import logging

from core.threads import BackgroundTaskRunner

from services.declare_work_shift_services import DeclareWorkShiftService
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class DeclareWorkShiftController:
    def __init__(
        self,
        parent_window,
        title_bar2,
        content,
        service: DeclareWorkShiftService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or DeclareWorkShiftService()

        self._selected_shift_id: int | None = None
        self._runner = BackgroundTaskRunner(
            self._parent_window, name="work_shift_refresh"
        )

    def bind(self) -> None:
        # Restore cached state BEFORE wiring signals to avoid triggering handlers.
        restored = False
        try:
            if hasattr(self._title_bar2, "restore_cached_state_if_any"):
                restored = (
                    bool(self._title_bar2.restore_cached_state_if_any()) or restored
                )
        except Exception:
            pass

        try:
            if hasattr(self._content, "restore_cached_state_if_any"):
                info = self._content.restore_cached_state_if_any()
                if isinstance(info, dict) and bool(info.get("restored")):
                    restored = True
                    sel_id = info.get("selected_id")
                    if sel_id is not None:
                        try:
                            self._selected_shift_id = int(sel_id)
                        except Exception:
                            self._selected_shift_id = None
        except Exception:
            pass

        self._title_bar2.refresh_clicked.connect(self.on_refresh)
        self._title_bar2.save_clicked.connect(self.on_save)
        self._title_bar2.delete_clicked.connect(self.on_delete)

        # Toggle định dạng giờ HH:MM / HH:MM:SS
        if hasattr(self._title_bar2, "time_format_changed") and hasattr(
            self._content, "set_show_seconds"
        ):
            self._title_bar2.time_format_changed.connect(self._content.set_show_seconds)

        self._content.table.itemSelectionChanged.connect(self._on_table_selection)

        if not restored:
            self.refresh()

    def refresh(self) -> None:
        def _fn() -> object:
            models = self._service.list_work_shifts()
            return [(m.id, m.shift_code, m.time_in, m.time_out) for m in models]

        def _ok(result: object) -> None:
            rows = list(result or []) if isinstance(result, list) else []
            self._content.set_work_shifts(rows)
            self._title_bar2.set_total(len(rows))

        def _err(_msg: str) -> None:
            logger.exception("Không thể tải danh sách ca làm việc")
            try:
                self._content.set_work_shifts([])
            except Exception:
                pass
            try:
                self._title_bar2.set_total(0)
            except Exception:
                pass

        self._runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def on_refresh(self) -> None:
        self._selected_shift_id = None
        # Reset UI immediately: clear table data and selection before async reload.
        try:
            if hasattr(self._content, "reset_table"):
                self._content.reset_table()
            else:
                self._content.set_work_shifts([])
                self._content.table.clearSelection()
                try:
                    sm = self._content.table.selectionModel()
                    if sm is not None:
                        from PySide6.QtCore import QItemSelectionModel, QModelIndex

                        sm.setCurrentIndex(QModelIndex(), QItemSelectionModel.NoUpdate)
                except Exception:
                    pass
        except Exception:
            try:
                self._content.table.clearSelection()
            except Exception:
                pass
        self._content.clear_form()
        try:
            self._title_bar2.set_total(0)
        except Exception:
            pass
        self.refresh()

    def _on_table_selection(self) -> None:
        selected = self._content.get_selected_work_shift()
        if not selected:
            self._selected_shift_id = None
            return

        shift_id, _code = selected
        self._selected_shift_id = int(shift_id)

        model = self._service.get_work_shift(self._selected_shift_id)
        if model is None:
            return

        self._content.set_form(
            shift_code=model.shift_code,
            time_in=str(model.time_in or ""),
            time_out=str(model.time_out or ""),
            lunch_start=str(model.lunch_start or ""),
            lunch_end=str(model.lunch_end or ""),
            total_minutes=model.total_minutes,
            work_count=model.work_count,
            in_window_start=str(model.in_window_start or ""),
            in_window_end=str(model.in_window_end or ""),
            out_window_start=str(model.out_window_start or ""),
            out_window_end=str(model.out_window_end or ""),
            overtime_round_minutes=getattr(model, "overtime_round_minutes", None),
        )

    def on_save(self) -> None:
        data = self._content.get_form_data()

        if self._selected_shift_id is None:
            ok, msg, new_id = self._service.create_work_shift(**data)
            if ok:
                self.refresh()
                if new_id is not None:
                    self._selected_shift_id = int(new_id)
                    self._content.select_work_shift_by_id(int(new_id))
            else:
                MessageDialog.info(self._parent_window, "Thông báo", msg)
            return

        ok, msg = self._service.update_work_shift(int(self._selected_shift_id), **data)
        if ok:
            self.refresh()
            self._content.select_work_shift_by_id(int(self._selected_shift_id))
        else:
            MessageDialog.info(self._parent_window, "Thông báo", msg)

    def on_delete(self) -> None:
        selected = self._content.get_selected_work_shift()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Xóa.",
            )
            return

        shift_id, code = selected

        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa ca: {code}?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_work_shift(int(shift_id))
        if ok:
            self.on_refresh()
        else:
            MessageDialog.info(self._parent_window, "Không thể xóa", msg)
