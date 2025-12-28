from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database


def main() -> None:
    # Load DB connection settings from database/db_config.json
    try:
        Database.load_config_from_file(str(ROOT / "database" / "db_config.json"))
    except Exception:
        # Keep going; Database.connect() will raise a clear error if not configured.
        pass

    wd = "2025-12-01"
    emp = "00042"
    year = 2025

    with Database.connect() as conn:
        cur = Database.get_cursor(conn, dictionary=True)
        table = Database.ensure_year_table(conn, "attendance_audit", year)
        q = (
            "SELECT id, employee_code, work_date, in_1, out_1, schedule, import_locked, "
            "late, early, hours, work, shift_code, updated_at "
            "FROM {} WHERE employee_code=%s AND work_date=%s ORDER BY id DESC LIMIT 5"
        ).format(table)
        cur.execute(q, (emp, wd))
        rows = cur.fetchall() or []
        print("table", table, "rows", len(rows))
        for r in rows:
            print(r)
        cur.close()


if __name__ == "__main__":
    main()
