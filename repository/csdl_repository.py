"""repository.csdl_repository

Lưu/đọc cấu hình kết nối MySQL cho ứng dụng.

Lưu ý:
- Không lưu trong DB (vì cần config để kết nối DB).
- Lưu ra file JSON dưới thư mục database/.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.resource import resource_path


@dataclass(frozen=True)
class CSDLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


class CSDLRepository:
    def __init__(self, config_file: str | None = None) -> None:
        # Mặc định lưu ở: database/db_config.json
        self._path = (
            Path(config_file)
            if config_file
            else Path(resource_path("database/db_config.json"))
        )

    def load(self) -> CSDLConfig | None:
        try:
            if not self._path.exists():
                return None

            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                return None

            host = str(data.get("host") or "").strip()
            user = str(data.get("user") or "").strip()
            password = str(data.get("password") or "")
            database = str(data.get("database") or "").strip()

            port = data.get("port")
            try:
                port_int = int(port) if port is not None and str(port).strip() else 3306
            except Exception:
                port_int = 3306

            if not host and not user and not database:
                return None

            return CSDLConfig(
                host=host,
                port=port_int,
                user=user,
                password=password,
                database=database,
            )
        except Exception:
            return None

    def save(self, config: CSDLConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = asdict(config)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
