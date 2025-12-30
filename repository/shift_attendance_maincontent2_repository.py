"""repository.shift_attendance_maincontent2_repository

Repository SQL cho MainContent2 (Shift Attendance).

Trách nhiệm:
- Chỉ truy vấn dữ liệu từ bảng attendance_audit (và join employees để lọc theo phòng ban/chức vụ).
- Trả về dữ liệu dạng dict để UI/controller render.

Lưu ý:
- Không xử lý nghiệp vụ sắp xếp in/out ở đây (thuộc Service layer).
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class ShiftAttendanceMainContent2Repository:
    TABLE = "attendance_audit"

    def update_import_locked_by_id(
        self,
        items: list[dict[str, Any]],
        *,
        import_locked: int,
    ) -> int:
        """Batch update import_locked by attendance_audit.id.

        Expected keys per item:
        - id (required)
        - work_date or date (required for routing to attendance_audit_YYYY)
        """

        lock_val = 1 if int(import_locked) == 1 else 0

        cleaned: list[dict[str, Any]] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            audit_id = it.get("id")
            if audit_id is None:
                continue
            try:
                aid = int(audit_id)
            except Exception:
                continue

            wd = it.get("work_date")
            if wd is None:
                wd = it.get("date")
            if wd is None:
                continue
            # Normalize date to ISO string
            try:
                if hasattr(wd, "isoformat"):
                    wd_s = wd.isoformat()  # type: ignore[assignment]
                else:
                    wd_s = str(wd).strip()
            except Exception:
                wd_s = str(wd).strip()
            if not wd_s:
                continue

            cleaned.append({"id": aid, "work_date": wd_s})

        if not cleaned:
            return 0

        by_year: dict[int, list[tuple[Any, ...]]] = {}
        legacy: list[tuple[Any, ...]] = []
        for r in cleaned:
            y = Database._year_from_work_date(r.get("work_date"))
            tup = (int(lock_val), int(r["id"]))
            if y is None:
                legacy.append(tup)
            else:
                by_year.setdefault(int(y), []).append(tup)

        sql_tpl = "UPDATE {table} SET import_locked=%s WHERE id=%s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                total_updated = 0

                if legacy:
                    cursor.executemany(sql_tpl.format(table=self.TABLE), legacy)
                    total_updated += int(cursor.rowcount or 0)

                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    payload = by_year.get(year, [])
                    if not payload:
                        continue
                    cursor.executemany(sql_tpl.format(table=table), payload)
                    total_updated += int(cursor.rowcount or 0)

                try:
                    conn.commit()
                except Exception:
                    pass
                return int(total_updated)
        except Exception:
            logger.exception("Lỗi update_import_locked_by_id")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_computed_fields_by_id(
        self,
        items: list[dict[str, Any]],
        *,
        allow_import_locked: bool = False,
    ) -> int:
        """Batch update computed fields by attendance_audit.id.

        Expected keys per item:
        - id (required)
        - work_date or date (required for routing to attendance_audit_YYYY)
        - late, early, hours, work, hours_plus, work_plus,
          tc1, tc2, tc3, total, schedule, shift_code

        Notes:
        - This method intentionally does NOT update in/out punch columns.
        - For compatibility with older DB schemas, it will fall back when
          columns like total/shift_code are missing.
        """

        cleaned: list[dict[str, Any]] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            audit_id = it.get("id")
            if audit_id is None:
                continue
            try:
                aid = int(audit_id)
            except Exception:
                continue

            wd = it.get("work_date")
            if wd is None:
                wd = it.get("date")
            wd_s = str(wd).strip() if wd is not None else ""
            if not wd_s:
                continue

            cleaned.append(
                {
                    "id": aid,
                    "work_date": wd_s,
                    "late": it.get("late"),
                    "early": it.get("early"),
                    "hours": it.get("hours"),
                    "work": it.get("work"),
                    "hours_plus": it.get("hours_plus"),
                    "work_plus": it.get("work_plus"),
                    "tc1": it.get("tc1"),
                    "tc2": it.get("tc2"),
                    "tc3": it.get("tc3"),
                    "total": it.get("total"),
                    "schedule": it.get("schedule"),
                    "shift_code": it.get("shift_code"),
                }
            )

        if not cleaned:
            return 0

        def _norm_str(v: Any, *, keep_empty: bool = False) -> str | None:
            if v is None:
                return None
            s = str(v).strip()
            if s:
                return s
            return "" if bool(keep_empty) else None

        def _norm_num(v: Any) -> Any:
            if v is None:
                return None
            # Keep numeric types as-is; let mysql connector handle conversion.
            if isinstance(v, (int, float)):
                return v
            s = str(v).strip()
            if not s:
                return None
            try:
                # Avoid importing Decimal here; keep dependency surface small.
                return float(s)
            except Exception:
                return None

        # Group updates by year table.
        by_year: dict[int, list[tuple[Any, ...]]] = {}
        legacy: list[tuple[Any, ...]] = []

        for r in cleaned:
            y = Database._year_from_work_date(r.get("work_date"))
            tup = (
                _norm_str(r.get("late"), keep_empty=True),
                _norm_str(r.get("early"), keep_empty=True),
                _norm_num(r.get("hours")),
                _norm_num(r.get("work")),
                _norm_num(r.get("hours_plus")),
                _norm_num(r.get("work_plus")),
                _norm_str(r.get("tc1")),
                _norm_str(r.get("tc2")),
                _norm_str(r.get("tc3")),
                _norm_num(r.get("total")),
                _norm_str(r.get("schedule")),
                _norm_str(r.get("shift_code")),
                int(r["id"]),
            )
            if y is None:
                legacy.append(tup)
            else:
                by_year.setdefault(int(y), []).append(tup)

        # Prefer full schema update (total + shift_code). Fall back if missing.
        where_locked_sql = (
            "" if bool(allow_import_locked) else " AND COALESCE(import_locked, 0) = 0"
        )

        update_full_tpl = (
            "UPDATE {table} SET "
            "late=%s, early=%s, hours=%s, work=%s, "
            "hours_plus=%s, work_plus=%s, "
            "tc1=%s, tc2=%s, tc3=%s, "
            "total=%s, schedule=%s, shift_code=%s "
            "WHERE id=%s" + where_locked_sql
        )

        update_no_shift_tpl = (
            "UPDATE {table} SET "
            "late=%s, early=%s, hours=%s, work=%s, "
            "hours_plus=%s, work_plus=%s, "
            "tc1=%s, tc2=%s, tc3=%s, "
            "total=%s, schedule=%s "
            "WHERE id=%s" + where_locked_sql
        )

        update_no_total_tpl = (
            "UPDATE {table} SET "
            "late=%s, early=%s, hours=%s, work=%s, "
            "hours_plus=%s, work_plus=%s, "
            "tc1=%s, tc2=%s, tc3=%s, "
            "schedule=%s, shift_code=%s "
            "WHERE id=%s" + where_locked_sql
        )

        update_min_tpl = (
            "UPDATE {table} SET "
            "late=%s, early=%s, hours=%s, work=%s, "
            "hours_plus=%s, work_plus=%s, "
            "tc1=%s, tc2=%s, tc3=%s, "
            "schedule=%s "
            "WHERE id=%s" + where_locked_sql
        )

        def _exec_many(cursor, table: str, payload: list[tuple[Any, ...]]) -> int:
            if not payload:
                return 0

            def _try_add_column(col: str) -> bool:
                """Best-effort add missing columns for older yearly tables."""

                col_norm = str(col or "").strip().lower()
                if not col_norm:
                    return False
                try:
                    if col_norm == "shift_code":
                        cursor.execute(
                            f"ALTER TABLE `{table}` ADD COLUMN shift_code VARCHAR(255) NULL"
                        )
                        return True
                    if col_norm == "total":
                        cursor.execute(
                            f"ALTER TABLE `{table}` ADD COLUMN total DECIMAL(10,2) NULL"
                        )
                        return True
                except Exception:
                    return False
                return False

            # Try in decreasing schema richness.
            try:
                cursor.executemany(update_full_tpl.format(table=table), payload)
                return int(cursor.rowcount or 0)
            except Exception as exc1:
                msg1 = str(exc1)
                # total missing OR shift_code missing
                try:
                    if "shift_code" in msg1 and "Unknown column" in msg1:
                        # Attempt auto-migrate: add shift_code and retry full update once.
                        if _try_add_column("shift_code"):
                            try:
                                cursor.executemany(
                                    update_full_tpl.format(table=table), payload
                                )
                                return int(cursor.rowcount or 0)
                            except Exception:
                                pass
                        # Drop shift_code (still keep total)
                        payload2 = [
                            (
                                p[0],
                                p[1],
                                p[2],
                                p[3],
                                p[4],
                                p[5],
                                p[6],
                                p[7],
                                p[8],
                                p[9],
                                p[10],
                                p[12],
                            )
                            for p in payload
                        ]
                        cursor.executemany(
                            update_no_shift_tpl.format(table=table), payload2
                        )
                        return int(cursor.rowcount or 0)

                    if "total" in msg1 and "Unknown column" in msg1:
                        # Attempt auto-migrate: add total and retry full update once.
                        if _try_add_column("total"):
                            try:
                                cursor.executemany(
                                    update_full_tpl.format(table=table), payload
                                )
                                return int(cursor.rowcount or 0)
                            except Exception:
                                pass
                        # Drop total (still keep shift_code)
                        payload2 = [
                            (
                                p[0],
                                p[1],
                                p[2],
                                p[3],
                                p[4],
                                p[5],
                                p[6],
                                p[7],
                                p[8],
                                p[10],
                                p[11],
                                p[12],
                            )
                            for p in payload
                        ]
                        cursor.executemany(
                            update_no_total_tpl.format(table=table), payload2
                        )
                        return int(cursor.rowcount or 0)

                    # If both missing or another schema mismatch, fall back to minimal.
                    payload2 = [
                        (
                            p[0],
                            p[1],
                            p[2],
                            p[3],
                            p[4],
                            p[5],
                            p[6],
                            p[7],
                            p[8],
                            p[10],
                            p[12],
                        )
                        for p in payload
                    ]
                    cursor.executemany(update_min_tpl.format(table=table), payload2)
                    return int(cursor.rowcount or 0)
                except Exception:
                    # Final fallback failed.
                    raise

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                total_updated = 0

                if legacy:
                    total_updated += _exec_many(cursor, self.TABLE, legacy)

                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    total_updated += _exec_many(cursor, table, by_year.get(year, []))
                try:
                    conn.commit()
                except Exception:
                    pass
                return int(total_updated)
        except Exception:
            logger.exception("Lỗi update_computed_fields_by_id")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_shift_codes(self, items: list[tuple[Any, ...]]) -> int:
        """Batch update shift_code by attendance_audit.id.

        items:
        - list of (audit_id, shift_code)
        - or list of (audit_id, work_date, shift_code)
          (work_date used to route to attendance_audit_YYYY)
        """

        cleaned: list[tuple[int, str | None, str | None]] = []
        for it in items or []:
            try:
                audit_id = it[0]
                aid = int(audit_id)
            except Exception:
                continue

            work_date = None
            code = None
            try:
                if len(it) >= 3:
                    work_date = it[1]
                    code = it[2]
                else:
                    code = it[1]
            except Exception:
                continue

            if code is None:
                cleaned.append((aid, None, str(work_date) if work_date else None))
                continue

            c = str(code or "").strip()
            cleaned.append(
                (aid, c if c else None, str(work_date) if work_date else None)
            )

        if not cleaned:
            return 0

        # Group updates by year table.
        by_year: dict[int, list[tuple[str | None, int]]] = {}
        legacy: list[tuple[str | None, int]] = []
        for aid, code, work_date in cleaned:
            y = Database._year_from_work_date(work_date)
            if y is None:
                legacy.append((code, aid))
            else:
                by_year.setdefault(int(y), []).append((code, aid))

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                total = 0

                # Backward-compat: update base table if year not provided/parsable.
                if legacy:
                    try:
                        query0 = (
                            f"UPDATE {self.TABLE} SET shift_code = %s "
                            "WHERE id = %s AND COALESCE(import_locked, 0) = 0"
                        )
                        cursor.executemany(query0, legacy)
                    except Exception as exc:
                        msg = str(exc)
                        if "import_locked" in msg and "Unknown column" in msg:
                            query0 = (
                                f"UPDATE {self.TABLE} SET shift_code = %s WHERE id = %s"
                            )
                            cursor.executemany(query0, legacy)
                        else:
                            raise
                    try:
                        total += int(cursor.rowcount or 0)
                    except Exception:
                        pass

                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self.TABLE, int(year))
                    try:
                        query = (
                            f"UPDATE {table} SET shift_code = %s "
                            "WHERE id = %s AND COALESCE(import_locked, 0) = 0"
                        )
                        cursor.executemany(query, by_year.get(year, []))
                    except Exception as exc:
                        msg = str(exc)
                        if "import_locked" in msg and "Unknown column" in msg:
                            query = f"UPDATE {table} SET shift_code = %s WHERE id = %s"
                            cursor.executemany(query, by_year.get(year, []))
                        else:
                            raise
                    try:
                        total += int(cursor.rowcount or 0)
                    except Exception:
                        pass
                try:
                    conn.commit()
                except Exception:
                    pass
                try:
                    return int(total)
                except Exception:
                    return 0
        except Exception:
            logger.exception("Lỗi update_shift_codes")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def list_holiday_dates(
        self,
        *,
        from_date: str | None,
        to_date: str | None,
    ) -> set[str]:
        if not from_date or not to_date:
            return set()

        query = (
            "SELECT holiday_date FROM hr_attendance.holidays "
            "WHERE holiday_date BETWEEN %s AND %s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (str(from_date), str(to_date)))
                rows = list(cursor.fetchall() or [])
                out: set[str] = set()
                for r in rows:
                    v = r.get("holiday_date")
                    if v is None:
                        continue
                    out.add(str(v))
                return out
        except Exception:
            logger.exception("Lỗi list_holiday_dates")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_schedule_id_mode_by_names(
        self, schedule_names: list[str]
    ) -> dict[str, dict[str, Any]]:
        names: list[str] = []
        for n in schedule_names or []:
            s = str(n or "").strip()
            if s:
                try:
                    s = unicodedata.normalize("NFC", s)
                except Exception:
                    pass
            if s:
                names.append(s)
        names = list(dict.fromkeys(names))
        if not names:
            return {}

        placeholders = ",".join(["%s"] * len(names))
        query = (
            "SELECT id, schedule_name, in_out_mode, "
            "ignore_absent_sat, ignore_absent_sun, ignore_absent_holiday, "
            "holiday_count_as_work, day_is_out_time "
            "FROM hr_attendance.arrange_schedules "
            f"WHERE schedule_name IN ({placeholders})"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(names))
                rows = list(cursor.fetchall() or [])
                out: dict[str, dict[str, Any]] = {}
                for r in rows:
                    key = str(r.get("schedule_name") or "").strip()
                    if not key:
                        continue
                    out[key] = {
                        "schedule_id": r.get("id"),
                        "in_out_mode": r.get("in_out_mode"),
                        "ignore_absent_sat": r.get("ignore_absent_sat"),
                        "ignore_absent_sun": r.get("ignore_absent_sun"),
                        "ignore_absent_holiday": r.get("ignore_absent_holiday"),
                        "holiday_count_as_work": r.get("holiday_count_as_work"),
                        "day_is_out_time": r.get("day_is_out_time"),
                    }
                return out
        except Exception:
            logger.exception("Lỗi get_schedule_id_mode_by_names")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_schedule_details_by_schedule_ids(
        self, schedule_ids: list[int]
    ) -> dict[tuple[int, str], dict[str, Any]]:
        ids: list[int] = []
        for v in schedule_ids or []:
            try:
                ids.append(int(v))
            except Exception:
                continue
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {}

        placeholders = ",".join(["%s"] * len(ids))
        query = (
            "SELECT schedule_id, day_key, day_name, day_order, "
            "shift1_id, shift2_id, shift3_id, shift4_id, shift5_id "
            "FROM hr_attendance.arrange_schedule_details "
            f"WHERE schedule_id IN ({placeholders})"
        )

        # Fallback for newer schema using unlimited shifts table.
        # We pivot first 5 positions into shift1_id..shift5_id.
        query_shifts = (
            "SELECT schedule_id, day_key, "
            "MAX(CASE WHEN position = 1 THEN shift_id END) AS shift1_id, "
            "MAX(CASE WHEN position = 2 THEN shift_id END) AS shift2_id, "
            "MAX(CASE WHEN position = 3 THEN shift_id END) AS shift3_id, "
            "MAX(CASE WHEN position = 4 THEN shift_id END) AS shift4_id, "
            "MAX(CASE WHEN position = 5 THEN shift_id END) AS shift5_id "
            "FROM hr_attendance.arrange_schedule_detail_shifts "
            f"WHERE schedule_id IN ({placeholders}) "
            "GROUP BY schedule_id, day_key"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, tuple(ids))
                rows = list(cursor.fetchall() or [])
                out: dict[tuple[int, str], dict[str, Any]] = {}
                for r in rows:
                    sid = r.get("schedule_id")
                    day_key = str(r.get("day_key") or "").strip()
                    if sid is None or not day_key:
                        continue
                    try:
                        out[(int(sid), day_key)] = r
                    except Exception:
                        continue

                # Merge pivoted shifts (if any). This supports installs where
                # arrange_schedule_details.shift*_id are empty but detail_shifts exists.
                try:
                    cursor.execute(query_shifts, tuple(ids))
                    rows2 = list(cursor.fetchall() or [])
                except Exception:
                    rows2 = []

                for r2 in rows2:
                    sid2 = r2.get("schedule_id")
                    day_key2 = str(r2.get("day_key") or "").strip()
                    if sid2 is None or not day_key2:
                        continue

                    try:
                        key = (int(sid2), day_key2)
                    except Exception:
                        continue

                    if key not in out:
                        out[key] = {
                            "schedule_id": sid2,
                            "day_key": day_key2,
                            "day_name": None,
                            "day_order": None,
                            "shift1_id": r2.get("shift1_id"),
                            "shift2_id": r2.get("shift2_id"),
                            "shift3_id": r2.get("shift3_id"),
                            "shift4_id": r2.get("shift4_id"),
                            "shift5_id": r2.get("shift5_id"),
                        }
                        continue

                    # Fill missing shift*_id from pivoted table
                    dst = out[key]
                    for k in (
                        "shift1_id",
                        "shift2_id",
                        "shift3_id",
                        "shift4_id",
                        "shift5_id",
                    ):
                        if dst.get(k) is None and r2.get(k) is not None:
                            dst[k] = r2.get(k)

                return out
        except Exception:
            logger.exception("Lỗi get_schedule_details_by_schedule_ids")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_work_shifts_by_ids(self, shift_ids: list[int]) -> dict[int, dict[str, Any]]:
        ids: list[int] = []
        for v in shift_ids or []:
            try:
                ids.append(int(v))
            except Exception:
                continue
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {}

        placeholders = ",".join(["%s"] * len(ids))
        query = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end, overtime_round_minutes "
            "FROM hr_attendance.work_shifts "
            f"WHERE id IN ({placeholders})"
        )
        query_legacy = (
            "SELECT id, shift_code, time_in, time_out, lunch_start, lunch_end, "
            "total_minutes, work_count, in_window_start, in_window_end, "
            "out_window_start, out_window_end "
            "FROM hr_attendance.work_shifts "
            f"WHERE id IN ({placeholders})"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                try:
                    cursor.execute(query, tuple(ids))
                    rows = list(cursor.fetchall() or [])
                except Exception as exc:
                    msg = str(exc)
                    if "overtime_round_minutes" in msg and "Unknown column" in msg:
                        cursor.execute(query_legacy, tuple(ids))
                        rows = list(cursor.fetchall() or [])
                        for r in rows:
                            try:
                                r.setdefault("overtime_round_minutes", 0)
                            except Exception:
                                pass
                    else:
                        raise

                out: dict[int, dict[str, Any]] = {}
                for r in rows:
                    sid = r.get("id")
                    if sid is None:
                        continue
                    try:
                        out[int(sid)] = r
                    except Exception:
                        continue
                return out
        except Exception:
            logger.exception("Lỗi get_work_shifts_by_ids")
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
        employment_status: str | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []

        if from_date:
            where.append("a.work_date >= %s")
            params.append(str(from_date))
        if to_date:
            where.append("a.work_date <= %s")
            params.append(str(to_date))

        ac = str(attendance_code or "").strip()

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
                # Backward-compat: some data sources store the key in employee_code
                # instead of attendance_code. Match both.
                parts.append(
                    "(a.attendance_code IN ("
                    + ",".join(["%s"] * len(codes))
                    + ") OR a.employee_code IN ("
                    + ",".join(["%s"] * len(codes))
                    + "))"
                )
                params.extend(codes)
                params.extend(codes)
            if parts:
                where.append("(" + " OR ".join(parts) + ")")

        join_sql = (
            " LEFT JOIN hr_attendance.employees e "
            "   ON ("
            "        e.id = a.employee_id "
            "     OR e.mcc_code = a.attendance_code "
            "     OR e.mcc_code = a.employee_code "
            "     OR e.employee_code = a.attendance_code "
            "     OR e.employee_code = a.employee_code"
            "   ) "
        )
        if department_id is not None:
            where.append("e.department_id = %s")
            params.append(int(department_id))
        if title_id is not None:
            where.append("e.title_id = %s")
            params.append(int(title_id))

        # Employment status filter (codes: '1'/'2'/'3')
        st = str(employment_status or "").strip()
        if st:
            if st == "1":
                # Practical default: treat NULL/blank (or unmatched employee join) as "Đi làm".
                where.append(
                    "(e.employment_status = %s OR e.employment_status IS NULL OR TRIM(e.employment_status) = '')"
                )
                params.append("1")
            else:
                where.append("e.employment_status = %s")
                params.append(st)

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

        query_tpl = (
            "SELECT "
            "a.id, "
            "a.attendance_code, a.employee_code, a.full_name, a.work_date AS date, a.weekday, "
            "a.import_locked, "
            "a.in_1_symbol, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.late, a.early, a.hours, a.work, a.`leave`, a.`leave` AS kh, a.hours_plus, a.work_plus, a.leave_plus, "
            "CASE "
            "  WHEN a.work IS NULL AND a.work_plus IS NULL THEN NULL "
            "  ELSE (COALESCE(a.work, 0) + COALESCE(a.work_plus, 0)) "
            "END AS total, "
            "a.tc1, a.tc2, a.tc3, "
            "a.shift_code AS shift_code_db, "
            "CASE "
            "  WHEN COALESCE(a.import_locked, 0) = 1 THEN a.schedule "
            "  ELSE COALESCE(("
            "    SELECT s.schedule_name "
            "    FROM hr_attendance.employee_schedule_assignments esa "
            "    JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "    WHERE esa.employee_id = e.id "
            "      AND esa.effective_from <= a.work_date "
            "      AND (esa.effective_to IS NULL OR esa.effective_to >= a.work_date) "
            "    ORDER BY esa.effective_from DESC, esa.id DESC "
            "    LIMIT 1"
            "  ), a.schedule) "
            "END AS schedule "
            "FROM {FROM_SQL}"
            f"{join_sql}"
            f"{where_sql} "
            "ORDER BY a.work_date ASC, a.employee_code ASC, a.id ASC"
        )

        # Backward-compat: some installs/tables don't have shift_code yet.
        # Keep in_1_symbol so imported symbols (OFF/V/Lễ) can still display.
        query_no_shift_tpl = (
            "SELECT "
            "a.id, "
            "a.attendance_code, a.employee_code, a.full_name, a.work_date AS date, a.weekday, "
            "a.import_locked, "
            "a.in_1_symbol, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.late, a.early, a.hours, a.work, a.`leave`, a.`leave` AS kh, a.hours_plus, a.work_plus, a.leave_plus, "
            "CASE "
            "  WHEN a.work IS NULL AND a.work_plus IS NULL THEN NULL "
            "  ELSE (COALESCE(a.work, 0) + COALESCE(a.work_plus, 0)) "
            "END AS total, "
            "a.tc1, a.tc2, a.tc3, "
            "NULL AS shift_code_db, "
            "CASE "
            "  WHEN COALESCE(a.import_locked, 0) = 1 THEN a.schedule "
            "  ELSE COALESCE(("
            "    SELECT s.schedule_name "
            "    FROM hr_attendance.employee_schedule_assignments esa "
            "    JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "    WHERE esa.employee_id = e.id "
            "      AND esa.effective_from <= a.work_date "
            "      AND (esa.effective_to IS NULL OR esa.effective_to >= a.work_date) "
            "    ORDER BY esa.effective_from DESC, esa.id DESC "
            "    LIMIT 1"
            "  ), a.schedule) "
            "END AS schedule "
            "FROM {FROM_SQL}"
            f"{join_sql}"
            f"{where_sql} "
            "ORDER BY a.work_date ASC, a.employee_code ASC, a.id ASC"
        )

        query_legacy_tpl = (
            "SELECT "
            "a.id, "
            "a.attendance_code, a.employee_code, a.full_name, a.work_date AS date, a.weekday, "
            "a.import_locked, "
            "NULL AS in_1_symbol, "
            "a.in_1, a.out_1, a.in_2, a.out_2, a.in_3, a.out_3, "
            "a.late, a.early, a.hours, a.work, a.`leave`, a.`leave` AS kh, a.hours_plus, a.work_plus, a.leave_plus, "
            "CASE "
            "  WHEN a.work IS NULL AND a.work_plus IS NULL THEN NULL "
            "  ELSE (COALESCE(a.work, 0) + COALESCE(a.work_plus, 0)) "
            "END AS total, "
            "a.tc1, a.tc2, a.tc3, "
            "CASE "
            "  WHEN COALESCE(a.import_locked, 0) = 1 THEN a.schedule "
            "  ELSE COALESCE(("
            "    SELECT s.schedule_name "
            "    FROM hr_attendance.employee_schedule_assignments esa "
            "    JOIN hr_attendance.arrange_schedules s ON s.id = esa.schedule_id "
            "    WHERE esa.employee_id = e.id "
            "      AND esa.effective_from <= a.work_date "
            "      AND (esa.effective_to IS NULL OR esa.effective_to >= a.work_date) "
            "    ORDER BY esa.effective_from DESC, esa.id DESC "
            "    LIMIT 1"
            "  ), a.schedule) "
            "END AS schedule "
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
                query_no_shift = query_no_shift_tpl.replace("{FROM_SQL}", from_sql)
                query_legacy = query_legacy_tpl.replace("{FROM_SQL}", from_sql)
                try:
                    cursor.execute(query, tuple(params))
                except Exception as exc:
                    msg = str(exc)
                    if "Unknown column" in msg:
                        # If shift_code is missing, retry a query that preserves in_1_symbol.
                        if "shift_code" in msg:
                            try:
                                cursor.execute(query_no_shift, tuple(params))
                            except Exception:
                                # Fall back to legacy (drops in_1_symbol) only if needed.
                                cursor.execute(query_legacy, tuple(params))
                        elif "in_1_symbol" in msg:
                            cursor.execute(query_legacy, tuple(params))
                        else:
                            raise
                    else:
                        raise

                rows = list(cursor.fetchall() or [])
                for r in rows:
                    r.setdefault("shift_code_db", None)
                    r.setdefault("import_locked", 0)
                    r.setdefault("in_1_symbol", None)
                return rows
        except Exception:
            logger.exception("Lỗi list_rows (shift_attendance_maincontent2)")
            raise
        finally:
            if cursor is not None:
                cursor.close()
