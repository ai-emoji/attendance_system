"""services.attendance_symbol_services

Service layer cho màn "Ký hiệu Chấm công":
- Load / lưu cấu hình ký hiệu
- Validate cơ bản

Lưu ý:
- Lưu theo dạng nhiều dòng (giống absence_symbols)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from repository.attendance_symbol_repository import AttendanceSymbolRepository


logger = logging.getLogger(__name__)


@dataclass
class AttendanceSymbolRow:
    code: str
    description: str = ""
    symbol: str = ""
    is_visible: bool = True


class AttendanceSymbolService:
    SYMBOL_MAX_LENGTH = 50
    DESCRIPTION_MAX_LENGTH = 255
    _CODE_RE = re.compile(r"^C(0[1-9]|10)$")

    def __init__(self, repository: AttendanceSymbolRepository | None = None) -> None:
        self._repo = repository or AttendanceSymbolRepository()

    def list_rows_by_code(self) -> dict[str, dict]:
        try:
            rows = self._repo.list_rows() or []
        except Exception:
            logger.exception("Không thể load attendance_symbols")
            rows = []

        out: dict[str, dict] = {}
        for r in rows:
            code = str(r.get("code") or "").strip()
            if not code:
                continue
            out[code] = {
                "id": r.get("id"),
                "code": code,
                "description": str(r.get("description") or ""),
                "symbol": str(r.get("symbol") or ""),
                "is_visible": int(r.get("is_visible") or 0),
            }
        return out

    def save_rows(self, rows: list[dict]) -> tuple[bool, str]:
        cleaned: list[dict] = []

        for r in rows:
            code = str(r.get("code") or "").strip().upper()
            if not self._CODE_RE.match(code):
                return False, f"Mã không hợp lệ: {code}."

            description = str(r.get("description") or "").strip()
            symbol = str(r.get("symbol") or "").strip()
            is_visible = bool(r.get("is_visible"))

            if len(description) > self.DESCRIPTION_MAX_LENGTH:
                return (
                    False,
                    f"{code}: mô tả tối đa {self.DESCRIPTION_MAX_LENGTH} ký tự.",
                )
            if len(symbol) > self.SYMBOL_MAX_LENGTH:
                return False, f"{code}: ký hiệu tối đa {self.SYMBOL_MAX_LENGTH} ký tự."

            cleaned.append(
                {
                    "code": code,
                    "description": description,
                    "symbol": symbol,
                    "is_visible": 1 if is_visible else 0,
                }
            )

        try:
            self._repo.upsert_rows(cleaned)
            return True, "Lưu cấu hình thành công."
        except Exception:
            logger.exception("Không thể lưu attendance_symbols")
            return False, "Không thể lưu cấu hình. Vui lòng thử lại."
