from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow running this script directly from the repo (ensure project root on sys.path)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import Database


@dataclass
class QueryArgs:
    work_date: str
    employee_code: str


def _norm_codes(code: str) -> list[str]:
    c = str(code or "").strip()
    if not c:
        return []
    alt = c.lstrip("0") or c
    if alt == c:
        return [c]
    return [c, alt]


def _fetch_rows(*, table: str, work_date: str, codes: list[str]) -> list[dict]:
    with Database.connect() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            placeholders = ",".join(["%s"] * len(codes))
            query = (
                "SELECT * "
                f"FROM hr_attendance.{table} "
                "WHERE work_date=%s "
                f"  AND (attendance_code IN ({placeholders}) OR employee_code IN ({placeholders})) "
                "ORDER BY device_no ASC, id ASC"
            )
            params = [work_date, *codes, *codes]
            cur.execute(query, params)
            return list(cur.fetchall() or [])
        finally:
            cur.close()


def _fetch_rows_by_attendance_code(
    *, table: str, work_date: str, codes: list[str]
) -> list[dict]:
    with Database.connect() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            placeholders = ",".join(["%s"] * len(codes))
            query = (
                "SELECT * "
                f"FROM hr_attendance.{table} "
                "WHERE work_date=%s "
                f"  AND attendance_code IN ({placeholders}) "
                "ORDER BY device_no ASC, id ASC"
            )
            params = [work_date, *codes]
            cur.execute(query, params)
            return list(cur.fetchall() or [])
        finally:
            cur.close()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Query attendance audit/raw punches for a single day"
    )
    p.add_argument("--date", required=True, help="Work date in YYYY-MM-DD")
    p.add_argument("--employee-code", required=True, help="Employee code (e.g. 00078)")
    ns = p.parse_args()
    args = QueryArgs(
        work_date=str(ns.date).strip(), employee_code=str(ns.employee_code).strip()
    )

    Database.load_config_from_file()

    codes = _norm_codes(args.employee_code)
    if not codes:
        raise SystemExit("employee code is empty")

    year = int(args.work_date[:4])
    audit_table = f"attendance_audit_{year}"
    raw_table = f"attendance_raw_{year}"

    out: dict[str, object] = {
        "date": args.work_date,
        "employee_code": args.employee_code,
    }

    for t in [audit_table, "attendance_audit"]:
        try:
            rows = _fetch_rows(table=t, work_date=args.work_date, codes=codes)
            if rows:
                out["audit"] = {"table": t, "rows": rows}
                break
        except Exception as e:
            out.setdefault("audit_errors", []).append({"table": t, "error": str(e)})

    for t in [raw_table, "attendance_raw", "download_attendance"]:
        try:
            out[t] = _fetch_rows_by_attendance_code(
                table=t, work_date=args.work_date, codes=codes
            )
        except Exception as e:
            out[t] = {"error": str(e)}

    print(json.dumps(out, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
