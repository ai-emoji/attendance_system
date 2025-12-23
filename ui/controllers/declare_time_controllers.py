"""ui.controllers.declare_time_controllers

Controller cho màn "Khai báo giờ Vào/Ra":
- Load danh sách cấu hình vào bảng (MainContent2)
- Làm mới (reload + clear form + clear selection)
- Lưu (thêm mới nếu chưa chọn; cập nhật nếu đang chọn)
- Xóa (xóa theo dòng đang chọn)

Không dùng QMessageBox; dùng MessageDialog.
"""

from __future__ import annotations

import logging

from services.declare_time_services import DeclareTimeService
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class DeclareTimeController:
    def __init__(
        self,
        parent_window,
        title_bar2,
        content1,
        content2,
        service: DeclareTimeService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content1 = content1
        self._content2 = content2
        self._service = service or DeclareTimeService()

        self._selected_id: int | None = None

    def bind(self) -> None:
        self._title_bar2.refresh_clicked.connect(self.on_refresh)
        self._title_bar2.save_clicked.connect(self.on_save)
        self._title_bar2.delete_clicked.connect(self.on_delete)

        self._content2.table.itemSelectionChanged.connect(self._on_table_selection)

        self.refresh()

    def refresh(self) -> None:
        try:
            models = self._service.list_items()

            def _sort_label(st: str | None) -> str:
                if st == "auto":
                    return "Sắp xếp giờ Vào/Ra theo tự động"
                if st == "device":
                    return "Theo giờ Vào/Ra trên máy chấm công"
                if st == "first_last":
                    return (
                        "Giờ vào là Giờ đầu tiên và giờ Ra là Giờ cuối cùng trong ngày"
                    )

                # Backward-compat (dữ liệu cũ)
                if st in ("in", "out"):
                    return "Theo giờ Vào/Ra trên máy chấm công"
                return "Chưa chọn"

            rows = [
                (m.id, m.code, m.description, _sort_label(m.sort_type)) for m in models
            ]
            self._content2.set_rows(rows)
            self._title_bar2.set_total(len(rows))

            if not rows:
                self._selected_id = None
                self._content2.clear_selection()
                self._content1.clear_form()
        except Exception:
            logger.exception("Không thể tải danh sách Khai báo giờ Vào/Ra")
            self._content2.set_rows([])
            self._title_bar2.set_total(0)

    def on_refresh(self) -> None:
        self._selected_id = None
        self._content2.clear_selection()
        self._content1.clear_form()
        self.refresh()

    def _on_table_selection(self) -> None:
        sel_id = self._content2.get_selected_id()
        if not sel_id:
            self._selected_id = None
            self._content1.clear_form()
            return

        self._selected_id = int(sel_id)

        try:
            m = self._service.get_item(int(sel_id))
            if m is None:
                return
            self._content1.set_form(
                {
                    "code": m.code,
                    "description": m.description,
                    "sort_type": m.sort_type,
                    "min_between_in_out": m.min_between_in_out,
                    "max_between_in_out": m.max_between_in_out,
                    "gap_between_pairs": m.gap_between_pairs,
                    "cycle_days": m.cycle_days,
                    "days_in_month": m.days_in_month,
                    "cycle_end_time": m.cycle_end_time,
                    "remove_prev_night": m.remove_prev_night,
                    "calc_from": m.calc_from,
                    "calc_to": m.calc_to,
                }
            )
        except Exception:
            logger.exception("Không thể load chi tiết cấu hình giờ Vào/Ra")

    def on_save(self) -> None:
        form = self._content1.get_form_data()

        if self._selected_id is None:
            ok, msg, new_id = self._service.create_item(form)
            if ok:
                self.refresh()
                if new_id is not None:
                    self._selected_id = int(new_id)
                    self._content2.select_by_id(int(new_id))
            else:
                MessageDialog.info(self._parent_window, "Thông báo", msg)
            return

        current_id = self._selected_id
        ok, msg = self._service.update_item(int(current_id), form)
        if ok:
            self.refresh()
            # refresh() may clear selection and reset _selected_id via selectionChanged
            if current_id is not None:
                self._selected_id = int(current_id)
                self._content2.select_by_id(int(current_id))
        else:
            MessageDialog.info(self._parent_window, "Thông báo", msg)

    def on_delete(self) -> None:
        sel_id = self._content2.get_selected_id()
        if not sel_id:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Xóa.",
            )
            return

        # Lấy code/desc để confirm
        code = ""
        desc = ""
        try:
            row = self._content2.table.currentRow()
            it_code = self._content2.table.item(row, 1)
            it_desc = self._content2.table.item(row, 2)
            code = str(it_code.text() if it_code else "")
            desc = str(it_desc.text() if it_desc else "")
        except Exception:
            pass

        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa: {code} - {desc}?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_item(int(sel_id))
        if ok:
            self.on_refresh()
        else:
            MessageDialog.info(self._parent_window, "Không thể xóa", msg)
