"""repository.title_repository

Repository layer: SQL thuần cho bảng job_titles.

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


class TitleRepository:
    """SQL CRUD cho bảng job_titles."""

    def list_titles(self) -> list[dict[str, Any]]:
        query = "SELECT id, title_name FROM job_titles ORDER BY id ASC"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_titles")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_title(self, title_id: int) -> dict[str, Any] | None:
        query = "SELECT id, title_name FROM job_titles WHERE id = %s LIMIT 1"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(title_id),))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi get_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_title(self, title_name: str) -> int:
        query = "INSERT INTO job_titles (title_name) VALUES (%s)"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (title_name,))
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_title(self, title_id: int, title_name: str) -> int:
        query = "UPDATE job_titles SET title_name = %s WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (title_name, int(title_id)))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_title(self, title_id: int) -> int:
        query = "DELETE FROM job_titles WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(title_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()
