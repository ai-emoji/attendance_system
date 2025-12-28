"""repository.export_grid_list_repository

Lưu cấu hình xuất lưới chấm công (single-row id=1).
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class ExportGridListRepository:
    _ID = 1

    def ensure_table(self) -> None:
        # best-effort schema creation
        ddl = (
            "CREATE TABLE IF NOT EXISTS export_grid_list_settings ("
            "id INT PRIMARY KEY,"
            "export_kind VARCHAR(20) NOT NULL DEFAULT 'grid',"
            "time_pairs INT NOT NULL DEFAULT 4,"
            "company_name VARCHAR(255) NULL,"
            "company_address VARCHAR(255) NULL,"
            "company_phone VARCHAR(50) NULL,"
            "company_name_font_size INT NULL,"
            "company_name_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "company_name_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "company_name_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "company_name_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "company_address_font_size INT NULL,"
            "company_address_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "company_address_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "company_address_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "company_address_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "company_phone_font_size INT NULL,"
            "company_phone_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "company_phone_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "company_phone_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "company_phone_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "creator VARCHAR(255) NULL,"
            "creator_font_size INT NULL,"
            "creator_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "creator_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "creator_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "creator_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "note_text TEXT NULL,"
            "note_font_size INT NULL,"
            "note_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "note_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "note_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "note_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "detail_note_text TEXT NULL,"
            "detail_note_font_size INT NULL,"
            "detail_note_bold TINYINT(1) NOT NULL DEFAULT 0,"
            "detail_note_italic TINYINT(1) NOT NULL DEFAULT 0,"
            "detail_note_underline TINYINT(1) NOT NULL DEFAULT 0,"
            "detail_note_align VARCHAR(10) NOT NULL DEFAULT 'left',"
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ")"
        )
        try:
            # Use a single connection to avoid repeated connects + noisy duplicate-column errors.
            cursor = None
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)

                cursor.execute(ddl)
                conn.commit()

                schema_name = str(Database.CONFIG.get("database") or "").strip()
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='export_grid_list_settings'",
                    (schema_name,),
                )
                existing = {
                    str(r[0]).strip() for r in (cursor.fetchall() or []) if r and r[0]
                }

                # Best-effort migration for older tables: add only missing columns.
                alters: list[tuple[str, str]] = [
                    (
                        "export_kind",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN export_kind VARCHAR(20) NOT NULL DEFAULT 'grid'",
                    ),
                    (
                        "time_pairs",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN time_pairs INT NOT NULL DEFAULT 4",
                    ),
                    (
                        "company_name_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_name_font_size INT NULL",
                    ),
                    (
                        "company_name_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_name_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_name_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_name_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_name_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_name_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_name_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_name_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                    (
                        "company_address_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_address_font_size INT NULL",
                    ),
                    (
                        "company_address_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_address_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_address_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_address_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_address_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_address_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_address_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_address_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                    (
                        "company_phone_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_phone_font_size INT NULL",
                    ),
                    (
                        "company_phone_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_phone_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_phone_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_phone_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_phone_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_phone_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "company_phone_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN company_phone_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                    (
                        "creator_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN creator_font_size INT NULL",
                    ),
                    (
                        "creator_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN creator_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "creator_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN creator_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "creator_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN creator_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "creator_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN creator_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                    (
                        "note_text",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_text TEXT NULL",
                    ),
                    (
                        "note_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_font_size INT NULL",
                    ),
                    (
                        "note_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "note_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "note_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "note_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN note_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                    (
                        "detail_note_text",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_text TEXT NULL",
                    ),
                    (
                        "detail_note_font_size",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_font_size INT NULL",
                    ),
                    (
                        "detail_note_bold",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_bold TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "detail_note_italic",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_italic TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "detail_note_underline",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_underline TINYINT(1) NOT NULL DEFAULT 0",
                    ),
                    (
                        "detail_note_align",
                        "ALTER TABLE export_grid_list_settings ADD COLUMN detail_note_align VARCHAR(10) NOT NULL DEFAULT 'left'",
                    ),
                ]

                for col, q in alters:
                    if col in existing:
                        continue
                    try:
                        cursor.execute(q)
                        conn.commit()
                        existing.add(col)
                    except Exception:
                        # Ignore: may lack permission, or another client migrated concurrently.
                        try:
                            conn.rollback()
                        except Exception:
                            pass
        except Exception:
            logger.exception("Không thể ensure bảng export_grid_list_settings")
            raise

    def get_settings(self) -> dict[str, Any] | None:
        self.ensure_table()
        q = (
            "SELECT export_kind, time_pairs, company_name, company_address, company_phone, "
            "company_name_font_size, company_name_bold, company_name_italic, company_name_underline, company_name_align, "
            "company_address_font_size, company_address_bold, company_address_italic, company_address_underline, company_address_align, "
            "company_phone_font_size, company_phone_bold, company_phone_italic, company_phone_underline, company_phone_align, "
            "creator, "
            "creator_font_size, creator_bold, creator_italic, creator_underline, creator_align, "
            "note_text, note_font_size, note_bold, note_italic, note_underline, note_align, "
            "detail_note_text, detail_note_font_size, detail_note_bold, detail_note_italic, detail_note_underline, detail_note_align "
            "FROM export_grid_list_settings WHERE id = %s LIMIT 1"
        )
        try:
            row = Database.execute_query(q, (self._ID,), fetch="one")
            return row if isinstance(row, dict) else None
        except Exception:
            logger.exception("Không thể load export_grid_list_settings")
            raise

    def upsert_settings(
        self,
        *,
        export_kind: str,
        time_pairs: int,
        company_name: str | None,
        company_address: str | None,
        company_phone: str | None,
        company_name_font_size: int | None,
        company_name_bold: bool,
        company_name_italic: bool,
        company_name_underline: bool,
        company_name_align: str,
        company_address_font_size: int | None,
        company_address_bold: bool,
        company_address_italic: bool,
        company_address_underline: bool,
        company_address_align: str,
        company_phone_font_size: int | None,
        company_phone_bold: bool,
        company_phone_italic: bool,
        company_phone_underline: bool,
        company_phone_align: str,
        creator: str | None,
        creator_font_size: int | None,
        creator_bold: bool,
        creator_italic: bool,
        creator_underline: bool,
        creator_align: str,
        note_text: str | None,
        note_font_size: int | None,
        note_bold: bool,
        note_italic: bool,
        note_underline: bool,
        note_align: str,
        detail_note_text: str | None,
        detail_note_font_size: int | None,
        detail_note_bold: bool,
        detail_note_italic: bool,
        detail_note_underline: bool,
        detail_note_align: str,
    ) -> None:
        self.ensure_table()
        q = (
            "INSERT INTO export_grid_list_settings ("
            "id, export_kind, time_pairs, company_name, company_address, company_phone, "
            "company_name_font_size, company_name_bold, company_name_italic, company_name_underline, company_name_align, "
            "company_address_font_size, company_address_bold, company_address_italic, company_address_underline, company_address_align, "
            "company_phone_font_size, company_phone_bold, company_phone_italic, company_phone_underline, company_phone_align, "
            "creator, "
            "creator_font_size, creator_bold, creator_italic, creator_underline, creator_align, "
            "note_text, note_font_size, note_bold, note_italic, note_underline, note_align, "
            "detail_note_text, detail_note_font_size, detail_note_bold, detail_note_italic, detail_note_underline, detail_note_align"
            ") VALUES ("
            "%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,"
            "%s,"
            "%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,%s,"
            "%s,%s,%s,%s,%s,%s"
            ") "
            "ON DUPLICATE KEY UPDATE "
            "export_kind=VALUES(export_kind),"
            "time_pairs=VALUES(time_pairs),"
            "company_name=VALUES(company_name),"
            "company_address=VALUES(company_address),"
            "company_phone=VALUES(company_phone),"
            "company_name_font_size=VALUES(company_name_font_size),"
            "company_name_bold=VALUES(company_name_bold),"
            "company_name_italic=VALUES(company_name_italic),"
            "company_name_underline=VALUES(company_name_underline),"
            "company_name_align=VALUES(company_name_align),"
            "company_address_font_size=VALUES(company_address_font_size),"
            "company_address_bold=VALUES(company_address_bold),"
            "company_address_italic=VALUES(company_address_italic),"
            "company_address_underline=VALUES(company_address_underline),"
            "company_address_align=VALUES(company_address_align),"
            "company_phone_font_size=VALUES(company_phone_font_size),"
            "company_phone_bold=VALUES(company_phone_bold),"
            "company_phone_italic=VALUES(company_phone_italic),"
            "company_phone_underline=VALUES(company_phone_underline),"
            "company_phone_align=VALUES(company_phone_align),"
            "creator=VALUES(creator),"
            "creator_font_size=VALUES(creator_font_size),"
            "creator_bold=VALUES(creator_bold),"
            "creator_italic=VALUES(creator_italic),"
            "creator_underline=VALUES(creator_underline),"
            "creator_align=VALUES(creator_align),"
            "note_text=VALUES(note_text),"
            "note_font_size=VALUES(note_font_size),"
            "note_bold=VALUES(note_bold),"
            "note_italic=VALUES(note_italic),"
            "note_underline=VALUES(note_underline),"
            "note_align=VALUES(note_align),"
            "detail_note_text=VALUES(detail_note_text),"
            "detail_note_font_size=VALUES(detail_note_font_size),"
            "detail_note_bold=VALUES(detail_note_bold),"
            "detail_note_italic=VALUES(detail_note_italic),"
            "detail_note_underline=VALUES(detail_note_underline),"
            "detail_note_align=VALUES(detail_note_align)"
        )
        Database.execute_update(
            q,
            (
                self._ID,
                str(export_kind or "grid"),
                int(time_pairs or 4),
                company_name,
                company_address,
                company_phone,
                company_name_font_size,
                1 if bool(company_name_bold) else 0,
                1 if bool(company_name_italic) else 0,
                1 if bool(company_name_underline) else 0,
                str(company_name_align or "left"),
                company_address_font_size,
                1 if bool(company_address_bold) else 0,
                1 if bool(company_address_italic) else 0,
                1 if bool(company_address_underline) else 0,
                str(company_address_align or "left"),
                company_phone_font_size,
                1 if bool(company_phone_bold) else 0,
                1 if bool(company_phone_italic) else 0,
                1 if bool(company_phone_underline) else 0,
                str(company_phone_align or "left"),
                creator,
                creator_font_size,
                1 if bool(creator_bold) else 0,
                1 if bool(creator_italic) else 0,
                1 if bool(creator_underline) else 0,
                str(creator_align or "left"),
                note_text,
                note_font_size,
                1 if bool(note_bold) else 0,
                1 if bool(note_italic) else 0,
                1 if bool(note_underline) else 0,
                str(note_align or "left"),
                detail_note_text,
                detail_note_font_size,
                1 if bool(detail_note_bold) else 0,
                1 if bool(detail_note_italic) else 0,
                1 if bool(detail_note_underline) else 0,
                str(detail_note_align or "left"),
            ),
        )
