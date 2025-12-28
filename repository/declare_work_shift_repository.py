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
