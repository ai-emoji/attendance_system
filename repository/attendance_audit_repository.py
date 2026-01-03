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

    def has_download_attendance_rows(
        self,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        device_no: int | None = None,
    ) -> bool:
        """Return True if attendance_audit_YYYY already has any rows for the filter."""

        where: list[str] = []
        params: list[Any] = []

        if from_date:
            where.append("a.work_date >= %s")
            params.append(str(from_date))
        if to_date:
            where.append("a.work_date <= %s")
            params.append(str(to_date))
        if device_no is not None:
            where.append("a.device_no = %s")
            params.append(int(device_no))

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        years = Database.years_between(from_date, to_date)
        if not years:
            try:
                years = [int(__import__("datetime").date.today().year)]
            except Exception:
                years = []

        def _from_sql_for_years(conn) -> str:
            tables: list[str] = []
            for y in years:
                tables.append(Database.ensure_year_table(conn, self.TABLE, int(y)))
            if not tables:
                return f"{self.TABLE} a"
            if len(tables) == 1:
                return f"{tables[0]} a"
            union = " UNION ALL ".join([f"SELECT * FROM {t}" for t in tables])
            return f"({union}) a"

        query_tpl = "SELECT 1 FROM {FROM_SQL}" + where_sql + " LIMIT 1"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                from_sql = _from_sql_for_years(conn)
                query = query_tpl.replace("{FROM_SQL}", from_sql)
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return row is not None
        except Exception:
            logger.exception("Lỗi has_download_attendance_rows (attendance_audit)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def has_any_row_each_day(
        self,
        *,
        from_date: str,
        to_date: str,
        device_no: int | None = None,
    ) -> bool:
        """Return True if audit contains at least one row for every day in [from_date, to_date].

        This is used to decide whether we can skip device connection.
        It's intentionally conservative: if any day has zero rows, return False.
        """

        # Compute expected day count
        try:
            d0 = __import__("datetime").date.fromisoformat(str(from_date))
            d1 = __import__("datetime").date.fromisoformat(str(to_date))
        except Exception:
            return False
        if d0 > d1:
            d0, d1 = d1, d0
        expected = int((d1 - d0).days) + 1
        if expected <= 0:
            return False

        where: list[str] = ["a.work_date >= %s", "a.work_date <= %s"]
        params: list[Any] = [str(d0.isoformat()), str(d1.isoformat())]
        if device_no is not None:
            where.append("a.device_no = %s")
            params.append(int(device_no))
        where_sql = " WHERE " + " AND ".join(where)

        years = Database.years_between(d0, d1)
        if not years:
            years = [int(d0.year)]

        def _from_sql_for_years(conn) -> str:
            tables: list[str] = []
            for y in years:
                tables.append(Database.ensure_year_table(conn, self.TABLE, int(y)))
            if not tables:
                return f"{self.TABLE} a"
            if len(tables) == 1:
                return f"{tables[0]} a"
            union = " UNION ALL ".join([f"SELECT * FROM {t}" for t in tables])
            return f"({union}) a"

        query_tpl = (
            "SELECT COUNT(DISTINCT a.work_date) AS n FROM {FROM_SQL}" + where_sql
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                from_sql = _from_sql_for_years(conn)
                query = query_tpl.replace("{FROM_SQL}", from_sql)
                cursor.execute(query, tuple(params))
                row = cursor.fetchone() or {}
                try:
                    n = int(row.get("n") or 0)
                except Exception:
                    n = 0
                return n >= expected
        except Exception:
            logger.exception("Lỗi has_any_row_each_day (attendance_audit)")
            # Best-effort: if check fails, do not skip download.
            return False
        finally:
            if cursor is not None:
                cursor.close()

    def list_download_attendance_rows(
        self,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        device_no: int | None = None,
    ) -> list[dict[str, Any]]:
        """List rows for the Download Attendance screen.

        Returns keys compatible with DownloadAttendanceService:
        - attendance_code, full_name, work_date, in_1..out_3, device_no, device_name

        Notes:
        - Reads from attendance_audit_YYYY (union across years when needed).
        - Does NOT synthesize missing days; missing days should be persisted (if desired)
          during the download/save step.
        """

        where: list[str] = []
        params: list[Any] = []

        if from_date:
            where.append("a.work_date >= %s")
            params.append(str(from_date))
        if to_date:
            where.append("a.work_date <= %s")
            params.append(str(to_date))
        if device_no is not None:
            where.append("a.device_no = %s")
            params.append(int(device_no))

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        years = Database.years_between(from_date, to_date)
        if not years:
            # If no range is provided, default to current year only (avoid scanning all years).
            try:
                years = [int(__import__("datetime").date.today().year)]
            except Exception:
                years = []

        def _from_sql_for_years(conn) -> str:
            # Build per-year SELECTs so we can join attendance_raw_YYYY to get name_on_mcc.
            selects: list[str] = []
            for y in years:
                audit_t = Database.ensure_year_table(conn, self.TABLE, int(y))
                raw_t = Database.ensure_year_table(conn, "attendance_raw", int(y))
                selects.append(
                    "SELECT "
                    "a.id, a.attendance_code, a.full_name, "
                    "COALESCE(NULLIF(ar.name_on_mcc,''), NULLIF(e.name_on_mcc,''), '') AS name_on_mcc, "
                    "a.work_date, a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
                    "a.device_no, a.device_name "
                    f"FROM {audit_t} a "
                    f"LEFT JOIN {raw_t} ar ON (ar.attendance_code = a.attendance_code AND ar.work_date = a.work_date AND ar.device_no = a.device_no) "
                    "LEFT JOIN hr_attendance.employees e ON (e.mcc_code = a.attendance_code OR e.employee_code = a.attendance_code)"
                )

            if not selects:
                # Fallback (best-effort): base table without yearly join.
                return (
                    "(SELECT "
                    "a.id, a.attendance_code, a.full_name, '' AS name_on_mcc, "
                    "a.work_date, a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
                    "a.device_no, a.device_name "
                    f"FROM {self.TABLE} a) a"
                )

            union = " UNION ALL ".join(selects)
            return f"({union}) a"

        query_tpl = (
            "SELECT "
            "a.attendance_code, "
            "a.full_name, "
            "a.name_on_mcc, "
            "a.work_date, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.device_no, a.device_name, a.id "
            "FROM {FROM_SQL}"
            f"{where_sql} "
            "ORDER BY a.work_date ASC, a.attendance_code ASC, a.id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                from_sql = _from_sql_for_years(conn)
                query = query_tpl.replace("{FROM_SQL}", from_sql)
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_download_attendance_rows (attendance_audit)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_from_download_rows(
        self,
        rows: list[dict[str, Any]],
        batch_size: int = 500,
        progress_hook=None,
    ) -> int:
        """Upsert audit rows directly from DownloadAttendanceService built rows.

        - Inserts if not exists.
        - Updates existing rows only when import_locked = 0.
        """

        if not rows:
            return 0

        try:
            bs = int(batch_size)
        except Exception:
            bs = 500
        if bs <= 0:
            bs = 500

        def _make_query(table: str) -> str:
            return (
                f"INSERT INTO {table} ("
                "attendance_code, device_no, device_id, device_name, "
                "employee_id, employee_code, full_name, work_date, weekday, "
                "schedule, "
                "in_1, out_1, in_2, out_2, in_3, out_3, "
                "late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                "tc1, tc2, tc3"
                ") VALUES ("
                "%s, %s, %s, %s, "
                "(SELECT e.id FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), "
                "COALESCE((SELECT e.employee_code FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), %s), "
                "COALESCE((SELECT COALESCE(NULLIF(e.full_name,''), NULLIF(e.name_on_mcc,'')) FROM hr_attendance.employees e WHERE (e.mcc_code = %s OR e.employee_code = %s) LIMIT 1), %s, ''), "
                "%s, %s, "
                "NULL, "
                "%s, %s, %s, %s, %s, %s, "
                "NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, "
                "NULL, NULL, NULL"
                ") ON DUPLICATE KEY UPDATE "
                "employee_id = IF(import_locked = 1, employee_id, VALUES(employee_id)), "
                "employee_code = IF(import_locked = 1, employee_code, VALUES(employee_code)), "
                "full_name = IF(import_locked = 1, full_name, VALUES(full_name)), "
                "weekday = IF(import_locked = 1, weekday, VALUES(weekday)), "
                "in_1 = IF(import_locked = 1, in_1, COALESCE(VALUES(in_1), in_1)), "
                "out_1 = IF(import_locked = 1, out_1, COALESCE(VALUES(out_1), out_1)), "
                "in_2 = IF(import_locked = 1, in_2, COALESCE(VALUES(in_2), in_2)), "
                "out_2 = IF(import_locked = 1, out_2, COALESCE(VALUES(out_2), out_2)), "
                "in_3 = IF(import_locked = 1, in_3, COALESCE(VALUES(in_3), in_3)), "
                "out_3 = IF(import_locked = 1, out_3, COALESCE(VALUES(out_3), out_3)), "
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

        # Group by year
        by_year: dict[int, list[tuple[Any, ...]]] = {}
        for r in rows:
            attendance_code = str(r.get("attendance_code") or "").strip()
            work_date = str(r.get("work_date") or "").strip()
            name_on_mcc = str(r.get("name_on_mcc") or "").strip()

            year = Database._year_from_work_date(work_date)
            if year is None:
                continue

            by_year.setdefault(int(year), []).append(
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

        if not by_year:
            return 0

        cursor = None
        total_rowcount = 0
        done = 0
        total_items = sum(len(v) for v in by_year.values())
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    query = _make_query(table)
                    params = by_year.get(year, [])
                    for i in range(0, len(params), bs):
                        chunk = params[i : i + bs]
                        cursor.executemany(query, chunk)
                        conn.commit()
                        try:
                            total_rowcount += int(cursor.rowcount or 0)
                        except Exception:
                            pass
                        done += len(chunk)
                        if progress_hook is not None:
                            try:
                                progress_hook(min(done, total_items), total_items)
                            except Exception:
                                pass
                return int(total_rowcount)
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

        # Determine year tables to query.
        years = Database.years_between(from_date, to_date)
        if not years:
            try:
                years = [int(__import__("datetime").date.today().year)]
            except Exception:
                years = []

        def _from_sql_for_years(conn) -> str:
            tables: list[str] = []
            for y in years:
                tables.append(Database.ensure_year_table(conn, self.TABLE, int(y)))
            if not tables:
                return f"{self.TABLE} a"
            if len(tables) == 1:
                return f"{tables[0]} a"
            union = " UNION ALL ".join([f"SELECT * FROM {t}" for t in tables])
            return f"({union}) a"

        query_tpl = (
            "SELECT "
            "a.attendance_code, a.employee_code, a.full_name, a.work_date AS date, a.weekday, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.late, a.early, a.hours, a.work, a.`leave`, a.hours_plus, a.work_plus, a.leave_plus, "
            "CASE "
            "  WHEN a.work IS NULL AND a.work_plus IS NULL THEN NULL "
            "  ELSE (COALESCE(a.work, 0) + COALESCE(a.work_plus, 0)) "
            "END AS total, "
            "a.tc1, a.tc2, a.tc3, "
            "COALESCE(("
            "  SELECT s.schedule_name "
            "  FROM hr_attendance.employee_schedule_assignments esa "
            "  JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "  WHERE esa.employee_id = e.id "
            "    AND esa.effective_from <= a.work_date "
            "    AND (esa.effective_to IS NULL OR esa.effective_to >= a.work_date) "
            "  ORDER BY esa.effective_from DESC, esa.id DESC "
            "  LIMIT 1"
            "), a.schedule) AS schedule "
            "FROM {FROM_SQL}"
            f"{join_sql}"
            f"{where_sql} "
            "ORDER BY a.work_date ASC, a.employee_code ASC, a.id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                from_sql = _from_sql_for_years(conn)
                query = query_tpl.replace("{FROM_SQL}", from_sql)
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

        years = Database.years_between(from_date, to_date)
        if not years:
            y0 = Database._year_from_work_date(from_date)
            if y0 is not None:
                years = [int(y0)]

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

        def _make_sync_query(audit_table: str, raw_table: str) -> str:
            return (
                f"INSERT INTO {audit_table} ("
                "attendance_code, device_no, device_id, device_name, "
                "employee_id, employee_code, full_name, work_date, weekday, "
                "schedule, "
                "in_1, out_1, in_2, out_2, in_3, out_3, "
                "late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                "tc1, tc2, tc3"
                ") "
                "SELECT "
                "ar.attendance_code, ar.device_no, ar.device_id, ar.device_name, "
                "e.id AS employee_id, "
                "COALESCE(e.employee_code, ar.attendance_code) AS employee_code, "
                "COALESCE(NULLIF(e.full_name,''), NULLIF(e.name_on_mcc,''), NULLIF(ar.name_on_mcc,''), '') AS full_name, "
                "ar.work_date, "
                f"{weekday_case} AS weekday, "
                "NULL AS schedule, "
                "ar.time_in_1, ar.time_out_1, ar.time_in_2, ar.time_out_2, ar.time_in_3, ar.time_out_3, "
                "NULL AS late, NULL AS early, "
                "NULL AS hours, NULL AS work, NULL AS `leave`, "
                "NULL AS hours_plus, NULL AS work_plus, NULL AS leave_plus, "
                "NULL AS tc1, NULL AS tc2, NULL AS tc3 "
                f"FROM {raw_table} ar "
                "LEFT JOIN hr_attendance.employees e "
                "  ON (e.mcc_code = ar.attendance_code OR e.employee_code = ar.attendance_code) "
                "WHERE {WHERE_SQL} "
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
                total = 0
                for y in years:
                    # Clip date range per year
                    y0 = int(y)
                    start = str(from_date)
                    end = str(to_date)
                    try:
                        if int(y0) != int(
                            Database._year_from_work_date(from_date) or y0
                        ):
                            start = f"{y0}-01-01"
                    except Exception:
                        pass
                    try:
                        if int(y0) != int(Database._year_from_work_date(to_date) or y0):
                            end = f"{y0}-12-31"
                    except Exception:
                        pass

                    where: list[str] = ["ar.work_date >= %s", "ar.work_date <= %s"]
                    params: list[Any] = [str(start), str(end)]
                    if device_no is not None:
                        where.append("ar.device_no = %s")
                        params.append(int(device_no))
                    where_sql = " AND ".join(where)

                    raw_table = Database.ensure_year_table(conn, "attendance_raw", y0)
                    audit_table = Database.ensure_year_table(conn, self.TABLE, y0)
                    query = _make_sync_query(audit_table, raw_table).replace(
                        "{WHERE_SQL}", where_sql
                    )
                    cursor.execute(query, tuple(params))
                    conn.commit()
                    try:
                        total += int(cursor.rowcount or 0)
                    except Exception:
                        pass
                return int(total)
        except Exception:
            logger.exception("Lỗi sync attendance_raw -> attendance_audit")
            raise
        finally:
            if cursor is not None:
                cursor.close()
