"""services.declare_time_services

Service layer cho màn "Khai báo giờ Vào/Ra":
- Validate form
- CRUD qua DeclareTimeRepository

Ghi chú:
- Các ô giờ nhập theo định dạng HH:MM hoặc HH:MM:SS (TIME MySQL).
- UI hiện chỉ dùng QLineEdit nên validate nhẹ (cho phép trống).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.declare_time_repository import DeclareTimeRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeclareTimeModel:
    id: int
    code: str
    description: str
    sort_type: str | None
    min_between_in_out: int
    max_between_in_out: int
    gap_between_pairs: int
    cycle_days: int
    days_in_month: int
    cycle_end_time: str | None
    remove_prev_night: bool
    calc_from: str | None
    calc_to: str | None


class DeclareTimeService:
    def __init__(self, repository: DeclareTimeRepository | None = None) -> None:
        self._repo = repository or DeclareTimeRepository()

    def list_items(self) -> list[DeclareTimeModel]:
        rows = self._repo.list_items()
        result: list[DeclareTimeModel] = []
        for r in rows:
            try:
                result.append(
                    DeclareTimeModel(
                        id=int(r.get("id")),
                        code=str(r.get("code") or ""),
                        description=str(r.get("description") or ""),
                        sort_type=(
                            str(r.get("sort_type"))
                            if r.get("sort_type") is not None
                            else None
                        ),
                        min_between_in_out=int(r.get("min_between_in_out") or 0),
                        max_between_in_out=int(r.get("max_between_in_out") or 0),
                        gap_between_pairs=int(r.get("gap_between_pairs") or 0),
                        cycle_days=int(r.get("cycle_days") or 0),
                        days_in_month=int(r.get("days_in_month") or 0),
                        cycle_end_time=str(r.get("cycle_end_time") or "") or None,
                        remove_prev_night=bool(r.get("remove_prev_night") or 0),
                        calc_from=str(r.get("calc_from") or "") or None,
                        calc_to=str(r.get("calc_to") or "") or None,
                    )
                )
            except Exception:
                continue
        return result

    def get_item(self, item_id: int) -> DeclareTimeModel | None:
        if not item_id:
            return None
        r = self._repo.get_item(int(item_id))
        if not r:
            return None
        try:
            return DeclareTimeModel(
                id=int(r.get("id")),
                code=str(r.get("code") or ""),
                description=str(r.get("description") or ""),
                sort_type=(
                    str(r.get("sort_type")) if r.get("sort_type") is not None else None
                ),
                min_between_in_out=int(r.get("min_between_in_out") or 0),
                max_between_in_out=int(r.get("max_between_in_out") or 0),
                gap_between_pairs=int(r.get("gap_between_pairs") or 0),
                cycle_days=int(r.get("cycle_days") or 0),
                days_in_month=int(r.get("days_in_month") or 0),
                cycle_end_time=str(r.get("cycle_end_time") or "") or None,
                remove_prev_night=bool(r.get("remove_prev_night") or 0),
                calc_from=str(r.get("calc_from") or "") or None,
                calc_to=str(r.get("calc_to") or "") or None,
            )
        except Exception:
            return None

    def create_item(self, form: dict) -> tuple[bool, str, int | None]:
        ok, msg, data = self._validate_form(form)
        if not ok or data is None:
            return False, msg, None

        try:
            new_id = self._repo.create_item(data)
            return True, "Lưu thành công.", int(new_id)
        except Exception:
            logger.exception("Service create_item thất bại")
            return False, "Không thể lưu. Vui lòng thử lại.", None

    def update_item(self, item_id: int, form: dict) -> tuple[bool, str]:
        if not item_id:
            return False, "Không tìm thấy dòng cần cập nhật."

        ok, msg, data = self._validate_form(form)
        if not ok or data is None:
            return False, msg

        try:
            affected = self._repo.update_item(int(item_id), data)
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Lưu thành công."
        except Exception:
            logger.exception("Service update_item thất bại")
            return False, "Không thể lưu. Vui lòng thử lại."

    def delete_item(self, item_id: int) -> tuple[bool, str]:
        if not item_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_item(int(item_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception:
            logger.exception("Service delete_item thất bại")
            return False, "Không thể xóa. Vui lòng thử lại."

    def _validate_form(self, form: dict) -> tuple[bool, str, dict | None]:
        code = str(form.get("code") or "").strip()
        description = str(form.get("description") or "").strip()
        sort_type = form.get("sort_type")

        if not code:
            return False, "Vui lòng nhập Mã.", None

        def _to_int(key: str, default: int = 0) -> int:
            raw = str(form.get(key) or "").strip()
            if raw == "":
                return int(default)
            try:
                return int(raw)
            except Exception:
                return int(default)

        min_between = _to_int("min_between_in_out", 0)
        max_between = _to_int("max_between_in_out", 0)
        gap_pairs = _to_int("gap_between_pairs", 0)
        cycle_days = _to_int("cycle_days", 0)
        days_in_month = _to_int("days_in_month", 0)

        cycle_end_time = str(form.get("cycle_end_time") or "").strip() or None
        calc_from = str(form.get("calc_from") or "").strip() or None
        calc_to = str(form.get("calc_to") or "").strip() or None
        remove_prev_night = bool(form.get("remove_prev_night"))

        st = None
        if sort_type is not None and str(sort_type).strip() != "":
            st = str(sort_type).strip()
            if st not in ("auto", "device", "first_last"):
                st = None

        return (
            True,
            "OK",
            {
                "code": code,
                "description": description,
                "sort_type": st,
                "min_between_in_out": int(min_between),
                "max_between_in_out": int(max_between),
                "gap_between_pairs": int(gap_pairs),
                "cycle_days": int(cycle_days),
                "days_in_month": int(days_in_month),
                "cycle_end_time": cycle_end_time,
                "remove_prev_night": 1 if remove_prev_night else 0,
                "calc_from": calc_from,
                "calc_to": calc_to,
            },
        )
