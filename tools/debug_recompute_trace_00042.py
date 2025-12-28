from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import Database
from repository.shift_attendance_maincontent2_repository import (
    ShiftAttendanceMainContent2Repository,
)


def dump_text(label: str, s: object | None) -> None:
    txt = "" if s is None else str(s)
    print(label, "=", repr(txt), "len=", len(txt))
    cps = [f"U+{ord(ch):04X}" for ch in txt]
    print(" codepoints:", " ".join(cps[:64]), ("..." if len(cps) > 64 else ""))
    try:
        nfc = unicodedata.normalize("NFC", txt)
        nfd = unicodedata.normalize("NFD", txt)
        print(" NFC==orig", nfc == txt, "NFD==orig", nfd == txt)
    except Exception:
        pass


def main() -> None:
    Database.load_config_from_file(str(ROOT / "database" / "db_config.json"))

    repo = ShiftAttendanceMainContent2Repository()

    rows = repo.list_rows(from_date="2025-12-01", to_date="2025-12-01", employee_ids=None, attendance_codes=None)
    row = None
    for r in rows:
        if str(r.get("employee_code") or "").strip() == "00042":
            row = r
            break

    if not row:
        print("Row not found")
        return

    print("Found row id", row.get("id"), "import_locked", row.get("import_locked"))
    dump_text("schedule", row.get("schedule"))

    schedule_names = [row.get("schedule")]
    m = repo.get_schedule_id_mode_by_names([str(schedule_names[0] or "")])
    print("schedule_map keys:", list(m.keys()))
    meta = m.get(str(schedule_names[0] or "").strip())
    print("meta direct:", meta)

    # Try normalized key lookup
    try:
        key_nfc = unicodedata.normalize("NFC", str(schedule_names[0] or "").strip())
    except Exception:
        key_nfc = str(schedule_names[0] or "").strip()
    meta2 = m.get(key_nfc)
    print("meta nfc:", meta2)

    sid = None
    if meta and meta.get("schedule_id") is not None:
        sid = int(meta.get("schedule_id"))
    elif meta2 and meta2.get("schedule_id") is not None:
        sid = int(meta2.get("schedule_id"))

    print("schedule_id:", sid)
    if not sid:
        return

    details = repo.get_schedule_details_by_schedule_ids([sid])
    print("details keys count:", len(details))
    mon = details.get((sid, "mon"))
    print("mon detail:", mon)
    if not mon:
        return

    shift1 = mon.get("shift1_id")
    print("shift1_id:", shift1)
    if not shift1:
        return

    ws = repo.get_work_shifts_by_ids([int(shift1)])
    print("work_shift:", ws.get(int(shift1)))


if __name__ == "__main__":
    main()
