"""repository.import_shift_attendance_repository

Repository layer cho tính năng "Import dữ liệu chấm công" (attendance_audit).

Trách nhiệm:
- Đọc dữ liệu hiện có trong attendance_audit theo (employee_code, work_date)
- Map nhân viên theo employee_code/mcc_code
- Upsert các dòng import vào attendance_audit

Ghi chú overwrite/skip:
- Controller/Service quyết định row nào cần upsert; repository chỉ thực thi SQL.
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class ImportShiftAttendanceRepository:
    TABLE = "attendance_audit"

    def get_existing_by_employee_code_date(
        self, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Fetch existing audit rows keyed by (employee_code, work_date).

        Returns dict[(employee_code, work_date)] -> row dict.
        If there are multiple rows (multiple device_no) for the same pair,
        prefers the most recently updated.
        """

        cleaned: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for emp_code, work_date in pairs or []:
            k = (str(emp_code or "").strip(), str(work_date or "").strip())
            if not k[0] or not k[1] or k in seen:
                continue
            seen.add(k)
            cleaned.append(k)

        if not cleaned:
            return {}

        # Group by year => attendance_audit_YYYY
        by_year: dict[int, list[tuple[str, str]]] = {}
        for emp_code, work_date in cleaned:
            y = Database._year_from_work_date(work_date)
            if y is None:
                continue
            by_year.setdefault(int(y), []).append((emp_code, work_date))

        rows: list[dict[str, Any]] = []
        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                for year in sorted(by_year.keys()):
                    pairs_y = by_year.get(year, [])
                    if not pairs_y:
                        continue

                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    in_sql = ",".join(["(%s,%s)"] * len(pairs_y))
                    query = (
                        "SELECT "
                        "  attendance_code, device_no, device_id, device_name, "
                        "  employee_id, employee_code, full_name, work_date, weekday, "
                        "  in_1, out_1, in_2, out_2, in_3, out_3, "
                        "  late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                        "  tc1, tc2, tc3, schedule, import_locked, updated_at "
                        f"FROM {table} "
                        "WHERE (employee_code, work_date) IN (" + in_sql + ") "
                        "ORDER BY updated_at DESC, id DESC"
                    )

                    params: list[Any] = []
                    for ec, wd in pairs_y:
                        params.append(ec)
                        params.append(wd)
                    cursor.execute(query, tuple(params))
                    rows.extend(list(cursor.fetchall() or []))
        except Exception:
            logger.exception("Lỗi get_existing_by_employee_code_date")
            raise
        finally:
            if cursor is not None:
                cursor.close()

        out: dict[tuple[str, str], dict[str, Any]] = {}
        for r in rows:
            k = (
                str(r.get("employee_code") or "").strip(),
                str(r.get("work_date") or ""),
            )
            if not k[0] or not k[1] or k in out:
                continue
            out[k] = r
        return out

    def get_employees_by_codes(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        """Lookup employees by employee_code or mcc_code.

        Returns mapping for both employee_code and mcc_code (lowercased key) -> employee dict.
        """

        cleaned: list[str] = []
        seen: set[str] = set()
        for s in codes or []:
            key = str(s or "").strip()
            if not key:
                continue
            key_low = key.lower()
            if key_low in seen:
                continue
            seen.add(key_low)
            cleaned.append(key)

        if not cleaned:
            return {}

        in_sql = ",".join(["%s"] * len(cleaned))
        query = (
            "SELECT id, employee_code, mcc_code, full_name, name_on_mcc "
            "FROM hr_attendance.employees "
            f"WHERE employee_code IN ({in_sql}) OR mcc_code IN ({in_sql})"
        )
        params: list[Any] = list(cleaned) + list(cleaned)

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(params))
                rows = list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi get_employees_by_codes")
            raise
        finally:
            if cursor is not None:
                cursor.close()

        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            ec = str(r.get("employee_code") or "").strip()
            mc = str(r.get("mcc_code") or "").strip()
            if ec:
                out[ec.lower()] = r
            if mc:
                out[mc.lower()] = r
        return out

    def upsert_import_rows(self, rows: list[dict[str, Any]]) -> int:
        """Upsert a batch of rows into attendance_audit.

        Expected each row contains all required audit fields including:
        attendance_code, device_no, work_date.
        """

        if not rows:
            return 0

        def _make_query(table: str) -> str:
            return (
            f"INSERT INTO {table} ("
            "attendance_code, device_no, device_id, device_name, "
            "employee_id, employee_code, full_name, work_date, weekday, "
            "schedule, "
            "in_1, out_1, in_2, out_2, in_3, out_3, "
            "late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
            "tc1, tc2, tc3, import_locked"
            ") VALUES ("
            "%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,"
            "%s,"
            "%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s"
            ") ON DUPLICATE KEY UPDATE "
            "device_id = VALUES(device_id), "
            "device_name = VALUES(device_name), "
            "employee_id = VALUES(employee_id), "
            "employee_code = VALUES(employee_code), "
            "full_name = VALUES(full_name), "
            "weekday = VALUES(weekday), "
            "schedule = VALUES(schedule), "
            "in_1 = VALUES(in_1), out_1 = VALUES(out_1), "
            "in_2 = VALUES(in_2), out_2 = VALUES(out_2), "
            "in_3 = VALUES(in_3), out_3 = VALUES(out_3), "
            "late = VALUES(late), early = VALUES(early), "
            "hours = VALUES(hours), work = VALUES(work), `leave` = VALUES(`leave`), "
            "hours_plus = VALUES(hours_plus), work_plus = VALUES(work_plus), leave_plus = VALUES(leave_plus), "
            "tc1 = VALUES(tc1), tc2 = VALUES(tc2), tc3 = VALUES(tc3), "
            "import_locked = VALUES(import_locked)"
            )

        by_year: dict[int, list[tuple[Any, ...]]] = {}
        for r in rows:
            y = Database._year_from_work_date(r.get("work_date"))
            if y is None:
                continue
            by_year.setdefault(int(y), []).append(
                (
                    r.get("attendance_code"),
                    int(r.get("device_no") or 0),
                    r.get("device_id"),
                    r.get("device_name"),
                    r.get("employee_id"),
                    r.get("employee_code"),
                    r.get("full_name"),
                    r.get("work_date"),
                    r.get("weekday"),
                    r.get("in_1"),
                    r.get("out_1"),
                    r.get("in_2"),
                    r.get("out_2"),
                    r.get("in_3"),
                    r.get("out_3"),
                    r.get("late"),
                    r.get("early"),
                    r.get("hours"),
                    r.get("work"),
                    r.get("leave"),
                    r.get("hours_plus"),
                    r.get("work_plus"),
                    r.get("leave_plus"),
                    r.get("tc1"),
                    r.get("tc2"),
                    r.get("tc3"),
                    r.get("schedule"),
                    int(r.get("import_locked") or 0),
                )
            )

        if not by_year:
            return 0

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                total = 0
                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    query = _make_query(table)
                    params = by_year.get(year, [])
                    if not params:
                        continue
                    cursor.executemany(query, params)
                    conn.commit()
                    try:
                        total += int(cursor.rowcount or 0)
                    except Exception:
                        pass
                return int(total)
        except Exception:
            logger.exception("Lỗi upsert_import_rows")
            raise
        finally:
            if cursor is not None:
                cursor.close()
