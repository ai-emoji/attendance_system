"""repository.attendance_symbol_repository

Repository layer: SQL thuần cho bảng attendance_symbols.

Quy ước:
- Lưu theo dạng nhiều dòng (giống absence_symbols)
- Mỗi dòng có code (C01..C10), description, symbol, is_visible
- Không validate, không nghiệp vụ
- Dùng query parameter %s (MySQL)
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class AttendanceSymbolRepository:
    TABLE = "attendance_symbols"

    def list_rows(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, code, description, symbol, is_visible "
            f"FROM {self.TABLE} ORDER BY code ASC"
        )

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
            f"INSERT INTO {self.TABLE} (code, description, symbol, is_visible) "
            "VALUES (%s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "description = VALUES(description), "
            "symbol = VALUES(symbol), "
            "is_visible = VALUES(is_visible)"
        )

        params = [
            (
                str(r.get("code") or "").strip(),
                str(r.get("description") or ""),
                str(r.get("symbol") or ""),
                int(r.get("is_visible") or 0),
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
