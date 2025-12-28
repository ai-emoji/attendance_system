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
        # SenseFace/Face dòng mới đôi khi cần ommit_ping hoặc force_udp
        return self._connect_zkteco(
            ip=ip, port=port, password=password, prefer_senseface=True
        )

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

        name = (device_name or "").strip().lower()
        if "senseface" in name or "a4" in name:
            return self.connect_senseface_a4(ip=ip, port=port, password=password)
        return self.connect_ronald_jack_x629id(ip=ip, port=port, password=password)

    def _connect_zkteco(
        self,
        ip: str,
        port: int,
        password: str,
        prefer_senseface: bool = False,
    ) -> tuple[bool, str]:
        ip = (ip or "").strip()
        try:
            port = int(port)
        except Exception:
            port = self.DEFAULT_PORT

        # Basic reachability hint first
        tcp_ok = self.test_connection_tcp(ip, port)

        # 1) Try real connect via `zk` library if available
        if importlib.util.find_spec("zk") is not None:
            try:
                # `zk` (pyzk) convention: from zk import ZK
                from zk import ZK  # type: ignore

                try:
                    pwd = int(password or 0)
                except Exception:
                    pwd = 0

                attempts: list[tuple[bool, bool, int]] = []
                # (force_udp, ommit_ping, timeout)
                attempts.append((False, False, 8))
                attempts.append((False, True, 8))
                # SenseFace: thường cần bỏ ping; thử UDP ở cuối
                attempts.append((True, True, 10 if prefer_senseface else 8))

                last_exc: Exception | None = None
                for force_udp, ommit_ping, timeout in attempts:
                    try:
                        zk = ZK(
                            ip,
                            port=port,
                            timeout=int(timeout),
                            password=pwd,
                            force_udp=bool(force_udp),
                            ommit_ping=bool(ommit_ping),
                        )
                        conn = zk.connect()
                        try:
                            self._zk_probe_best_effort(conn)
                        finally:
                            try:
                                conn.disconnect()
                            except Exception:
                                pass

                        mode = []
                        mode.append("UDP" if force_udp else "TCP")
                        if ommit_ping:
                            mode.append("ommit_ping")
                        return True, f"Kết nối thiết bị thành công ({', '.join(mode)})."
                    except Exception as exc:
                        last_exc = exc
                        logger.warning(
                            "Kết nối ZK thất bại (%s:%s) force_udp=%s ommit_ping=%s: %s",
                            ip,
                            port,
                            force_udp,
                            ommit_ping,
                            exc,
                        )

                if last_exc is not None:
                    hint = "TCP OK" if tcp_ok else "TCP FAIL"
                    return (
                        False,
                        "Kết nối thất bại. "
                        f"Trạng thái port {port}: {hint}. "
                        f"Lỗi: {last_exc}",
                    )
            except Exception as exc:
                logger.warning("Kết nối ZK thất bại (%s:%s): %s", ip, port, exc)
                # fallback to tcp below

        # 2) Fallback: TCP reachability
        if tcp_ok:
            return (
                True,
                "Thiết bị có phản hồi TCP. (Không handshake ZKTeco đầy đủ)",
            )

        return (
            False,
            "Không kết nối được thiết bị. "
            "Vui lòng kiểm tra: đúng IP, đúng port (thường 4370), cùng mạng LAN, firewall/router không chặn port.",
        )

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
