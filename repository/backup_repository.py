"""repository.backup_repository

Lưu cấu hình đơn giản cho chức năng backup/restore:
- thư mục backup lần cuối
- file restore lần cuối

Lưu ra JSON trong database/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resource import resource_path


class BackupRepository:
    def __init__(self, settings_file: str | None = None) -> None:
        self._path = (
            Path(settings_file)
            if settings_file
            else Path(resource_path("database/backup_settings.json"))
        )

    def load_settings(self) -> dict[str, Any]:
        try:
            if not self._path.exists():
                return {}
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save_settings(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_last_backup_path(self) -> str:
        data = self.load_settings()
        return str(data.get("last_backup_path") or "")

    def set_last_backup_path(self, path: str) -> None:
        data = self.load_settings()
        data["last_backup_path"] = path
        self.save_settings(data)

    def get_last_restore_path(self) -> str:
        data = self.load_settings()
        return str(data.get("last_restore_path") or "")

    def set_last_restore_path(self, path: str) -> None:
        data = self.load_settings()
        data["last_restore_path"] = path
        self.save_settings(data)
