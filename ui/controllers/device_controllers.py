"""ui.controllers.device_controllers

Controller cho màn "Thêm Máy chấm công":
- Load danh sách thiết bị vào bảng
- Làm mới (reload + clear form)
- Lưu (thêm mới nếu chưa chọn dòng; cập nhật nếu đang chọn)
- Xóa (xóa theo dòng đang chọn)

Không dùng QMessageBox; dùng MessageDialog (dialog dùng chung).
"""

from __future__ import annotations

import logging

from services.device_services import DeviceService
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class DeviceController:
    def __init__(
        self, parent_window, title_bar2, content, service: DeviceService | None = None
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or DeviceService()

        self._selected_device_id: int | None = None

    def bind(self) -> None:
        self._title_bar2.refresh_clicked.connect(self.on_refresh)
        self._title_bar2.save_clicked.connect(self.on_save)
        self._title_bar2.delete_clicked.connect(self.on_delete)

        if hasattr(self._content, "btn_connect"):
            self._content.btn_connect.clicked.connect(self.on_connect)

        self._content.table.itemSelectionChanged.connect(self._on_table_selection)

        self.refresh()
        if hasattr(self._content, "set_connection_status"):
            self._content.set_connection_status("Chưa kết nối")

    def refresh(self) -> None:
        try:
            models = self._service.list_devices()
            rows = [(m.id, m.device_name, m.ip_address) for m in models]
            self._content.set_devices(rows)
            self._title_bar2.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách thiết bị")
            self._content.set_devices([])
            self._title_bar2.set_total(0)

    def on_refresh(self) -> None:
        self._selected_device_id = None
        self._content.table.clearSelection()
        self._content.clear_form()
        self.refresh()

    def _on_table_selection(self) -> None:
        selected = self._content.get_selected_device()
        if not selected:
            self._selected_device_id = None
            return

        device_id, name, ip_addr = selected
        self._selected_device_id = int(device_id)

        if hasattr(self._content, "set_connection_status"):
            self._content.set_connection_status("Chưa kết nối")

        # Load full row from DB to fill form
        try:
            models = self._service.list_devices()
            match = next((m for m in models if m.id == self._selected_device_id), None)
            if match is None:
                return
            self._content.set_form(
                device_no=match.device_no,
                name=match.device_name,
                device_type=match.device_type,
                ip_address=match.ip_address,
                password=match.password,
                port=match.port,
            )
        except Exception:
            logger.exception("Không thể load thiết bị để fill form")

    def on_save(self) -> None:
        data = self._content.get_form_data()

        if self._selected_device_id is None:
            ok, msg, _new_id = self._service.create_device(
                device_no=data.get("device_no", ""),
                device_name=data.get("device_name", ""),
                device_type=data.get("device_type", ""),
                ip_address=data.get("ip_address", ""),
                password=data.get("password", ""),
                port=data.get("port", ""),
            )
            if ok:
                self.refresh()
                if _new_id is not None:
                    self._selected_device_id = int(_new_id)
                    if hasattr(self._content, "select_device_by_id"):
                        self._content.select_device_by_id(int(_new_id))
            else:
                MessageDialog.info(self._parent_window, "Thông báo", msg)
            return

        ok, msg = self._service.update_device(
            device_id=int(self._selected_device_id),
            device_no=data.get("device_no", ""),
            device_name=data.get("device_name", ""),
            device_type=data.get("device_type", ""),
            ip_address=data.get("ip_address", ""),
            password=data.get("password", ""),
            port=data.get("port", ""),
        )
        if ok:
            self.refresh()
            if hasattr(self._content, "select_device_by_id"):
                self._content.select_device_by_id(int(self._selected_device_id))
        else:
            MessageDialog.info(self._parent_window, "Thông báo", msg)

    def on_connect(self) -> None:
        data = self._content.get_form_data()
        device_name = data.get("device_name", "")
        device_type = data.get("device_type", "")
        ip_address = data.get("ip_address", "")
        password = data.get("password", "")
        port_raw = data.get("port", "")

        try:
            port = (
                int(port_raw)
                if str(port_raw).strip()
                else int(self._service.DEFAULT_PORT)
            )
        except Exception:
            port = int(self._service.DEFAULT_PORT)

        ok, msg = self._service.connect_device(
            device_type=device_type,
            device_name=device_name,
            ip=ip_address,
            port=port,
            password=password,
        )

        if hasattr(self._content, "set_connection_status"):
            self._content.set_connection_status(
                "Kết nối thành công" if ok else "Kết nối thất bại",
                ok=ok,
            )

        if not ok:
            # Hiển thị lý do (chi tiết) bằng dialog
            MessageDialog.info(self._parent_window, "Không thể kết nối", msg)

    def on_delete(self) -> None:
        selected = self._content.get_selected_device()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Xóa.",
            )
            return

        device_id, name, ip_addr = selected

        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa máy: {name} ({ip_addr})?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_device(int(device_id))
        if ok:
            self.on_refresh()
        else:
            MessageDialog.info(self._parent_window, "Không thể xóa", msg)
