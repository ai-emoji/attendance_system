"""ui.controllers.title_controllers

Controller cho màn "Khai báo Chức danh".

Trách nhiệm:
- Load dữ liệu vào bảng
- Xử lý Thêm/Sửa/Xóa
- Cập nhật label Tổng

Không dùng QMessageBox; lỗi hiển thị trong dialog.
"""

from __future__ import annotations

import logging

from services.title_services import TitleService
from ui.dialog.title_dialog import TitleDialog


logger = logging.getLogger(__name__)


class TitleController:
    def __init__(
        self, parent_window, title_bar2, content, service: TitleService | None = None
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or TitleService()

    def bind(self) -> None:
        self._title_bar2.add_clicked.connect(self.on_add)
        self._title_bar2.edit_clicked.connect(self.on_edit)
        self._title_bar2.delete_clicked.connect(self.on_delete)

        self.refresh()

    def refresh(self) -> None:
        try:
            models = self._service.list_titles()
            rows = [(m.id, m.title_name) for m in models]
            self._content.set_titles(rows)
            self._title_bar2.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách chức danh")
            self._content.set_titles([])
            self._title_bar2.set_total(0)

    def on_add(self) -> None:
        dialog = TitleDialog(mode="add", parent=self._parent_window)

        def _save() -> None:
            ok, msg, _new_id = self._service.create_title(dialog.get_title_name())
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == TitleDialog.Accepted:
            self.refresh()

    def on_edit(self) -> None:
        selected = self._content.get_selected_title()
        if not selected:
            return

        title_id, current_name = selected
        dialog = TitleDialog(
            mode="edit", title_name=current_name, parent=self._parent_window
        )

        def _save() -> None:
            ok, msg = self._service.update_title(title_id, dialog.get_title_name())
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == TitleDialog.Accepted:
            self.refresh()

    def on_delete(self) -> None:
        selected = self._content.get_selected_title()
        if not selected:
            return

        title_id, _name = selected
        ok, _msg = self._service.delete_title(title_id)
        if ok:
            self.refresh()
        else:
            # Không có vùng status ở view -> chỉ log
            logger.warning("Xóa thất bại cho id=%s", title_id)
