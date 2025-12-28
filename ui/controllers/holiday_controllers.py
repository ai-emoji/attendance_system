"""ui.controllers.holiday_controllers

Controller cho màn "Khai báo Ngày lễ".

Trách nhiệm:
- Load dữ liệu vào bảng
- Xử lý Thêm/Sửa/Xóa
- Không dùng QMessageBox; dùng MessageDialog (trong title_dialog.py)
"""

from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import QDate, QLocale

from services.holiday_services import HolidayService
from ui.dialog.holiday_dialog import HolidayDialog
from ui.dialog.title_dialog import MessageDialog


logger = logging.getLogger(__name__)


def _to_display_date(iso_date: str) -> str:
    try:
        d = date.fromisoformat(iso_date)
        qd = QDate(d.year, d.month, d.day)

        # Hiển thị theo tiếng Việt: "Thứ Hai, 20/12/2025" (hoặc "Chủ Nhật, ...")
        vi = QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam)
        weekday = (vi.dayName(qd.dayOfWeek()) or "").title()
        return f"{weekday}, {qd.toString('dd/MM/yyyy')}"
    except Exception:
        return iso_date or ""


def _display_to_iso(display_date: str) -> str | None:
    """Chuyển display dạng 'Thứ Hai, 20/12/2025' hoặc '20/12/2025' về ISO."""

    if not display_date:
        return None

    try:
        s = str(display_date).strip()
        if "," in s:
            s = s.split(",")[-1].strip()
        if "/" not in s:
            return None
        dd, mm, yyyy = [p.strip() for p in s.split("/")]
        return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"
    except Exception:
        return None


class HolidayController:
    def __init__(
        self, parent_window, title_bar2, content, service: HolidayService | None = None
    ) -> None:
        self._parent_window = parent_window
        self._title_bar2 = title_bar2
        self._content = content
        self._service = service or HolidayService()

    def bind(self) -> None:
        self._title_bar2.add_clicked.connect(self.on_add)
        self._title_bar2.edit_clicked.connect(self.on_edit)
        self._title_bar2.delete_clicked.connect(self.on_delete)
        self.refresh()

    def refresh(self) -> None:
        try:
            models = self._service.list_holidays()
            rows = [
                (m.id, _to_display_date(m.holiday_date), m.holiday_info) for m in models
            ]
            self._content.set_holidays(rows)
            self._title_bar2.set_total(len(rows))
        except Exception:
            logger.exception("Không thể tải danh sách ngày lễ")
            self._content.set_holidays([])
            self._title_bar2.set_total(0)

    def on_add(self) -> None:
        dialog = HolidayDialog(mode="add", parent=self._parent_window)

        def _save() -> None:
            ok, msg, _new_id = self._service.create_holiday(
                dialog.get_holiday_date_iso(),
                dialog.get_holiday_info(),
            )
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == HolidayDialog.Accepted:
            self.refresh()

    def on_edit(self) -> None:
        selected = self._content.get_selected_holiday()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Sửa đổi.",
            )
            return

        holiday_id, _date_display, info = selected

        # Lấy iso từ display (đã có thêm Thứ ...,
        iso_date = _display_to_iso(_date_display)

        dialog = HolidayDialog(
            mode="edit",
            holiday_date_iso=iso_date,
            holiday_info=info,
            parent=self._parent_window,
        )

        def _save() -> None:
            ok, msg = self._service.update_holiday(
                holiday_id,
                dialog.get_holiday_date_iso(),
                dialog.get_holiday_info(),
            )
            dialog.set_status(msg, ok=ok)
            if ok:
                dialog.accept()

        dialog.btn_save.clicked.connect(_save)
        if dialog.exec() == HolidayDialog.Accepted:
            self.refresh()

    def on_delete(self) -> None:
        selected = self._content.get_selected_holiday()
        if not selected:
            MessageDialog.info(
                self._parent_window,
                "Thông báo",
                "Hãy chọn 1 dòng trong bảng trước khi Xóa.",
            )
            return

        holiday_id, date_display, info = selected

        if not MessageDialog.confirm(
            self._parent_window,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa ngày lễ: {date_display} - {info}?",
            ok_text="Xóa",
            cancel_text="Hủy",
            destructive=True,
        ):
            return

        ok, msg = self._service.delete_holiday(holiday_id)
        if ok:
            self.refresh()
        else:
            MessageDialog.info(
                self._parent_window,
                "Không thể xóa",
                msg or "Xóa thất bại.",
            )
