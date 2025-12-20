"""repository.holiday_repository

Repository layer: SQL thuần cho bảng holidays.
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


def _is_duplicate_key(exc: Exception) -> bool:
    try:
        import mysql.connector  # type: ignore

        return (
            isinstance(exc, mysql.connector.Error)
            and getattr(exc, "errno", None) == 1062
        )
    except Exception:
        return "Duplicate" in str(exc) or "1062" in str(exc)


class HolidayRepository:
    def list_holidays(self) -> list[dict[str, Any]]:
        query = "SELECT id, holiday_date, holiday_info FROM holidays ORDER BY holiday_date ASC, id ASC"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_holidays")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_holiday(self, holiday_date: str, holiday_info: str) -> int:
        query = "INSERT INTO holidays (holiday_date, holiday_info) VALUES (%s, %s)"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (holiday_date, holiday_info))
                conn.commit()
                return int(cursor.lastrowid)
        except Exception as exc:
            if _is_duplicate_key(exc):
                logger.warning(
                    "create_holiday duplicate: date=%s info=%s",
                    holiday_date,
                    holiday_info,
                )
                raise
            logger.exception("Lỗi create_holiday")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_holiday(
        self, holiday_id: int, holiday_date: str, holiday_info: str
    ) -> int:
        query = "UPDATE holidays SET holiday_date = %s, holiday_info = %s WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (holiday_date, holiday_info, int(holiday_id)))
                conn.commit()
                return int(cursor.rowcount)
        except Exception as exc:
            if _is_duplicate_key(exc):
                logger.warning(
                    "update_holiday duplicate: id=%s date=%s info=%s",
                    holiday_id,
                    holiday_date,
                    holiday_info,
                )
                raise
            logger.exception("Lỗi update_holiday")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_holiday(self, holiday_id: int) -> int:
        query = "DELETE FROM holidays WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(holiday_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_holiday")
            raise
        finally:
            if cursor is not None:
                cursor.close()
