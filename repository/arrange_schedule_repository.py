"""repository.arrange_schedule_repository

Repository layer: SQL thuần cho module "Sắp xếp ca theo lịch trình".

Quy ước:
- Dùng query parameter %s (MySQL)
- Không validate, không nghiệp vụ
- Mở kết nối ngắn, đóng ngay
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class ArrangeScheduleRepository:
    def list_schedules(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, schedule_name "
            "FROM hr_attendance.arrange_schedules "
            "ORDER BY id DESC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_schedules")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_schedule_header(self, schedule_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT id, schedule_name, in_out_mode, "
            "ignore_absent_sat, ignore_absent_sun, ignore_absent_holiday, "
            "holiday_count_as_work, day_is_out_time "
            "FROM hr_attendance.arrange_schedules WHERE id = %s LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(schedule_id),))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi get_schedule_header")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_schedule_details(self, schedule_id: int) -> list[dict[str, Any]]:
        query = (
            "SELECT day_key, day_name, day_order, shift1_id, shift2_id, shift3_id, shift4_id, shift5_id "
            "FROM hr_attendance.arrange_schedule_details "
            "WHERE schedule_id = %s ORDER BY day_order ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(schedule_id),))
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_schedule_details")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_schedule_day_shifts(self, schedule_id: int) -> dict[str, list[int]]:
        """Trả về map day_key -> [shift_id...] theo position ASC."""

        query = (
            "SELECT day_key, shift_id "
            "FROM hr_attendance.arrange_schedule_detail_shifts "
            "WHERE schedule_id = %s "
            "ORDER BY day_key ASC, position ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(schedule_id),))
                rows = list(cursor.fetchall() or [])

            result: dict[str, list[int]] = {}
            for r in rows:
                day_key = str(r.get("day_key") or "").strip()
                if not day_key:
                    continue
                sid = r.get("shift_id")
                if sid is None:
                    continue
                try:
                    result.setdefault(day_key, []).append(int(sid))
                except Exception:
                    continue
            return result
        except Exception:
            logger.exception("Lỗi list_schedule_day_shifts")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_in_out_mode_by_schedule_names(
        self, schedule_names: list[str]
    ) -> dict[str, str | None]:
        names: list[str] = []
        for n in schedule_names or []:
            s = str(n or "").strip()
            if s:
                names.append(s)
        names = list(dict.fromkeys(names))
        if not names:
            return {}

        placeholders = ",".join(["%s"] * len(names))
        query = (
            "SELECT schedule_name, in_out_mode "
            "FROM hr_attendance.arrange_schedules "
            f"WHERE schedule_name IN ({placeholders})"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(names))
                rows = list(cursor.fetchall() or [])
                out: dict[str, str | None] = {}
                for r in rows:
                    try:
                        key = str(r.get("schedule_name") or "").strip()
                        if not key:
                            continue
                        v = r.get("in_out_mode")
                        out[key] = str(v) if v is not None else None
                    except Exception:
                        continue
                return out
        except Exception:
            logger.exception("Lỗi get_in_out_mode_by_schedule_names")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def replace_schedule_day_shifts(
        self, schedule_id: int, day_key: str, shift_ids: list[int | None]
    ) -> None:
        """Ghi đè danh sách ca theo ngày (xóa hết rồi insert lại theo position)."""

        day_key = str(day_key or "").strip()
        if not day_key:
            return

        del_query = (
            "DELETE FROM hr_attendance.arrange_schedule_detail_shifts "
            "WHERE schedule_id = %s AND day_key = %s"
        )
        ins_query = (
            "INSERT INTO hr_attendance.arrange_schedule_detail_shifts "
            "(schedule_id, day_key, position, shift_id) VALUES (%s, %s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(del_query, (int(schedule_id), day_key))
                pos = 1
                for sid in shift_ids or []:
                    if sid is None:
                        continue
                    cursor.execute(
                        ins_query, (int(schedule_id), day_key, int(pos), int(sid))
                    )
                    pos += 1
                conn.commit()
        except Exception:
            logger.exception("Lỗi replace_schedule_day_shifts")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_day_types(self) -> list[dict[str, Any]]:
        query = (
            "SELECT day_key, day_name, day_order "
            "FROM hr_attendance.arrange_schedule_day_types "
            "ORDER BY day_order ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_day_types")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_schedule(
        self,
        schedule_name: str,
        in_out_mode: str | None,
        ignore_absent_sat: int,
        ignore_absent_sun: int,
        ignore_absent_holiday: int,
        holiday_count_as_work: int,
        day_is_out_time: int,
    ) -> int:
        query = (
            "INSERT INTO hr_attendance.arrange_schedules "
            "(schedule_name, in_out_mode, ignore_absent_sat, ignore_absent_sun, "
            " ignore_absent_holiday, holiday_count_as_work, day_is_out_time) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        schedule_name,
                        in_out_mode,
                        int(ignore_absent_sat),
                        int(ignore_absent_sun),
                        int(ignore_absent_holiday),
                        int(holiday_count_as_work),
                        int(day_is_out_time),
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_schedule")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_schedule(
        self,
        schedule_id: int,
        schedule_name: str,
        in_out_mode: str | None,
        ignore_absent_sat: int,
        ignore_absent_sun: int,
        ignore_absent_holiday: int,
        holiday_count_as_work: int,
        day_is_out_time: int,
    ) -> int:
        query = (
            "UPDATE hr_attendance.arrange_schedules "
            "SET schedule_name = %s, in_out_mode = %s, "
            "ignore_absent_sat = %s, ignore_absent_sun = %s, ignore_absent_holiday = %s, "
            "holiday_count_as_work = %s, day_is_out_time = %s "
            "WHERE id = %s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        schedule_name,
                        in_out_mode,
                        int(ignore_absent_sat),
                        int(ignore_absent_sun),
                        int(ignore_absent_holiday),
                        int(holiday_count_as_work),
                        int(day_is_out_time),
                        int(schedule_id),
                    ),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_schedule")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_schedule_details(
        self,
        schedule_id: int,
        details: list[dict[str, Any]],
    ) -> None:
        """Upsert chi tiết theo (schedule_id, day_key)."""

        if not details:
            return

        query = (
            "INSERT INTO hr_attendance.arrange_schedule_details "
            "(schedule_id, day_key, day_name, day_order, shift1_id, shift2_id, shift3_id, shift4_id, shift5_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "day_name = VALUES(day_name), day_order = VALUES(day_order), "
            "shift1_id = VALUES(shift1_id), shift2_id = VALUES(shift2_id), shift3_id = VALUES(shift3_id), "
            "shift4_id = VALUES(shift4_id), shift5_id = VALUES(shift5_id)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for d in details:
                    cursor.execute(
                        query,
                        (
                            int(schedule_id),
                            str(d.get("day_key")),
                            str(d.get("day_name")),
                            int(d.get("day_order")),
                            d.get("shift1_id"),
                            d.get("shift2_id"),
                            d.get("shift3_id"),
                            d.get("shift4_id"),
                            d.get("shift5_id"),
                        ),
                    )
                conn.commit()
        except Exception:
            logger.exception("Lỗi upsert_schedule_details")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_schedule(self, schedule_id: int) -> int:
        query = "DELETE FROM hr_attendance.arrange_schedules WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(schedule_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_schedule")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_work_shift_codes_by_ids(self, ids: list[int]) -> dict[int, str]:
        ids = [int(x) for x in (ids or []) if x is not None]
        ids = sorted(set(ids))
        if not ids:
            return {}

        placeholders = ",".join(["%s"] * len(ids))
        query = (
            "SELECT id, shift_code "
            "FROM hr_attendance.work_shifts "
            f"WHERE id IN ({placeholders})"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(ids))
                rows = list(cursor.fetchall() or [])

            result: dict[int, str] = {}
            for r in rows:
                try:
                    result[int(r.get("id"))] = str(r.get("shift_code") or "")
                except Exception:
                    continue
            return result
        except Exception:
            logger.exception("Lỗi get_work_shift_codes_by_ids")
            raise
        finally:
            if cursor is not None:
                cursor.close()
