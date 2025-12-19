"""repository.company_repository

Repository layer: chỉ chứa SQL thuần cho bảng company.

Quy ước:
- Dùng query parameter %s (MySQL)
- Không validate, không nghiệp vụ
- Mở kết nối ngắn, đóng ngay
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class CompanyRepository:
    """SQL CRUD cho bảng company (thiết kế single-row id=1)."""

    _COMPANY_ID = 1

    def get_company(self) -> dict[str, Any] | None:
        query = (
            "SELECT company_name, company_address, company_phone, company_logo "
            "FROM company WHERE id = %s LIMIT 1"
        )

        conn = None
        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (self._COMPANY_ID,))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi lấy thông tin công ty")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def upsert_company(
        self,
        company_name: str,
        company_address: str | None,
        company_phone: str | None,
        company_logo: bytes | None,
    ) -> None:
        query = (
            "INSERT INTO company (id, company_name, company_address, company_phone, company_logo) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE "
            "company_name = VALUES(company_name), "
            "company_address = VALUES(company_address), "
            "company_phone = VALUES(company_phone), "
            "company_logo = VALUES(company_logo)"
        )

        conn = None
        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        self._COMPANY_ID,
                        company_name,
                        company_address,
                        company_phone,
                        company_logo,
                    ),
                )
                conn.commit()
        except Exception:
            logger.exception("Lỗi lưu thông tin công ty")
            raise
        finally:
            if cursor is not None:
                cursor.close()
