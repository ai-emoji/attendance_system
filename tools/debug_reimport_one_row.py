from __future__ import annotations

import sys
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database
from services.import_shift_attendance_services import ImportShiftAttendanceService


def query_row(*, emp: str, wd: str) -> dict | None:
    with Database.connect() as conn:
        cur = Database.get_cursor(conn, dictionary=True)
        table = Database.ensure_year_table(conn, "attendance_audit", 2025)
        cur.execute(
            (
                "SELECT id, employee_code, work_date, in_1, out_1, schedule, import_locked, "
                "late, early, hours, work, shift_code, updated_at "
                f"FROM {table} WHERE employee_code=%s AND work_date=%s ORDER BY id DESC LIMIT 1"
            ),
            (emp, wd),
        )
        row = cur.fetchone()
        cur.close()
        return row


def main() -> None:
    # Load DB config
    Database.load_config_from_file(str(ROOT / "database" / "db_config.json"))

    xlsx = ROOT / "file mẫu tải dữ liệu công 1.xlsx"
    svc = ImportShiftAttendanceService()

    ok, msg, rows = svc.read_shift_attendance_from_xlsx(str(xlsx))
    print("read", ok, msg, "rows", len(rows))
    if not ok:
        return

    targets = [
        ("00004", "2025-12-01"),
        ("00042", "2025-12-01"),
    ]

    for target_emp, target_date in targets:
        # Pick the first matching row and force in_1=10:00 to simulate re-import change.
        picked = None
        for r in rows:
            if (
                str(r.get("employee_code") or "").strip() == target_emp
                and str(r.get("work_date") or "").strip() == target_date
            ):
                picked = dict(r)
                break

        if not picked:
            print("No matching row found in Excel for", target_emp, target_date)
            continue

        print("\n===", target_emp, target_date, "===")
        print("DB before:", query_row(emp=target_emp, wd=target_date))

        picked["in_1"] = time(10, 0, 0)
        picked["out_1"] = time(17, 0, 0)

        report: list[dict] = []
        res = svc.import_shift_attendance_rows([picked], report=report)
        print("import result:", res)
        if report:
            print("report:", report[0])

        print("DB after:", query_row(emp=target_emp, wd=target_date))


if __name__ == "__main__":
    main()
