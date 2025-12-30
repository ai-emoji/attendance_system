"""repository.declare_work_shift_repository

SQL CRUD cho bảng work_shifts (Khai báo Ca làm việc).

Quy ước:
- Dùng query parameter %s (MySQL)
- Repository chỉ làm SQL thuần, không nghiệp vụ
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class DeclareWorkShiftRepository:
    def list_work_shifts(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end, overtime_round_minutes "
            "FROM work_shifts ORDER BY id ASC"
        )

        query_legacy = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end "
            "FROM work_shifts ORDER BY id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                try:
                    cursor.execute(query)
                    rows = list(cursor.fetchall() or [])
                except Exception as exc:
                    msg = str(exc)
                    if "overtime_round_minutes" in msg and "Unknown column" in msg:
                        cursor.execute(query_legacy)
                        rows = list(cursor.fetchall() or [])
                    else:
                        raise

                for r in rows:
                    try:
                        r.setdefault("overtime_round_minutes", 0)
                    except Exception:
                        pass
                return rows
        except Exception:
            logger.exception("Lỗi list_work_shifts")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_work_shift(self, shift_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end, overtime_round_minutes "
            "FROM work_shifts WHERE id = %s LIMIT 1"
        )

        query_legacy = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end "
            "FROM work_shifts WHERE id = %s LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                try:
                    cursor.execute(query, (int(shift_id),))
                    row = cursor.fetchone()
                except Exception as exc:
                    msg = str(exc)
                    if "overtime_round_minutes" in msg and "Unknown column" in msg:
                        cursor.execute(query_legacy, (int(shift_id),))
                        row = cursor.fetchone()
                    else:
                        raise

                if row is not None:
                    try:
                        row.setdefault("overtime_round_minutes", 0)
                    except Exception:
                        pass
                return row
        except Exception:
            logger.exception("Lỗi get_work_shift")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_work_shift(
        self,
        shift_code: str,
        time_in: str,
        time_out: str,
        lunch_start: str | None,
        lunch_end: str | None,
        total_minutes: int | None,
        work_count: float | None,
        in_window_start: str | None,
        in_window_end: str | None,
        out_window_start: str | None,
        out_window_end: str | None,
        overtime_round_minutes: int | None,
    ) -> int:
        query = (
            "INSERT INTO work_shifts (shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, out_window_start, out_window_end, overtime_round_minutes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        shift_code,
                        time_in,
                        time_out,
                        lunch_start,
                        lunch_end,
                        total_minutes,
                        work_count,
                        in_window_start,
                        in_window_end,
                        out_window_start,
                        out_window_end,
                        overtime_round_minutes,
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_work_shift")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_work_shift(
        self,
        shift_id: int,
        shift_code: str,
        time_in: str,
        time_out: str,
        lunch_start: str | None,
        lunch_end: str | None,
        total_minutes: int | None,
        work_count: float | None,
        in_window_start: str | None,
        in_window_end: str | None,
        out_window_start: str | None,
        out_window_end: str | None,
        overtime_round_minutes: int | None,
    ) -> int:
        query = (
            "UPDATE work_shifts SET shift_code=%s, time_in=%s, time_out=%s, "
            "lunch_start=%s, lunch_end=%s, total_minutes=%s, work_count=%s, "
            "in_window_start=%s, in_window_end=%s, out_window_start=%s, out_window_end=%s, overtime_round_minutes=%s "
            "WHERE id=%s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        shift_code,
                        time_in,
                        time_out,
                        lunch_start,
                        lunch_end,
                        total_minutes,
                        work_count,
                        in_window_start,
                        in_window_end,
                        out_window_start,
                        out_window_end,
                        overtime_round_minutes,
                        int(shift_id),
                    ),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_work_shift")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_work_shift(self, shift_id: int) -> int:
        query = "DELETE FROM work_shifts WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(shift_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_work_shift")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_work_shift_usage_counts(self, shift_id: int) -> dict[str, int]:
        """Đếm số nơi đang tham chiếu work_shifts.id.

        Hiện tại ca làm việc được dùng chủ yếu trong module Sắp xếp lịch trình:
        - arrange_schedule_details: shift1_id..shift5_id (schema cũ có thể chỉ có 1..3)
        - arrange_schedule_detail_shifts: shift_id (có thể chưa tồn tại ở DB cũ)
        """
        result: dict[str, int] = {
            "arrange_schedule_details": 0,
            "arrange_schedule_detail_shifts": 0,
        }

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)

                # 1) arrange_schedule_details
                q_details = (
                    "SELECT COUNT(*) AS c "
                    "FROM arrange_schedule_details "
                    "WHERE shift1_id = %s OR shift2_id = %s OR shift3_id = %s "
                    "OR shift4_id = %s OR shift5_id = %s"
                )
                q_details_legacy = (
                    "SELECT COUNT(*) AS c "
                    "FROM arrange_schedule_details "
                    "WHERE shift1_id = %s OR shift2_id = %s OR shift3_id = %s"
                )
                try:
                    cursor.execute(
                        q_details,
                        (
                            int(shift_id),
                            int(shift_id),
                            int(shift_id),
                            int(shift_id),
                            int(shift_id),
                        ),
                    )
                    row = cursor.fetchone() or {}
                    result["arrange_schedule_details"] = int(row.get("c") or 0)
                except Exception as exc:
                    msg = str(exc)
                    # DB cũ chưa có shift4_id/shift5_id
                    if "Unknown column" in msg and (
                        "shift4_id" in msg or "shift5_id" in msg
                    ):
                        cursor.execute(
                            q_details_legacy,
                            (int(shift_id), int(shift_id), int(shift_id)),
                        )
                        row = cursor.fetchone() or {}
                        result["arrange_schedule_details"] = int(row.get("c") or 0)
                    # Nếu DB cũ chưa có module lịch trình thì bỏ qua
                    elif "doesn't exist" in msg or "does not exist" in msg:
                        result["arrange_schedule_details"] = 0
                    else:
                        raise

                # 2) arrange_schedule_detail_shifts
                q_detail_shifts = "SELECT COUNT(*) AS c FROM arrange_schedule_detail_shifts WHERE shift_id = %s"
                try:
                    cursor.execute(q_detail_shifts, (int(shift_id),))
                    row = cursor.fetchone() or {}
                    result["arrange_schedule_detail_shifts"] = int(row.get("c") or 0)
                except Exception as exc:
                    msg = str(exc)
                    if "doesn't exist" in msg or "does not exist" in msg:
                        result["arrange_schedule_detail_shifts"] = 0
                    else:
                        raise

                return result
        except Exception:
            logger.exception("Lỗi get_work_shift_usage_counts")
            raise
        finally:
            if cursor is not None:
                cursor.close()
