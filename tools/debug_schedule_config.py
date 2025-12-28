from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database


def main() -> None:
    Database.load_config_from_file(str(ROOT / "database" / "db_config.json"))

    schedule_name = "ca đêm"

    with Database.connect() as conn:
        cur = Database.get_cursor(conn, dictionary=True)

        cur.execute(
            "SELECT id, schedule_name, in_out_mode, ignore_absent_sat, ignore_absent_sun, "
            "ignore_absent_holiday, holiday_count_as_work, day_is_out_time "
            "FROM hr_attendance.arrange_schedules WHERE schedule_name=%s",
            (schedule_name,),
        )
        sch = cur.fetchall() or []
        print("schedule rows:", len(sch))
        for r in sch:
            print(r)

        if not sch:
            cur.close()
            return

        schedule_id = int(sch[0]["id"])

        cur.execute(
            "SELECT schedule_id, day_key, shift1_id, shift2_id, shift3_id, shift4_id, shift5_id "
            "FROM hr_attendance.arrange_schedule_details WHERE schedule_id=%s",
            (schedule_id,),
        )
        details = cur.fetchall() or []
        print("details rows:", len(details))

        # Show mon + others quickly
        for r in sorted(details, key=lambda x: str(x.get("day_key") or "")):
            if r.get("day_key") in {"mon", "tue", "wed", "thu", "fri", "sat", "sun", "holiday"}:
                print("detail", r)

        # Collect shift ids
        shift_ids: list[int] = []
        for r in details:
            for k in ("shift1_id", "shift2_id", "shift3_id", "shift4_id", "shift5_id"):
                v = r.get(k)
                if v is None:
                    continue
                try:
                    shift_ids.append(int(v))
                except Exception:
                    pass
        shift_ids = list(dict.fromkeys([x for x in shift_ids if x > 0]))
        print("unique shift_ids:", shift_ids)

        if shift_ids:
            ph = ",".join(["%s"] * len(shift_ids))
            cur.execute(
                "SELECT id, shift_code, time_in, time_out, total_minutes, work_count, "
                "in_window_start, in_window_end, out_window_start, out_window_end "
                f"FROM hr_attendance.work_shifts WHERE id IN ({ph})",
                tuple(shift_ids),
            )
            ws = cur.fetchall() or []
            print("work_shifts rows:", len(ws))
            for r in ws:
                print(r)

        cur.close()


if __name__ == "__main__":
    main()
