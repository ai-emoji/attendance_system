"""services.device_connectors.senseface_a4_connector

Kết nối máy chấm công ZKTeco SenseFace A4.

Ưu tiên dùng thư viện `zk` (pyzk) nếu có để handshake thật.
Nếu không có `zk`, fallback test TCP port để kiểm tra reachable.

Ghi chú:
- SenseFace đời mới đôi khi cần `ommit_ping=True` (mạng chặn ICMP).
- Một số môi trường cần thử UDP.

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
    """Best-effort extract Windows socket error code like 10054."""

    # Common: OSError(10054, ...) or ConnectionResetError(10054, ...)
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

    # Fallback: parse from string like "[WinError 10054] ..."
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
        return (
            "(10054: kết nối bị thiết bị reset. Thường gặp khi dùng sai chế độ TCP/UDP; "
            "SenseFace A4 hay cần UDP hoặc ommit_ping=True.)"
        )
    if (
        isinstance(exc, (TimeoutError, socket.timeout))
        or "timed out" in str(exc).lower()
    ):
        return (
            "(timeout: không nhận phản hồi. Thường do sai port, thiết bị/PC khác mạng LAN, "
            "hoặc firewall/router chặn kết nối.)"
        )
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

    # Quick reachability check (keep small to avoid long UI wait)
    tcp_ok = _test_connection_tcp(ip, port, timeout=1.2)

    # 1) Try real connect via `zk` library if available
    if importlib.util.find_spec("zk") is not None:
        try:
            from zk import ZK  # type: ignore

            try:
                pwd = int(password or 0)
            except Exception:
                pwd = 0

            # SenseFace: ưu tiên UDP + ommit_ping.
            # Nếu TCP port không connect được, bỏ qua các attempt TCP để tránh chờ timeout dài.
            attempts: list[tuple[bool, bool, int]] = []
            # (force_udp, ommit_ping, timeout)
            if not tcp_ok:
                attempts.append((True, True, 5))
                attempts.append((True, False, 5))
            else:
                attempts.append((True, True, 10))
                attempts.append((False, True, 8))
                attempts.append((True, False, 10))
                attempts.append((False, False, 8))

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
                    hint = _hint_for_exception(exc)

                    if bool(force_udp) and isinstance(
                        exc, (TimeoutError, socket.timeout)
                    ):
                        saw_udp_timeout = True

                    # Nếu UDP báo reset/unreachable và TCP cũng không connect được,
                    # khả năng cao port đang đóng/sai -> dừng sớm để tránh chờ timeout dài.
                    if bool(force_udp):
                        code = _extract_winerror_code(exc)
                        if code == 10054:
                            saw_udp_reset = True
                            if not tcp_ok:
                                return (
                                    False,
                                    "Không thể kết nối. Có dấu hiệu port đang đóng/sai: "
                                    f"TCP timeout, UDP reset (10054) tại port {port}. "
                                    "Hãy kiểm tra lại cổng giao tiếp (comm port) trên máy SenseFace A4 "
                                    "và firewall/router.",
                                )

                    logger.warning(
                        "Kết nối SenseFace A4 thất bại (%s:%s) force_udp=%s ommit_ping=%s: %s %s",
                        ip,
                        port,
                        force_udp,
                        ommit_ping,
                        exc,
                        hint,
                    )

            if last_exc is not None:
                hint = "TCP OK" if tcp_ok else "TCP FAIL"

                # Fail-fast message for the most common field issue:
                # TCP timeout + UDP timeout/reset often means port is blocked/closed or device is not allowing LAN SDK.
                if not tcp_ok and (saw_udp_timeout or saw_udp_reset):
                    return (
                        False,
                        "Không thể kết nối qua LAN SDK tại "
                        f"{ip}:{port}. (TCP timeout; UDP {'timeout' if saw_udp_timeout else 'reset'}) "
                        "Hãy kiểm tra: PC và thiết bị cùng subnet/VLAN, firewall/router không chặn, "
                        "thiết bị có bật giao tiếp TCP/IP/SDK (nếu đang để chế độ Cloud có thể không mở SDK LAN).",
                    )
                return (
                    False,
                    "Kết nối thất bại. "
                    f"Trạng thái port {port}: {hint}. "
                    f"Lỗi: {last_exc} {_hint_for_exception(last_exc)}",
                )
        except Exception as exc:
            logger.warning(
                "Kết nối SenseFace A4 qua ZK thất bại (%s:%s): %s", ip, port, exc
            )

    # 2) Fallback: TCP reachability
    if tcp_ok:
        return True, "Thiết bị có phản hồi TCP. (Không handshake ZKTeco đầy đủ)"

    return (
        False,
        "Không kết nối được thiết bị. "
        "Vui lòng kiểm tra: đúng IP, đúng port (thường 4370), cùng mạng LAN, firewall/router không chặn port.",
    )
