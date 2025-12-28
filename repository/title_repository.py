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


def _is_duplicate_key(exc: Exception) -> bool:
    try:
        import mysql.connector  # type: ignore

        return (
            isinstance(exc, mysql.connector.Error)
            and getattr(exc, "errno", None) == 1062
        )
    except Exception:
        return "Duplicate" in str(exc) or "1062" in str(exc)


class TitleRepository:
    """SQL CRUD cho bảng job_titles."""

    _schema_checked: bool = False
    _has_department_id: bool = False

    def ensure_schema(self) -> None:
        """Ensure optional columns exist (backward compatible migration).

        Adds:
        - department_id (nullable) for linking titles to departments
        """

        if TitleRepository._schema_checked:
            return

        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'job_titles'
                      AND COLUMN_NAME IN ('department_id')
                    """
                )
                cols = {
                    str(r.get("COLUMN_NAME") or "").strip().lower()
                    for r in (cursor.fetchall() or [])
                }
                TitleRepository._has_department_id = "department_id" in cols

                alters: list[str] = []
                if not TitleRepository._has_department_id:
                    alters.append("ADD COLUMN department_id INT NULL AFTER title_name")

                if alters:
                    sql = "ALTER TABLE job_titles " + ", ".join(alters)
                    cur2 = Database.get_cursor(conn, dictionary=False)
                    cur2.execute(sql)
                    conn.commit()
                    TitleRepository._has_department_id = True

                # Best-effort index (ignore if already exists or no perms)
                try:
                    if TitleRepository._has_department_id:
                        cur3 = Database.get_cursor(conn, dictionary=False)
                        cur3.execute(
                            "CREATE INDEX idx_job_titles_department_id ON job_titles (department_id)"
                        )
                        conn.commit()
                except Exception:
                    pass
        except Exception:
            # Keep the app usable if no INFORMATION_SCHEMA/ALTER permissions.
            TitleRepository._has_department_id = False

        TitleRepository._schema_checked = True

    def list_titles(self) -> list[dict[str, Any]]:
        self.ensure_schema()
        if TitleRepository._has_department_id:
            query = "SELECT id, title_name, department_id FROM job_titles ORDER BY id ASC"
        else:
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
        self.ensure_schema()
        if TitleRepository._has_department_id:
            query = (
                "SELECT id, title_name, department_id "
                "FROM job_titles WHERE id = %s LIMIT 1"
            )
        else:
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

    def create_title(self, title_name: str, department_id: int | None = None) -> int:
        self.ensure_schema()
        if TitleRepository._has_department_id:
            query = "INSERT INTO job_titles (title_name, department_id) VALUES (%s, %s)"
        else:
            query = "INSERT INTO job_titles (title_name) VALUES (%s)"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                if TitleRepository._has_department_id:
                    cursor.execute(
                        query,
                        (title_name, int(department_id) if department_id else None),
                    )
                else:
                    cursor.execute(query, (title_name,))
                conn.commit()
                return int(cursor.lastrowid)
        except Exception as exc:
            # Duplicate là case nghiệp vụ dự kiến (service sẽ trả message thân thiện)
            if _is_duplicate_key(exc):
                logger.warning("create_title duplicate: %s", title_name)
                raise
            logger.exception("Lỗi create_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_title(
        self, title_id: int, title_name: str, department_id: int | None = None
    ) -> int:
        self.ensure_schema()
        if TitleRepository._has_department_id:
            query = "UPDATE job_titles SET title_name = %s, department_id = %s WHERE id = %s"
        else:
            query = "UPDATE job_titles SET title_name = %s WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                if TitleRepository._has_department_id:
                    cursor.execute(
                        query,
                        (
                            title_name,
                            int(department_id) if department_id else None,
                            int(title_id),
                        ),
                    )
                else:
                    cursor.execute(query, (title_name, int(title_id)))
                conn.commit()
                return int(cursor.rowcount)
        except Exception as exc:
            if _is_duplicate_key(exc):
                logger.warning(
                    "update_title duplicate: id=%s name=%s", title_id, title_name
                )
                raise
            logger.exception("Lỗi update_title")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_title(self, title_id: int) -> int:
        self.ensure_schema()
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
