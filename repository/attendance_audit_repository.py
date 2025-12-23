"""repository.attendance_audit_repository

SQL layer cho bảng attendance_audit.

Bảng này dùng để UI (Shift Attendance - MainContent2) gọi lại dữ liệu đã tổng hợp từ DB.
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class AttendanceAuditRepository:
    TABLE = "attendance_audit"

    def upsert_from_download_rows(self, rows: list[dict[str, Any]]) -> int:
        """Upsert audit rows directly from DownloadAttendanceService built rows.

        - Inserts if not exists.
        - Updates existing rows only when import_locked = 0.
        """

        if not rows:
            return 0

        query = (
            f"INSERT INTO {self.TABLE} ("
            "attendance_code, device_no, device_id, device_name, "
            "employee_id, employee_code, full_name, work_date, weekday, "
            "in_1, out_1, in_2, out_2, in_3, out_3, "
            "late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
            "tc1, tc2, tc3, total"
            ") VALUES ("
            "%s, %s, %s, %s, "
            "(SELECT e.id FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), "
            "COALESCE((SELECT e.employee_code FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), %s), "
            "COALESCE((SELECT COALESCE(NULLIF(e.full_name,''), NULLIF(e.name_on_mcc,'')) FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), %s, ''), "
            "%s, %s, "
            "%s, %s, %s, %s, %s, %s, "
            "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, "
            "NULL, NULL, NULL, NULL"
            ") ON DUPLICATE KEY UPDATE "
            "employee_id = IF(import_locked = 1, employee_id, VALUES(employee_id)), "
            "employee_code = IF(import_locked = 1, employee_code, VALUES(employee_code)), "
            "full_name = IF(import_locked = 1, full_name, VALUES(full_name)), "
            "weekday = IF(import_locked = 1, weekday, VALUES(weekday)), "
            "in_1 = IF(import_locked = 1, in_1, VALUES(in_1)), "
            "out_1 = IF(import_locked = 1, out_1, VALUES(out_1)), "
            "in_2 = IF(import_locked = 1, in_2, VALUES(in_2)), "
            "out_2 = IF(import_locked = 1, out_2, VALUES(out_2)), "
            "in_3 = IF(import_locked = 1, in_3, VALUES(in_3)), "
            "out_3 = IF(import_locked = 1, out_3, VALUES(out_3)), "
            "device_id = IF(import_locked = 1, device_id, VALUES(device_id)), "
            "device_name = IF(import_locked = 1, device_name, VALUES(device_name))"
        )

        def weekday_label_from_iso(d: str) -> str:
            try:
                # 0=Mon .. 6=Sun
                w = __import__("datetime").date.fromisoformat(str(d)).weekday()
                return (
                    "Thứ 2"
                    if w == 0
                    else (
                        "Thứ 3"
                        if w == 1
                        else (
                            "Thứ 4"
                            if w == 2
                            else (
                                "Thứ 5"
                                if w == 3
                                else (
                                    "Thứ 6"
                                    if w == 4
                                    else "Thứ 7" if w == 5 else "Chủ nhật"
                                )
                            )
                        )
                    )
                )
            except Exception:
                return ""

        params: list[tuple[Any, ...]] = []
        for r in rows:
            attendance_code = str(r.get("attendance_code") or "").strip()
            work_date = str(r.get("work_date") or "").strip()
            name_on_mcc = str(r.get("name_on_mcc") or "").strip()

            params.append(
                (
                    attendance_code,
                    int(r.get("device_no") or 0),
                    (
                        int(r.get("device_id") or 0)
                        if r.get("device_id") is not None
                        else None
                    ),
                    str(r.get("device_name") or ""),
                    # employee_id lookup
                    attendance_code,
                    attendance_code,
                    # employee_code lookup
                    attendance_code,
                    attendance_code,
                    attendance_code,
                    # full_name lookup
                    attendance_code,
                    attendance_code,
                    name_on_mcc,
                    # work_date / weekday
                    work_date,
                    weekday_label_from_iso(work_date),
                    # times
                    r.get("time_in_1"),
                    r.get("time_out_1"),
                    r.get("time_in_2"),
                    r.get("time_out_2"),
                    r.get("time_in_3"),
                    r.get("time_out_3"),
                )
            )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.executemany(query, params)
                conn.commit()
                return int(cursor.rowcount or 0)
        except Exception:
            logger.exception("Lỗi upsert attendance_audit từ dữ liệu tải")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_rows(
        self,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        employee_id: int | None = None,
        attendance_code: str | None = None,
        employee_ids: list[int] | None = None,
        attendance_codes: list[str] | None = None,
        department_id: int | None = None,
        title_id: int | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []

        if from_date:
            where.append("work_date >= %s")
            params.append(str(from_date))
        if to_date:
            where.append("work_date <= %s")
            params.append(str(to_date))

        ac = str(attendance_code or "").strip()

        # Normalize list filters
        ids: list[int] = []
        for v in employee_ids or []:
            try:
                ids.append(int(v))
            except Exception:
                continue
        codes: list[str] = [str(s or "").strip() for s in (attendance_codes or [])]
        codes = [s for s in codes if s]

        if employee_id is not None:
            ids.append(int(employee_id))
        if ac:
            codes.append(ac)

        ids = list(dict.fromkeys(ids))
        codes = list(dict.fromkeys(codes))

        if ids or codes:
            parts: list[str] = []
            if ids:
                parts.append("a.employee_id IN (" + ",".join(["%s"] * len(ids)) + ")")
                params.extend(ids)
            if codes:
                parts.append(
                    "a.attendance_code IN (" + ",".join(["%s"] * len(codes)) + ")"
                )
                params.extend(codes)
            if parts:
                where.append("(" + " OR ".join(parts) + ")")

        # Department/title filters (only apply when provided)
        # Use employees join via either employee_id or attendance_code mapping.
        join_sql = (
            " LEFT JOIN hr_attendance.employees e "
            "   ON (e.id = a.employee_id OR e.mcc_code = a.attendance_code OR e.employee_code = a.attendance_code) "
        )
        if department_id is not None:
            where.append("e.department_id = %s")
            params.append(int(department_id))
        if title_id is not None:
            where.append("e.title_id = %s")
            params.append(int(title_id))

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        query = (
            "SELECT "
            "a.employee_code, a.full_name, a.work_date AS date, a.weekday, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.late, a.early, a.hours, a.work, a.`leave`, a.hours_plus, a.work_plus, a.leave_plus, "
            "a.tc1, a.tc2, a.tc3, a.total "
            f"FROM {self.TABLE} a"
            f"{join_sql}"
            f"{where_sql} "
            "ORDER BY a.work_date ASC, a.employee_code ASC, a.id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list attendance_audit")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def sync_from_attendance_raw(
        self,
        *,
        from_date: str,
        to_date: str,
        device_no: int | None = None,
    ) -> int:
        """Copy attendance_raw -> attendance_audit for a date range (optionally 1 device).

        Idempotent: uses INSERT .. ON DUPLICATE KEY UPDATE based on
        (attendance_code, work_date, device_no).
        """

        where: list[str] = ["ar.work_date >= %s", "ar.work_date <= %s"]
        params: list[Any] = [str(from_date), str(to_date)]
        if device_no is not None:
            where.append("ar.device_no = %s")
            params.append(int(device_no))
        where_sql = " AND ".join(where)

        # Vietnamese weekday label
        weekday_case = (
            "CASE DAYOFWEEK(ar.work_date) "
            "WHEN 1 THEN 'Chủ nhật' "
            "WHEN 2 THEN 'Thứ 2' "
            "WHEN 3 THEN 'Thứ 3' "
            "WHEN 4 THEN 'Thứ 4' "
            "WHEN 5 THEN 'Thứ 5' "
            "WHEN 6 THEN 'Thứ 6' "
            "WHEN 7 THEN 'Thứ 7' "
            "END"
        )

        query = (
            f"INSERT INTO {self.TABLE} ("
            "attendance_code, device_no, device_id, device_name, "
            "employee_id, employee_code, full_name, work_date, weekday, "
            "in_1, out_1, in_2, out_2, in_3, out_3, "
            "late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
            "tc1, tc2, tc3, total"
            ") "
            "SELECT "
            "ar.attendance_code, ar.device_no, ar.device_id, ar.device_name, "
            "e.id AS employee_id, "
            "COALESCE(e.employee_code, ar.attendance_code) AS employee_code, "
            "COALESCE(NULLIF(e.full_name,''), NULLIF(e.name_on_mcc,''), NULLIF(ar.name_on_mcc,''), '') AS full_name, "
            "ar.work_date, "
            f"{weekday_case} AS weekday, "
            "ar.time_in_1, ar.time_out_1, ar.time_in_2, ar.time_out_2, ar.time_in_3, ar.time_out_3, "
            "NULL AS late, NULL AS early, "
            "NULL AS hours, NULL AS work, NULL AS `leave`, "
            "NULL AS hours_plus, NULL AS work_plus, NULL AS leave_plus, "
            "NULL AS tc1, NULL AS tc2, NULL AS tc3, NULL AS total "
            "FROM hr_attendance.attendance_raw ar "
            "LEFT JOIN hr_attendance.employees e "
            "  ON (e.mcc_code = ar.attendance_code OR e.employee_code = ar.attendance_code) "
            f"WHERE {where_sql} "
            "ON DUPLICATE KEY UPDATE "
            "employee_id = IF(import_locked = 1, employee_id, VALUES(employee_id)), "
            "employee_code = IF(import_locked = 1, employee_code, VALUES(employee_code)), "
            "full_name = IF(import_locked = 1, full_name, VALUES(full_name)), "
            "weekday = IF(import_locked = 1, weekday, VALUES(weekday)), "
            "in_1 = IF(import_locked = 1, in_1, VALUES(in_1)), "
            "out_1 = IF(import_locked = 1, out_1, VALUES(out_1)), "
            "in_2 = IF(import_locked = 1, in_2, VALUES(in_2)), "
            "out_2 = IF(import_locked = 1, out_2, VALUES(out_2)), "
            "in_3 = IF(import_locked = 1, in_3, VALUES(in_3)), "
            "out_3 = IF(import_locked = 1, out_3, VALUES(out_3)), "
            "device_id = IF(import_locked = 1, device_id, VALUES(device_id)), "
            "device_name = IF(import_locked = 1, device_name, VALUES(device_name))"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, tuple(params))
                conn.commit()
                return int(cursor.rowcount or 0)
        except Exception:
            logger.exception("Lỗi sync attendance_raw -> attendance_audit")
            raise
        finally:
            if cursor is not None:
                cursor.close()
