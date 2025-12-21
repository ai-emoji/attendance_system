"""services.csdl_services

Service cho chức năng "Kết nối CSDL SQL".
- Validate cấu hình
- Apply vào core.database.Database.CONFIG
- Test connection
"""

from __future__ import annotations

from dataclasses import replace

import mysql.connector

from core.database import Database
from repository.csdl_repository import CSDLConfig, CSDLRepository


class CSDLService:
    def __init__(self, repo: CSDLRepository | None = None) -> None:
        self._repo = repo or CSDLRepository()

    def load_config(self) -> CSDLConfig:
        saved = self._repo.load()
        cfg = Database.CONFIG

        if saved is not None:
            return saved

        # Fallback từ Database.CONFIG
        host = str(cfg.get("host") or "").strip()
        user = str(cfg.get("user") or "").strip()
        password = str(cfg.get("password") or "")
        database = str(cfg.get("database") or "").strip()
        port = int(cfg.get("port") or 3306)
        return CSDLConfig(
            host=host, port=port, user=user, password=password, database=database
        )

    def validate(self, config: CSDLConfig) -> tuple[bool, str]:
        if not config.host:
            return False, "Vui lòng nhập Host."
        if not config.user:
            return False, "Vui lòng nhập User."
        if not config.database:
            return False, "Vui lòng nhập Database."
        if config.port <= 0:
            return False, "Port không hợp lệ."
        return True, "OK"

    def test_connection(self, config: CSDLConfig) -> tuple[bool, str]:
        ok, msg = self.validate(config)
        if not ok:
            return False, msg

        try:
            conn = mysql.connector.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                charset=Database.CONFIG.get("charset") or "utf8mb4",
                use_unicode=bool(Database.CONFIG.get("use_unicode", True)),
            )
            try:
                conn.close()
            except Exception:
                pass
            return True, "Kết nối thành công."
        except Exception as exc:
            return False, f"Kết nối thất bại: {exc}"

    def apply_and_save(self, config: CSDLConfig) -> tuple[bool, str]:
        ok, msg = self.test_connection(config)
        if not ok:
            return False, msg

        # Apply vào Database.CONFIG
        Database.CONFIG.update(
            {
                "host": config.host,
                "port": int(config.port),
                "user": config.user,
                "password": config.password,
                "database": config.database,
            }
        )
        self._repo.save(config)
        return True, "Đã lưu cấu hình và kết nối OK."
