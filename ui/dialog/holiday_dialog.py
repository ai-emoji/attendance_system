"""ui.dialog.holiday_dialog

Dialog thêm mới / sửa đổi Ngày lễ.

Yêu cầu:
- Không dùng QMessageBox (hiển thị lỗi nội tuyến)
- Thông số (kích thước, màu, font) lấy từ core/resource.py
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QLocale, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    COLOR_BG_HEADER,
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    HOLIDAY_DIALOG_HEIGHT,
    HOLIDAY_DIALOG_WIDTH,
    UI_FONT,
)


class HolidayDialog(QDialog):
    def __init__(
        self,
        mode: str = "add",
        holiday_date_iso: str | None = None,
        holiday_info: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._init_ui()
        self.set_holiday_date_iso(holiday_date_iso)
        self.set_holiday_info(holiday_info)

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setFixedSize(HOLIDAY_DIALOG_WIDTH, HOLIDAY_DIALOG_HEIGHT)
        self.setWindowTitle("Thêm mới" if self._mode == "add" else "Sửa đổi")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        form_widget = QWidget(self)
        form_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.input_holiday_date = QDateEdit()
        self.input_holiday_date.setFont(font_normal)
        self.input_holiday_date.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_holiday_date.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.input_holiday_date.setCalendarPopup(True)
        self.input_holiday_date.setDisplayFormat("dd/MM/yyyy")
        # Lịch hiển thị tiếng Việt
        self.input_holiday_date.setLocale(
            QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam)
        )
        self.input_holiday_date.setToolTip("Chọn ngày nghỉ")
        self.input_holiday_date.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_holiday_date.setStyleSheet(
            "\n".join(
                [
                    f"QDateEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                    f"QDateEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )

        self.input_holiday_info = QLineEdit()
        self.input_holiday_info.setFont(font_normal)
        self.input_holiday_info.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_holiday_info.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.input_holiday_info.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_holiday_info.setPlaceholderText("Ví dụ: Tết Dương lịch")
        self.input_holiday_info.setToolTip("Nhập thông tin ngày nghỉ")
        self.input_holiday_info.setStyleSheet(
            "\n".join(
                [
                    f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                    f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )

        form.addRow("Ngày Tháng Năm", self.input_holiday_date)
        form.addRow("Thông tin ngày nghỉ", self.input_holiday_info)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setAutoDefault(True)
        self.btn_save.setDefault(True)
        self.btn_save.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setFont(font_button)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_CANCEL}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_CANCEL_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_save.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_cancel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn_layout.addWidget(self.btn_save, 1)
        btn_layout.addWidget(self.btn_cancel, 1)

        root.addWidget(form_widget)
        root.addWidget(self.label_status)
        root.addStretch(1)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.input_holiday_info.returnPressed.connect(self.btn_save.click)
        self.input_holiday_info.setFocus()

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def get_holiday_date_iso(self) -> str:
        qdate = self.input_holiday_date.date()
        return qdate.toString("yyyy-MM-dd")

    def set_holiday_date_iso(self, value: str | None) -> None:
        if not value:
            self.input_holiday_date.setDate(QDate.currentDate())
            return

        # Expect yyyy-MM-dd
        parts = str(value).split("-")
        if len(parts) == 3:
            try:
                y, m, d = (int(parts[0]), int(parts[1]), int(parts[2]))
                self.input_holiday_date.setDate(QDate(y, m, d))
                return
            except Exception:
                pass

        self.input_holiday_date.setDate(QDate.currentDate())

    def get_holiday_info(self) -> str:
        return (self.input_holiday_info.text() or "").strip()

    def set_holiday_info(self, value: str) -> None:
        self.input_holiday_info.setText(value or "")
        self.input_holiday_info.setCursorPosition(len(self.input_holiday_info.text()))
