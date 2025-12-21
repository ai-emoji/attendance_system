"""repository.absence_symbol_repository

Repository layer: SQL thuần cho bảng absence_symbols.

Quy ước:
- code cố định A01..A15 (UI hiển thị sẵn)
- Không validate, không nghiệp vụ
- Dùng query parameter %s (MySQL)
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class AbsenceSymbolRepository:
    TABLE = "absence_symbols"

    def list_symbols(self) -> list[dict[str, Any]]:
        query = (
            f"SELECT id, code, description, symbol, is_used, is_paid "
            f"FROM {self.TABLE} ORDER BY code ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_symbols")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_symbol(
        self,
        code: str,
        description: str,
        symbol: str,
        is_used: int,
        is_paid: int,
    ) -> None:
        query = (
            f"INSERT INTO {self.TABLE} (code, description, symbol, is_used, is_paid) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "description = VALUES(description), "
            "symbol = VALUES(symbol), "
            "is_used = VALUES(is_used), "
            "is_paid = VALUES(is_paid)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        str(code),
                        str(description or ""),
                        str(symbol or ""),
                        int(is_used),
                        int(is_paid),
                    ),
                )
                conn.commit()
        except Exception:
            logger.exception("Lỗi upsert_symbol")
            raise
        finally:
            if cursor is not None:
                cursor.close()
