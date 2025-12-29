from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this script directly from tools/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--employee-code", required=True)
    ap.add_argument("--work-date", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    emp_code = str(args.employee_code).strip()
    wd = str(args.work_date).strip()
    if not emp_code or not wd:
        raise SystemExit("Missing args")

    year = int(wd.split("-", 1)[0])

    # Load config from project root (running from tools/ would otherwise
    # resolve resource_path relative to the entrypoint).
    try:
        Database.load_config_from_file(str(ROOT / "database" / "db_config.json"))
    except Exception:
        pass

    with Database.connect() as conn:
        cur = Database.get_cursor(conn, dictionary=True)
        try:
            table = Database.ensure_year_table(conn, "attendance_audit", year)
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE "
                "FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s "
                "AND COLUMN_NAME IN ('in_1_symbol','in_1','out_1','in_2','out_2','in_3','out_3','import_locked') "
                "ORDER BY COLUMN_NAME",
                (table,),
            )
            cols = list(cur.fetchall() or [])
            print("table:", table)
            print("cols:", cols)

            cur.execute(
                f"SELECT employee_code, work_date, in_1_symbol, in_1, out_1, in_2, out_2, in_3, out_3, import_locked "
                f"FROM {table} WHERE employee_code=%s AND work_date=%s ORDER BY id DESC LIMIT 5",
                (emp_code, wd),
            )
            rows = list(cur.fetchall() or [])
            print("rows:")
            for r in rows:
                print(r)
        finally:
            cur.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
