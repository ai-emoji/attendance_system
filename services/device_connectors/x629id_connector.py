"""services.device_connectors.x629id_connector

Kết nối máy chấm công Ronald Jack X629ID.

Ưu tiên dùng thư viện `zk` (pyzk) nếu có để handshake thật.
Nếu không có `zk`, fallback test TCP port để kiểm tra reachable.

Return: (ok: bool, message: str)
"""

from __future__ import annotations

import importlib.util
import logging
import re
import socket


logger = logging.getLogger(__name__)


DEFAULT_PORT = 4370


def _extract_winerror_code(exc: Exception) -> int | None:
    try:
        if getattr(exc, "args", None) and isinstance(exc.args[0], int):
            return int(exc.args[0])
    except Exception:
        pass

    for attr in ("winerror", "errno"):
        try:
            value = getattr(exc, attr, None)
            if value is None:
                continue
            return int(value)
        except Exception:
            continue

    try:
        m = re.search(r"WinError\s*(\d+)", str(exc))
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _hint_for_exception(exc: Exception) -> str:
    code = _extract_winerror_code(exc)
    if code == 10054:
        return "(10054: kết nối bị thiết bị reset.)"
    if (
        isinstance(exc, (TimeoutError, socket.timeout))
        or "timed out" in str(exc).lower()
    ):
        return "(timeout: không nhận phản hồi; thường do port bị chặn/đóng hoặc khác mạng.)"
    return ""


def _test_connection_tcp(ip: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def _zk_probe_best_effort(conn) -> None:
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
                pass


def connect(ip: str, port: int = DEFAULT_PORT, password: str = "") -> tuple[bool, str]:
    ip = (ip or "").strip()
    try:
        port = int(port)
    except Exception:
        port = DEFAULT_PORT

    tcp_ok = _test_connection_tcp(ip, port, timeout=1.2)

    # 1) Try real connect via `zk` library if available
    if importlib.util.find_spec("zk") is not None:
        try:
            from zk import ZK  # type: ignore

            try:
                pwd = int(password or 0)
            except Exception:
                pwd = 0

            # Ronald Jack: thường chạy ổn với TCP; thử ommit_ping trước để tránh chậm do ICMP.
            attempts: list[tuple[bool, bool, int]] = []
            # (force_udp, ommit_ping, timeout)
            if not tcp_ok:
                # Nếu TCP không vào được port, thử nhanh UDP để có thêm tín hiệu rồi fail-fast.
                attempts.append((True, True, 5))
                attempts.append((True, False, 5))
            else:
                attempts.append((False, True, 8))
                attempts.append((False, False, 8))
                attempts.append((True, True, 8))

            last_exc: Exception | None = None
            saw_udp_reset = False
            saw_udp_timeout = False
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
                        _zk_probe_best_effort(conn)
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
                        "Kết nối X629ID thất bại (%s:%s) force_udp=%s ommit_ping=%s: %s %s",
                        ip,
                        port,
                        force_udp,
                        ommit_ping,
                        exc,
                        _hint_for_exception(exc),
                    )

                    if bool(force_udp):
                        code = _extract_winerror_code(exc)
                        if code == 10054:
                            saw_udp_reset = True
                        if (
                            isinstance(exc, (TimeoutError, socket.timeout))
                            or "timed out" in str(exc).lower()
                        ):
                            saw_udp_timeout = True

                        if not tcp_ok and saw_udp_reset:
                            return (
                                False,
                                "Không thể kết nối. Có dấu hiệu port đang đóng/sai: "
                                f"TCP timeout, UDP reset (10054) tại port {port}. "
                                "Hãy kiểm tra lại cổng giao tiếp và firewall/router.",
                            )

            if last_exc is not None:
                hint = "TCP OK" if tcp_ok else "TCP FAIL"
                if not tcp_ok and (saw_udp_reset or saw_udp_timeout):
                    return (
                        False,
                        "Không thể kết nối qua LAN SDK tại "
                        f"{ip}:{port}. (TCP timeout; UDP {'timeout' if saw_udp_timeout else 'reset'}) "
                        "Hãy kiểm tra: PC và thiết bị cùng subnet/VLAN, firewall/router không chặn, "
                        "thiết bị có bật giao tiếp TCP/IP/SDK.",
                    )
                return (
                    False,
                    "Kết nối thất bại. "
                    f"Trạng thái port {port}: {hint}. "
                    f"Lỗi: {last_exc} {_hint_for_exception(last_exc)}",
                )
        except Exception as exc:
            logger.warning("Kết nối X629ID qua ZK thất bại (%s:%s): %s", ip, port, exc)

    # 2) Fallback: TCP reachability
    if tcp_ok:
        return True, "Thiết bị có phản hồi TCP. (Không handshake ZKTeco đầy đủ)"

    return (
        False,
        "Không kết nối được thiết bị. "
        "Vui lòng kiểm tra: đúng IP, đúng port (thường 4370), cùng mạng LAN, firewall/router không chặn port.",
    )
