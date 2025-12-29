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

    def get_existing_employee_id_date_pairs(
        self, pairs: list[tuple[int, str]]
    ) -> set[tuple[int, str]]:
        """Return set of (employee_id, work_date) that already exist in attendance_audit.

        This is used to avoid creating placeholder rows for days that already have
        any attendance data (even if employee_code is NULL or attendance_code differs).
        """

        cleaned: list[tuple[int, str]] = []
        seen: set[tuple[int, str]] = set()
        for eid, work_date in pairs or []:
            try:
                eid_i = int(eid)
            except Exception:
                continue
            wd = str(work_date or "").strip()
            if eid_i <= 0 or not wd:
                continue
            k = (eid_i, wd)
            if k in seen:
                continue
            seen.add(k)
            cleaned.append(k)

        if not cleaned:
            return set()

        by_year: dict[int, list[tuple[int, str]]] = {}
        for eid_i, wd in cleaned:
            y = Database._year_from_work_date(wd)
            if y is None:
                continue
            by_year.setdefault(int(y), []).append((eid_i, wd))

        out: set[tuple[int, str]] = set()
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
                        "SELECT employee_id, work_date "
                        f"FROM {table} "
                        "WHERE (employee_id, work_date) IN (" + in_sql + ")"
                    )

                    params: list[Any] = []
                    for eid2, wd2 in pairs_y:
                        params.append(int(eid2))
                        params.append(str(wd2))
                    cursor.execute(query, tuple(params))
                    rows = list(cursor.fetchall() or [])
                    for r in rows:
                        try:
                            eid3 = int(r.get("employee_id") or 0)
                            wd3 = str(r.get("work_date") or "").strip()
                            if eid3 > 0 and wd3:
                                out.add((eid3, wd3))
                        except Exception:
                            continue
        except Exception:
            logger.exception("Lỗi get_existing_employee_id_date_pairs")
            raise
        finally:
            if cursor is not None:
                cursor.close()

        return out

    def get_existing_by_attendance_code_date(
        self, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Fetch existing audit rows keyed by (attendance_code, work_date).

        This is needed for legacy data where employee_code may be NULL
        (download/sync writes attendance_code but not always employee_code).
        """

        cleaned: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for att_code, work_date in pairs or []:
            k = (str(att_code or "").strip(), str(work_date or "").strip())
            if not k[0] or not k[1] or k in seen:
                continue
            seen.add(k)
            cleaned.append(k)

        if not cleaned:
            return {}

        by_year: dict[int, list[tuple[str, str]]] = {}
        for att_code, work_date in cleaned:
            y = Database._year_from_work_date(work_date)
            if y is None:
                continue
            by_year.setdefault(int(y), []).append((att_code, work_date))

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
                        "  in_1_symbol, "
                        "  in_1, out_1, in_2, out_2, in_3, out_3, "
                        "  late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                        "  tc1, tc2, tc3, schedule, shift_code, import_locked, updated_at "
                        f"FROM {table} "
                        "WHERE (attendance_code, work_date) IN (" + in_sql + ") "
                        "ORDER BY updated_at DESC, id DESC"
                    )

                    params: list[Any] = []
                    for ac, wd in pairs_y:
                        params.append(ac)
                        params.append(wd)
                    try:
                        cursor.execute(query, tuple(params))
                    except Exception as exc:
                        msg = str(exc)
                        if "in_1_symbol" in msg and "Unknown column" in msg:
                            query2 = (
                                "SELECT "
                                "  attendance_code, device_no, device_id, device_name, "
                                "  employee_id, employee_code, full_name, work_date, weekday, "
                                "  NULL AS in_1_symbol, "
                                "  in_1, out_1, in_2, out_2, in_3, out_3, "
                                "  late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                                "  tc1, tc2, tc3, schedule, shift_code, import_locked, updated_at "
                                f"FROM {table} "
                                "WHERE (attendance_code, work_date) IN ("
                                + in_sql
                                + ") "
                                "ORDER BY updated_at DESC, id DESC"
                            )
                            cursor.execute(query2, tuple(params))
                        else:
                            raise
                    rows.extend(list(cursor.fetchall() or []))
        except Exception:
            logger.exception("Lỗi get_existing_by_attendance_code_date")
            raise
        finally:
            if cursor is not None:
                cursor.close()

        out: dict[tuple[str, str], dict[str, Any]] = {}
        for r in rows:
            k = (
                str(r.get("attendance_code") or "").strip(),
                str(r.get("work_date") or ""),
            )
            if not k[0] or not k[1] or k in out:
                continue
            out[k] = r
        return out

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
                        "  in_1_symbol, "
                        "  in_1, out_1, in_2, out_2, in_3, out_3, "
                        "  late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                        "  tc1, tc2, tc3, schedule, shift_code, import_locked, updated_at "
                        f"FROM {table} "
                        "WHERE (employee_code, work_date) IN (" + in_sql + ") "
                        "ORDER BY updated_at DESC, id DESC"
                    )

                    params: list[Any] = []
                    for ec, wd in pairs_y:
                        params.append(ec)
                        params.append(wd)
                    try:
                        cursor.execute(query, tuple(params))
                    except Exception as exc:
                        msg = str(exc)
                        if "in_1_symbol" in msg and "Unknown column" in msg:
                            query2 = (
                                "SELECT "
                                "  attendance_code, device_no, device_id, device_name, "
                                "  employee_id, employee_code, full_name, work_date, weekday, "
                                "  NULL AS in_1_symbol, "
                                "  in_1, out_1, in_2, out_2, in_3, out_3, "
                                "  late, early, hours, work, `leave`, hours_plus, work_plus, leave_plus, "
                                "  tc1, tc2, tc3, schedule, shift_code, import_locked, updated_at "
                                f"FROM {table} "
                                "WHERE (employee_code, work_date) IN (" + in_sql + ") "
                                "ORDER BY updated_at DESC, id DESC"
                            )
                            cursor.execute(query2, tuple(params))
                        else:
                            raise
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

        def _make_query(
            table: str,
            *,
            include_shift_code: bool,
            include_in_1_symbol: bool,
        ) -> str:
            cols: list[str] = [
                "attendance_code",
                "device_no",
                "device_id",
                "device_name",
                "employee_id",
                "employee_code",
                "full_name",
                "work_date",
                "weekday",
                "schedule",
            ]
            if include_shift_code:
                cols.append("shift_code")
            if include_in_1_symbol:
                cols.append("in_1_symbol")
            cols.extend(
                [
                    "in_1",
                    "out_1",
                    "in_2",
                    "out_2",
                    "in_3",
                    "out_3",
                    "late",
                    "early",
                    "hours",
                    "work",
                    "`leave`",
                    "hours_plus",
                    "work_plus",
                    "leave_plus",
                    "tc1",
                    "tc2",
                    "tc3",
                    "import_locked",
                ]
            )

            values_sql = ",".join(["%s"] * len(cols))

            updates: list[str] = [
                # Protect rows that were imported from Excel (import_locked=1)
                # from being overwritten/unlocked by other sources (import_locked=0).
                # Also: do NOT clear existing values when Excel provides NULL/empty.
                "device_id = IF(import_locked = 1 AND VALUES(import_locked) = 0, device_id, COALESCE(VALUES(device_id), device_id))",
                "device_name = IF(import_locked = 1 AND VALUES(import_locked) = 0, device_name, COALESCE(NULLIF(VALUES(device_name), ''), device_name))",
                "employee_id = IF(import_locked = 1 AND VALUES(import_locked) = 0, employee_id, COALESCE(VALUES(employee_id), employee_id))",
                "employee_code = IF(import_locked = 1 AND VALUES(import_locked) = 0, employee_code, COALESCE(NULLIF(VALUES(employee_code), ''), employee_code))",
                "full_name = IF(import_locked = 1 AND VALUES(import_locked) = 0, full_name, COALESCE(NULLIF(VALUES(full_name), ''), full_name))",
                "weekday = IF(import_locked = 1 AND VALUES(import_locked) = 0, weekday, COALESCE(NULLIF(VALUES(weekday), ''), weekday))",
                "schedule = IF(import_locked = 1 AND VALUES(import_locked) = 0, schedule, COALESCE(NULLIF(VALUES(schedule), ''), schedule))",
            ]

            def _time_update_expr(col: str) -> str:
                # Default behavior: don't clear existing TIME values when import provides NULL.
                # Special case for Excel import: if an explicit in_1_symbol is provided,
                # allow clearing punch columns to NULL (ONLY when the imported row provides
                # no punch times at all) so UI can display the symbol in in_1.
                if include_in_1_symbol:
                    allow_clear = (
                        "(VALUES(import_locked) = 1 "
                        "AND NULLIF(VALUES(in_1_symbol), '') IS NOT NULL "
                        "AND VALUES(in_1) IS NULL AND VALUES(out_1) IS NULL "
                        "AND VALUES(in_2) IS NULL AND VALUES(out_2) IS NULL "
                        "AND VALUES(in_3) IS NULL AND VALUES(out_3) IS NULL)"
                    )
                    return (
                        f"{col} = IF(import_locked = 1 AND VALUES(import_locked) = 0, {col}, "
                        f"IF({allow_clear}, VALUES({col}), COALESCE(VALUES({col}), {col})))"
                    )
                return (
                    f"{col} = IF(import_locked = 1 AND VALUES(import_locked) = 0, {col}, COALESCE(VALUES({col}), {col}))"
                )

            if include_shift_code:
                updates.append(
                    "shift_code = IF(import_locked = 1 AND VALUES(import_locked) = 0, shift_code, COALESCE(NULLIF(VALUES(shift_code), ''), shift_code))"
                )
            if include_in_1_symbol:
                updates.append(
                    "in_1_symbol = IF(import_locked = 1 AND VALUES(import_locked) = 0, in_1_symbol, COALESCE(NULLIF(VALUES(in_1_symbol), ''), in_1_symbol))"
                )
            updates.extend(
                [
                    _time_update_expr("in_1"),
                    _time_update_expr("out_1"),
                    _time_update_expr("in_2"),
                    _time_update_expr("out_2"),
                    _time_update_expr("in_3"),
                    _time_update_expr("out_3"),
                    "late = IF(import_locked = 1 AND VALUES(import_locked) = 0, late, COALESCE(NULLIF(VALUES(late), ''), late))",
                    "early = IF(import_locked = 1 AND VALUES(import_locked) = 0, early, COALESCE(NULLIF(VALUES(early), ''), early))",
                    "hours = IF(import_locked = 1 AND VALUES(import_locked) = 0, hours, COALESCE(VALUES(hours), hours))",
                    "work = IF(import_locked = 1 AND VALUES(import_locked) = 0, work, COALESCE(VALUES(work), work))",
                    "`leave` = IF(import_locked = 1 AND VALUES(import_locked) = 0, `leave`, COALESCE(VALUES(`leave`), `leave`))",
                    "hours_plus = IF(import_locked = 1 AND VALUES(import_locked) = 0, hours_plus, COALESCE(VALUES(hours_plus), hours_plus))",
                    "work_plus = IF(import_locked = 1 AND VALUES(import_locked) = 0, work_plus, COALESCE(VALUES(work_plus), work_plus))",
                    "leave_plus = IF(import_locked = 1 AND VALUES(import_locked) = 0, leave_plus, COALESCE(VALUES(leave_plus), leave_plus))",
                    "tc1 = IF(import_locked = 1 AND VALUES(import_locked) = 0, tc1, COALESCE(NULLIF(VALUES(tc1), ''), tc1))",
                    "tc2 = IF(import_locked = 1 AND VALUES(import_locked) = 0, tc2, COALESCE(NULLIF(VALUES(tc2), ''), tc2))",
                    "tc3 = IF(import_locked = 1 AND VALUES(import_locked) = 0, tc3, COALESCE(NULLIF(VALUES(tc3), ''), tc3))",
                    "import_locked = IF(import_locked = 1, 1, VALUES(import_locked))",
                ]
            )

            return (
                f"INSERT INTO {table} (" + ", ".join(cols) + ") "
                f"VALUES ({values_sql}) "
                "ON DUPLICATE KEY UPDATE " + ", ".join(updates)
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
                    r.get("schedule"),
                    r.get("shift_code"),
                    r.get("in_1_symbol"),
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
                    raw_params = by_year.get(year, [])
                    if not raw_params:
                        continue

                    # Newer schema columns are optional for backward compatibility.
                    include_shift_code = True
                    include_in_1_symbol = True

                    def _project_tuple(t: tuple[Any, ...]) -> tuple[Any, ...]:
                        # base tuple layout:
                        # [..weekday]=8, schedule=9, shift_code=10, in_1_symbol=11, then in_1.., import_locked last
                        out = list(t)
                        if not include_shift_code:
                            # drop shift_code at index 10
                            out.pop(10)
                        if not include_in_1_symbol:
                            # if shift_code dropped, in_1_symbol shifts left by 1
                            idx = 11 if include_shift_code else 10
                            out.pop(idx)
                        return tuple(out)

                    while True:
                        query = _make_query(
                            table,
                            include_shift_code=include_shift_code,
                            include_in_1_symbol=include_in_1_symbol,
                        )
                        params = [_project_tuple(t) for t in raw_params]
                        try:
                            cursor.executemany(query, params)
                            break
                        except Exception as exc:
                            msg = str(exc)
                            if "Unknown column" in msg:
                                if include_in_1_symbol and "in_1_symbol" in msg:
                                    include_in_1_symbol = False
                                    continue
                                if include_shift_code and "shift_code" in msg:
                                    include_shift_code = False
                                    continue
                            raise

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
