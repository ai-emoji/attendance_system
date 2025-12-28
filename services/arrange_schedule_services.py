"""services.arrange_schedule_services

Service layer cho module "Sắp xếp ca theo lịch trình":
- Validate dữ liệu cơ bản
- Gọi repository
- Trả về (ok, message) thân thiện cho UI
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.arrange_schedule_repository import ArrangeScheduleRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArrangeScheduleHeader:
    id: int
    schedule_name: str
    in_out_mode: str | None
    ignore_absent_sat: int
    ignore_absent_sun: int
    ignore_absent_holiday: int
    holiday_count_as_work: int
    day_is_out_time: int


@dataclass(frozen=True)
class ArrangeScheduleDayType:
    day_key: str
    day_name: str
    day_order: int


@dataclass(frozen=True)
class ArrangeScheduleDetail:
    day_key: str
    day_name: str
    day_order: int
    shift1_id: int | None
    shift2_id: int | None
    shift3_id: int | None
    shift4_id: int | None
    shift5_id: int | None
    shift_ids: list[int]


class ArrangeScheduleService:
    def __init__(self, repo: ArrangeScheduleRepository | None = None) -> None:
        self._repo = repo or ArrangeScheduleRepository()

    def get_in_out_mode_map(self, schedule_names: list[str]) -> dict[str, str | None]:
        """Return schedule_name -> normalized in_out_mode.

        Normalization:
        - old values (in/out) => device
        - allowed: None/auto/device/first_last
        - invalid => None
        """

        raw = self._repo.get_in_out_mode_by_schedule_names(schedule_names or [])
        out: dict[str, str | None] = {}
        for k, v in (raw or {}).items():
            mode = v or None
            if mode in ("in", "out"):
                mode = "device"
            if mode not in (None, "auto", "device", "first_last"):
                mode = None
            out[str(k or "").strip()] = mode
        return out

    def list_schedules(self) -> list[tuple[int, str]]:
        rows = self._repo.list_schedules()
        result: list[tuple[int, str]] = []
        for r in rows:
            try:
                result.append((int(r.get("id")), str(r.get("schedule_name") or "")))
            except Exception:
                continue
        return result

    def list_day_types(self) -> list[ArrangeScheduleDayType]:
        """Ưu tiên đọc từ DB; fallback về danh sách cố định."""
        try:
            rows = self._repo.list_day_types()
            result: list[ArrangeScheduleDayType] = []
            for r in rows:
                result.append(
                    ArrangeScheduleDayType(
                        day_key=str(r.get("day_key") or ""),
                        day_name=str(r.get("day_name") or ""),
                        day_order=int(r.get("day_order") or 0),
                    )
                )
            result = [d for d in result if d.day_key and d.day_name and d.day_order]
            if result:
                return result
        except Exception:
            pass

        fallback = [
            ArrangeScheduleDayType("mon", "Thứ 2", 1),
            ArrangeScheduleDayType("tue", "Thứ 3", 2),
            ArrangeScheduleDayType("wed", "Thứ 4", 3),
            ArrangeScheduleDayType("thu", "Thứ 5", 4),
            ArrangeScheduleDayType("fri", "Thứ 6", 5),
            ArrangeScheduleDayType("sat", "Thứ 7", 6),
            ArrangeScheduleDayType("sun", "Chủ nhật", 7),
            ArrangeScheduleDayType("holiday", "Ngày lễ", 8),
        ]
        return fallback

    def get_schedule(
        self, schedule_id: int
    ) -> tuple[ArrangeScheduleHeader | None, list[ArrangeScheduleDetail]]:
        if not schedule_id:
            return None, []

        header_row = self._repo.get_schedule_header(int(schedule_id))
        if not header_row:
            return None, []

        header = ArrangeScheduleHeader(
            id=int(header_row.get("id")),
            schedule_name=str(header_row.get("schedule_name") or ""),
            in_out_mode=(
                str(header_row.get("in_out_mode"))
                if header_row.get("in_out_mode") is not None
                else None
            ),
            ignore_absent_sat=int(header_row.get("ignore_absent_sat") or 0),
            ignore_absent_sun=int(header_row.get("ignore_absent_sun") or 0),
            ignore_absent_holiday=int(header_row.get("ignore_absent_holiday") or 0),
            holiday_count_as_work=int(header_row.get("holiday_count_as_work") or 0),
            day_is_out_time=int(header_row.get("day_is_out_time") or 0),
        )

        details_rows = self._repo.list_schedule_details(int(schedule_id))
        # New storage (unlimited shifts)
        shifts_map: dict[str, list[int]] = {}
        try:
            shifts_map = self._repo.list_schedule_day_shifts(int(schedule_id))
        except Exception:
            shifts_map = {}
        details: list[ArrangeScheduleDetail] = []
        for r in details_rows:
            try:
                day_key = str(r.get("day_key") or "")
                shift_ids = list(shifts_map.get(day_key, []) or [])

                # Fallback to legacy columns if new table empty for this day
                if not shift_ids:
                    for k in (
                        "shift1_id",
                        "shift2_id",
                        "shift3_id",
                        "shift4_id",
                        "shift5_id",
                    ):
                        v = r.get(k)
                        if v is not None:
                            try:
                                shift_ids.append(int(v))
                            except Exception:
                                pass

                details.append(
                    ArrangeScheduleDetail(
                        day_key=day_key,
                        day_name=str(r.get("day_name") or ""),
                        day_order=int(r.get("day_order") or 0),
                        shift1_id=(
                            int(r.get("shift1_id"))
                            if r.get("shift1_id") is not None
                            else None
                        ),
                        shift2_id=(
                            int(r.get("shift2_id"))
                            if r.get("shift2_id") is not None
                            else None
                        ),
                        shift3_id=(
                            int(r.get("shift3_id"))
                            if r.get("shift3_id") is not None
                            else None
                        ),
                        shift4_id=(
                            int(r.get("shift4_id"))
                            if r.get("shift4_id") is not None
                            else None
                        ),
                        shift5_id=(
                            int(r.get("shift5_id"))
                            if r.get("shift5_id") is not None
                            else None
                        ),
                        shift_ids=shift_ids,
                    )
                )
            except Exception:
                continue
        details.sort(key=lambda d: d.day_order)
        return header, details

    def save_schedule(
        self,
        schedule_id: int | None,
        schedule_name: str,
        in_out_mode: str | None,
        ignore_absent_sat: bool,
        ignore_absent_sun: bool,
        ignore_absent_holiday: bool,
        holiday_count_as_work: bool,
        day_is_out_time: bool,
        details_by_day_name: dict[str, list[int | None]],
    ) -> tuple[bool, str, int | None]:
        schedule_name = (schedule_name or "").strip()
        if not schedule_name:
            return False, "Vui lòng nhập Tên lịch trình.", None
        if len(schedule_name) > 255:
            return False, "Tên lịch trình tối đa 255 ký tự.", None

        in_out_mode = in_out_mode or None
        # New synced values: auto/device/first_last
        # Backward-compat: old values (in/out) map to device.
        if in_out_mode in ("in", "out"):
            in_out_mode = "device"
        if in_out_mode not in (None, "auto", "device", "first_last"):
            in_out_mode = None

        try:
            if schedule_id:
                self._repo.update_schedule(
                    schedule_id=int(schedule_id),
                    schedule_name=schedule_name,
                    in_out_mode=in_out_mode,
                    ignore_absent_sat=int(bool(ignore_absent_sat)),
                    ignore_absent_sun=int(bool(ignore_absent_sun)),
                    ignore_absent_holiday=int(bool(ignore_absent_holiday)),
                    holiday_count_as_work=int(bool(holiday_count_as_work)),
                    day_is_out_time=int(bool(day_is_out_time)),
                )
                saved_id = int(schedule_id)
            else:
                saved_id = self._repo.create_schedule(
                    schedule_name=schedule_name,
                    in_out_mode=in_out_mode,
                    ignore_absent_sat=int(bool(ignore_absent_sat)),
                    ignore_absent_sun=int(bool(ignore_absent_sun)),
                    ignore_absent_holiday=int(bool(ignore_absent_holiday)),
                    holiday_count_as_work=int(bool(holiday_count_as_work)),
                    day_is_out_time=int(bool(day_is_out_time)),
                )

            # Upsert details
            day_types = self.list_day_types()
            name_to_type = {d.day_name: d for d in day_types}

            details_payload = []
            for day_name, shifts in (details_by_day_name or {}).items():
                dt = name_to_type.get(day_name)
                if not dt:
                    continue
                shift_ids = list(shifts or [])
                # Persist legacy columns as first 5 for compatibility
                while len(shift_ids) < 5:
                    shift_ids.append(None)
                shift1_id, shift2_id, shift3_id, shift4_id, shift5_id = shift_ids[:5]
                details_payload.append(
                    {
                        "day_key": dt.day_key,
                        "day_name": dt.day_name,
                        "day_order": dt.day_order,
                        "shift1_id": shift1_id,
                        "shift2_id": shift2_id,
                        "shift3_id": shift3_id,
                        "shift4_id": shift4_id,
                        "shift5_id": shift5_id,
                    }
                )

            self._repo.upsert_schedule_details(int(saved_id), details_payload)

            # Persist unlimited shifts
            for day_name, shifts in (details_by_day_name or {}).items():
                dt = name_to_type.get(day_name)
                if not dt:
                    continue
                self._repo.replace_schedule_day_shifts(
                    int(saved_id), dt.day_key, list(shifts or [])
                )
            return True, "Lưu thành công.", int(saved_id)
        except Exception as exc:
            # Duplicate schedule name
            if self._is_duplicate_key(exc):
                return False, "Tên lịch trình đã tồn tại (trùng tên).", None
            logger.exception("save_schedule thất bại")
            return False, "Không thể lưu. Vui lòng thử lại.", None

    def delete_schedule(self, schedule_id: int) -> tuple[bool, str]:
        if not schedule_id:
            return False, "Vui lòng chọn lịch trình cần xóa."

        try:
            affected = self._repo.delete_schedule(int(schedule_id))
            if affected <= 0:
                return False, "Không tìm thấy lịch trình cần xóa."
            return True, "Xóa thành công."
        except Exception as exc:
            logger.exception("delete_schedule thất bại")
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

    def get_work_shift_codes_by_ids(self, ids: list[int]) -> dict[int, str]:
        try:
            return self._repo.get_work_shift_codes_by_ids(ids)
        except Exception:
            return {}
