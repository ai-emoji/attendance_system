"""ui.controllers.absence_symbol_controllers

Controller cho dialog "Ký hiệu Vắng".

Trách nhiệm:
- Mở dialog ở giữa cửa sổ cha
- Load dữ liệu A01..A15
- Lưu
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect

from services.absence_symbol_services import AbsenceSymbolService
from ui.dialog.absence_symbol_dialog import AbsenceSymbolDialog


logger = logging.getLogger(__name__)


class AbsenceSymbolController:
    def __init__(
        self, parent_window, service: AbsenceSymbolService | None = None
    ) -> None:
        self._parent_window = parent_window
        self._service = service or AbsenceSymbolService()
        self._dialog: AbsenceSymbolDialog | None = None

    def show_dialog(self) -> None:
        logger.info("Mở dialog Ký hiệu Vắng")
        dlg = AbsenceSymbolDialog(self._parent_window)
        self._dialog = dlg

        self._bind(dlg)
        self._load(dlg)
        self._center_dialog(dlg)

        dlg.exec()

    def _bind(self, dialog: AbsenceSymbolDialog) -> None:
        dialog.btn_save.clicked.connect(lambda: self._on_save(dialog))

    def _load(self, dialog: AbsenceSymbolDialog) -> None:
        try:
            models = self._service.list_symbols()
            by_code = {}
            for m in models:
                by_code[m.code] = {
                    "id": m.id,
                    "code": m.code,
                    "description": m.description,
                    "symbol": m.symbol,
                    "is_used": 1 if m.is_used else 0,
                    "is_paid": 1 if m.is_paid else 0,
                }
            dialog.set_rows(by_code)
            dialog.set_status("", ok=True)
        except Exception:
            logger.exception("Không thể load absence_symbols")
            dialog.set_status("Không thể tải dữ liệu.", ok=False)

    def _on_save(self, dialog: AbsenceSymbolDialog) -> None:
        items = dialog.collect_rows()
        ok, msg = self._service.save_symbols(items)
        dialog.set_status(msg, ok=ok)

    def _center_dialog(self, dialog: AbsenceSymbolDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
