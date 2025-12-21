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

import importlib.util
import logging
import socket
from dataclasses import dataclass

from repository.device_repository import DeviceRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceModel:
    id: int
    device_no: int
    device_name: str
    ip_address: str
    password: str
    port: int


class DeviceService:
    DEFAULT_PORT = 4370

    MODEL_RONALD_JACK_X629ID = "Ronald Jack X629ID"
    MODEL_SENSEFACE_A4 = "SenseFace A4"

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
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str, int | None]:
        ok, msg, parsed = self._validate_form(
            device_no=device_no,
            device_name=device_name,
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
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str]:
        if not device_id:
            return False, "Không tìm thấy dòng cần cập nhật."

        ok, msg, parsed = self._validate_form(
            device_no=device_no,
            device_name=device_name,
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
        ip_address: str,
        password: str,
        port: str,
    ) -> tuple[bool, str, dict | None]:
        device_no = (device_no or "").strip()
        device_name = (device_name or "").strip()
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
    def test_connection_tcp(self, ip: str, port: int, timeout: float = 3.0) -> bool:
        try:
            with socket.create_connection((ip, int(port)), timeout=timeout):
                return True
        except Exception:
            return False

    def connect_ronald_jack_x629id(
        self, ip: str, port: int = DEFAULT_PORT, password: str = ""
    ) -> tuple[bool, str]:
        return self._connect_zkteco(ip=ip, port=port, password=password)

    def connect_senseface_a4(
        self, ip: str, port: int = DEFAULT_PORT, password: str = ""
    ) -> tuple[bool, str]:
        return self._connect_zkteco(ip=ip, port=port, password=password)

    def connect_device(
        self,
        device_name: str,
        ip: str,
        port: int = DEFAULT_PORT,
        password: str = "",
    ) -> tuple[bool, str]:
        """Chọn module kết nối theo tên máy.

        Hỗ trợ:
        - Ronald Jack X629ID
        - SenseFace A4
        Fallback: ZKTeco (cùng giao thức phổ biến).
        """

        name = (device_name or "").strip().lower()
        if "ronald" in name or "x629" in name:
            return self.connect_ronald_jack_x629id(ip=ip, port=port, password=password)
        if "senseface" in name or "a4" in name:
            return self.connect_senseface_a4(ip=ip, port=port, password=password)
        return self.connect_ronald_jack_x629id(ip=ip, port=port, password=password)

    def _connect_zkteco(self, ip: str, port: int, password: str) -> tuple[bool, str]:
        ip = (ip or "").strip()
        try:
            port = int(port)
        except Exception:
            port = self.DEFAULT_PORT

        # 1) Try real connect via `zk` library if available
        if importlib.util.find_spec("zk") is not None:
            try:
                # `zk` (pyzk) convention: from zk import ZK
                from zk import ZK  # type: ignore

                zk = ZK(ip, port=port, timeout=8, password=int(password or 0))
                conn = zk.connect()
                try:
                    # Một số dòng (đặc biệt dòng Face/Visible Light) có thể không hỗ trợ
                    # các lệnh như disable/enable_device. Chỉ probe nhẹ; fail thì bỏ qua.
                    self._zk_probe_best_effort(conn)
                finally:
                    try:
                        conn.disconnect()
                    except Exception:
                        pass

                return True, "Kết nối thiết bị thành công."
            except Exception as exc:
                logger.warning("Kết nối ZK thất bại (%s:%s): %s", ip, port, exc)
                # fallback to tcp below

        # 2) Fallback: TCP reachability
        if self.test_connection_tcp(ip, port):
            return (
                True,
                "Thiết bị có phản hồi TCP. (Không handshake ZKTeco đầy đủ)",
            )

        return False, "Không kết nối được thiết bị. Kiểm tra IP/Port và mạng LAN."

    def _zk_probe_best_effort(self, conn) -> None:
        """Probe nhẹ để xác nhận giao tiếp, không bắt buộc thiết bị phải hỗ trợ đầy đủ."""

        for method_name, args in (
            ("get_time", ()),
            ("get_device_name", ()),
            ("get_serialnumber", ()),
            ("get_firmware_version", ()),
        ):
            method = getattr(conn, method_name, None)
            if callable(method):
                try:
                    method(*args)
                except Exception:
                    # Bỏ qua lỗi probe; miễn là connect() thành công.
                    pass
