"""repository.declare_time_repository

SQL CRUD cho bảng declare_time_settings.

Bảng dự kiến (MySQL):
    declare_time_settings(
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(50) UNIQUE,
        description VARCHAR(255),
        sort_type VARCHAR(10) NULL,   -- 'in'|'out'
        min_between_in_out INT,
        max_between_in_out INT,
        gap_between_pairs INT,
        cycle_days INT,
        days_in_month INT,
        cycle_end_time TIME,
        remove_prev_night TINYINT(1),
        calc_from TIME,
        calc_to TIME,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )

Ghi chú:
- Repository chỉ làm SQL thuần.
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class DeclareTimeRepository:
    def list_items(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, code, description, sort_type, min_between_in_out, max_between_in_out, "
            "gap_between_pairs, cycle_days, days_in_month, cycle_end_time, remove_prev_night, "
            "calc_from, calc_to "
            "FROM declare_time_settings ORDER BY id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_items declare_time_settings")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT id, code, description, sort_type, min_between_in_out, max_between_in_out, "
            "gap_between_pairs, cycle_days, days_in_month, cycle_end_time, remove_prev_night, "
            "calc_from, calc_to "
            "FROM declare_time_settings WHERE id = %s LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(item_id),))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi get_item declare_time_settings")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_item(self, data: dict[str, Any]) -> int:
        query = (
            "INSERT INTO declare_time_settings (code, description, sort_type, min_between_in_out, max_between_in_out, "
            "gap_between_pairs, cycle_days, days_in_month, cycle_end_time, remove_prev_night, calc_from, calc_to) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        data.get("code"),
                        data.get("description"),
                        data.get("sort_type"),
                        data.get("min_between_in_out"),
                        data.get("max_between_in_out"),
                        data.get("gap_between_pairs"),
                        data.get("cycle_days"),
                        data.get("days_in_month"),
                        data.get("cycle_end_time"),
                        data.get("remove_prev_night"),
                        data.get("calc_from"),
                        data.get("calc_to"),
                    ),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_item declare_time_settings")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_item(self, item_id: int, data: dict[str, Any]) -> int:
        query = (
            "UPDATE declare_time_settings SET code=%s, description=%s, sort_type=%s, min_between_in_out=%s, "
            "max_between_in_out=%s, gap_between_pairs=%s, cycle_days=%s, days_in_month=%s, cycle_end_time=%s, "
            "remove_prev_night=%s, calc_from=%s, calc_to=%s WHERE id=%s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        data.get("code"),
                        data.get("description"),
                        data.get("sort_type"),
                        data.get("min_between_in_out"),
                        data.get("max_between_in_out"),
                        data.get("gap_between_pairs"),
                        data.get("cycle_days"),
                        data.get("days_in_month"),
                        data.get("cycle_end_time"),
                        data.get("remove_prev_night"),
                        data.get("calc_from"),
                        data.get("calc_to"),
                        int(item_id),
                    ),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_item declare_time_settings")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_item(self, item_id: int) -> int:
        query = "DELETE FROM declare_time_settings WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(item_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_item declare_time_settings")
            raise
        finally:
            if cursor is not None:
                cursor.close()
