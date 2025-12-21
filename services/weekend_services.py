"""services.weekend_services

Service layer cho màn "Chọn ngày Cuối tuần":
- Load / lưu cấu hình ngày cuối tuần
- Validate cơ bản
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.weekend_repository import WeekendRepository


logger = logging.getLogger(__name__)


@dataclass
class WeekendDay:
    id: int | None
    day_name: str
    is_weekend: bool


class WeekendService:
    DAY_NAMES: list[str] = [
        "Thứ 2",
        "Thứ 3",
        "Thứ 4",
        "Thứ 5",
        "Thứ 6",
        "Thứ 7",
        "Chủ nhật",
    ]

    def __init__(self, repository: WeekendRepository | None = None) -> None:
        self._repo = repository or WeekendRepository()

    def list_days(self) -> list[WeekendDay]:
        try:
            rows = self._repo.list_rows() or []
        except Exception:
            logger.exception("Không thể load weekend_settings")
            rows = []

        by_name: dict[str, dict] = {}
        for r in rows:
            name = str(r.get("day_name") or "").strip()
            if name:
                by_name[name] = r

        # luôn trả đủ 7 ngày theo thứ tự
        out: list[WeekendDay] = []
        for name in self.DAY_NAMES:
            r = by_name.get(name) or {}
            out.append(
                WeekendDay(
                    id=(int(r.get("id")) if r.get("id") is not None else None),
                    day_name=name,
                    is_weekend=bool(int(r.get("is_weekend") or 0)),
                )
            )
        return out

    def save_days(self, items: list[dict]) -> tuple[bool, str]:
        cleaned: list[dict] = []
        allowed = set(self.DAY_NAMES)

        for it in items:
            day_name = str(it.get("day_name") or "").strip()
            if day_name not in allowed:
                return False, f"Thứ không hợp lệ: {day_name}."

            cleaned.append(
                {
                    "day_name": day_name,
                    "is_weekend": 1 if bool(it.get("is_weekend")) else 0,
                }
            )

        try:
            self._repo.upsert_rows(cleaned)
            return True, "Lưu cấu hình thành công."
        except Exception:
            logger.exception("Không thể lưu weekend_settings")
            return False, "Không thể lưu cấu hình. Vui lòng thử lại."
