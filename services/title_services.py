"""services.title_services

Service layer cho màn "Khai báo Chức danh":
- Validate dữ liệu
- Gọi repository
- Trả về (ok, message) thân thiện cho UI
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.resource import TITLE_NAME_MAX_LENGTH
from repository.title_repository import TitleRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TitleModel:
    id: int
    title_name: str
    department_id: int | None = None


class TitleService:
    def __init__(self, repository: TitleRepository | None = None) -> None:
        self._repo = repository or TitleRepository()

    def list_titles(self) -> list[TitleModel]:
        rows = self._repo.list_titles()
        result: list[TitleModel] = []
        for r in rows:
            try:
                result.append(
                    TitleModel(
                        id=int(r.get("id")),
                        title_name=str(r.get("title_name") or ""),
                        department_id=(
                            int(r.get("department_id"))
                            if r.get("department_id") is not None
                            else None
                        ),
                    )
                )
            except Exception:
                # Bỏ qua row lỗi format để UI không crash
                continue
        return result

    def get_title(self, title_id: int) -> TitleModel | None:
        if not title_id:
            return None
        try:
            row = self._repo.get_title(int(title_id))
        except Exception:
            logger.exception("Service get_title thất bại")
            return None
        if not row:
            return None
        try:
            return TitleModel(
                id=int(row.get("id")),
                title_name=str(row.get("title_name") or ""),
                department_id=(
                    int(row.get("department_id"))
                    if row.get("department_id") is not None
                    else None
                ),
            )
        except Exception:
            return None

    def create_title(
        self, title_name: str, department_id: int | None = None
    ) -> tuple[bool, str, int | None]:
        title_name = (title_name or "").strip()
        if not title_name:
            return False, "Vui lòng nhập Tên Chức Danh.", None
        if len(title_name) > TITLE_NAME_MAX_LENGTH:
            return False, f"Tên Chức Danh tối đa {TITLE_NAME_MAX_LENGTH} ký tự.", None

        try:
            new_id = self._repo.create_title(title_name, department_id=department_id)
            return True, "Thêm mới thành công.", new_id
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Chức danh đã tồn tại.", None
            logger.exception("Service create_title thất bại")
            return False, "Không thể thêm mới. Vui lòng thử lại.", None

    def update_title(
        self, title_id: int, title_name: str, department_id: int | None = None
    ) -> tuple[bool, str]:
        title_name = (title_name or "").strip()
        if not title_id:
            return False, "Không tìm thấy dòng cần sửa."
        if not title_name:
            return False, "Vui lòng nhập Tên Chức Danh."
        if len(title_name) > TITLE_NAME_MAX_LENGTH:
            return False, f"Tên Chức Danh tối đa {TITLE_NAME_MAX_LENGTH} ký tự."

        try:
            affected = self._repo.update_title(
                int(title_id), title_name, department_id=department_id
            )
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Sửa đổi thành công."
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Chức danh đã tồn tại."
            logger.exception("Service update_title thất bại")
            return False, "Không thể sửa đổi. Vui lòng thử lại."

    def delete_title(self, title_id: int) -> tuple[bool, str]:
        if not title_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_title(int(title_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception:
            logger.exception("Service delete_title thất bại")
            return False, "Không thể xóa. Vui lòng thử lại."

    def _is_duplicate_key(self, exc: Exception) -> bool:
        try:
            import mysql.connector  # type: ignore

            return (
                isinstance(exc, mysql.connector.Error)
                and getattr(exc, "errno", None) == 1062
            )
        except Exception:
            # fallback theo message
            return "Duplicate" in str(exc) or "1062" in str(exc)
