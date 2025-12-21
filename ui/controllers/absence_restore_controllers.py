"""ui.controllers.absence_restore_controllers

Controller cho dialog "Khôi phục Dữ liệu".
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect

from repository.backup_repository import BackupRepository
from services.backup_services import BackupService
from ui.dialog.absence_restore_dialog import AbsenceRestoreDialog


logger = logging.getLogger(__name__)


class AbsenceRestoreController:
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
        logger.info("Mở dialog Khôi phục Dữ liệu")
        dlg = AbsenceRestoreDialog(self._parent_window)

        last = self._repo.get_last_restore_path()
        if last:
            dlg.set_path(last)

        dlg.set_status("", ok=True)
        dlg.btn_restore.clicked.connect(lambda: self._on_restore(dlg))
        self._center_dialog(dlg)
        dlg.exec()

    def _on_restore(self, dialog: AbsenceRestoreDialog) -> None:
        path = dialog.get_path()
        ok, msg = self._service.restore_from_file(path)
        dialog.set_status(msg, ok=ok)
        if ok:
            self._repo.set_last_restore_path(path)

    def _center_dialog(self, dialog: AbsenceRestoreDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
