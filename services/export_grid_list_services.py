"""services.export_grid_list_services

Nghiệp vụ lưu cấu hình xuất lưới chấm công.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.export_grid_list_repository import ExportGridListRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportGridListSettings:
    export_kind: str = "grid"  # grid|detail
    time_pairs: int = 4  # 2|4|6 (number of time columns)
    company_name: str = ""
    company_address: str = ""
    company_phone: str = ""
    company_name_font_size: int = 13
    company_name_bold: bool = False
    company_name_italic: bool = False
    company_name_underline: bool = False
    company_name_align: str = "left"  # left|center|right
    company_address_font_size: int = 13
    company_address_bold: bool = False
    company_address_italic: bool = False
    company_address_underline: bool = False
    company_address_align: str = "left"  # left|center|right
    company_phone_font_size: int = 13
    company_phone_bold: bool = False
    company_phone_italic: bool = False
    company_phone_underline: bool = False
    company_phone_align: str = "left"  # left|center|right
    creator: str = ""
    creator_font_size: int = 13
    creator_bold: bool = False
    creator_italic: bool = False
    creator_underline: bool = False
    creator_align: str = "left"  # left|center|right
    note_text: str = ""
    note_font_size: int = 13
    note_bold: bool = False
    note_italic: bool = False
    note_underline: bool = False
    note_align: str = "left"  # left|center|right
    detail_note_text: str = ""
    detail_note_font_size: int = 13
    detail_note_bold: bool = False
    detail_note_italic: bool = False
    detail_note_underline: bool = False
    detail_note_align: str = "left"  # left|center|right


class ExportGridListService:
    def __init__(self, repo: ExportGridListRepository | None = None) -> None:
        self._repo = repo or ExportGridListRepository()

    def load(self) -> ExportGridListSettings | None:
        try:
            row = self._repo.get_settings()
            if not row:
                return None

            def _b(v) -> bool:
                try:
                    return bool(int(v))
                except Exception:
                    return bool(v)

            def _norm_align(v) -> str:
                a = str(v or "left").strip().lower()
                return a if a in {"left", "center", "right"} else "left"

            def _norm_export_kind(v) -> str:
                k = str(v or "grid").strip().lower()
                return k if k in {"grid", "detail"} else "grid"

            def _norm_time_pairs(v) -> int:
                try:
                    iv = int(v)
                except Exception:
                    iv = 4
                return iv if iv in {2, 4, 6} else 4

            note_align = _norm_align(row.get("note_align"))
            detail_note_align = _norm_align(row.get("detail_note_align"))
            creator_align = _norm_align(row.get("creator_align"))
            company_name_align = _norm_align(row.get("company_name_align"))
            company_address_align = _norm_align(row.get("company_address_align"))
            company_phone_align = _norm_align(row.get("company_phone_align"))

            def _norm_size(v) -> int:
                try:
                    iv = int(v) if v is not None else 13
                except Exception:
                    iv = 13
                return max(8, min(40, iv))

            note_size = _norm_size(row.get("note_font_size"))
            detail_note_size = _norm_size(row.get("detail_note_font_size"))
            creator_size = _norm_size(row.get("creator_font_size"))
            company_name_size = _norm_size(row.get("company_name_font_size"))
            company_address_size = _norm_size(row.get("company_address_font_size"))
            company_phone_size = _norm_size(row.get("company_phone_font_size"))

            # Fallback: if detail_note_* are missing/null in DB, use grid note as initial default
            raw_detail_text = row.get("detail_note_text")
            if raw_detail_text is None:
                detail_text = str(row.get("note_text") or "")
            else:
                detail_text = str(raw_detail_text or "")

            def _detail_b(key: str, fallback_key: str) -> bool:
                v = row.get(key)
                if v is None:
                    v = row.get(fallback_key)
                return _b(v)

            return ExportGridListSettings(
                export_kind=_norm_export_kind(row.get("export_kind")),
                time_pairs=_norm_time_pairs(row.get("time_pairs")),
                company_name=str(row.get("company_name") or ""),
                company_address=str(row.get("company_address") or ""),
                company_phone=str(row.get("company_phone") or ""),
                company_name_font_size=company_name_size,
                company_name_bold=_b(row.get("company_name_bold")),
                company_name_italic=_b(row.get("company_name_italic")),
                company_name_underline=_b(row.get("company_name_underline")),
                company_name_align=company_name_align,
                company_address_font_size=company_address_size,
                company_address_bold=_b(row.get("company_address_bold")),
                company_address_italic=_b(row.get("company_address_italic")),
                company_address_underline=_b(row.get("company_address_underline")),
                company_address_align=company_address_align,
                company_phone_font_size=company_phone_size,
                company_phone_bold=_b(row.get("company_phone_bold")),
                company_phone_italic=_b(row.get("company_phone_italic")),
                company_phone_underline=_b(row.get("company_phone_underline")),
                company_phone_align=company_phone_align,
                creator=str(row.get("creator") or ""),
                creator_font_size=creator_size,
                creator_bold=_b(row.get("creator_bold")),
                creator_italic=_b(row.get("creator_italic")),
                creator_underline=_b(row.get("creator_underline")),
                creator_align=creator_align,
                note_text=str(row.get("note_text") or ""),
                note_font_size=note_size,
                note_bold=_b(row.get("note_bold")),
                note_italic=_b(row.get("note_italic")),
                note_underline=_b(row.get("note_underline")),
                note_align=note_align,
                detail_note_text=detail_text,
                detail_note_font_size=detail_note_size,
                detail_note_bold=_detail_b("detail_note_bold", "note_bold"),
                detail_note_italic=_detail_b("detail_note_italic", "note_italic"),
                detail_note_underline=_detail_b(
                    "detail_note_underline", "note_underline"
                ),
                detail_note_align=(detail_note_align or note_align),
            )
        except Exception:
            logger.exception("Service load export_grid_list_settings thất bại")
            raise

    def save(
        self, s: ExportGridListSettings, *, context: str = "xuất lưới"
    ) -> tuple[bool, str]:
        company_name = (s.company_name or "").strip()
        company_address = (s.company_address or "").strip()
        company_phone = (s.company_phone or "").strip()
        creator = (s.creator or "").strip()
        note_text = str(s.note_text or "")
        detail_note_text = str(s.detail_note_text or "")

        def _norm_align(v) -> str:
            a = str(v or "left").strip().lower()
            return a if a in {"left", "center", "right"} else "left"

        note_align = _norm_align(s.note_align)
        detail_note_align = _norm_align(s.detail_note_align)
        creator_align = _norm_align(s.creator_align)
        company_name_align = _norm_align(s.company_name_align)
        company_address_align = _norm_align(s.company_address_align)
        company_phone_align = _norm_align(s.company_phone_align)

        def _norm_size(v) -> int:
            try:
                iv = int(v) if v is not None else 13
            except Exception:
                iv = 13
            return max(8, min(40, iv))

        note_size = _norm_size(s.note_font_size)
        detail_note_size = _norm_size(s.detail_note_font_size)
        creator_size = _norm_size(s.creator_font_size)
        company_name_size = _norm_size(s.company_name_font_size)
        company_address_size = _norm_size(s.company_address_font_size)
        company_phone_size = _norm_size(s.company_phone_font_size)

        try:
            export_kind = (
                str(getattr(s, "export_kind", "grid") or "grid").strip().lower()
            )
            if export_kind not in {"grid", "detail"}:
                export_kind = "grid"
            try:
                time_pairs = int(getattr(s, "time_pairs", 4) or 4)
            except Exception:
                time_pairs = 4
            if time_pairs not in {2, 4, 6}:
                time_pairs = 4

            self._repo.upsert_settings(
                export_kind=export_kind,
                time_pairs=time_pairs,
                company_name=(company_name or None),
                company_address=(company_address or None),
                company_phone=(company_phone or None),
                company_name_font_size=company_name_size,
                company_name_bold=bool(s.company_name_bold),
                company_name_italic=bool(s.company_name_italic),
                company_name_underline=bool(s.company_name_underline),
                company_name_align=company_name_align,
                company_address_font_size=company_address_size,
                company_address_bold=bool(s.company_address_bold),
                company_address_italic=bool(s.company_address_italic),
                company_address_underline=bool(s.company_address_underline),
                company_address_align=company_address_align,
                company_phone_font_size=company_phone_size,
                company_phone_bold=bool(s.company_phone_bold),
                company_phone_italic=bool(s.company_phone_italic),
                company_phone_underline=bool(s.company_phone_underline),
                company_phone_align=company_phone_align,
                creator=(creator or None),
                creator_font_size=creator_size,
                creator_bold=bool(s.creator_bold),
                creator_italic=bool(s.creator_italic),
                creator_underline=bool(s.creator_underline),
                creator_align=creator_align,
                note_text=(note_text or None),
                note_font_size=note_size,
                note_bold=bool(s.note_bold),
                note_italic=bool(s.note_italic),
                note_underline=bool(s.note_underline),
                note_align=note_align,
                detail_note_text=(detail_note_text or None),
                detail_note_font_size=detail_note_size,
                detail_note_bold=bool(s.detail_note_bold),
                detail_note_italic=bool(s.detail_note_italic),
                detail_note_underline=bool(s.detail_note_underline),
                detail_note_align=detail_note_align,
            )
            ctx = str(context or "xuất lưới").strip().lower()
            if ctx not in {"xuất lưới", "xuất chi tiết"}:
                ctx = "xuất lưới"
            return True, f"Đã lưu cấu hình {ctx}."
        except Exception:
            logger.exception("Service save export_grid_list_settings thất bại")
            ctx = str(context or "xuất lưới").strip().lower()
            if ctx not in {"xuất lưới", "xuất chi tiết"}:
                ctx = "xuất lưới"
            return False, f"Không thể lưu cấu hình {ctx}. Vui lòng thử lại."
