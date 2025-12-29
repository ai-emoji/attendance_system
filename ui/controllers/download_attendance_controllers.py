"""ui.controllers.download_attendance_controllers

Controller cho màn "Tải dữ liệu Máy chấm công":
- Load danh sách thiết bị vào combobox
- Click "Tải dữ liệu chấm công" -> tải log từ máy, hiển thị tiến trình
- Sau khi tải: hiển thị data trong bảng (download_attendance)

Không dùng QMessageBox; dùng MessageDialog.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from core.threads import BackgroundTaskRunner
from PySide6.QtCore import QTimer

from services.download_attendance_services import DownloadAttendanceService
from ui.dialog.loading_dialog import LoadingDialog
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class _UiProxy(QObject):
    """Đảm bảo các slot chạy trên UI thread.

    Lưu ý: nếu connect signal từ worker thread tới Python callable thường,
    callable có thể chạy trên worker thread -> tạo QObject con với parent UI sẽ lỗi.
    """

    def __init__(self, controller: "DownloadAttendanceController", parent=None) -> None:
        super().__init__(parent)
        self._controller = controller

    @Slot(str, int, int, str)
    def on_progress(self, phase: str, done: int, total: int, message: str) -> None:
        self._controller._on_worker_progress_ui(phase, done, total, message)

    @Slot(bool, str, int)
    def on_finished(self, ok: bool, msg: str, count: int) -> None:
        self._controller._on_worker_finished_ui(ok, msg, count)


class _Worker(QObject):
    progress = Signal(str, int, int, str)  # phase, done, total, message
    finished = Signal(bool, str, int)  # ok, msg, count

    def __init__(
        self, service: DownloadAttendanceService, device_id: int, d1: date, d2: date
    ) -> None:
        super().__init__()
        self._service = service
        self._device_id = int(device_id)
        self._d1 = d1
        self._d2 = d2

    @Slot()
    def run(self) -> None:
        try:

            def cb(phase: str, done: int, total: int, message: str) -> None:
                self.progress.emit(
                    str(phase), int(done), int(total), str(message or "")
                )

            ok, msg, count = self._service.download_from_device(
                device_id=self._device_id,
                from_date=self._d1,
                to_date=self._d2,
                progress_cb=cb,
            )
            self.finished.emit(bool(ok), str(msg or ""), int(count or 0))
        except Exception as exc:
            # Không để exception trong thread làm app thoát
            self.finished.emit(False, f"Không thể tải dữ liệu: {exc}", 0)


@dataclass
class _UiRow:
    code: str
    name_on_mcc: str
    date_str: str
    in1: str
    out1: str
    in2: str
    out2: str
    in3: str
    out3: str
    device_name: str


class DownloadAttendanceController:
    def __init__(
        self,
        parent_window,
        title_bar2,
        content,
        service: DownloadAttendanceService | None = None,
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or DownloadAttendanceService()

        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._progress: LoadingDialog | None = None
        self._progress_update_timer: QTimer | None = None
        self._pending_progress: tuple[str, int, int, str] | None = None
        self._last_progress_phase: str | None = None
        self._last_progress_total: int | None = None

        # Keep phase for minor UX decisions
        self._progress_phase: str | None = None

        # While connecting, device calls may block for a while (no progress callbacks).
        # Run a small UI-side pulse so it doesn't look "treo".
        self._connect_pulse_timer: QTimer | None = None
        self._connect_pulse_value: int = 0

        # Proxy QObject để slot chạy đúng UI thread
        self._ui_proxy = _UiProxy(self, parent=self._parent_window)

        self._all_rows: list[_UiRow] = []
        self._search_by: str = "attendance_code"
        self._search_text: str = ""
        self._show_seconds: bool = True

        self._devices_runner = BackgroundTaskRunner(
            self._parent_window, name="download_attendance_devices"
        )
        self._table_runner = BackgroundTaskRunner(
            self._parent_window, name="download_attendance_table"
        )

    def bind(self) -> None:
        self._title_bar2.download_clicked.connect(self.on_download)
        if hasattr(self._title_bar2, "search_changed"):
            self._title_bar2.search_changed.connect(self.on_search_changed)
        if hasattr(self._title_bar2, "time_format_changed"):
            self._title_bar2.time_format_changed.connect(self.on_time_format_changed)
        self.refresh_devices()
        self.refresh_table()

        # Ensure initial render matches UI button default
        try:
            # default button is HH:MM:SS
            self._show_seconds = True
        except Exception:
            pass

    def refresh_devices(self) -> None:
        def _fn() -> object:
            return list(self._service.list_devices_for_combo() or [])

        def _ok(result: object) -> None:
            devices = list(result or []) if isinstance(result, list) else []
            self._title_bar2.set_devices(devices)

        def _err(_msg: str) -> None:
            logger.exception("Không thể tải danh sách máy")
            try:
                self._title_bar2.set_devices([])
            except Exception:
                pass

        self._devices_runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def refresh_table(self) -> None:
        # Bảng tạm hiển thị dữ liệu đã tải trong phiên.
        # Yêu cầu: dữ liệu tạm chỉ xóa khi thoát app -> khi mở lại màn hình,
        # phải hiển thị lại dữ liệu tạm (không phụ thuộc date picker đang để hôm nay).
        def _fn() -> object:
            rows = self._service.list_download_attendance(
                from_date=None,
                to_date=None,
                device_no=None,
            )
            return [self._to_ui_row(r) for r in (rows or [])]

        def _ok(result: object) -> None:
            self._all_rows = list(result or []) if isinstance(result, list) else []
            self._apply_filters()

        def _err(_msg: str) -> None:
            logger.exception("Không thể load bảng download_attendance")
            self._all_rows = []
            try:
                self._content.set_attendance_rows([])
            except RuntimeError:
                return
            except Exception:
                pass
            try:
                if hasattr(self._title_bar2, "set_total"):
                    self._title_bar2.set_total(0)
            except Exception:
                pass

        self._table_runner.run(fn=_fn, on_success=_ok, on_error=_err, coalesce=True)

    def _to_ui_row(self, r) -> _UiRow:
        def fmt_date(d: date) -> str:
            return d.strftime("%d/%m/%Y")

        def fmt_time(t) -> str:
            if t is None:
                return ""
            # mysql connector có thể trả về datetime.timedelta, datetime.time, hoặc str
            if isinstance(t, str):
                return t
            if hasattr(t, "strftime"):
                try:
                    return t.strftime("%H:%M:%S")
                except Exception:
                    pass
            return str(t)

        wd = r.work_date
        if isinstance(wd, datetime):
            wd = wd.date()

        return _UiRow(
            code=str(r.attendance_code or ""),
            name_on_mcc=str(getattr(r, "name_on_mcc", "") or ""),
            date_str=fmt_date(wd),
            in1=fmt_time(r.time_in_1),
            out1=fmt_time(r.time_out_1),
            in2=fmt_time(r.time_in_2),
            out2=fmt_time(r.time_out_2),
            in3=fmt_time(r.time_in_3),
            out3=fmt_time(r.time_out_3),
            device_name=str(r.device_name or ""),
        )

    def on_search_changed(self) -> None:
        try:
            if hasattr(self._title_bar2, "get_search_filters"):
                f = self._title_bar2.get_search_filters() or {}
                self._search_by = str(f.get("search_by") or "attendance_code").strip()
                self._search_text = str(f.get("search_text") or "").strip()
        except Exception:
            self._search_by = "attendance_code"
            self._search_text = ""
        self._apply_filters()

    def on_time_format_changed(self, show_seconds: bool) -> None:
        self._show_seconds = bool(show_seconds)
        self._apply_filters()

    def _apply_filters(self) -> None:
        needle = str(self._search_text or "").strip().lower()
        by = str(self._search_by or "attendance_code").strip()

        if not needle:
            filtered = list(self._all_rows)
        else:
            if by == "name_on_mcc":
                filtered = [
                    u for u in self._all_rows if needle in str(u.name_on_mcc).lower()
                ]
            else:
                filtered = [u for u in self._all_rows if needle in str(u.code).lower()]

        try:
            self._content.set_attendance_rows(
                [
                    (
                        u.code,
                        u.name_on_mcc,
                        u.date_str,
                        self._fmt_time(u.in1),
                        self._fmt_time(u.out1),
                        self._fmt_time(u.in2),
                        self._fmt_time(u.out2),
                        self._fmt_time(u.in3),
                        self._fmt_time(u.out3),
                        u.device_name,
                    )
                    for u in filtered
                ]
            )
        except RuntimeError:
            # view already destroyed
            return
        try:
            if hasattr(self._title_bar2, "set_total"):
                self._title_bar2.set_total(len(filtered))
        except Exception:
            pass

    def _fmt_time(self, s: str) -> str:
        v = str(s or "")
        if not v:
            return ""
        if self._show_seconds:
            return v
        # HH:MM (avoid trailing ':')
        if ":" in v:
            parts = v.split(":")
            if len(parts) >= 2:
                hh = (parts[0] or "").zfill(2)
                mm = (parts[1] or "").zfill(2)
                return f"{hh[:2]}:{mm[:2]}"
        return v

    def on_download(self) -> None:
        device_id = self._title_bar2.get_selected_device_id()
        if not device_id:
            MessageDialog.info(
                self._parent_window, "Thông báo", "Vui lòng chọn máy chấm công."
            )
            return

        d1, d2 = self._title_bar2.get_date_range()
        if d1 > d2:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "'Từ ngày' không được lớn hơn 'Đến ngày'.",
            )
            return

        # Preflight: nếu thiếu thư viện/điều kiện thì báo ngay, không bật progress/thread
        try:
            if (
                hasattr(self._service, "has_zk_library")
                and not self._service.has_zk_library()
            ):
                MessageDialog.info(
                    self._parent_window,
                    "Không thể tải",
                    "Chưa cài thư viện 'zk' (pyzk) nên không thể tải dữ liệu từ máy.",
                )
                return
        except Exception:
            # Nếu preflight lỗi, vẫn cho chạy luồng bình thường
            pass

        # UI yêu cầu: chỉ hiển thị 3 trạng thái (kết nối / tải / lưu), không show chi tiết.
        # Vẫn giữ thanh loading nền (busy/indeterminate).

        # Loading dialog (shared UX)
        dlg = LoadingDialog(
            self._parent_window,
            title="Tải dữ liệu Máy chấm công",
            message="Đang kết nối...",
        )
        try:
            dlg.set_indeterminate(True, "Đang kết nối...")
        except Exception:
            pass
        # Avoid "too fast" feel on small downloads
        try:
            dlg.set_min_duration_ms(1200)
        except Exception:
            pass
        self._progress = dlg
        self._pending_progress = None
        self._last_progress_phase = None
        self._last_progress_total = None

        self._progress_phase = None
        self._connect_pulse_value = 0

        # Show initial state immediately (and start pulse while waiting for device connect).
        self._set_smooth_progress_state(
            "connect",
            0,
            0,
            "Đang kết nối...",
        )

        # Ẩn bảng trong lúc đang tải để tránh hiển thị dữ liệu cũ.
        try:
            if (
                hasattr(self._content, "table_frame")
                and self._content.table_frame is not None
            ):
                self._content.table_frame.setVisible(False)
        except Exception:
            pass

        # Worker thread
        # Giữ reference để tránh worker bị GC (có thể làm app crash/thoát)
        thread = QThread(self._parent_window)
        worker = _Worker(self._service, int(device_id), d1, d2)
        worker.moveToThread(thread)

        worker.progress.connect(self._ui_proxy.on_progress)
        worker.finished.connect(self._ui_proxy.on_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        thread.started.connect(worker.run)

        self._thread = thread
        self._worker = worker

        # Show dialog first to avoid paint/close race
        try:
            dlg.show()
        except Exception:
            pass
        QTimer.singleShot(0, thread.start)

    def _on_worker_progress_ui(
        self, phase: str, done: int, total: int, message: str
    ) -> None:
        if self._progress is None:
            return

        # Coalesce updates to avoid repaint storms
        self._pending_progress = (str(phase), int(done), int(total), str(message or ""))

        if self._progress_update_timer is None:
            self._progress_update_timer = QTimer(self._parent_window)
            self._progress_update_timer.setSingleShot(True)
            self._progress_update_timer.timeout.connect(self._apply_pending_progress)

        if not self._progress_update_timer.isActive():
            # ~30ms throttle
            self._progress_update_timer.start(30)

    def _apply_pending_progress(self) -> None:
        if self._progress is None or self._pending_progress is None:
            return

        phase, done, total, message = self._pending_progress
        self._pending_progress = None

        # Normalize phases: support new phases (connect/download/save/done)
        # and backward compatible old phase "fetch".
        norm = str(phase or "").strip().lower()
        if norm == "fetch":
            # Old service used "fetch" for connect+download.
            # If it reports attempts (has total), treat as connect; else as download.
            norm = "connect" if int(total or 0) > 0 else "download"

        self._set_smooth_progress_state(
            phase=norm,
            done=int(done or 0),
            total=int(total or 0),
            message=str(message or ""),
        )

        # Keep legacy trackers for safety (no longer drives UI range)
        self._last_progress_phase = norm
        self._last_progress_total = int(total or 0)

    def _set_smooth_progress_state(
        self, phase: str, done: int, total: int, message: str
    ) -> None:
        dlg = self._progress
        if dlg is None:
            return

        # Keep old tracking vars for safety; dialog is now driven by count-mode.
        if phase != self._progress_phase:
            self._progress_phase = phase

        # Stop connect pulse when leaving connect phase.
        if phase != "connect":
            try:
                if self._connect_pulse_timer is not None:
                    self._connect_pulse_timer.stop()
            except Exception:
                pass

        # Chỉ hiển thị 3 trạng thái; không hiển thị message chi tiết / không hiển thị đếm dòng.
        default_msg = {
            "connect": "Đang kết nối...",
            "download": "Đang tải dữ liệu...",
            "save": "Đang lưu vào CSDL...",
            "done": "Hoàn tất",
        }.get(phase, "Đang xử lý...")
        msg = str(default_msg).strip()

        if phase == "done":
            try:
                dlg.set_message(msg)
            except Exception:
                pass
            try:
                dlg.finish_and_close()
            except Exception:
                try:
                    dlg.close()
                except Exception:
                    pass
            return

        # Busy-only: giữ thanh loading nền (indeterminate) và chỉ set message.
        try:
            dlg.set_indeterminate(True)
        except Exception:
            pass
        try:
            dlg.set_message(msg)
        except Exception:
            pass

        # Khi connect có thể bị block, vẫn giữ timer để tránh cảm giác treo;
        # timer chỉ cập nhật message (không progress chi tiết).
        if phase == "connect":
            if self._connect_pulse_timer is None:
                self._connect_pulse_timer = QTimer(self._parent_window)
                self._connect_pulse_timer.setInterval(500)
                self._connect_pulse_timer.timeout.connect(self._tick_connect_pulse)
            if not self._connect_pulse_timer.isActive():
                self._connect_pulse_timer.start()
        return

    def _tick_connect_pulse(self) -> None:
        dlg = self._progress
        if dlg is None:
            try:
                if self._connect_pulse_timer is not None:
                    self._connect_pulse_timer.stop()
            except Exception:
                pass
            return

        if self._progress_phase != "connect":
            try:
                if self._connect_pulse_timer is not None:
                    self._connect_pulse_timer.stop()
            except Exception:
                pass
            return

        try:
            dlg.set_indeterminate(True)
            dlg.set_message("Đang kết nối...")
        except Exception:
            pass

    def _on_worker_finished_ui(self, ok: bool, msg: str, _count: int) -> None:
        if (
            self._progress_update_timer is not None
            and self._progress_update_timer.isActive()
        ):
            try:
                self._progress_update_timer.stop()
            except Exception:
                pass
        self._pending_progress = None
        self._last_progress_phase = None
        self._last_progress_total = None

        try:
            if self._connect_pulse_timer is not None:
                self._connect_pulse_timer.stop()
        except Exception:
            pass

        if self._progress is not None and ok:
            p = self._progress
            self._progress = None
            try:
                p.finish_and_close()
            except Exception:
                try:
                    p.close()
                except Exception:
                    pass

        elif self._progress is not None and not ok:
            p = self._progress
            self._progress = None
            try:
                QTimer.singleShot(0, p.close)
            except Exception:
                pass

        if not ok:
            QTimer.singleShot(
                0,
                lambda: MessageDialog.info(
                    self._parent_window,
                    "Không thể tải",
                    msg or "Không thể tải dữ liệu.",
                ),
            )
            # cleanup refs
            self._worker = None
            self._thread = None
            # Hiển thị lại bảng (dữ liệu cũ nếu có)
            try:
                if (
                    hasattr(self._content, "table_frame")
                    and self._content.table_frame is not None
                ):
                    self._content.table_frame.setVisible(True)
            except Exception:
                pass
            return

        self.refresh_table()
        # Hiển thị lại bảng sau khi tải xong
        try:
            if (
                hasattr(self._content, "table_frame")
                and self._content.table_frame is not None
            ):
                self._content.table_frame.setVisible(True)
        except Exception:
            pass
        # cleanup refs
        self._worker = None
        self._thread = None
