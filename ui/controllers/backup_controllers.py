"""ui.controllers.backup_controllers

Controller cho dialog "Sao lưu Dữ liệu".
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect

from repository.backup_repository import BackupRepository
from services.backup_services import BackupService
from ui.dialog.backup_dialog import BackupDialog


logger = logging.getLogger(__name__)


class BackupController:
    def __init__(
        self,
        parent_window,
        service: BackupService | None = None,
        repo: BackupRepository | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._service = service or BackupService()
        self._repo = repo or BackupRepository()

    def show_dialog(self) -> None:
        logger.info("Mở dialog Sao lưu Dữ liệu")
        dlg = BackupDialog(self._parent_window)

        last = self._repo.get_last_backup_path()
        if last:
            dlg.set_path(last)

        dlg.set_status("", ok=True)
        dlg.btn_backup.clicked.connect(lambda: self._on_backup(dlg))
        self._center_dialog(dlg)
        dlg.exec()

    def _on_backup(self, dialog: BackupDialog) -> None:
        path = dialog.get_path()
        ok, msg = self._service.backup_to_file(path)
        dialog.set_status(msg, ok=ok)
        if ok:
            # update last path (dịch vụ có thể tự thêm .sql)
            dialog_path = dialog.get_path()
            self._repo.set_last_backup_path(dialog_path)

    def _center_dialog(self, dialog: BackupDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
