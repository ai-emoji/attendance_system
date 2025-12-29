"""tools.migrate_attendance_audit_add_symbol_columns

Migrate best-effort: add missing columns needed for Shift Attendance import/display.

Why:
- Import supports `in_1_symbol` (OFF/V/Lễ...) and optional `shift_code`/`total`.
- Older DB schemas may not have these columns, causing the import to silently
  fall back (Unknown column) and symbols won't persist.

Run:
  python tools/migrate_attendance_audit_add_symbol_columns.py

Notes:
- Uses the same DB credentials from database/db_config.json.
- Requires ALTER permission.
"""

from __future__ import annotations

import sys
from pathlib import Path


# Ensure project root is importable when running as: python tools/...
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from core.database import Database


def _list_attendance_audit_tables(conn) -> list[str]:
    schema = str(Database.CONFIG.get("database") or "").strip()
    if not schema:
        return []

    cursor = None
    try:
        cursor = Database.get_cursor(conn, dictionary=True)
        cursor.execute(
            "SELECT TABLE_NAME "
            "FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME LIKE 'attendance_audit%'",
            (schema,),
        )
        rows = list(cursor.fetchall() or [])
        out: list[str] = []
        for r in rows:
            tn = str((r or {}).get("TABLE_NAME") or "").strip()
            if tn:
                out.append(tn)
        # stable order: base first, then yearly
        out = list(dict.fromkeys(out))
        out.sort(key=lambda s: (0 if s == "attendance_audit" else 1, s))
        return out
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass


def main() -> int:
    # resource_path() resolves relative to sys.argv[0] (entrypoint).
    # When running from tools/, explicitly load config from project root.
    try:
        Database.load_config_from_file(str(_ROOT / "database" / "db_config.json"))
    except Exception:
        pass

    if not Database.is_configured(reload=False):
        print(
            "Chưa cấu hình DB. Vui lòng cập nhật database/db_config.json hoặc dùng dialog 'Kết nối CSDL SQL'."
        )
        return 2

    try:
        with Database.connect(ensure_schema=True) as conn:
            tables = _list_attendance_audit_tables(conn)
            if not tables:
                print("Không tìm thấy bảng attendance_audit trong schema hiện tại.")
                return 3

            columns = [
                ("total", "ADD COLUMN total DECIMAL(10,2) NULL"),
                ("shift_code", "ADD COLUMN shift_code VARCHAR(255) NULL"),
                ("in_1_symbol", "ADD COLUMN in_1_symbol VARCHAR(50) NULL"),
            ]

            print(f"Tìm thấy {len(tables)} bảng cần kiểm tra.")
            for tn in tables:
                Database._ensure_table_columns_best_effort(  # type: ignore[attr-defined]
                    conn,
                    table_name=str(tn),
                    columns=columns,
                    log_prefix=str(tn),
                )

            print("Hoàn tất. Nếu không thấy dòng 'Auto-migrate', có thể DB đã đủ cột hoặc thiếu quyền ALTER.")
            print("Gợi ý kiểm tra: DESCRIBE hr_attendance.attendance_audit_YYYY;")
            return 0
    except Exception as exc:
        print(f"Lỗi migrate: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
