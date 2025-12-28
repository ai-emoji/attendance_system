"""services.company_services

Service layer:
- Validate dữ liệu
- Gọi repository
- Bắt lỗi và chuyển thành message thân thiện
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.company_repository import CompanyRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanyModel:
    """Model dữ liệu công ty cho UI."""

    company_name: str
    company_address: str
    company_phone: str
    company_logo: bytes | None


class CompanyService:
    """Nghiệp vụ thông tin công ty."""

    def __init__(self, repository: CompanyRepository | None = None) -> None:
        self._repo = repository or CompanyRepository()

    def load_company(self) -> CompanyModel | None:
        try:
            row = self._repo.get_company()
            if not row:
                return None

            return CompanyModel(
                company_name=str(row.get("company_name") or ""),
                company_address=str(row.get("company_address") or ""),
                company_phone=str(row.get("company_phone") or ""),
                company_logo=row.get("company_logo"),
            )
        except Exception:
            logger.exception("Service load_company thất bại")
            raise

    def save_company(
        self,
        company_name: str,
        company_address: str,
        company_phone: str,
        company_logo: bytes | None,
    ) -> tuple[bool, str]:
        company_name = (company_name or "").strip()
        company_address = (company_address or "").strip()
        company_phone = (company_phone or "").strip()

        if not company_name:
            return False, "Vui lòng nhập thông tin công ty."

        if company_phone and len(company_phone) > 50:
            return False, "Số điện thoại quá dài."

        try:
            self._repo.upsert_company(
                company_name=company_name,
                company_address=company_address or None,
                company_phone=company_phone or None,
                company_logo=company_logo,
            )
            return True, "Lưu thông tin công ty thành công."
        except Exception:
            logger.exception("Service save_company thất bại")
            return False, "Không thể lưu thông tin công ty. Vui lòng thử lại."
