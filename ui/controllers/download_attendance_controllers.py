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
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QProgressDialog

from services.download_attendance_services import DownloadAttendanceService
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
        self._progress: QProgressDialog | None = None
        self._progress_update_timer: QTimer | None = None
        self._pending_progress: tuple[str, int, int, str] | None = None
        self._last_progress_phase: str | None = None
        self._last_progress_total: int | None = None

        # Proxy QObject để slot chạy đúng UI thread
        self._ui_proxy = _UiProxy(self, parent=self._parent_window)

    def bind(self) -> None:
        self._title_bar2.download_clicked.connect(self.on_download)
        self.refresh_devices()
        self.refresh_table()

    def refresh_devices(self) -> None:
        try:
            devices = self._service.list_devices_for_combo()
            self._title_bar2.set_devices(devices)
        except Exception:
            logger.exception("Không thể tải danh sách máy")
            self._title_bar2.set_devices([])

    def refresh_table(self) -> None:
        # Bảng tạm hiển thị dữ liệu đã tải trong phiên
        try:
            rows = self._service.list_download_attendance()
            ui_rows = [self._to_ui_row(r) for r in rows]
            self._content.set_attendance_rows(
                [
                    (
                        u.code,
                        u.date_str,
                        u.in1,
                        u.out1,
                        u.in2,
                        u.out2,
                        u.in3,
                        u.out3,
                        u.device_name,
                    )
                    for u in ui_rows
                ]
            )
        except Exception:
            logger.exception("Không thể load bảng download_attendance")
            self._content.set_attendance_rows([])

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
            date_str=fmt_date(wd),
            in1=fmt_time(r.time_in_1),
            out1=fmt_time(r.time_out_1),
            in2=fmt_time(r.time_in_2),
            out2=fmt_time(r.time_out_2),
            in3=fmt_time(r.time_in_3),
            out3=fmt_time(r.time_out_3),
            device_name=str(r.device_name or ""),
        )

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

        # Progress dialog
        progress = QProgressDialog(
            "Đang tải dữ liệu từ máy...", None, 0, 0, self._parent_window
        )
        progress.setWindowTitle("Tải dữ liệu Máy chấm công")
        progress.setFixedHeight(150)
        progress.setFixedWidth(400)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.setCancelButton(None)
        self._progress = progress
        self._pending_progress = None
        self._last_progress_phase = None
        self._last_progress_total = None

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
        progress.show()
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

        if phase == "fetch":
            if self._last_progress_phase != phase:
                self._progress.setRange(0, 0)
                self._last_progress_total = None
            self._progress.setLabelText(message or "Đang tải dữ liệu từ máy...")
            self._last_progress_phase = phase
            return

        if phase == "save":
            t = int(total or 0)
            if self._last_progress_phase != phase or self._last_progress_total != t:
                if t <= 0:
                    self._progress.setRange(0, 0)
                else:
                    self._progress.setRange(0, t)
                self._last_progress_total = t

            if t > 0:
                self._progress.setValue(min(int(done), t))
            else:
                self._progress.setValue(0)

            self._progress.setLabelText(message or "Đang lưu vào CSDL...")
            self._last_progress_phase = phase
            return

        if phase == "done":
            t = max(1, int(total or 1))
            if self._last_progress_phase != phase or self._last_progress_total != t:
                self._progress.setRange(0, t)
                self._last_progress_total = t
            self._progress.setValue(max(0, int(done)))
            self._progress.setLabelText(message or "Hoàn tất")
            self._last_progress_phase = phase

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

        if self._progress is not None:
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
            return

        self.refresh_table()
        QTimer.singleShot(
            0,
            lambda: MessageDialog.info(
                self._parent_window,
                "Thông báo",
                msg or "Hoàn tất",
            ),
        )
        # cleanup refs
        self._worker = None
        self._thread = None
