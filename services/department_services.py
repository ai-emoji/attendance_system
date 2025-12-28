"""services.department_services

Service layer cho màn "Khai báo Phòng ban":
- Validate dữ liệu
- Gọi repository
- Trả về (ok, message) thân thiện cho UI

Yêu cầu nghiệp vụ:
- Tên phòng ban không được trùng ở mọi cấp (unique toàn hệ thống)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.resource import DEPARTMENT_NAME_MAX_LENGTH, DEPARTMENT_NOTE_MAX_LENGTH
from repository.department_repository import DepartmentRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DepartmentModel:
    id: int
    parent_id: int | None
    department_name: str
    department_note: str


class DepartmentService:
    def __init__(self, repository: DepartmentRepository | None = None) -> None:
        self._repo = repository or DepartmentRepository()

    def list_departments(self) -> list[DepartmentModel]:
        rows = self._repo.list_departments()
        result: list[DepartmentModel] = []
        for r in rows:
            try:
                result.append(
                    DepartmentModel(
                        id=int(r.get("id")),
                        parent_id=(
                            int(r.get("parent_id"))
                            if r.get("parent_id") is not None
                            else None
                        ),
                        department_name=str(r.get("department_name") or ""),
                        department_note=str(r.get("department_note") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def create_department(
        self,
        department_name: str,
        parent_id: int | None,
        department_note: str,
    ) -> tuple[bool, str, int | None]:
        department_name = (department_name or "").strip()
        department_note = (department_note or "").strip()

        if not department_name:
            return False, "Vui lòng nhập Tên Phòng ban.", None
        if len(department_name) > DEPARTMENT_NAME_MAX_LENGTH:
            return (
                False,
                f"Tên Phòng ban tối đa {DEPARTMENT_NAME_MAX_LENGTH} ký tự.",
                None,
            )
        if len(department_note) > DEPARTMENT_NOTE_MAX_LENGTH:
            return (
                False,
                f"Ghi chú tối đa {DEPARTMENT_NOTE_MAX_LENGTH} ký tự.",
                None,
            )

        try:
            new_id = self._repo.create_department(
                department_name=department_name,
                parent_id=int(parent_id) if parent_id else None,
                department_note=department_note or None,
            )
            return True, "Thêm mới thành công.", new_id
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Phòng ban đã tồn tại (trùng tên).", None
            logger.exception("Service create_department thất bại")
            return False, "Không thể thêm mới. Vui lòng thử lại.", None

    def update_department(
        self,
        department_id: int,
        department_name: str,
        parent_id: int | None,
        department_note: str,
    ) -> tuple[bool, str]:
        department_name = (department_name or "").strip()
        department_note = (department_note or "").strip()

        if not department_id:
            return False, "Không tìm thấy dòng cần sửa."
        if not department_name:
            return False, "Vui lòng nhập Tên Phòng ban."
        if len(department_name) > DEPARTMENT_NAME_MAX_LENGTH:
            return False, f"Tên Phòng ban tối đa {DEPARTMENT_NAME_MAX_LENGTH} ký tự."
        if len(department_note) > DEPARTMENT_NOTE_MAX_LENGTH:
            return False, f"Ghi chú tối đa {DEPARTMENT_NOTE_MAX_LENGTH} ký tự."

        if parent_id is not None and int(parent_id) == int(department_id):
            return False, "Phòng ban cha không hợp lệ."

        try:
            affected = self._repo.update_department(
                department_id=int(department_id),
                department_name=department_name,
                parent_id=int(parent_id) if parent_id else None,
                department_note=department_note or None,
            )
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Sửa đổi thành công."
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Phòng ban đã tồn tại (trùng tên)."
            logger.exception("Service update_department thất bại")
            return False, "Không thể sửa đổi. Vui lòng thử lại."

    def delete_department(self, department_id: int) -> tuple[bool, str]:
        if not department_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_department(int(department_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception as exc:
            # Có thể fail nếu còn con (FK). Với ON DELETE SET NULL thì vẫn xóa được.
            logger.exception("Service delete_department thất bại")
            if self._is_foreign_key_error(exc):
                return False, "Không thể xóa vì đang được sử dụng."
            return False, "Không thể xóa. Vui lòng thử lại."

    def _is_duplicate_key(self, exc: Exception) -> bool:
        try:
            import mysql.connector  # type: ignore

            return (
                isinstance(exc, mysql.connector.Error)
                and getattr(exc, "errno", None) == 1062
            )
        except Exception:
            return "Duplicate" in str(exc) or "1062" in str(exc)

    def _is_foreign_key_error(self, exc: Exception) -> bool:
        try:
            import mysql.connector  # type: ignore

            return isinstance(exc, mysql.connector.Error) and getattr(
                exc, "errno", None
            ) in (1451, 1452)
        except Exception:
            return "foreign key" in str(exc).lower()
