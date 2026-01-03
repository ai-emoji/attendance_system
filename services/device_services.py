"""services.device_services

Service layer cho màn "Thêm Máy chấm công":
- Validate dữ liệu form
- CRUD qua DeviceRepository
- Hỗ trợ kết nối thiết bị chấm công (Ronald Jack X629ID, SenseFace A4)

Ghi chú về kết nối:
- Nhiều thiết bị Ronald Jack/SenseFace dùng giao thức ZKTeco (port thường 4370).
- Nếu cài thư viện `zk` (pyzk), service sẽ thử connect thật.
- Nếu chưa có thư viện, service vẫn có thể test TCP port để kiểm tra thiết bị reachable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from repository.device_repository import DeviceRepository
from services.device_connectors.senseface_a4_connector import (
    connect as connect_senseface_a4,
)
from services.device_connectors.x629id_connector import connect as connect_x629id


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceModel:
    id: int
    device_no: int
    device_name: str
    device_type: str
    ip_address: str
    password: str
    port: int


class DeviceService:
    DEFAULT_PORT = 4370

    DEVICE_TYPE_X629ID = "X629ID"
    DEVICE_TYPE_SENSEFACE_A4 = "SENSEFACE_A4"

    def __init__(self, repository: DeviceRepository | None = None) -> None:
        self._repo = repository or DeviceRepository()

    # -----------------
    # CRUD
    # -----------------
    def list_devices(self) -> list[DeviceModel]:
        rows = self._repo.list_devices()
        result: list[DeviceModel] = []
        for r in rows:
            try:
                result.append(
                    DeviceModel(
                        id=int(r.get("id")),
                        device_no=int(r.get("device_no") or 0),
                        device_name=str(r.get("device_name") or ""),
                        device_type=str(r.get("device_type") or ""),
                        ip_address=str(r.get("ip_address") or ""),
                        password=str(r.get("password") or ""),
                        port=int(r.get("port") or 0),
                    )
                )
            except Exception:
                continue
        return result

    def create_device(
        self,
        device_no: str,
        device_name: str,
        device_type: str,
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str, int | None]:
        ok, msg, parsed = self._validate_form(
            device_no=device_no,
            device_name=device_name,
            device_type=device_type,
            ip_address=ip_address,
            password=password,
            port=port,
        )
        if not ok or parsed is None:
            return False, msg, None

        try:
            new_id = self._repo.create_device(**parsed)
            return True, "Lưu thành công.", new_id
        except Exception:
            logger.exception("Service create_device thất bại")
            return False, "Không thể lưu. Vui lòng thử lại.", None

    def update_device(
        self,
        device_id: int,
        device_no: str,
        device_name: str,
        device_type: str,
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str]:
        if not device_id:
            return False, "Không tìm thấy dòng cần cập nhật."

        ok, msg, parsed = self._validate_form(
            device_no=device_no,
            device_name=device_name,
            device_type=device_type,
            ip_address=ip_address,
            password=password,
            port=port,
        )
        if not ok or parsed is None:
            return False, msg

        try:
            affected = self._repo.update_device(device_id=int(device_id), **parsed)
            if affected <= 0:
                return False, "Không có thay đổi."
            return True, "Lưu thành công."
        except Exception:
            logger.exception("Service update_device thất bại")
            return False, "Không thể lưu. Vui lòng thử lại."

    def delete_device(self, device_id: int) -> tuple[bool, str]:
        if not device_id:
            return False, "Vui lòng chọn dòng cần xóa."

        try:
            affected = self._repo.delete_device(int(device_id))
            if affected <= 0:
                return False, "Không tìm thấy dòng cần xóa."
            return True, "Xóa thành công."
        except Exception:
            logger.exception("Service delete_device thất bại")
            return False, "Không thể xóa. Vui lòng thử lại."

    def _validate_form(
        self,
        device_no: str,
        device_name: str,
        device_type: str,
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str, dict | None]:
        device_no = (device_no or "").strip()
        device_name = (device_name or "").strip()
        device_type = (device_type or "").strip()
        ip_address = (ip_address or "").strip()
        password = (password or "").strip()
        port = (port or "").strip()

        if not device_no:
            return False, "Vui lòng nhập Số máy.", None
        try:
            device_no_int = int(device_no)
        except Exception:
            return False, "Số máy không hợp lệ.", None

        if not device_name:
            return False, "Vui lòng nhập Tên máy.", None

        if device_type not in (self.DEVICE_TYPE_SENSEFACE_A4, self.DEVICE_TYPE_X629ID):
            return False, "Vui lòng chọn đúng loại máy chấm công.", None

        ok_ip, ip_msg = self._validate_ip(ip_address)
        if not ok_ip:
            return False, ip_msg, None

        if not port:
            port_int = self.DEFAULT_PORT
        else:
            try:
                port_int = int(port)
            except Exception:
                return False, "Cổng kết nối không hợp lệ.", None

        if port_int < 0 or port_int > 65535:
            return False, "Cổng kết nối phải trong khoảng 0-65535.", None

        return (
            True,
            "OK",
            {
                "device_no": int(device_no_int),
                "device_name": device_name,
                "device_type": device_type,
                "ip_address": ip_address,
                "password": password,
                "port": int(port_int),
            },
        )

    def _validate_ip(self, ip: str) -> tuple[bool, str]:
        parts = [p.strip() for p in (ip or "").split(".")]
        if len(parts) != 4:
            return False, "Địa chỉ IP không hợp lệ."
        try:
            nums = [int(p) for p in parts]
        except Exception:
            return False, "Địa chỉ IP không hợp lệ."
        for n in nums:
            if n < 0 or n > 255:
                return False, "Địa chỉ IP không hợp lệ."
        return True, "OK"

    # -----------------
    # Device connection helpers
    # -----------------
    def connect_ronald_jack_x629id(
        self, ip: str, port: int = DEFAULT_PORT, password: str = ""
    ) -> tuple[bool, str]:
        return connect_x629id(ip=ip, port=port, password=password)

    def connect_senseface_a4(
        self, ip: str, port: int = DEFAULT_PORT, password: str = ""
    ) -> tuple[bool, str]:
        return connect_senseface_a4(ip=ip, port=port, password=password)

    def connect_device(
        self,
        device_type: str,
        device_name: str,
        ip: str,
        port: int = DEFAULT_PORT,
        password: str = "",
    ) -> tuple[bool, str]:
        """Chọn module kết nối theo loại máy (ưu tiên) và fallback theo tên.

        Hỗ trợ:
        - Ronald Jack X629ID
        - SenseFace A4
        Fallback: ZKTeco (cùng giao thức phổ biến).
        """

        dt = (device_type or "").strip().upper()
        if dt == self.DEVICE_TYPE_X629ID:
            return self.connect_ronald_jack_x629id(ip=ip, port=port, password=password)
        if dt == self.DEVICE_TYPE_SENSEFACE_A4:
            return self.connect_senseface_a4(ip=ip, port=port, password=password)

        # Fallback theo tên nếu device_type trống/khác chuẩn
        name = (device_name or "").strip().lower()
        if "senseface" in name or "a4" in name:
            return self.connect_senseface_a4(ip=ip, port=port, password=password)
        return self.connect_ronald_jack_x629id(ip=ip, port=port, password=password)
