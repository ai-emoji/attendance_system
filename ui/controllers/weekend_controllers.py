"""ui.controllers.weekend_controllers

Controller cho dialog "Chọn ngày Cuối tuần".

Trách nhiệm:
- Mở dialog ở giữa cửa sổ cha
- Load dữ liệu Thứ 2..Chủ nhật
- Lưu
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect

from services.weekend_services import WeekendService
from ui.dialog.weekend_dialog import WeekendDialog


logger = logging.getLogger(__name__)


class WeekendController:
    def __init__(self, parent_window, service: WeekendService | None = None) -> None:
        self._parent_window = parent_window
        self._service = service or WeekendService()
        self._dialog: WeekendDialog | None = None

    def show_dialog(self) -> None:
        logger.info("Mở dialog Chọn ngày Cuối tuần")
        dlg = WeekendDialog(self._parent_window)
        self._dialog = dlg

        self._bind(dlg)
        self._load(dlg)
        self._center_dialog(dlg)

        dlg.exec()

    def _bind(self, dialog: WeekendDialog) -> None:
        dialog.btn_save.clicked.connect(lambda: self._on_save(dialog))

    def _load(self, dialog: WeekendDialog) -> None:
        try:
            models = self._service.list_days()
            by_day = {}
            for m in models:
                by_day[m.day_name] = {
                    "id": m.id,
                    "day_name": m.day_name,
                    "is_weekend": 1 if m.is_weekend else 0,
                }
            dialog.set_rows(by_day)
            dialog.set_status("", ok=True)
        except Exception:
            logger.exception("Không thể load weekend_settings")
            dialog.set_status("Không thể tải dữ liệu.", ok=False)

    def _on_save(self, dialog: WeekendDialog) -> None:
        items = dialog.collect_rows()
        ok, msg = self._service.save_days(items)
        dialog.set_status(msg, ok=ok)

    def _center_dialog(self, dialog: WeekendDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
