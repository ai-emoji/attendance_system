"""services.declare_work_shift_services

Service layer cho màn "Khai báo Ca làm việc":
- Validate dữ liệu form
- CRUD qua DeclareWorkShiftRepository

Quy ước giờ:
- Nhập theo HH:MM (24h)
- Lưu xuống MySQL dạng TIME (chuẩn hóa HH:MM:SS)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.declare_work_shift_repository import DeclareWorkShiftRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkShiftModel:
    id: int
    shift_code: str
    time_in: str
    time_out: str
    lunch_start: str | None
    lunch_end: str | None
    total_minutes: int | None
    work_count: float | None
    in_window_start: str | None
    in_window_end: str | None
    out_window_start: str | None
    out_window_end: str | None
    overtime_round_minutes: int | None


class DeclareWorkShiftService:
    SHIFT_CODE_MAX_LENGTH = 50

    def __init__(self, repository: DeclareWorkShiftRepository | None = None) -> None:
        self._repo = repository or DeclareWorkShiftRepository()

    def list_work_shifts(self) -> list[WorkShiftModel]:
        rows = self._repo.list_work_shifts()
        result: list[WorkShiftModel] = []
        for r in rows:
            try:
                result.append(
                    WorkShiftModel(
                        id=int(r.get("id")),
                        shift_code=str(r.get("shift_code") or ""),
                        time_in=str(r.get("time_in") or ""),
                        time_out=str(r.get("time_out") or ""),
                        lunch_start=(
                            str(r.get("lunch_start"))
                            if r.get("lunch_start") is not None
                            else None
                        ),
                        lunch_end=(
                            str(r.get("lunch_end"))
                            if r.get("lunch_end") is not None
                            else None
                        ),
                        total_minutes=(
                            int(r.get("total_minutes"))
                            if r.get("total_minutes") is not None
                            else None
                        ),
                        work_count=(
                            float(r.get("work_count"))
                            if r.get("work_count") is not None
                            else None
                        ),
                        in_window_start=(
                            str(r.get("in_window_start"))
                            if r.get("in_window_start") is not None
                            else None
                        ),
                        in_window_end=(
                            str(r.get("in_window_end"))
                            if r.get("in_window_end") is not None
                            else None
                        ),
                        out_window_start=(
                            str(r.get("out_window_start"))
                            if r.get("out_window_start") is not None
                            else None
                        ),
                        out_window_end=(
                            str(r.get("out_window_end"))
                            if r.get("out_window_end") is not None
                            else None
                        ),
                        overtime_round_minutes=(
                            int(r.get("overtime_round_minutes"))
                            if r.get("overtime_round_minutes") is not None
                            else None
                        ),
                    )
                )
            except Exception:
                continue
        return result

    def get_work_shift(self, shift_id: int) -> WorkShiftModel | None:
        if not shift_id:
            return None
        row = self._repo.get_work_shift(int(shift_id))
        if not row:
            return None
        try:
            return WorkShiftModel(
                id=int(row.get("id")),
                shift_code=str(row.get("shift_code") or ""),
                time_in=str(row.get("time_in") or ""),
                time_out=str(row.get("time_out") or ""),
                lunch_start=(
                    str(row.get("lunch_start"))
                    if row.get("lunch_start") is not None
                    else None
                ),
                lunch_end=(
                    str(row.get("lunch_end"))
                    if row.get("lunch_end") is not None
                    else None
                ),
                total_minutes=(
                    int(row.get("total_minutes"))
                    if row.get("total_minutes") is not None
                    else None
                ),
                work_count=(
                    float(row.get("work_count"))
                    if row.get("work_count") is not None
                    else None
                ),
                in_window_start=(
                    str(row.get("in_window_start"))
                    if row.get("in_window_start") is not None
                    else None
                ),
                in_window_end=(
                    str(row.get("in_window_end"))
                    if row.get("in_window_end") is not None
                    else None
                ),
                out_window_start=(
                    str(row.get("out_window_start"))
                    if row.get("out_window_start") is not None
                    else None
                ),
                out_window_end=(
                    str(row.get("out_window_end"))
                    if row.get("out_window_end") is not None
                    else None
                ),
                overtime_round_minutes=(
                    int(row.get("overtime_round_minutes"))
                    if row.get("overtime_round_minutes") is not None
                    else None
                ),
            )
        except Exception:
            return None

    def create_work_shift(self, **form: str) -> tuple[bool, str, int | None]:
        ok, msg, parsed = self._validate_form(**form)
        if not ok or parsed is None:
            return False, msg, None

        try:
            new_id = self._repo.create_work_shift(**parsed)
            return True, "Lưu thành công.", new_id
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Mã ca đã tồn tại.", None
            logger.exception("Service create_work_shift thất bại")
            return False, "Không thể lưu. Vui lòng thử lại.", None

    def update_work_shift(self, shift_id: int, **form: str) -> tuple[bool, str]:
        if not shift_id:
            return False, "Không tìm thấy dòng cần cập nhật."

        ok, msg, parsed = self._validate_form(**form)
        if not ok or parsed is None:
            return False, msg

        try:
            affected = self._repo.update_work_shift(int(shift_id), **parsed)
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Lưu thành công."
        except Exception as exc:
            if self._is_duplicate_key(exc):
                return False, "Mã ca đã tồn tại."
            logger.exception("Service update_work_shift thất bại")
            return False, "Không thể lưu. Vui lòng thử lại."

    def delete_work_shift(self, shift_id: int) -> tuple[bool, str]:
        if not shift_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_work_shift(int(shift_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception:
            logger.exception("Service delete_work_shift thất bại")
            return False, "Không thể xóa. Vui lòng thử lại."

    # -----------------
    # Validation
    # -----------------
    def _validate_form(self, **form: str) -> tuple[bool, str, dict | None]:
        shift_code = (form.get("shift_code") or "").strip()
        time_in_raw = (form.get("time_in") or "").strip()
        time_out_raw = (form.get("time_out") or "").strip()

        lunch_start_raw = (form.get("lunch_start") or "").strip()
        lunch_end_raw = (form.get("lunch_end") or "").strip()

        total_minutes_raw = (form.get("total_minutes") or "").strip()
        work_count_raw = (form.get("work_count") or "").strip()

        in_window_start_raw = (form.get("in_window_start") or "").strip()
        in_window_end_raw = (form.get("in_window_end") or "").strip()
        out_window_start_raw = (form.get("out_window_start") or "").strip()
        out_window_end_raw = (form.get("out_window_end") or "").strip()
        overtime_round_minutes_raw = (form.get("overtime_round_minutes") or "").strip()

        if not shift_code:
            return False, "Vui lòng nhập Mã ca làm việc.", None
        if len(shift_code) > self.SHIFT_CODE_MAX_LENGTH:
            return (
                False,
                f"Mã ca tối đa {self.SHIFT_CODE_MAX_LENGTH} ký tự.",
                None,
            )

        if not time_in_raw:
            return False, "Vui lòng nhập Giờ vào làm việc.", None
        if not time_out_raw:
            return False, "Vui lòng nhập Giờ kết thúc làm việc.", None

        ok, msg, time_in = self._parse_time_required(time_in_raw, "Giờ vào làm việc")
        if not ok:
            return False, msg, None

        ok, msg, time_out = self._parse_time_required(
            time_out_raw, "Giờ kết thúc làm việc"
        )
        if not ok:
            return False, msg, None

        ok, msg, lunch_start = self._parse_time_optional(
            lunch_start_raw, "Giờ bắt đầu ăn trưa"
        )
        if not ok:
            return False, msg, None

        ok, msg, lunch_end = self._parse_time_optional(
            lunch_end_raw, "Giờ kết thúc ăn trưa"
        )
        if not ok:
            return False, msg, None

        ok, msg, in_window_start = self._parse_time_optional(
            in_window_start_raw, "Giờ bắt đầu vào để hiểu ca"
        )
        if not ok:
            return False, msg, None

        ok, msg, in_window_end = self._parse_time_optional(
            in_window_end_raw, "Giờ kết thúc vào để hiểu ca"
        )
        if not ok:
            return False, msg, None

        ok, msg, out_window_start = self._parse_time_optional(
            out_window_start_raw, "Bắt đầu giờ ra để hiểu ca"
        )
        if not ok:
            return False, msg, None

        ok, msg, out_window_end = self._parse_time_optional(
            out_window_end_raw, "Kết thúc giờ ra để hiểu ca"
        )
        if not ok:
            return False, msg, None

        total_minutes: int | None
        if not total_minutes_raw:
            total_minutes = None
        else:
            try:
                total_minutes = int(total_minutes_raw)
            except Exception:
                return False, "Tổng giờ <phút> không hợp lệ.", None
            if total_minutes < 0:
                return False, "Tổng giờ <phút> không hợp lệ.", None

        work_count: float | None
        if not work_count_raw:
            work_count = None
        else:
            try:
                work_count = float(work_count_raw)
            except Exception:
                return False, "Đếm công <công> không hợp lệ.", None
            if work_count < 0:
                return False, "Đếm công <công> không hợp lệ.", None

        overtime_round_minutes: int | None
        if not overtime_round_minutes_raw:
            overtime_round_minutes = None
        else:
            try:
                overtime_round_minutes = int(float(overtime_round_minutes_raw))
            except Exception:
                return False, "Mức làm tròn cho phép giờ + <phút> không hợp lệ.", None
            if overtime_round_minutes < 0:
                return False, "Mức làm tròn cho phép giờ + <phút> không hợp lệ.", None

        return (
            True,
            "OK",
            {
                "shift_code": shift_code,
                "time_in": time_in,
                "time_out": time_out,
                "lunch_start": lunch_start,
                "lunch_end": lunch_end,
                "total_minutes": total_minutes,
                "work_count": work_count,
                "in_window_start": in_window_start,
                "in_window_end": in_window_end,
                "out_window_start": out_window_start,
                "out_window_end": out_window_end,
                "overtime_round_minutes": overtime_round_minutes,
            },
        )

    def _parse_time_required(
        self, value: str, field_label: str
    ) -> tuple[bool, str, str]:
        ok, msg, parsed = self._parse_time_optional(value, field_label)
        if not ok or parsed is None:
            return False, f"{field_label} không hợp lệ (HH:MM).", ""
        return True, "OK", parsed

    def _parse_time_optional(
        self, value: str, field_label: str
    ) -> tuple[bool, str, str | None]:
        raw = (value or "").strip()
        if not raw:
            return True, "OK", None

        parts = raw.split(":")
        if len(parts) not in (2, 3):
            return False, f"{field_label} không hợp lệ (HH:MM).", None

        try:
            hh = int(parts[0])
            mm = int(parts[1])
            ss = int(parts[2]) if len(parts) == 3 else 0
        except Exception:
            return False, f"{field_label} không hợp lệ (HH:MM).", None

        if hh < 0 or hh > 23 or mm < 0 or mm > 59 or ss < 0 or ss > 59:
            return False, f"{field_label} không hợp lệ (HH:MM).", None

        return True, "OK", f"{hh:02d}:{mm:02d}:{ss:02d}"

    def _is_duplicate_key(self, exc: Exception) -> bool:
        try:
            import mysql.connector  # type: ignore

            return (
                isinstance(exc, mysql.connector.Error)
                and getattr(exc, "errno", None) == 1062
            )
        except Exception:
            return "Duplicate" in str(exc) or "1062" in str(exc)
