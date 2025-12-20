"""ui.controllers.department_controllers

Controller cho màn "Khai báo Phòng ban".

Trách nhiệm:
- Load dữ liệu vào cây
- Xử lý Thêm/Sửa/Xóa
- Không dùng QMessageBox; dùng MessageDialog (trong title_dialog.py)
"""

from __future__ import annotations

import logging

from services.department_services import DepartmentService
from ui.dialog.department_dialog import DepartmentDialog
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class DepartmentController:
    def __init__(
        self,
        parent_window,
        title_bar2,
        content,
        service: DepartmentService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or DepartmentService()

        self._id_to_parent: dict[int, int | None] = {}
        self._id_to_name: dict[int, str] = {}
        self._id_to_note: dict[int, str] = {}

    def bind(self) -> None:
        self._title_bar2.add_clicked.connect(self.on_add)
        self._title_bar2.edit_clicked.connect(self.on_edit)
        self._title_bar2.delete_clicked.connect(self.on_delete)
        self.refresh()

    def refresh(self) -> None:
        try:
            models = self._service.list_departments()
            self._id_to_parent = {m.id: m.parent_id for m in models}
            self._id_to_name = {m.id: m.department_name for m in models}
            self._id_to_note = {m.id: m.department_note for m in models}

            self._models_cache = models

            rows = [
                (m.id, m.parent_id, m.department_name, m.department_note)
                for m in models
            ]
            self._content.set_departments(rows)
            self._title_bar2.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách phòng ban")
            self._content.set_departments([])
            self._title_bar2.set_total(0)

    def _build_parent_options(self) -> list[tuple[int, int | None, str]]:
        models = getattr(self, "_models_cache", None) or []
        return [(m.id, m.parent_id, m.department_name) for m in models]

    def _collect_descendants(self, root_id: int) -> set[int]:
        children_map: dict[int, list[int]] = {}
        for child_id, parent_id in self._id_to_parent.items():
            if parent_id is None:
                continue
            children_map.setdefault(int(parent_id), []).append(int(child_id))

        result: set[int] = set()
        stack = [int(root_id)]
        while stack:
            current = stack.pop()
            for child in children_map.get(current, []):
                if child not in result:
                    result.add(child)
                    stack.append(child)
        return result

    def _get_selected(self) -> tuple[int, str] | None:
        return self._content.get_selected_department()

    def on_add(self) -> None:
        selected = self._get_selected()
        default_parent_id = selected[0] if selected else None

        dialog = DepartmentDialog(
            mode="add",
            parent_options=self._build_parent_options(),
            selected_parent_id=default_parent_id,
            exclude_parent_ids=set(),
            parent=self._parent_window,
        )

        def _save() -> None:
            parent_id = dialog.get_parent_id()
            ok, msg, _new_id = self._service.create_department(
                dialog.get_department_name(),
                parent_id,
                "",  # ghi chú không còn ở UI
            )
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == DepartmentDialog.Accepted:
            self.refresh()

    def on_edit(self) -> None:
        selected = self._get_selected()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong cây trước khi Sửa đổi.",
            )
            return

        dept_id, _ = selected
        current_parent_id = self._id_to_parent.get(dept_id)

        exclude_ids = {int(dept_id)}
        exclude_ids |= self._collect_descendants(int(dept_id))

        dialog = DepartmentDialog(
            mode="edit",
            parent_options=self._build_parent_options(),
            selected_parent_id=current_parent_id,
            exclude_parent_ids=exclude_ids,
            department_name=self._id_to_name.get(dept_id, ""),
            parent=self._parent_window,
        )

        def _save() -> None:
            parent_id = dialog.get_parent_id()
            # Preserve note hiện có vì UI không còn chỉnh note
            current_note = self._id_to_note.get(dept_id, "")
            ok, msg = self._service.update_department(
                dept_id,
                dialog.get_department_name(),
                parent_id,
                current_note,
            )
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == DepartmentDialog.Accepted:
            self.refresh()

    def on_delete(self) -> None:
        selected = self._get_selected()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong cây trước khi Xóa.",
            )
            return

        dept_id, name = selected

        # Không cho phép xóa phòng ban cha nếu có phòng ban con
        has_children = any(
            parent_id == dept_id for parent_id in self._id_to_parent.values()
        )
        if has_children:
            MessageDialog.info(
                self._parent_window,
                "Không thể xóa",
                "Không cho phép xóa phòng ban cha khi đang có phòng ban con.",
            )
            return

        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa phòng ban: {name}?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_department(dept_id)
        if ok:
            self.refresh()
        else:
            MessageDialog.info(
                self._parent_window,
                "Không thể xóa",
                msg or "Xóa thất bại.",
            )
