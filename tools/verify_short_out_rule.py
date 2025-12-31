from __future__ import annotations

import datetime as dt

import os
import sys

# Ensure project root is importable when running as a script.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.shift_attendance_maincontent2_services import (
    ShiftAttendanceMainContent2Service,
)


def _fmt(v: object | None) -> str:
    if v is None:
        return "-"
    if isinstance(v, dt.timedelta):
        s = int(v.total_seconds()) % 86400
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
    if isinstance(v, dt.time):
        return v.strftime("%H:%M:%S")
    return str(v)


def main() -> None:
    svc = ShiftAttendanceMainContent2Service()

    # Adjust these two lines to test other employees/days
    target_date = "2025-09-10"
    target_employee_code = "00078"

    rows = svc.list_attendance_audit_arranged(
        from_date=target_date, to_date=target_date
    )
    rows = [
        r
        for r in rows
        if str(r.get("employee_code") or "").strip() == target_employee_code
    ]

    print("rows:", len(rows))
    for r in rows:
        print(
            "mode=",
            r.get("in_out_mode"),
            "schedule=",
            r.get("schedule"),
            "attendance_code=",
            r.get("attendance_code"),
            "employee_code=",
            r.get("employee_code"),
        )
        print(
            "in_1",
            _fmt(r.get("in_1")),
            "out_1",
            _fmt(r.get("out_1")),
            "in_2",
            _fmt(r.get("in_2")),
            "out_2",
            _fmt(r.get("out_2")),
            "in_3",
            _fmt(r.get("in_3")),
            "out_3",
            _fmt(r.get("out_3")),
        )


if __name__ == "__main__":
    main()
