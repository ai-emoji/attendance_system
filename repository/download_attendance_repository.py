"""repository.download_attendance_repository

SQL layer cho:
- download_attendance (bảng tạm trong phiên)
- attendance_raw (bảng lưu thô lâu dài)

Yêu cầu nghiệp vụ:
- Sau khi tải, ghi vào download_attendance
- Đồng thời sao chép (upsert) vào attendance_raw
- Nếu trùng các trường khóa (attendance_code, work_date, device_no) thì ghi đè để tránh clone
- download_attendance sẽ được xóa khi đóng phần mềm (handled ở service/controller)
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class DownloadAttendanceRepository:
    _TABLE_TEMP = "download_attendance"
    _TABLE_RAW = "attendance_raw"

    def list_download_attendance(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        device_no: int | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []

        if from_date:
            where.append("work_date >= %s")
            params.append(str(from_date))
        if to_date:
            where.append("work_date <= %s")
            params.append(str(to_date))
        if device_no is not None:
            where.append("device_no = %s")
            params.append(int(device_no))

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        query = (
            "SELECT "
            "t.attendance_code, "
            "COALESCE(NULLIF(t.name_on_mcc,''), NULLIF(e.name_on_mcc,''), '') AS name_on_mcc, "
            "t.work_date, t.time_in_1, t.time_out_1, t.time_in_2, t.time_out_2, t.time_in_3, t.time_out_3, "
            "t.device_name "
            f"FROM {self._TABLE_TEMP} t "
            "LEFT JOIN employees e ON (e.mcc_code = t.attendance_code OR e.employee_code = t.attendance_code) "
            f"{where_sql} "
            "ORDER BY t.work_date ASC, t.attendance_code ASC"
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
            logger.exception("Lỗi list_download_attendance")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def clear_download_attendance(self) -> int:
        query = f"DELETE FROM {self._TABLE_TEMP}"
        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query)
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi clear_download_attendance")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_download_attendance(
        self,
        rows: list[dict[str, Any]],
        *,
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        return self._upsert_many(
            self._TABLE_TEMP,
            rows,
            batch_size=batch_size,
            progress_hook=progress_hook,
        )

    def upsert_attendance_raw(
        self,
        rows: list[dict[str, Any]],
        *,
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        if not rows:
            return 0

        # Group rows by work_date year => attendance_raw_YYYY
        by_year: dict[int, list[dict[str, Any]]] = {}
        for r in rows:
            y = Database._year_from_work_date(r.get("work_date"))
            if y is None:
                continue
            by_year.setdefault(int(y), []).append(r)
        if not by_year:
            return 0

        try:
            bs = int(batch_size)
        except Exception:
            bs = 1000
        if bs <= 0:
            bs = 1000

        total = 0
        done = 0
        total_items = sum(len(v) for v in by_year.values())

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self._TABLE_RAW, int(year))
                    query = (
                        f"INSERT INTO {table} ("
                        "attendance_code, name_on_mcc, work_date, time_in_1, time_out_1, time_in_2, time_out_2, time_in_3, time_out_3, "
                        "device_no, device_id, device_name"
                        ") VALUES ("
                        "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                        ") ON DUPLICATE KEY UPDATE "
                        "name_on_mcc = VALUES(name_on_mcc), "
                        "time_in_1 = VALUES(time_in_1), "
                        "time_out_1 = VALUES(time_out_1), "
                        "time_in_2 = VALUES(time_in_2), "
                        "time_out_2 = VALUES(time_out_2), "
                        "time_in_3 = VALUES(time_in_3), "
                        "time_out_3 = VALUES(time_out_3), "
                        "device_id = VALUES(device_id), "
                        "device_name = VALUES(device_name)"
                    )

                    params: list[tuple[Any, ...]] = []
                    for r in by_year.get(year, []):
                        params.append(
                            (
                                str(r.get("attendance_code") or ""),
                                str(r.get("name_on_mcc") or ""),
                                str(r.get("work_date") or ""),
                                r.get("time_in_1"),
                                r.get("time_out_1"),
                                r.get("time_in_2"),
                                r.get("time_out_2"),
                                r.get("time_in_3"),
                                r.get("time_out_3"),
                                int(r.get("device_no") or 0),
                                (
                                    int(r.get("device_id") or 0)
                                    if r.get("device_id") is not None
                                    else None
                                ),
                                str(r.get("device_name") or ""),
                            )
                        )

                    for i in range(0, len(params), bs):
                        chunk = params[i : i + bs]
                        cursor.executemany(query, chunk)
                        conn.commit()
                        try:
                            total += int(cursor.rowcount or 0)
                        except Exception:
                            pass
                        done += len(chunk)
                        if progress_hook is not None:
                            try:
                                progress_hook(min(done, total_items), total_items)
                            except Exception:
                                pass
                return int(total)
        except Exception:
            logger.exception("Lỗi upsert_attendance_raw (yearly)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def insert_ignore_download_attendance(
        self,
        rows: list[dict[str, Any]],
        *,
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        return self._insert_ignore_many(
            self._TABLE_TEMP,
            rows,
            batch_size=batch_size,
            progress_hook=progress_hook,
        )

    def insert_ignore_attendance_raw(
        self,
        rows: list[dict[str, Any]],
        *,
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        if not rows:
            return 0

        by_year: dict[int, list[dict[str, Any]]] = {}
        for r in rows:
            y = Database._year_from_work_date(r.get("work_date"))
            if y is None:
                continue
            by_year.setdefault(int(y), []).append(r)
        if not by_year:
            return 0

        try:
            bs = int(batch_size)
        except Exception:
            bs = 1000
        if bs <= 0:
            bs = 1000

        total = 0
        done = 0
        total_items = sum(len(v) for v in by_year.values())

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for year in sorted(by_year.keys()):
                    table = Database.ensure_year_table(conn, self._TABLE_RAW, int(year))
                    query = (
                        f"INSERT IGNORE INTO {table} ("
                        "attendance_code, name_on_mcc, work_date, time_in_1, time_out_1, time_in_2, time_out_2, time_in_3, time_out_3, "
                        "device_no, device_id, device_name"
                        ") VALUES ("
                        "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
                        ")"
                    )

                    params: list[tuple[Any, ...]] = []
                    for r in by_year.get(year, []):
                        params.append(
                            (
                                str(r.get("attendance_code") or ""),
                                str(r.get("name_on_mcc") or ""),
                                str(r.get("work_date") or ""),
                                r.get("time_in_1"),
                                r.get("time_out_1"),
                                r.get("time_in_2"),
                                r.get("time_out_2"),
                                r.get("time_in_3"),
                                r.get("time_out_3"),
                                int(r.get("device_no") or 0),
                                (
                                    int(r.get("device_id") or 0)
                                    if r.get("device_id") is not None
                                    else None
                                ),
                                str(r.get("device_name") or ""),
                            )
                        )

                    for i in range(0, len(params), bs):
                        chunk = params[i : i + bs]
                        cursor.executemany(query, chunk)
                        conn.commit()
                        try:
                            total += int(cursor.rowcount or 0)
                        except Exception:
                            pass
                        done += len(chunk)
                        if progress_hook is not None:
                            try:
                                progress_hook(min(done, total_items), total_items)
                            except Exception:
                                pass
                return int(total)
        except Exception:
            logger.exception("Lỗi insert_ignore_attendance_raw (yearly)")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def _upsert_many(
        self,
        table: str,
        rows: list[dict[str, Any]],
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        if not rows:
            return 0

        try:
            bs = int(batch_size)
        except Exception:
            bs = 1000
        if bs <= 0:
            bs = 1000

        query = (
            f"INSERT INTO {table} ("
            "attendance_code, name_on_mcc, work_date, time_in_1, time_out_1, time_in_2, time_out_2, time_in_3, time_out_3, "
            "device_no, device_id, device_name"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
            ") ON DUPLICATE KEY UPDATE "
            "name_on_mcc = VALUES(name_on_mcc), "
            "time_in_1 = VALUES(time_in_1), "
            "time_out_1 = VALUES(time_out_1), "
            "time_in_2 = VALUES(time_in_2), "
            "time_out_2 = VALUES(time_out_2), "
            "time_in_3 = VALUES(time_in_3), "
            "time_out_3 = VALUES(time_out_3), "
            "device_id = VALUES(device_id), "
            "device_name = VALUES(device_name)"
        )

        params: list[tuple[Any, ...]] = []
        for r in rows:
            params.append(
                (
                    str(r.get("attendance_code") or ""),
                    str(r.get("name_on_mcc") or ""),
                    str(r.get("work_date") or ""),
                    r.get("time_in_1"),
                    r.get("time_out_1"),
                    r.get("time_in_2"),
                    r.get("time_out_2"),
                    r.get("time_in_3"),
                    r.get("time_out_3"),
                    int(r.get("device_no") or 0),
                    (
                        int(r.get("device_id") or 0)
                        if r.get("device_id") is not None
                        else None
                    ),
                    str(r.get("device_name") or ""),
                )
            )

        cursor = None
        total_rowcount = 0
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for i in range(0, len(params), bs):
                    chunk = params[i : i + bs]
                    cursor.executemany(query, chunk)
                    conn.commit()
                    try:
                        total_rowcount += int(cursor.rowcount or 0)
                    except Exception:
                        pass
                    if progress_hook is not None:
                        try:
                            progress_hook(min(i + len(chunk), len(params)), len(params))
                        except Exception:
                            pass
                return int(total_rowcount)
        except Exception:
            logger.exception("Lỗi upsert_many (%s)", table)
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def _insert_ignore_many(
        self,
        table: str,
        rows: list[dict[str, Any]],
        batch_size: int = 1000,
        progress_hook=None,
    ) -> int:
        """Insert rows but never overwrite existing ones.

        Used for generating 'no-punch' placeholder rows: we must not wipe real punches
        that may already exist for the same (attendance_code, work_date, device_no).
        """

        if not rows:
            return 0

        try:
            bs = int(batch_size)
        except Exception:
            bs = 1000
        if bs <= 0:
            bs = 1000

        query = (
            f"INSERT IGNORE INTO {table} ("
            "attendance_code, name_on_mcc, work_date, time_in_1, time_out_1, time_in_2, time_out_2, time_in_3, time_out_3, "
            "device_no, device_id, device_name"
            ") VALUES ("
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
            ")"
        )

        params: list[tuple[Any, ...]] = []
        for r in rows:
            params.append(
                (
                    str(r.get("attendance_code") or ""),
                    str(r.get("name_on_mcc") or ""),
                    str(r.get("work_date") or ""),
                    r.get("time_in_1"),
                    r.get("time_out_1"),
                    r.get("time_in_2"),
                    r.get("time_out_2"),
                    r.get("time_in_3"),
                    r.get("time_out_3"),
                    int(r.get("device_no") or 0),
                    (
                        int(r.get("device_id") or 0)
                        if r.get("device_id") is not None
                        else None
                    ),
                    str(r.get("device_name") or ""),
                )
            )

        cursor = None
        total_rowcount = 0
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                for i in range(0, len(params), bs):
                    chunk = params[i : i + bs]
                    cursor.executemany(query, chunk)
                    conn.commit()
                    try:
                        total_rowcount += int(cursor.rowcount or 0)
                    except Exception:
                        pass
                    if progress_hook is not None:
                        try:
                            progress_hook(min(i + len(chunk), len(params)), len(params))
                        except Exception:
                            pass
                return int(total_rowcount)
        except Exception:
            logger.exception("Lỗi insert_ignore_many (%s)", table)
            raise
        finally:
            if cursor is not None:
                cursor.close()
