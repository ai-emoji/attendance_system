"""ui.controllers.department_controllers

Controller cho màn "Khai báo Phòng ban".

Trách nhiệm:
- Load dữ liệu vào cây
- Xử lý Thêm/Sửa/Xóa
- Không dùng QMessageBox; dùng MessageDialog (trong title_dialog.py)
"""

from __future__ import annotations

import logging

from core.threads import BackgroundTaskRunner

from services.department_services import DepartmentService
from services.title_services import TitleService
from repository.employee_repository import EmployeeRepository
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

        self._runner = BackgroundTaskRunner(
            self._parent_window, name="department_refresh"
        )

    def bind(self) -> None:
        self._title_bar2.add_clicked.connect(self.on_add)
        self._title_bar2.edit_clicked.connect(self.on_edit)
        self._title_bar2.delete_clicked.connect(self.on_delete)
        self.refresh()

    def refresh(self) -> None:
        def _fn() -> object:
            models = self._service.list_departments()
            dept_rows = [
                (m.id, m.parent_id, m.department_name, m.department_note)
                for m in models
            ]

            try:
                title_models = TitleService().list_titles()
                title_rows = [
                    (t.id, t.department_id, t.title_name) for t in title_models
                ]
            except Exception:
                title_rows = []

            # Return both for UI thread application.
            return (models, dept_rows, title_rows)

        def _ok(result: object) -> None:
            try:
                models, dept_rows, title_rows = (
                    result
                    if isinstance(result, tuple) and len(result) == 3
                    else ([], [], [])
                )
            except Exception:
                models, dept_rows, title_rows = ([], [], [])

            models = list(models or [])
            dept_rows = list(dept_rows or [])
            title_rows = list(title_rows or [])

            try:
                self._id_to_parent = {m.id: m.parent_id for m in models}
                self._id_to_name = {m.id: m.department_name for m in models}
                self._id_to_note = {m.id: m.department_note for m in models}
            except Exception:
                self._id_to_parent = {}
                self._id_to_name = {}
                self._id_to_note = {}

            self._models_cache = models
            self._title_rows_cache = list(title_rows)

            self._titles_by_department = {}
            for tid, did, _tname in title_rows:
                if did is None:
                    continue
                self._titles_by_department.setdefault(int(did), []).append(int(tid))

            self._content.set_departments(dept_rows, titles=title_rows)
            self._title_bar2.set_total(len(dept_rows) + len(title_rows))

        def _err(_msg: str) -> None:
            logger.exception("Không thể tải danh sách phòng ban")
            try:
                self._content.set_departments([])
            except Exception:
                pass
            try:
                self._title_bar2.set_total(0)
            except Exception:
                pass

        self._runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def _build_parent_options(self) -> list[tuple[int, int | None, str]]:
        models = getattr(self, "_models_cache", None) or []
        items = [(m.id, m.parent_id, m.department_name) for m in models]
        # Keep dropdown order stable: oldest -> newest (by id)
        try:
            items.sort(key=lambda x: int(x[0]))
        except Exception:
            pass
        return items

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
        # Backward compatible for callers that still expect departments only.
        return self._content.get_selected_department()

    def _get_selected_node(self) -> dict | None:
        try:
            return self._content.get_selected_node_context()
        except Exception:
            return None

    def on_add(self) -> None:
        selected_node = self._get_selected_node() or {}
        if selected_node.get("type") == "title":
            default_parent_id = selected_node.get("department_id")
        else:
            default_parent_id = selected_node.get("id")

        dialog = DepartmentDialog(
            mode="add",
            parent_options=self._build_parent_options(),
            selected_parent_id=default_parent_id,
            exclude_parent_ids=set(),
            parent=self._parent_window,
        )

        def _save() -> None:
            parent_id = dialog.get_parent_id()
            if dialog.get_scope() == "title":
                ok, msg, _new_id = TitleService().create_title(
                    dialog.get_department_name(),
                    department_id=parent_id,
                )
                dialog.set_status(msg, ok=ok)
                if ok:
                    dialog.accept()
                return

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
        selected_node = self._get_selected_node()
        if not selected_node:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong cây trước khi Sửa đổi.",
            )
            return

        node_type = str(selected_node.get("type") or "dept")
        node_id = int(selected_node.get("id") or 0)

        if node_type == "title":
            title_id = node_id
            dialog = DepartmentDialog(
                mode="edit",
                parent_options=self._build_parent_options(),
                selected_parent_id=selected_node.get("department_id"),
                exclude_parent_ids=set(),
                department_name=str(selected_node.get("name") or ""),
                scope="title",
                parent=self._parent_window,
            )

            def _save() -> None:
                new_scope = dialog.get_scope()
                parent_id = dialog.get_parent_id()
                name = dialog.get_department_name()

                # title -> department conversion
                if new_scope == "department":
                    try:
                        used = EmployeeRepository().count_employees_by_title(title_id)
                    except Exception:
                        used = 0
                    if used > 0:
                        dialog.set_status(
                            "Không thể chuyển đổi vì đang có nhân viên thuộc Chức danh này.",
                            ok=False,
                        )
                        return

                    ok, msg, _new_id = self._service.create_department(
                        name,
                        parent_id,
                        "",
                    )
                    if not ok:
                        dialog.set_status(msg, ok=False)
                        return

                    ok2, msg2 = TitleService().delete_title(title_id)
                    if not ok2:
                        dialog.set_status(msg2, ok=False)
                        return

                    dialog.set_status("Chuyển đổi thành công.", ok=True)
                    dialog.accept()
                    return

                # Normal title edit
                ok, msg = TitleService().update_title(
                    title_id,
                    name,
                    department_id=parent_id,
                )
                dialog.set_status(msg, ok=ok)
                if ok:
                    dialog.accept()

            dialog.btn_save.clicked.connect(_save)
            if dialog.exec() == DepartmentDialog.Accepted:
                self.refresh()
            return

        # dept node
        dept_id = node_id
        current_parent_id = self._id_to_parent.get(dept_id)

        exclude_ids = {int(dept_id)}
        exclude_ids |= self._collect_descendants(int(dept_id))

        dialog = DepartmentDialog(
            mode="edit",
            parent_options=self._build_parent_options(),
            selected_parent_id=current_parent_id,
            exclude_parent_ids=exclude_ids,
            department_name=self._id_to_name.get(dept_id, ""),
            scope="department",
            parent=self._parent_window,
        )

        def _save() -> None:
            new_scope = dialog.get_scope()
            parent_id = dialog.get_parent_id()
            name = dialog.get_department_name()

            # dept -> title conversion
            if new_scope == "title":
                # Safety checks
                has_children = any(
                    p == dept_id for p in self._id_to_parent.values() if p is not None
                )
                if has_children:
                    dialog.set_status(
                        "Không thể chuyển đổi vì phòng ban đang có phòng ban con.",
                        ok=False,
                    )
                    return

                if (getattr(self, "_titles_by_department", {}) or {}).get(int(dept_id)):
                    dialog.set_status(
                        "Không thể chuyển đổi vì phòng ban đang có Chức danh bên trong.",
                        ok=False,
                    )
                    return

                try:
                    used = EmployeeRepository().count_employees_by_department(dept_id)
                except Exception:
                    used = 0
                if used > 0:
                    dialog.set_status(
                        "Không thể chuyển đổi vì đang có nhân viên thuộc Phòng ban này.",
                        ok=False,
                    )
                    return

                ok, msg, _new_id = TitleService().create_title(
                    name,
                    department_id=parent_id,
                )
                if not ok:
                    dialog.set_status(msg, ok=False)
                    return

                ok2, msg2 = self._service.delete_department(dept_id)
                if not ok2:
                    dialog.set_status(msg2, ok=False)
                    return

                dialog.set_status("Chuyển đổi thành công.", ok=True)
                dialog.accept()
                return

            # Normal department edit
            current_note = self._id_to_note.get(dept_id, "")
            ok, msg = self._service.update_department(
                dept_id,
                name,
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
        selected_node = self._get_selected_node()
        if not selected_node:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong cây trước khi Xóa.",
            )
            return

        node_type = str(selected_node.get("type") or "dept")
        node_id = int(selected_node.get("id") or 0)
        name = str(selected_node.get("name") or "")

        if node_type == "title":
            title_id = node_id
            try:
                used = EmployeeRepository().count_employees_by_title(title_id)
            except Exception:
                used = 0
            if used > 0:
                MessageDialog.info(
                    self._parent_window,
                    "Không thể xóa",
                    "Không cho phép xóa Chức danh khi đang có nhân viên thuộc chức danh này.",
                )
                return

            if not MessageDialog.confirm(
                self._parent_window,
                "Xác nhận xóa",
                f"Bạn có chắc muốn xóa chức danh: {name}?",
                ok_text="Xóa",
                cancel_text="Hủy",
                destructive=True,
            ):
                return

            ok, msg = TitleService().delete_title(title_id)
            if ok:
                self.refresh()
            else:
                MessageDialog.info(
                    self._parent_window, "Không thể xóa", msg or "Xóa thất bại."
                )
            return

        dept_id = node_id

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

        # Không cho phép xóa phòng ban nếu có chức danh bên trong
        if (getattr(self, "_titles_by_department", {}) or {}).get(int(dept_id)):
            MessageDialog.info(
                self._parent_window,
                "Không thể xóa",
                "Không cho phép xóa phòng ban khi đang có Chức danh bên trong.",
            )
            return

        try:
            used = EmployeeRepository().count_employees_by_department(dept_id)
        except Exception:
            used = 0
        if used > 0:
            MessageDialog.info(
                self._parent_window,
                "Không thể xóa",
                "Không cho phép xóa phòng ban khi đang có nhân viên thuộc phòng ban này.",
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
