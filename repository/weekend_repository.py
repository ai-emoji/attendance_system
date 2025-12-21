"""repository.weekend_repository

Repository layer: SQL thuần cho bảng weekend_settings.

Quy ước:
- Lưu theo dạng nhiều dòng (giống absence_symbols)
- Mỗi dòng có day_name (Thứ 2..Chủ nhật) và is_weekend
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class WeekendRepository:
    TABLE = "weekend_settings"

    def list_rows(self) -> list[dict[str, Any]]:
        query = "SELECT id, day_name, is_weekend " f"FROM {self.TABLE} ORDER BY id ASC"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_rows")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_rows(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        query = (
            f"INSERT INTO {self.TABLE} (day_name, is_weekend) "
            "VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE is_weekend = VALUES(is_weekend)"
        )

        params = [
            (
                str(r.get("day_name") or "").strip(),
                int(r.get("is_weekend") or 0),
            )
            for r in rows
        ]

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.executemany(query, params)
                conn.commit()
        except Exception:
            logger.exception("Lỗi upsert_rows")
            raise
        finally:
            if cursor is not None:
                cursor.close()
