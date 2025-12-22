"""ui.dialog.comapy_dialog

Dialog thông tin công ty.

Yêu cầu:
- Hiển thị: thông tin công ty, địa chỉ, số điện thoại
- Ảnh APP_ICO (mặc định) và cho phép thay đổi ảnh
- Button: Thay đổi ảnh, Lưu và thoát
- Sử dụng biến INPUT trong core/resource.py
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
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
    COMPANY_DIALOG_HEIGHT,
    COMPANY_DIALOG_WIDTH,
    CONTENT_FONT,
    COLOR_BG_HEADER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    FONT_WEIGHT_NORMAL,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    UI_FONT,
    FONT_WEIGHT_SEMIBOLD,
)


class CompanyDialog(QDialog):
    """Dialog nhập và hiển thị thông tin công ty."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._logo_bytes: bytes | None = None
        self._is_formatting_text = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("Thông tin công ty")
        self.setModal(True)
        self.setFixedSize(COMPANY_DIALOG_WIDTH, COMPANY_DIALOG_HEIGHT)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        # Khu vực ảnh + nút thay đổi ảnh
        top = QWidget(self)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        self.label_logo = QLabel()
        self.label_logo.setFixedSize(96, 96)
        self.label_logo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.label_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_change_image = QPushButton("Thay đổi ảnh")
        self.btn_change_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_change_image.setFixedHeight(32)
        self.btn_change_image.setStyleSheet(
            f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; font-weight: {FONT_WEIGHT_SEMIBOLD}; border: none; border-radius: 8px; padding: 0 14px; }}"
        )
        # Không cho Enter kích hoạt nút đổi ảnh
        self.btn_change_image.setAutoDefault(False)
        self.btn_change_image.setDefault(False)

        top_layout.addWidget(self.label_logo)
        top_layout.addWidget(self.btn_change_image)
        top_layout.addStretch(1)

        # Form
        form_widget = QWidget(self)
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        self.input_company_name = QLineEdit()
        self.input_company_address = QLineEdit()
        self.input_company_phone = QLineEdit()

        self.input_company_name.setPlaceholderText("Nhập tên công ty")
        self.input_company_address.setPlaceholderText("Nhập địa chỉ")
        self.input_company_phone.setPlaceholderText("Nhập số điện thoại")

        self.input_company_name.setToolTip(
            "Tên công ty sẽ tự viết hoa chữ cái đầu mỗi từ"
        )
        self.input_company_address.setToolTip(
            "Địa chỉ sẽ tự viết hoa chữ cái đầu mỗi từ"
        )
        self.input_company_phone.setToolTip("Chỉ cho nhập số")

        for w in (
            self.input_company_name,
            self.input_company_address,
            self.input_company_phone,
        ):
            w.setFont(font_normal)
            w.setFixedHeight(INPUT_HEIGHT_DEFAULT)
            w.setMinimumWidth(INPUT_WIDTH_DEFAULT)
            w.setCursor(Qt.CursorShape.IBeamCursor)
            w.setStyleSheet(
                "\n".join(
                    [
                        f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                        f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    ]
                )
            )

        # Auto viết hoa chữ cái đầu mỗi từ (ví dụ: "xin chào" -> "Xin Chào")
        self.input_company_name.textEdited.connect(
            lambda _t: self._ensure_title_case(self.input_company_name)
        )
        self.input_company_address.textEdited.connect(
            lambda _t: self._ensure_title_case(self.input_company_address)
        )

        # Số điện thoại: chỉ cho nhập số
        try:
            from PySide6.QtCore import QRegularExpression
            from PySide6.QtGui import QRegularExpressionValidator

            self.input_company_phone.setInputMethodHints(
                Qt.InputMethodHint.ImhDigitsOnly
            )
            self.input_company_phone.setValidator(
                QRegularExpressionValidator(QRegularExpression(r"\d*"), self)
            )
        except Exception:
            # Nếu thiếu QtGui validator vì môi trường, vẫn chạy bình thường
            pass

        form_layout.addRow("Thông tin công ty", self.input_company_name)
        form_layout.addRow("Địa chỉ", self.input_company_address)
        form_layout.addRow("Số điện thoại", self.input_company_phone)

        # Buttons
        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        self.btn_save_exit = QPushButton("Lưu và thoát")
        self.btn_save_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_exit.setFixedHeight(36)
        self.btn_save_exit.setMinimumWidth(140)

        btn_font = QFont(UI_FONT, CONTENT_FONT)
        btn_font.setWeight(QFont.Weight.Bold)
        self.btn_save_exit.setFont(btn_font)

        # Enter sẽ kích hoạt nút này
        self.btn_save_exit.setAutoDefault(True)
        self.btn_save_exit.setDefault(True)
        self.btn_save_exit.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        btn_layout.addWidget(self.btn_save_exit)

        # Thông báo nội tuyến (thay cho QMessageBox)
        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        root.addWidget(top)
        root.addWidget(form_widget)
        root.addWidget(self.label_status)
        root.addStretch(1)
        root.addWidget(btn_row)

        # Enter trong input sẽ lưu và thoát
        self.input_company_name.returnPressed.connect(self.btn_save_exit.click)
        self.input_company_address.returnPressed.connect(self.btn_save_exit.click)
        self.input_company_phone.returnPressed.connect(self.btn_save_exit.click)

        # Focus mặc định vào ô tên công ty
        self.input_company_name.setFocus()

    def set_status(self, message: str, ok: bool = True) -> None:
        color = COLOR_SUCCESS if ok else COLOR_ERROR
        self.label_status.setStyleSheet(f"color: {color};")
        self.label_status.setText(message or "")

    def _ensure_title_case(self, line_edit: QLineEdit) -> None:
        if self._is_formatting_text:
            return

        text = line_edit.text()
        if not text:
            return

        def title_case_keep_spaces(value: str) -> str:
            # Giữ nguyên khoảng trắng người dùng nhập (không tự trim/collapse)
            parts: list[str] = []
            current: list[str] = []
            for ch in value:
                if ch.isspace():
                    if current:
                        word = "".join(current)
                        parts.append(word[:1].upper() + word[1:].lower())
                        current = []
                    parts.append(ch)
                else:
                    current.append(ch)
            if current:
                word = "".join(current)
                parts.append(word[:1].upper() + word[1:].lower())
            return "".join(parts)

        new_text = title_case_keep_spaces(text)
        if new_text == text:
            return

        self._is_formatting_text = True
        try:
            cursor_pos = line_edit.cursorPosition()
            line_edit.setText(new_text)
            line_edit.setCursorPosition(min(cursor_pos, len(new_text)))
        finally:
            self._is_formatting_text = False

    def set_logo_pixmap(self, pixmap: QPixmap | None) -> None:
        if pixmap is None:
            self.label_logo.clear()
            return

        scaled = pixmap.scaled(
            self.label_logo.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label_logo.setPixmap(scaled)

    def set_logo_bytes(self, data: bytes | None) -> None:
        self._logo_bytes = data
        if not data:
            self.set_logo_pixmap(None)
            return

        # Hỗ trợ cả SVG bytes để preview không bị trống
        head = data[:512].lower()
        is_svg = b"<svg" in head or head.strip().startswith(b"<?xml")
        if is_svg:
            from PySide6.QtCore import QByteArray, QSize
            from PySide6.QtGui import QImage, QPainter
            from PySide6.QtSvg import QSvgRenderer

            painter = None
            try:
                renderer = QSvgRenderer(QByteArray(data))
                size = renderer.defaultSize()
                if not size.isValid():
                    size = QSize(256, 256)

                image = QImage(size, QImage.Format.Format_ARGB32)
                image.fill(0)
                painter = QPainter(image)
                renderer.render(painter)
                pixmap = QPixmap.fromImage(image)
            except Exception:
                self.set_logo_pixmap(None)
                return
            finally:
                try:
                    if painter is not None:
                        painter.end()
                except Exception:
                    pass
        else:
            pixmap = QPixmap()
            if not pixmap.loadFromData(data):
                self.set_logo_pixmap(None)
                return

        self.set_logo_pixmap(pixmap)

    def get_logo_bytes(self) -> bytes | None:
        return self._logo_bytes

    def set_form_values(
        self, company_name: str, company_address: str, company_phone: str
    ) -> None:
        self.input_company_name.setText(company_name or "")
        self.input_company_address.setText(company_address or "")
        self.input_company_phone.setText(company_phone or "")

    def get_form_values(self) -> tuple[str, str, str]:
        return (
            self.input_company_name.text(),
            self.input_company_address.text(),
            self.input_company_phone.text(),
        )
