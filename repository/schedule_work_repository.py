"""repository.schedule_work_repository

Repository layer: SQL thuần cho màn "Sắp xếp lịch Làm việc".

Hiện tại UI mới dựng phần khung, nên repository cung cấp tối thiểu:
- Load cây Phòng ban / Chức danh
- Tìm nhân viên theo bộ lọc
- Bảng gán lịch trình cho nhân viên (employee_schedule_assignments)

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


class ScheduleWorkRepository:
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
            logger.exception("Lỗi list_schedules (schedule_work)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

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
            logger.exception("Lỗi list_departments (schedule_work)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_titles(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, department_id, title_name " "FROM job_titles ORDER BY id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_titles (schedule_work)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_employees(
        self,
        search_by: str | None,
        search_text: str | None,
        department_id: int | None,
        title_id: int | None,
    ) -> list[dict[str, Any]]:
        """List employees for Schedule Work.

        search_by:
        - employee_code
        - employee_name
        """

        where: list[str] = []
        params: list[Any] = []

        st = (search_text or "").strip()
        sb = (search_by or "").strip()

        if st:
            if sb == "employee_name":
                where.append("full_name LIKE %s")
                params.append(f"%{st}%")
            else:
                where.append("employee_code LIKE %s")
                params.append(f"%{st}%")

        if department_id is not None:
            where.append("e.department_id = %s")
            params.append(int(department_id))

        if title_id is not None:
            where.append("e.title_id = %s")
            params.append(int(title_id))

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        query = (
            "SELECT "
            "e.id, e.employee_code, e.mcc_code, e.full_name, e.department_id, e.title_id, "
            "COALESCE(d.department_name, '') AS department_name, "
            "COALESCE(jt.title_name, '') AS title_name "
            "FROM employees e "
            "LEFT JOIN departments d ON d.id = e.department_id "
            "LEFT JOIN job_titles jt ON jt.id = e.title_id "
            + where_sql
            + " ORDER BY e.id DESC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(params))
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_employees (schedule_work)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_employee_schedule_assignment(
        self,
        employee_id: int,
        schedule_id: int,
        effective_from: str,
        effective_to: str | None,
        note: str | None,
    ) -> int:
        """Upsert assignment by UNIQUE(employee_id, effective_from)."""

        query = (
            "INSERT INTO hr_attendance.employee_schedule_assignments "
            "(employee_id, schedule_id, effective_from, effective_to, note) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "schedule_id = VALUES(schedule_id), "
            "effective_to = VALUES(effective_to), "
            "note = VALUES(note), "
            "updated_at = CURRENT_TIMESTAMP"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        int(employee_id),
                        int(schedule_id),
                        str(effective_from),
                        effective_to,
                        note,
                    ),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi upsert_employee_schedule_assignment")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_assignments_by_employee_id(self, employee_id: int) -> int:
        query = (
            "DELETE FROM hr_attendance.employee_schedule_assignments "
            "WHERE employee_id = %s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(employee_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_assignments_by_employee_id")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_employee_schedule_name_map(
        self,
        *,
        employee_ids: list[int],
        on_date: str,
    ) -> dict[int, str]:
        ids: list[int] = []
        for x in employee_ids or []:
            try:
                v = int(x)
            except Exception:
                continue
            if v > 0:
                ids.append(v)
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {}

        placeholders = ",".join(["%s"] * len(ids))
        query = (
            "SELECT esa.employee_id, s.schedule_name "
            "FROM hr_attendance.employee_schedule_assignments esa "
            "JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "JOIN ("
            "  SELECT employee_id, MAX(effective_from) AS max_from "
            "  FROM hr_attendance.employee_schedule_assignments "
            f"  WHERE employee_id IN ({placeholders}) "
            "    AND effective_from <= %s "
            "    AND (effective_to IS NULL OR effective_to >= %s) "
            "  GROUP BY employee_id"
            ") t ON t.employee_id = esa.employee_id AND t.max_from = esa.effective_from"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(ids + [str(on_date), str(on_date)]))
                rows = list(cursor.fetchall() or [])
                out: dict[int, str] = {}
                for r in rows:
                    try:
                        out[int(r.get("employee_id"))] = str(
                            r.get("schedule_name") or ""
                        )
                    except Exception:
                        continue
                return out
        except Exception:
            logger.exception("Lỗi get_employee_schedule_name_map")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_employee_schedule_assignments(
        self, employee_id: int
    ) -> list[dict[str, Any]]:
        """List all schedule assignments for a single employee (used by TempScheduleContent)."""

        query = (
            "SELECT esa.id, e.employee_code, e.full_name, "
            "esa.employee_id, esa.schedule_id, esa.effective_from, esa.effective_to, "
            "COALESCE(s.schedule_name, '') AS schedule_name "
            "FROM hr_attendance.employee_schedule_assignments esa "
            "JOIN hr_attendance.employees e ON e.id = esa.employee_id "
            "JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "WHERE esa.employee_id = %s "
            "ORDER BY esa.effective_from DESC, esa.id DESC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(employee_id),))
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_employee_schedule_assignments")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_temp_schedule_assignments(
        self, employee_ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """List temporary schedule assignments.

        Convention: temp rows are assignments that have an end date (effective_to IS NOT NULL).
        """

        where: list[str] = ["esa.effective_to IS NOT NULL"]
        params: list[Any] = []

        ids: list[int] = []
        for x in employee_ids or []:
            try:
                v = int(x)
            except Exception:
                continue
            if v > 0:
                ids.append(v)
        ids = list(dict.fromkeys(ids))

        if ids:
            placeholders = ",".join(["%s"] * len(ids))
            where.append(f"esa.employee_id IN ({placeholders})")
            params.extend(ids)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        query = (
            "SELECT esa.id, e.employee_code, e.full_name, "
            "esa.employee_id, esa.schedule_id, esa.effective_from, esa.effective_to, "
            "COALESCE(s.schedule_name, '') AS schedule_name "
            "FROM hr_attendance.employee_schedule_assignments esa "
            "JOIN hr_attendance.employees e ON e.id = esa.employee_id "
            "JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            + where_sql
            + " ORDER BY esa.effective_from DESC, esa.id DESC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(params))
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_temp_schedule_assignments")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_employee_active_schedule_assignment(
        self,
        *,
        employee_id: int,
        on_date: str,
    ) -> dict[str, Any] | None:
        """Get the active assignment at a given date (if any)."""

        query = (
            "SELECT esa.id, esa.employee_id, esa.schedule_id, esa.effective_from, esa.effective_to, "
            "COALESCE(s.schedule_name, '') AS schedule_name "
            "FROM hr_attendance.employee_schedule_assignments esa "
            "JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "WHERE esa.employee_id = %s "
            "  AND esa.effective_from <= %s "
            "  AND (esa.effective_to IS NULL OR esa.effective_to >= %s) "
            "ORDER BY esa.effective_from DESC, esa.id DESC "
            "LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(employee_id), str(on_date), str(on_date)))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception:
            logger.exception("Lỗi get_employee_active_schedule_assignment")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_assignment_id_by_employee_from(
        self,
        *,
        employee_id: int,
        effective_from: str,
    ) -> int | None:
        query = (
            "SELECT id FROM hr_attendance.employee_schedule_assignments "
            "WHERE employee_id = %s AND effective_from = %s "
            "LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(employee_id), str(effective_from)))
                row = cursor.fetchone()
                if not row:
                    return None
                try:
                    return int(row.get("id"))
                except Exception:
                    return None
        except Exception:
            logger.exception("Lỗi get_assignment_id_by_employee_from")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_assignment_by_id(self, assignment_id: int) -> int:
        query = "DELETE FROM hr_attendance.employee_schedule_assignments WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(assignment_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_assignment_by_id")
            raise
        finally:
            if cursor is not None:
                cursor.close()
