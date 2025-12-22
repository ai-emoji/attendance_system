"""services.download_attendance_services

Service cho nghiệp vụ "Tải dữ liệu Máy chấm công":
- Lấy danh sách máy từ bảng devices
- Tải log chấm công từ thiết bị (ZKTeco/pyzk nếu có)
- Gom nhóm theo (attendance_code, work_date) để tạo tối đa 3 cặp vào/ra
- Upsert vào download_attendance và attendance_raw
- Xóa bảng download_attendance khi đóng phần mềm (best-effort)
"""

from __future__ import annotations

import importlib.util
import logging
from dataclasses import dataclass
from datetime import date, datetime, time

from repository.device_repository import DeviceRepository
from repository.download_attendance_repository import DownloadAttendanceRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadAttendanceRow:
    attendance_code: str
    work_date: date
    time_in_1: time | None
    time_out_1: time | None
    time_in_2: time | None
    time_out_2: time | None
    time_in_3: time | None
    time_out_3: time | None
    device_no: int
    device_id: int | None
    device_name: str


class DownloadAttendanceService:
    def __init__(
        self,
        repo: DownloadAttendanceRepository | None = None,
        device_repo: DeviceRepository | None = None,
    ) -> None:
        self._repo = repo or DownloadAttendanceRepository()
        self._device_repo = device_repo or DeviceRepository()

    def list_devices_for_combo(self) -> list[tuple[int, str]]:
        rows = self._device_repo.list_devices()
        result: list[tuple[int, str]] = []
        for r in rows:
            try:
                result.append((int(r.get("id")), str(r.get("device_name") or "")))
            except Exception:
                continue
        return result

    def has_zk_library(self) -> bool:
        try:
            return importlib.util.find_spec("zk") is not None
        except Exception:
            return False

    def _norm(self, s: str) -> str:
        return "".join(ch.lower() for ch in (s or "") if ch.isalnum())

    def _expected_device_kind(self, device_name: str) -> str | None:
        """Suy ra loại máy từ tên đã lưu trong DB.

        Quy ước đơn giản để phân biệt 2 dòng máy:
        - ZKTeco SenseFace A4
        - Ronald Jack X629ID

        Người dùng có thể đặt device_name chứa các từ khóa để nhận dạng.
        """

        n = self._norm(device_name)
        if any(k in n for k in ("senseface", "a4", "zkteco")):
            return "SENSEFACE_A4"
        if any(k in n for k in ("ronaldjack", "ronald", "jack", "x629", "x629id")):
            return "X629ID"
        return None

    def _detect_device_kind_from_info(self, info: str) -> str | None:
        n = self._norm(info)
        if any(k in n for k in ("senseface", "a4", "zkteco")):
            return "SENSEFACE_A4"
        if any(k in n for k in ("ronaldjack", "ronald", "jack", "x629", "x629id")):
            return "X629ID"
        return None

    def _device_kind_label(self, kind: str | None) -> str:
        if kind == "SENSEFACE_A4":
            return "ZKTeco SenseFace A4"
        if kind == "X629ID":
            return "Ronald Jack X629ID"
        return "(không xác định)"

    def clear_download_attendance(self) -> None:
        try:
            self._repo.clear_download_attendance()
        except Exception:
            logger.exception("Không thể clear download_attendance (best-effort)")

    def list_download_attendance(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
        device_no: int | None = None,
    ) -> list[DownloadAttendanceRow]:
        def _fmt(d: date | None) -> str | None:
            return d.isoformat() if d else None

        rows = self._repo.list_download_attendance(
            from_date=_fmt(from_date),
            to_date=_fmt(to_date),
            device_no=device_no,
        )
        result: list[DownloadAttendanceRow] = []
        for r in rows:
            try:
                wd = r.get("work_date")
                if isinstance(wd, datetime):
                    wd = wd.date()
                if not isinstance(wd, date):
                    continue

                result.append(
                    DownloadAttendanceRow(
                        attendance_code=str(r.get("attendance_code") or ""),
                        work_date=wd,
                        time_in_1=r.get("time_in_1"),
                        time_out_1=r.get("time_out_1"),
                        time_in_2=r.get("time_in_2"),
                        time_out_2=r.get("time_out_2"),
                        time_in_3=r.get("time_in_3"),
                        time_out_3=r.get("time_out_3"),
                        device_no=(
                            int(r.get("device_no") or 0)
                            if r.get("device_no") is not None
                            else 0
                        ),
                        device_id=None,
                        device_name=str(r.get("device_name") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def download_from_device(
        self,
        device_id: int,
        from_date: date,
        to_date: date,
        progress_cb=None,
    ) -> tuple[bool, str, int]:
        """Tải dữ liệu từ máy và lưu DB.

        progress_cb signature (optional): (phase: str, done: int, total: int, message: str) -> None
        phase in: "fetch", "save", "done"
        """

        if not device_id:
            return False, "Vui lòng chọn máy chấm công.", 0

        if from_date > to_date:
            return False, "'Từ ngày' không được lớn hơn 'Đến ngày'.", 0

        device = self._device_repo.get_device(int(device_id))
        if not device:
            return False, "Không tìm thấy máy chấm công.", 0

        device_no = int(device.get("device_no") or 0)
        device_name = str(device.get("device_name") or "")
        ip = str(device.get("ip_address") or "")
        password_raw = str(device.get("password") or "")
        port = int(device.get("port") or 4370)

        expected_kind = self._expected_device_kind(device_name)
        if expected_kind is None:
            return (
                False,
                "Chưa xác định loại máy chấm công. Vui lòng đặt 'Tên máy' chứa 'SenseFace A4' hoặc 'X629ID' để tránh xung đột khi dùng 2 máy.",
                0,
            )

        if progress_cb:
            progress_cb("fetch", 0, 0, "Đang tải dữ liệu từ máy...")

        if importlib.util.find_spec("zk") is None:
            return (
                False,
                "Chưa cài thư viện 'zk' (pyzk) nên không thể tải dữ liệu từ máy.",
                0,
            )

        try:
            from zk import ZK  # type: ignore
        except Exception:
            return False, "Không thể import thư viện 'zk'.", 0

        try:
            try:
                password = int(password_raw or 0)
            except Exception:
                password = 0

            zk = ZK(ip, port=port, timeout=15, password=password)
            conn = zk.connect()
            try:
                # Nhận dạng thiết bị sau khi connect để tránh chọn nhầm loại máy
                info_parts: list[str] = []
                try:
                    for attr in (
                        "get_device_name",
                        "get_platform",
                        "get_serialnumber",
                        "get_firmware_version",
                    ):
                        fn = getattr(conn, attr, None)
                        if callable(fn):
                            v = fn()
                            if v:
                                info_parts.append(str(v))
                except Exception:
                    # Không để lỗi đọc info làm fail tải
                    pass

                info = " | ".join(info_parts)
                detected_kind = (
                    self._detect_device_kind_from_info(info) if info else None
                )

                # Chỉ chặn khi phát hiện chắc chắn đang kết nối nhầm dòng máy
                if detected_kind is not None and detected_kind != expected_kind:
                    return (
                        False,
                        "Đang kết nối nhầm loại máy chấm công. "
                        f"Máy đã chọn: {self._device_kind_label(expected_kind)}; "
                        f"Thiết bị thực tế: {self._device_kind_label(detected_kind)}. "
                        f"Thông tin thiết bị: {info}",
                        0,
                    )

                logs = conn.get_attendance() or []
            finally:
                try:
                    conn.disconnect()
                except Exception:
                    pass

            # Filter logs by date range
            start_dt = datetime.combine(from_date, time.min)
            end_dt = datetime.combine(to_date, time.max)

            filtered: list[tuple[str, datetime]] = []
            for a in logs:
                try:
                    user_id = str(getattr(a, "user_id", "") or "")
                    ts = getattr(a, "timestamp", None)
                    if not user_id or ts is None:
                        continue
                    if isinstance(ts, date) and not isinstance(ts, datetime):
                        ts = datetime.combine(ts, time.min)
                    if not isinstance(ts, datetime):
                        continue
                    if ts < start_dt or ts > end_dt:
                        continue
                    filtered.append((user_id, ts))
                except Exception:
                    continue

            # Group by (user_id, work_date)
            groups: dict[tuple[str, date], list[datetime]] = {}
            for user_id, ts in filtered:
                key = (user_id, ts.date())
                groups.setdefault(key, []).append(ts)

            # Build rows (max 6 timestamps -> 3 pairs)
            built: list[dict] = []
            total = len(groups)
            done = 0

            for (user_id, wd), ts_list in groups.items():
                ts_list.sort()
                times = [t.time().replace(microsecond=0) for t in ts_list[:6]]

                def _get(i: int) -> time | None:
                    return times[i] if i < len(times) else None

                built.append(
                    {
                        "attendance_code": user_id,
                        "work_date": wd.isoformat(),
                        "time_in_1": _get(0),
                        "time_out_1": _get(1),
                        "time_in_2": _get(2),
                        "time_out_2": _get(3),
                        "time_in_3": _get(4),
                        "time_out_3": _get(5),
                        "device_no": device_no,
                        "device_id": int(device_id),
                        "device_name": device_name,
                    }
                )

                done += 1
                if progress_cb and total > 0 and done % 50 == 0:
                    progress_cb("save", done, total, f"Đang xử lý {done}/{total}...")

            if progress_cb:
                progress_cb("save", 0, max(1, len(built)), "Đang lưu vào CSDL...")

            # Upsert temp + raw
            self._repo.upsert_download_attendance(built)
            self._repo.upsert_attendance_raw(built)

            if progress_cb:
                progress_cb("done", len(built), len(built), "Hoàn tất")

            return True, "Tải dữ liệu chấm công thành công.", len(built)
        except Exception:
            logger.exception("download_from_device thất bại")
            return (
                False,
                "Không thể tải dữ liệu. Vui lòng kiểm tra kết nối thiết bị/CSDL.",
                0,
            )
