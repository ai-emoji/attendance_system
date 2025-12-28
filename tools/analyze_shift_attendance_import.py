"""tools.analyze_shift_attendance_import

Analyze impact of importing Shift Attendance Excel file into attendance_audit_<year>.

This script:
- Reads rows from Excel using ImportShiftAttendanceService
- Fetches existing DB rows for (employee_code, work_date)
- Runs import (writes to DB)
- Fetches rows again and compares field-level changes

Outputs a detailed report to stdout and writes a log file under ./log.

Usage:
  python tools/analyze_shift_attendance_import.py "path/to/file.xlsx"

Note:
- This WILL modify the DB by performing the import.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure project root is importable when executed as a script.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.import_shift_attendance_services import ImportShiftAttendanceService
from core.database import Database


COMPARE_KEYS = [
    "employee_code",
    "full_name",
    "work_date",
    "weekday",
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
    "leave",
    "hours_plus",
    "work_plus",
    "leave_plus",
    "tc1",
    "tc2",
    "tc3",
    "schedule",
    "import_locked",
]


def _norm(v: Any) -> Any:
    if v is None:
        return None
    # times/dates are already python objects from mysql connector, keep as string for compare
    s = str(v)
    s = s.strip()
    return s if s != "" else None


@dataclass
class DiffStats:
    total_pairs: int = 0
    existed_before: int = 0
    missing_before: int = 0
    existed_after: int = 0
    missing_after: int = 0

    inserted: int = 0
    updated_rows: int = 0

    fields_changed: int = 0
    fields_cleared: int = 0


def _count_nulls(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {k: 0 for k in COMPARE_KEYS}
    for r in rows:
        for k in COMPARE_KEYS:
            if _norm(r.get(k)) is None:
                counts[k] += 1
    return counts


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tools/analyze_shift_attendance_import.py <xlsx_path>")
        return 2

    xlsx_path = Path(argv[1]).expanduser()
    if not xlsx_path.exists():
        print(f"File not found: {xlsx_path}")
        return 2

    service = ImportShiftAttendanceService()

    # When running as a standalone script, resource_path() would resolve relative to this script.
    # Load DB config explicitly from project root.
    try:
        Database.load_config_from_file(str(_ROOT / "database" / "db_config.json"))
    except Exception:
        pass

    ok, msg, rows = service.read_shift_attendance_from_xlsx(str(xlsx_path))
    print(f"READ: ok={ok} | {msg}")
    if not ok:
        return 1

    # Build pairs
    pairs: list[tuple[str, str]] = []
    years: set[int] = set()
    for r in rows:
        ec = str(r.get("employee_code") or "").strip()
        wd = str(r.get("work_date") or "").strip()
        if ec and wd:
            pairs.append((ec, wd))
            try:
                years.add(int(wd[:4]))
            except Exception:
                pass

    # de-dup
    pairs = list(dict.fromkeys(pairs))

    repo = service._repo  # intentional for analysis

    def _table_metrics(conn, table: str) -> tuple[int | None, int | None]:
        """Return (actual_count, estimated_count) for a table."""
        cursor = None
        try:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            row = cursor.fetchone()
            actual = int(row[0]) if row else None

            schema_name = str(Database.CONFIG.get("database") or "").strip() or "hr_attendance"
            cursor.execute(
                "SELECT TABLE_ROWS FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",
                (schema_name, table),
            )
            row2 = cursor.fetchone()
            est = int(row2[0]) if row2 and row2[0] is not None else None
            return actual, est
        except Exception:
            return None, None
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    metrics_before: dict[str, tuple[int | None, int | None]] = {}
    metrics_after: dict[str, tuple[int | None, int | None]] = {}

    # Snapshot table counts BEFORE import (to explain phpMyAdmin '~' numbers)
    try:
        with Database.connect() as conn:
            for y in sorted(years):
                tbl = f"attendance_audit_{y}"
                metrics_before[tbl] = _table_metrics(conn, tbl)
    except Exception as exc:
        print(f"WARN: cannot read table metrics before import: {exc}")

    before_map = repo.get_existing_by_employee_code_date(pairs)

    stats = DiffStats()
    stats.total_pairs = len(pairs)
    stats.existed_before = len(before_map)
    stats.missing_before = stats.total_pairs - stats.existed_before

    before_rows = list(before_map.values())
    before_nulls = _count_nulls(before_rows)

    # Import (writes to DB)
    report_items: list[dict[str, Any]] = []
    result = service.import_shift_attendance_rows(rows, report=report_items)

    # Snapshot table counts AFTER import
    try:
        with Database.connect() as conn:
            for y in sorted(years):
                tbl = f"attendance_audit_{y}"
                metrics_after[tbl] = _table_metrics(conn, tbl)
    except Exception as exc:
        print(f"WARN: cannot read table metrics after import: {exc}")

    # Re-fetch
    after_map = repo.get_existing_by_employee_code_date(pairs)
    stats.existed_after = len(after_map)
    stats.missing_after = stats.total_pairs - stats.existed_after

    # Parse result counters
    stats.inserted = int(getattr(result, "inserted", 0) or 0)
    stats.updated_rows = int(getattr(result, "updated", 0) or 0)

    after_rows = list(after_map.values())
    after_nulls = _count_nulls(after_rows)

    # Field diffs
    for key in pairs:
        b = before_map.get(key)
        a = after_map.get(key)
        if a is None:
            continue
        if b is None:
            continue

        for k in COMPARE_KEYS:
            old_v = _norm(b.get(k))
            new_v = _norm(a.get(k))
            if old_v != new_v:
                stats.fields_changed += 1
            if old_v is not None and new_v is None:
                stats.fields_cleared += 1

    # Summaries
    print("\n=== SUMMARY (pairs from Excel) ===")
    print(f"Total pairs (employee_code, work_date): {stats.total_pairs}")
    print(f"Existed before: {stats.existed_before} | Missing before: {stats.missing_before}")
    print(f"Existed after : {stats.existed_after} | Missing after : {stats.missing_after}")

    print("\n=== IMPORT RESULT ===")
    print(f"ok={result.ok} | {result.message}")
    print(f"inserted={stats.inserted} updated={stats.updated_rows} skipped={getattr(result,'skipped',0)} failed={getattr(result,'failed',0)}")

    print("\n=== FIELD NULL COUNTS (before -> after) ===")
    for k in COMPARE_KEYS:
        b = before_nulls.get(k, 0)
        a = after_nulls.get(k, 0)
        if b != a:
            print(f"{k}: {b} -> {a}")

    print("\n=== FIELD DIFFS (existing rows only) ===")
    print(f"fields_changed={stats.fields_changed}")
    print(f"fields_cleared (non-empty -> empty)={stats.fields_cleared}")

    print("\n=== TABLE ROW COUNTS (COUNT(*) vs information_schema.TABLE_ROWS) ===")
    for tbl in sorted(set(list(metrics_before.keys()) + list(metrics_after.keys()))):
        b_act, b_est = metrics_before.get(tbl, (None, None))
        a_act, a_est = metrics_after.get(tbl, (None, None))
        if b_act is None and b_est is None and a_act is None and a_est is None:
            continue
        print(f"{tbl}: actual {b_act} -> {a_act} | estimated {b_est} -> {a_est}")

    # Write detailed report file
    log_dir = Path("log")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = log_dir / f"analyze_import_shift_attendance_{ts}.txt"

    def _fmt_report(items: list[dict[str, Any]], limit: int = 50) -> str:
        lines: list[str] = []
        for it in items[:limit]:
            lines.append(
                f"{it.get('index')}\t{it.get('result')}\t{it.get('action')}\t{it.get('employee_code')}\t{it.get('message')}"
            )
        if len(items) > limit:
            lines.append(f"... (+{len(items) - limit} rows)")
        return "\n".join(lines)

    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"Excel: {xlsx_path}\n")
        f.write(f"READ: ok={ok} | {msg}\n\n")
        f.write("SUMMARY\n")
        f.write(f"total_pairs={stats.total_pairs}\n")
        f.write(f"existed_before={stats.existed_before}\n")
        f.write(f"missing_before={stats.missing_before}\n")
        f.write(f"existed_after={stats.existed_after}\n")
        f.write(f"missing_after={stats.missing_after}\n\n")
        f.write("IMPORT_RESULT\n")
        f.write(f"ok={result.ok}\nmessage={result.message}\n")
        f.write(
            f"inserted={stats.inserted}\nupdated={stats.updated_rows}\nskipped={getattr(result,'skipped',0)}\nfailed={getattr(result,'failed',0)}\n\n"
        )
        f.write("NULL_COUNTS (before -> after)\n")
        for k in COMPARE_KEYS:
            f.write(f"{k}: {before_nulls.get(k,0)} -> {after_nulls.get(k,0)}\n")
        f.write("\nFIELD_DIFFS (existing rows only)\n")
        f.write(f"fields_changed={stats.fields_changed}\n")
        f.write(f"fields_cleared={stats.fields_cleared}\n\n")

        f.write("TABLE_ROW_COUNTS (COUNT(*) vs information_schema.TABLE_ROWS)\n")
        for tbl in sorted(set(list(metrics_before.keys()) + list(metrics_after.keys()))):
            b_act, b_est = metrics_before.get(tbl, (None, None))
            a_act, a_est = metrics_after.get(tbl, (None, None))
            f.write(f"{tbl}: actual {b_act} -> {a_act} | estimated {b_est} -> {a_est}\n")
        f.write("\n")
        f.write("REPORT_ITEMS (first 50)\n")
        f.write("index\tresult\taction\temployee_code\tmessage\n")
        f.write(_fmt_report(report_items, limit=50))
        f.write("\n")

    print(f"\nWROTE REPORT: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
