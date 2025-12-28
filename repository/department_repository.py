"""repository.department_repository

Repository layer: SQL thuần cho bảng departments (cây phòng ban).

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


class DepartmentRepository:
    """SQL CRUD cho bảng departments."""

    def list_departments(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, parent_id, department_name, department_note "
            "FROM departments ORDER BY id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_departments")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_department(self, department_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT id, parent_id, department_name, department_note "
            "FROM departments WHERE id = %s LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(department_id),))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi get_department")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_department(
        self,
        department_name: str,
        parent_id: int | None,
        department_note: str | None,
    ) -> int:
        query = (
            "INSERT INTO departments (parent_id, department_name, department_note) "
            "VALUES (%s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (parent_id, department_name, department_note))
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_department")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_department(
        self,
        department_id: int,
        department_name: str,
        parent_id: int | None,
        department_note: str | None,
    ) -> int:
        query = (
            "UPDATE departments "
            "SET parent_id = %s, department_name = %s, department_note = %s "
            "WHERE id = %s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (parent_id, department_name, department_note, int(department_id)),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_department")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_department(self, department_id: int) -> int:
        query = "DELETE FROM departments WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(department_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_department")
            raise
        finally:
            if cursor is not None:
                cursor.close()
