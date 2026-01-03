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
import time as time_module
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from repository.device_repository import DeviceRepository
from repository.attendance_audit_repository import AttendanceAuditRepository
from repository.employee_repository import EmployeeRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DownloadAttendanceRow:
    attendance_code: str
    name_on_mcc: str
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
        device_repo: DeviceRepository | None = None,
    ) -> None:
        self._device_repo = device_repo or DeviceRepository()
        self._audit_repo = AttendanceAuditRepository()
        self._employee_repo = EmployeeRepository()

    def list_devices_for_combo(self) -> list[tuple[int, str]]:
        rows = self._device_repo.list_devices()
        result: list[tuple[int, str]] = []
        for r in rows:
            try:
                result.append((int(r.get("id")), str(r.get("device_name") or "")))
            except Exception:
                continue
        return result

    def get_device_no_by_id(self, device_id: int | None) -> int | None:
        if not device_id:
            return None
        try:
            device = self._device_repo.get_device(int(device_id))
        except Exception:
            return None
        if not device:
            return None
        try:
            return int(device.get("device_no") or 0)
        except Exception:
            return None

    def has_zk_library(self) -> bool:
        try:
            return importlib.util.find_spec("zk") is not None
        except Exception:
            return False

    def _norm(self, s: str) -> str:
        return "".join(ch.lower() for ch in (s or "") if ch.isalnum())

    def _expected_device_kind(self, device_type: str) -> str | None:
        dt = (device_type or "").strip().upper()
        if dt in ("SENSEFACE_A4", "X629ID"):
            return dt
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
        """Giữ tương thích API cũ.

        Trước đây app xóa bảng tạm download_attendance khi thoát.
        Hiện tại luồng tải ghi trực tiếp vào attendance_audit_YYYY,
        nên không còn dữ liệu tạm để xóa.
        """

        return

    def list_download_attendance(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
        device_no: int | None = None,
    ) -> list[DownloadAttendanceRow]:
        # IMPORTANT:
        # - Màn tải dữ liệu ưu tiên hiển thị từ attendance_audit_YYYY.
        # - Không sinh "ngày trống" ở layer đọc; các ngày không chấm công (nếu cần)
        #   sẽ được ghi thực vào attendance_audit_YYYY ở bước tải.

        def _fmt(d: date | None) -> str | None:
            return d.isoformat() if d else None

        rows = self._audit_repo.list_download_attendance_rows(
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
                        # Prefer name_on_mcc if available; fall back to full_name.
                        name_on_mcc=str(
                            r.get("name_on_mcc") or r.get("full_name") or ""
                        ),
                        work_date=wd,
                        # audit table uses in_1/out_1 naming.
                        time_in_1=r.get("in_1"),
                        time_out_1=r.get("out_1"),
                        time_in_2=r.get("in_2"),
                        time_out_2=r.get("out_2"),
                        time_in_3=r.get("in_3"),
                        time_out_3=r.get("out_3"),
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

    def has_audit_data(
        self,
        *,
        from_date: date,
        to_date: date,
        device_no: int,
    ) -> bool:
        """Return True if audit has at least one row for every day in range.

        Used by UI to skip device connection only when the date range
        appears already populated.
        """

        try:
            return bool(
                self._audit_repo.has_any_row_each_day(
                    from_date=from_date.isoformat(),
                    to_date=to_date.isoformat(),
                    device_no=int(device_no),
                )
            )
        except Exception:
            # Best-effort: if check fails, do not block download.
            return False

    def download_from_device(
        self,
        device_id: int,
        from_date: date,
        to_date: date,
        progress_cb=None,
    ) -> tuple[bool, str, int]:
        """Tải dữ liệu từ máy và lưu DB.

        progress_cb signature (optional): (phase: str, done: int, total: int, message: str) -> None
        phase in: "connect", "download", "save", "done" (backward compatible: may emit "fetch")
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
        device_type = str(device.get("device_type") or "")
        ip = str(device.get("ip_address") or "")
        password_raw = str(device.get("password") or "")
        port = int(device.get("port") or 4370)

        expected_kind = self._expected_device_kind(device_type)
        if expected_kind is None:
            return (
                False,
                "Chưa thiết lập loại máy chấm công cho thiết bị này. Vui lòng vào mục 'Thiết bị' và chọn đúng loại máy (SenseFace A4 hoặc X629ID) rồi lưu lại.",
                0,
            )

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

        def _is_timeout_error(exc: Exception) -> bool:
            msg = str(exc).lower()
            return "timed out" in msg or "timeout" in msg

        def _fetch_attendance_with_retry() -> tuple[list, str | None]:
            """Return (logs, error_message). error_message is None on success."""
            base_timeout = 15
            max_attempts = 3

            last_err: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                timeout = base_timeout + (attempt - 1) * 10
                if progress_cb:
                    progress_cb(
                        "connect",
                        attempt - 1,
                        max_attempts,
                        f"Đang kết nối với {device_name or '<máy chấm công>'}... (lần {attempt}/{max_attempts})",
                    )

                try:
                    zk = ZK(ip, port=port, timeout=timeout, password=password)
                    conn = zk.connect()
                    try:
                        if progress_cb:
                            progress_cb(
                                "connect",
                                max_attempts,
                                max_attempts,
                                f"Kết nối {device_name or '<máy chấm công>'} thành công.",
                            )

                        # Fetch user list (best-effort) to map user_id -> name on device
                        user_name_by_id: dict[str, str] = {}
                        try:
                            users = None
                            fn_users = getattr(conn, "get_users", None)
                            if callable(fn_users):
                                users = fn_users() or []
                            for u in users or []:
                                try:
                                    uid = str(getattr(u, "user_id", "") or "").strip()
                                    nm = str(getattr(u, "name", "") or "").strip()
                                    if uid:
                                        user_name_by_id[uid] = nm
                                except Exception:
                                    continue
                        except Exception:
                            user_name_by_id = {}

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
                            pass

                        info = " | ".join(info_parts)
                        detected_kind = (
                            self._detect_device_kind_from_info(info) if info else None
                        )

                        # Chỉ chặn khi phát hiện chắc chắn đang kết nối nhầm dòng máy
                        if detected_kind is not None and detected_kind != expected_kind:
                            return (
                                [],
                                "Đang kết nối nhầm loại máy chấm công. "
                                f"Máy đã chọn: {self._device_kind_label(expected_kind)}; "
                                f"Thiết bị thực tế: {self._device_kind_label(detected_kind)}. "
                                f"Thông tin thiết bị: {info}",
                            )

                        if progress_cb:
                            progress_cb(
                                "download",
                                0,
                                0,
                                f"Đang tải dữ liệu từ {device_name or '<máy chấm công>'}...",
                            )

                        logs = conn.get_attendance() or []

                        if progress_cb:
                            progress_cb(
                                "download",
                                1,
                                1,
                                "Tải dữ liệu thành công.",
                            )
                        # Attach mapping to outer scope by returning via closure var
                        return ([(user_name_by_id, logs)], None)
                    finally:
                        try:
                            conn.disconnect()
                        except Exception:
                            pass
                except Exception as e:
                    last_err = e
                    logger.warning(
                        "Tải dữ liệu từ máy thất bại (lần %s/%s) ip=%s port=%s timeout=%s: %s",
                        attempt,
                        max_attempts,
                        ip,
                        port,
                        timeout,
                        e,
                    )

                    if attempt < max_attempts:
                        # backoff nhẹ để tránh spam thiết bị
                        time_module.sleep(1.0)
                        continue

            if last_err is None:
                return [], "Không thể kết nối tới thiết bị."

            if _is_timeout_error(last_err):
                return (
                    [],
                    f"Thiết bị không phản hồi (timeout) khi tải dữ liệu. Vui lòng kiểm tra mạng/điện/port. (IP: {ip}, Port: {port})",
                )

            return (
                [],
                f"Không thể tải dữ liệu từ thiết bị. (IP: {ip}, Port: {port})",
            )

        try:
            try:
                password = int(password_raw or 0)
            except Exception:
                password = 0

            # Retry + tăng timeout để giảm lỗi ZKNetworkError: timed out
            fetched, fetch_err = _fetch_attendance_with_retry()
            if fetch_err:
                return False, fetch_err, 0

            # unpack closure-returned data
            user_name_by_id, logs = fetched[0]

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

            downloaded_events = int(len(filtered))

            # Group by (user_id, work_date)
            groups: dict[tuple[str, date], list[datetime]] = {}
            for user_id, ts in filtered:
                key = (user_id, ts.date())
                groups.setdefault(key, []).append(ts)

            # Build rows (max 6 timestamps -> 3 pairs)
            built: list[dict] = []
            built_keys: set[tuple[str, date]] = set()
            total = len(groups)
            done = 0

            # Throttle: ~100 updates max (mượt mà nhưng không spam UI)
            step = max(1, int(total / 100)) if total > 0 else 1

            for (user_id, wd), ts_list in groups.items():
                ts_list.sort()
                times = [t.time().replace(microsecond=0) for t in ts_list[:6]]

                def _get(i: int) -> time | None:
                    return times[i] if i < len(times) else None

                built.append(
                    {
                        "attendance_code": user_id,
                        "name_on_mcc": str(user_name_by_id.get(str(user_id), "") or ""),
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
                built_keys.add((str(user_id), wd))

                done += 1
                if progress_cb and total > 0 and (done % step == 0 or done == total):
                    progress_cb(
                        "save",
                        done,
                        total,
                        f"Đang lưu vào cơ sở dữ liệu {done}/{total}",
                    )

            if progress_cb:
                progress_cb(
                    "save",
                    0,
                    max(1, len(built)),
                    f"Đang lưu vào cơ sở dữ liệu 0/{max(1, len(built))}",
                )

            # Build employee code set early so we can compute total rows to write
            # (punch rows + no-punch rows) before starting DB writes.
            code_to_name: dict[str, str] = {}

            try:
                employees = self._employee_repo.list_employees()
            except Exception:
                employees = []

            for e in employees or []:
                code = str(e.get("mcc_code") or "").strip()
                if not code:
                    continue
                nm = str(e.get("name_on_mcc") or "" or "").strip()
                if not nm:
                    nm = str(e.get("full_name") or "").strip()
                if code not in code_to_name:
                    code_to_name[code] = nm

            # Always include codes that appear in logs.
            for code, _wd in built_keys:
                if code and code not in code_to_name:
                    code_to_name[code] = str(user_name_by_id.get(code) or "").strip()

            # Compute total records to persist into temp/raw within the selected date range
            codes = list(code_to_name.keys())
            days = (to_date - from_date).days if from_date <= to_date else 0
            total_combo = (days + 1) * len(codes) if codes else 0
            present = 0
            if total_combo > 0 and built_keys:
                code_set = set(codes)
                for c, d in built_keys:
                    if c in code_set and from_date <= d <= to_date:
                        present += 1
            missing = max(0, total_combo - present)
            total_rows_to_write = int(len(built)) + int(missing)
            total_to_save = max(1, total_rows_to_write)

            # Overall work units to keep progress monotonic in UI:
            # This download writes directly to attendance_audit_YYYY only.
            total_work_units = max(1, int(total_to_save))

            work_done_units = 0

            def _emit_save_progress(
                label: str, stage_done: int, stage_total: int
            ) -> None:
                if not progress_cb:
                    return
                # Work-done unit is monotonic; stage counters are shown in message.
                progress_cb(
                    "save",
                    int(work_done_units),
                    int(total_work_units),
                    f"Đang lưu vào cơ sở dữ liệu {int(stage_done)}/{int(max(1, stage_total))} ({label})",
                )

            # Start save phase immediately to avoid UI stalling at the end of download (~69%).
            _emit_save_progress("chuẩn bị", 0, total_to_save)

            # Upsert punch rows into attendance_audit_YYYY
            if built:

                def _hook_audit(done_rows: int, total_rows: int) -> None:
                    nonlocal work_done_units
                    work_done_units = int(done_rows)
                    _emit_save_progress("bảng tổng hợp", work_done_units, total_to_save)

                try:
                    self._audit_repo.upsert_from_download_rows(
                        built,
                        batch_size=500,
                        progress_hook=_hook_audit,
                    )
                except Exception:
                    logger.exception("Không thể ghi attendance_audit khi tải dữ liệu")
            work_done_units = int(len(built))

            # Persist placeholder rows for days without punches (không chấm công).
            # Must NOT overwrite existing punch rows; upsert query uses
            # COALESCE(VALUES(in_x), in_x) so NULL placeholders won't overwrite.

            no_punch_written = 0

            # Stream-generate no-punch rows and insert in batches to keep UI responsive
            if codes and from_date <= to_date:
                if progress_cb:
                    progress_cb(
                        "save",
                        int(work_done_units),
                        int(total_work_units),
                        "Đang tạo và lưu dữ liệu không chấm công...",
                    )

                batch: list[dict] = []
                batch_size = 1000

                def _flush_batch() -> None:
                    nonlocal batch, no_punch_written, work_done_units
                    if not batch:
                        return

                    # Upsert audit placeholders (best-effort)
                    done_before = int(work_done_units)

                    def _hook_np_audit(done_rows: int, total_rows: int) -> None:
                        nonlocal work_done_units
                        work_done_units = done_before + int(done_rows)
                        _emit_save_progress(
                            "không chấm công - bảng tổng hợp",
                            work_done_units,
                            total_to_save,
                        )

                    try:
                        self._audit_repo.upsert_from_download_rows(
                            batch,
                            batch_size=500,
                            progress_hook=_hook_np_audit,
                        )
                    except Exception:
                        logger.exception(
                            "Không thể ghi attendance_audit khi tải dữ liệu"
                        )
                    work_done_units = done_before + int(len(batch))

                    no_punch_written += int(len(batch))
                    batch = []

                for offset in range(days + 1):
                    d = from_date + timedelta(days=offset)
                    for code in codes:
                        if (code, d) in built_keys:
                            continue
                        nm = code_to_name.get(code) or ""
                        batch.append(
                            {
                                "attendance_code": code,
                                "name_on_mcc": str(nm or ""),
                                "work_date": d.isoformat(),
                                "time_in_1": None,
                                "time_out_1": None,
                                "time_in_2": None,
                                "time_out_2": None,
                                "time_in_3": None,
                                "time_out_3": None,
                                "device_no": device_no,
                                "device_id": int(device_id),
                                "device_name": device_name,
                            }
                        )
                        if len(batch) >= batch_size:
                            _flush_batch()

                _flush_batch()

            if progress_cb:
                progress_cb(
                    "save",
                    int(total_work_units),
                    int(total_work_units),
                    f"Đang lưu vào cơ sở dữ liệu {total_to_save}/{total_to_save}",
                )

            if progress_cb:
                progress_cb("done", 1, 1, "Hoàn tất")

            punch_rows = int(len(built))
            total_written_rows = int(punch_rows + no_punch_written)

            return (
                True,
                "Tải dữ liệu chấm công thành công. "
                f"Đã tải: {downloaded_events} lượt; "
                f"Đã ghi: {total_written_rows} dòng (chấm công: {punch_rows}, không chấm công: {no_punch_written}).",
                int(punch_rows),
            )
        except Exception:
            logger.exception("download_from_device thất bại")
            return (
                False,
                "Không thể tải dữ liệu. Vui lòng kiểm tra kết nối thiết bị/CSDL.",
                0,
            )
