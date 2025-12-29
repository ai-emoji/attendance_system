"""ui.controllers.company_controllers

Controller xử lý sự kiện cho CompanyDialog.

Trách nhiệm:
- Mở dialog ở giữa màn hình
- Load dữ liệu từ CompanyService
- Xử lý đổi ảnh
- Xử lý lưu và thoát
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QRect, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog

from core.resource import (
    APP_ICO,
    get_app_icon,
    resource_path,
    set_app_icon_from_bytes,
    set_window_icon,
)
from services.company_services import CompanyService
from ui.dialog.comapy_dialog import CompanyDialog
from core.threads import BackgroundTaskRunner


logger = logging.getLogger(__name__)


class CompanyController:
    """Controller cho cửa sổ Thông tin công ty."""

    def __init__(self, parent_window, service: CompanyService | None = None) -> None:
        self._parent_window = parent_window
        self._service = service or CompanyService()
        self._dialog: CompanyDialog | None = None
        self._runner = BackgroundTaskRunner(self._parent_window, name="company_load")

    def show_dialog(self) -> None:
        """Hiển thị dialog ở giữa cửa sổ cha."""
        logger.info("Mở dialog Thông tin công ty")

        self._dialog = CompanyDialog(self._parent_window)
        set_window_icon(self._dialog)

        self._bind_dialog_events(self._dialog)
        self._center_dialog(self._dialog)

        # Show dialog immediately; load data asynchronously.
        try:
            self._dialog.set_status("Đang tải...", ok=True)
        except Exception:
            pass
        try:
            QTimer.singleShot(0, lambda: self._load_data_async(self._dialog))
        except Exception:
            self._load_data_async(self._dialog)

        self._dialog.exec()

    def _bind_dialog_events(self, dialog: CompanyDialog) -> None:
        dialog.btn_change_image.clicked.connect(lambda: self._on_change_image(dialog))
        dialog.btn_save_exit.clicked.connect(lambda: self._on_save(dialog))

    def _load_data_async(self, dialog: CompanyDialog) -> None:
        def _fn() -> object:
            return self._service.load_company()

        def _ok(result: object) -> None:
            data = result
            try:
                if data is None:
                    dialog.set_logo_pixmap(get_app_icon().pixmap(256, 256))
                    dialog.set_status("", ok=True)
                    return

                dialog.set_form_values(
                    data.company_name, data.company_address, data.company_phone
                )
                if getattr(data, "company_logo", None):
                    dialog.set_logo_bytes(data.company_logo)
                    set_app_icon_from_bytes(data.company_logo)
                else:
                    dialog.set_logo_pixmap(get_app_icon().pixmap(256, 256))
                dialog.set_status("", ok=True)
            except Exception:
                logger.exception("Không thể apply dữ liệu công ty")
                try:
                    dialog.set_status("Không thể tải thông tin công ty.", ok=False)
                except Exception:
                    pass

        def _err(_msg: str) -> None:
            logger.exception("Không thể load dữ liệu công ty")
            try:
                dialog.set_status("Không thể tải thông tin công ty.", ok=False)
            except Exception:
                pass

        self._runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def _on_change_image(self, dialog: CompanyDialog) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            dialog,
            "Chọn ảnh công ty",
            "",
            "Hình ảnh (*.png *.jpg *.jpeg *.bmp *.ico *.svg)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                data = f.read()
            dialog.set_logo_bytes(data)

            # Đồng bộ icon real-time ở mọi cửa sổ
            set_app_icon_from_bytes(data)
            logger.debug("Đã chọn ảnh mới: %s", file_path)
            dialog.set_status("Đã cập nhật ảnh.", ok=True)

            # Tăng kích thước font chữ cho các thành phần trong dialog
            font = dialog.font()
            font.setPointSize(font.pointSize() + 5)
            dialog.setFont(font)
        except Exception:
            logger.exception("Không thể đọc file ảnh")
            dialog.set_status("Không thể đọc file ảnh.", ok=False)

    def _on_save(self, dialog: CompanyDialog) -> None:
        company_name, company_address, company_phone = dialog.get_form_values()
        ok, message = self._service.save_company(
            company_name=company_name,
            company_address=company_address,
            company_phone=company_phone,
            company_logo=dialog.get_logo_bytes(),
        )

        if ok:
            logger.info("Lưu thông tin công ty thành công")
            dialog.set_status(message, ok=True)
            dialog.accept()
        else:
            logger.warning("Lưu thông tin công ty thất bại: %s", message)
            dialog.set_status(message, ok=False)

    def _center_dialog(self, dialog: CompanyDialog) -> None:
        parent = self._parent_window
        if parent is None:
            return

        parent_geo: QRect = parent.frameGeometry()
        dlg_geo: QRect = dialog.frameGeometry()
        dlg_geo.moveCenter(parent_geo.center())
        dialog.move(dlg_geo.topLeft())
