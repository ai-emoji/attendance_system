"""ui.controllers.csdl_controllers

Controller cho dialog "Kết nối CSDL SQL".
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect

from repository.csdl_repository import CSDLConfig
from services.csdl_services import CSDLService
from ui.dialog.csdl_dialog import CSDLDialog


logger = logging.getLogger(__name__)


class CSDLController:
    def __init__(self, parent_window, service: CSDLService | None = None) -> None:
        self._parent_window = parent_window
        self._service = service or CSDLService()

    def show_dialog(self) -> None:
        logger.info("Mở dialog Kết nối CSDL SQL")
        dlg = CSDLDialog(self._parent_window)

        cfg = self._service.load_config()
        dlg.set_form(cfg.host, cfg.port, cfg.user, cfg.password, cfg.database)
        dlg.set_status("", ok=True)

        dlg.btn_connect.clicked.connect(lambda: self._on_connect(dlg))
        self._center_dialog(dlg)
        dlg.exec()

    def _on_connect(self, dialog: CSDLDialog) -> None:
        data = dialog.get_form()
        cfg = CSDLConfig(
            host=str(data.get("host") or "").strip(),
            port=int(data.get("port") or 3306),
            user=str(data.get("user") or "").strip(),
            password=str(data.get("password") or ""),
            database=str(data.get("database") or "").strip(),
        )

        ok, msg = self._service.apply_and_save(cfg)
        dialog.set_status(msg, ok=ok)

    def _center_dialog(self, dialog: CSDLDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
