"""ui.controllers.import_shift_attendance_controllers

Controller cho dialog "Import dữ liệu chấm công".

Trách nhiệm:
- Mở dialog
- Xử lý nút: Xem mẫu / Xem thông tin / Cập nhập vào CSDL
- Hiển thị progress
- Tạo báo cáo chi tiết (success/skip/fail) và lưu log

Không dùng QMessageBox; dùng MessageDialog.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QProgressDialog

from services.import_shift_attendance_services import ImportShiftAttendanceService
from core.ui_settings import get_last_save_dir, set_last_save_dir
from ui.dialog.import_shift_attendance_dialog import ImportShiftAttendanceDialog
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


class ImportShiftAttendanceController:
    def __init__(
        self,
        *,
        parent=None,
        service: ImportShiftAttendanceService | None = None,
    ) -> None:
        self._parent = parent
        self._service = service or ImportShiftAttendanceService()

    def open(self) -> None:
        dlg = ImportShiftAttendanceDialog(self._parent)
        self._wire(dlg)
        dlg.exec()

    def _wire(self, dlg: ImportShiftAttendanceDialog) -> None:
        dlg.btn_view_template.clicked.connect(lambda: self._on_view_template(dlg))
        dlg.btn_view_info.clicked.connect(lambda: self._on_view_info(dlg))
        dlg.btn_apply_db.clicked.connect(lambda: self._on_apply_db(dlg))

    def _on_view_template(self, dlg: ImportShiftAttendanceDialog) -> None:
        default_name = "file mẫu tải dữ liệu công.xlsx"
        initial = str(Path(get_last_save_dir()) / default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            dlg,
            "Tải file mẫu tải dữ liệu công",
            initial,
            "Excel (*.xlsx)",
        )
        if not file_path:
            return

        try:
            set_last_save_dir(str(Path(file_path).parent))
        except Exception:
            pass

        ok, msg = self._service.export_shift_attendance_template_xlsx(file_path)
        dlg.set_status(msg, ok=ok)
        if ok:
            try:
                MessageDialog.info(dlg, "File mẫu", msg)
            except Exception:
                pass

    def _on_view_info(self, dlg: ImportShiftAttendanceDialog) -> None:
        path = dlg.get_excel_path()
        ok, msg, rows = self._service.read_shift_attendance_from_xlsx(path)
        dlg.set_status(msg, ok=ok)
        if not ok:
            return
        dlg.set_preview_rows(rows)

    def _on_apply_db(self, dlg: ImportShiftAttendanceDialog) -> None:
        rows = dlg.get_rows_for_import()
        if not rows:
            # Try read from file path
            path = dlg.get_excel_path()
            ok, msg, rows = self._service.read_shift_attendance_from_xlsx(path)
            dlg.set_status(msg, ok=ok)
            if not ok:
                return
            dlg.set_preview_rows(rows)
            rows = dlg.get_rows_for_import()

        # If user checked some rows, only import those.
        try:
            checked_count = len(dlg.get_checked_preview_rows())
        except Exception:
            checked_count = 0
        if checked_count > 0:
            dlg.set_status(f"Sẽ cập nhập {checked_count} dòng đã chọn.", ok=True)

        total = len(rows)
        progress = QProgressDialog("Đang cập nhập vào CSDL...", "Hủy", 0, total, dlg)
        progress.setWindowTitle("Import dữ liệu chấm công")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        report_items: list[dict] = []

        def on_progress(i: int, ok_row: bool, code: str, message: str) -> None:
            progress.setValue(i)
            progress.setLabelText(
                f"{i}/{total} - {code or '(không mã)'} - {'OK' if ok_row else 'FAIL'}"
            )
            if progress.wasCanceled():
                raise RuntimeError("Đã hủy.")

        try:
            result = self._service.import_shift_attendance_rows(
                rows, progress_cb=on_progress, report=report_items
            )
        except Exception as exc:
            try:
                progress.close()
            except Exception:
                pass
            dlg.set_status(str(exc), ok=False)
            try:
                MessageDialog.info(dlg, "Import dữ liệu chấm công", str(exc))
            except Exception:
                pass
            return
        finally:
            try:
                progress.setValue(total)
            except Exception:
                pass

        dlg.set_status(result.message, ok=result.ok)

        # Summarize report
        try:
            success_items = [
                it
                for it in report_items
                if str(it.get("result") or "").upper() == "SUCCESS"
            ]
            skipped_items = [
                it
                for it in report_items
                if str(it.get("result") or "").upper() == "SKIPPED"
            ]
            invalid_items = [
                it
                for it in report_items
                if str(it.get("result") or "").upper() == "INVALID"
            ]
            failed_items = [
                it
                for it in report_items
                if str(it.get("result") or "").upper() == "FAILED"
            ]

            def _fmt_lines(items: list[dict], limit: int = 8) -> str:
                lines: list[str] = []
                for it in items[:limit]:
                    code = str(it.get("employee_code") or "").strip() or "(không mã)"
                    msg_row = str(it.get("message") or "").strip()
                    action = str(it.get("action") or "").strip()
                    if action:
                        lines.append(f"- {code} | {action} | {msg_row}")
                    else:
                        lines.append(f"- {code} | {msg_row}")
                if len(items) > limit:
                    lines.append(f"... (+{len(items) - limit} dòng)")
                return "\n".join(lines)

            detail_msg_parts: list[str] = [result.message, ""]
            detail_msg_parts.append(f"Thành công ({len(success_items)}):")
            detail_msg_parts.append(_fmt_lines(success_items))
            detail_msg_parts.append("")
            detail_msg_parts.append(f"Bỏ qua ({len(skipped_items)}):")
            detail_msg_parts.append(_fmt_lines(skipped_items))
            detail_msg_parts.append("")
            detail_msg_parts.append(f"Lỗi dữ liệu ({len(invalid_items)}):")
            detail_msg_parts.append(_fmt_lines(invalid_items))
            detail_msg_parts.append("")
            detail_msg_parts.append(f"Thất bại ({len(failed_items)}):")
            detail_msg_parts.append(_fmt_lines(failed_items))

            # Save full report to log file
            report_path: Path | None = None
            try:
                log_dir = Path("log")
                log_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = log_dir / f"import_shift_attendance_report_{ts}.txt"
                with report_path.open("w", encoding="utf-8") as f:
                    f.write(result.message + "\n\n")
                    f.write("index\tresult\taction\temployee_code\tmessage\n")
                    for it in report_items:
                        idx = str(it.get("index") or "")
                        res = str(it.get("result") or "")
                        action = str(it.get("action") or "")
                        code = str(it.get("employee_code") or "")
                        msg_row = str(it.get("message") or "")
                        f.write(f"{idx}\t{res}\t{action}\t{code}\t{msg_row}\n")
            except Exception:
                report_path = None

            if report_path is not None:
                detail_msg_parts.append("")
                detail_msg_parts.append(f"Chi tiết đầy đủ đã lưu: {report_path}")

            MessageDialog.info_scroll(
                dlg, "Import dữ liệu chấm công", "\n".join(detail_msg_parts), width=600, height=500
            )
        except Exception:
            try:
                MessageDialog.info(dlg, "Import dữ liệu chấm công", result.message)
            except Exception:
                pass

        if result.ok:
            dlg.accept()
