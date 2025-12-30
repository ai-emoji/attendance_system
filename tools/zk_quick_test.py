"""tools.zk_quick_test

Test nhanh kết nối và tải log từ máy chấm công ZKTeco-compatible (pyzk).

Chạy:
  H:/attendance_system/venv/Scripts/python.exe tools/zk_quick_test.py

Mặc định lọc 2 ngày: hôm nay và hôm qua.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta


logger = logging.getLogger(__name__)


def _connect(ip: str, port: int, password: int) -> object:
    from zk import ZK  # type: ignore

    # Nhiều mạng chặn ICMP => ưu tiên ommit_ping để giảm chờ.
    attempts: list[tuple[bool, bool, int]] = [
        (False, True, 8),
        (False, False, 8),
        (True, True, 10),
    ]

    last_exc: Exception | None = None
    for force_udp, ommit_ping, timeout in attempts:
        try:
            zk = ZK(
                ip,
                port=int(port),
                timeout=int(timeout),
                password=int(password),
                force_udp=bool(force_udp),
                ommit_ping=bool(ommit_ping),
            )
            t0 = datetime.now()
            conn = zk.connect()
            dt = (datetime.now() - t0).total_seconds()
            logger.info(
                "Kết nối OK (%.2fs) mode=%s%s",
                dt,
                "UDP" if force_udp else "TCP",
                "+ommit_ping" if ommit_ping else "",
            )
            return conn
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Kết nối thất bại mode=%s%s: %s",
                "UDP" if force_udp else "TCP",
                "+ommit_ping" if ommit_ping else "",
                exc,
            )

    raise RuntimeError(f"Không thể kết nối thiết bị: {last_exc}")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    ip = "192.168.1.17"
    port = 4370
    password = 0

    to_date = date.today()
    from_date = to_date - timedelta(days=1)

    logger.info("Test máy: %s:%s | range=%s..%s", ip, port, from_date, to_date)

    conn = None
    try:
        conn = _connect(ip=ip, port=port, password=password)

        # probe best-effort
        try:
            dn = getattr(conn, "get_device_name", None)
            if callable(dn):
                logger.info("Device name: %s", dn())
        except Exception as exc:
            logger.info("Probe get_device_name lỗi (bỏ qua): %s", exc)

        # Download all logs (pyzk limitation) then filter by date range.
        logger.info("Đang tải attendance logs (có thể lâu nếu máy nhiều dữ liệu)...")
        t1 = datetime.now()
        logs = []
        try:
            logs = conn.get_attendance() or []
        except Exception as exc:
            raise RuntimeError(f"get_attendance thất bại: {exc}")
        dt2 = (datetime.now() - t1).total_seconds()
        logger.info("Tải xong %s logs trong %.2fs", len(logs), dt2)

        start_dt = datetime.combine(from_date, time.min)
        end_dt = datetime.combine(to_date, time.max)

        filtered = 0
        sample = None
        for a in logs:
            try:
                ts = getattr(a, "timestamp", None)
                if ts is None:
                    continue
                if isinstance(ts, date) and not isinstance(ts, datetime):
                    ts = datetime.combine(ts, time.min)
                if not isinstance(ts, datetime):
                    continue
                if start_dt <= ts <= end_dt:
                    filtered += 1
                    if sample is None:
                        sample = a
            except Exception:
                continue

        logger.info("Số log trong khoảng %s..%s: %s", from_date, to_date, filtered)
        if sample is not None:
            logger.info(
                "Sample: user_id=%s timestamp=%s",
                getattr(sample, "user_id", None),
                getattr(sample, "timestamp", None),
            )

        return 0
    except Exception as exc:
        logger.exception("TEST THẤT BẠI: %s", exc)
        return 2
    finally:
        try:
            if conn is not None:
                conn.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
