"""services.holiday_services

Service layer cho màn "Khai báo Ngày lễ":
- Validate dữ liệu
- Gọi repository
- Trả về (ok, message) thân thiện cho UI
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from core.resource import HOLIDAY_INFO_MAX_LENGTH
from repository.holiday_repository import HolidayRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HolidayModel:
    id: int
    holiday_date: str  # yyyy-MM-dd
    holiday_info: str


class HolidayService:
    def __init__(self, repository: HolidayRepository | None = None) -> None:
        self._repo = repository or HolidayRepository()

    def list_holidays(self) -> list[HolidayModel]:
        rows = self._repo.list_holidays()
        result: list[HolidayModel] = []
        for r in rows:
            try:
                raw_date = r.get("holiday_date")
                # mysql connector có thể trả datetime.date
                if hasattr(raw_date, "isoformat"):
                    holiday_date = raw_date.isoformat()
                else:
                    holiday_date = str(raw_date or "")

                result.append(
                    HolidayModel(
                        id=int(r.get("id")),
                        holiday_date=holiday_date,
                        holiday_info=str(r.get("holiday_info") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def create_holiday(
        self, holiday_date: str, holiday_info: str
    ) -> tuple[bool, str, int | None]:
        holiday_date = (holiday_date or "").strip()
        holiday_info = (holiday_info or "").strip()

        if not holiday_date:
            return False, "Vui lòng chọn Ngày Tháng Năm.", None
        if not self._is_valid_iso_date(holiday_date):
            return False, "Ngày Tháng Năm không hợp lệ.", None
        if not holiday_info:
            return False, "Vui lòng nhập Thông tin ngày nghỉ.", None
        if len(holiday_info) > HOLIDAY_INFO_MAX_LENGTH:
            return (
                False,
                f"Thông tin ngày nghỉ tối đa {HOLIDAY_INFO_MAX_LENGTH} ký tự.",
                None,
            )

        try:
            new_id = self._repo.create_holiday(holiday_date, holiday_info)
            return True, "Thêm mới thành công.", new_id
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Ngày lễ đã tồn tại.", None
            logger.exception("Service create_holiday thất bại")
            return False, "Không thể thêm mới. Vui lòng thử lại.", None

    def update_holiday(
        self, holiday_id: int, holiday_date: str, holiday_info: str
    ) -> tuple[bool, str]:
        holiday_date = (holiday_date or "").strip()
        holiday_info = (holiday_info or "").strip()

        if not holiday_id:
            return False, "Không tìm thấy dòng cần sửa."
        if not holiday_date or not self._is_valid_iso_date(holiday_date):
            return False, "Ngày Tháng Năm không hợp lệ."
        if not holiday_info:
            return False, "Vui lòng nhập Thông tin ngày nghỉ."
        if len(holiday_info) > HOLIDAY_INFO_MAX_LENGTH:
            return False, f"Thông tin ngày nghỉ tối đa {HOLIDAY_INFO_MAX_LENGTH} ký tự."

        try:
            affected = self._repo.update_holiday(
                int(holiday_id), holiday_date, holiday_info
            )
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Sửa đổi thành công."
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Ngày lễ đã tồn tại."
            logger.exception("Service update_holiday thất bại")
            return False, "Không thể sửa đổi. Vui lòng thử lại."

    def delete_holiday(self, holiday_id: int) -> tuple[bool, str]:
        if not holiday_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_holiday(int(holiday_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception:
            logger.exception("Service delete_holiday thất bại")
            return False, "Không thể xóa. Vui lòng thử lại."

    def _is_valid_iso_date(self, value: str) -> bool:
        try:
            date.fromisoformat(value)
            return True
        except Exception:
            return False

    def _is_duplicate_key(self, exc: Exception) -> bool:
        try:
            import mysql.connector  # type: ignore

            return (
                isinstance(exc, mysql.connector.Error)
                and getattr(exc, "errno", None) == 1062
            )
        except Exception:
            return "Duplicate" in str(exc) or "1062" in str(exc)
