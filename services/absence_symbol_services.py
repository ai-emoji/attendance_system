"""services.absence_symbol_services

Service layer cho màn "Ký hiệu Vắng":
- Load / lưu danh sách ký hiệu A01..A15
- Validate cơ bản
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.absence_symbol_repository import AbsenceSymbolRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AbsenceSymbolModel:
    id: int | None
    code: str
    description: str
    symbol: str
    is_used: bool
    is_paid: bool


class AbsenceSymbolService:
    CODE_PREFIX = "A"
    CODE_MIN = 1
    CODE_MAX = 15
    DESCRIPTION_MAX = 255
    SYMBOL_MAX = 50

    def __init__(self, repository: AbsenceSymbolRepository | None = None) -> None:
        self._repo = repository or AbsenceSymbolRepository()

    def list_symbols(self) -> list[AbsenceSymbolModel]:
        rows = self._repo.list_symbols()
        result: list[AbsenceSymbolModel] = []
        for r in rows:
            try:
                result.append(
                    AbsenceSymbolModel(
                        id=int(r.get("id")) if r.get("id") is not None else None,
                        code=str(r.get("code") or ""),
                        description=str(r.get("description") or ""),
                        symbol=str(r.get("symbol") or ""),
                        is_used=bool(int(r.get("is_used") or 0)),
                        is_paid=bool(int(r.get("is_paid") or 0)),
                    )
                )
            except Exception:
                continue
        return result

    def save_symbols(self, items: list[dict]) -> tuple[bool, str]:
        try:
            for it in items or []:
                code = str(it.get("code") or "").strip()
                description = str(it.get("description") or "").strip()
                symbol = str(it.get("symbol") or "").strip()
                is_used = bool(it.get("is_used"))
                is_paid = bool(it.get("is_paid"))

                if not self._is_valid_code(code):
                    return False, f"Mã không hợp lệ: {code}"
                if len(description) > self.DESCRIPTION_MAX:
                    return False, f"Mô tả ({code}) tối đa {self.DESCRIPTION_MAX} ký tự."
                if len(symbol) > self.SYMBOL_MAX:
                    return False, f"Ký hiệu ({code}) tối đa {self.SYMBOL_MAX} ký tự."

                self._repo.upsert_symbol(
                    code=code,
                    description=description,
                    symbol=symbol,
                    is_used=1 if is_used else 0,
                    is_paid=1 if is_paid else 0,
                )

            return True, "Lưu thành công."
        except Exception:
            logger.exception("Không thể lưu absence_symbols")
            return False, "Không thể lưu. Vui lòng thử lại."

    def _is_valid_code(self, code: str) -> bool:
        if not code.startswith(self.CODE_PREFIX):
            return False
        num = code[1:]
        if not num.isdigit():
            return False
        n = int(num)
        return self.CODE_MIN <= n <= self.CODE_MAX
