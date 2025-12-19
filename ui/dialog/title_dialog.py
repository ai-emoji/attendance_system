"""ui.dialog.title_dialog

Dialog thêm mới / sửa đổi Chức danh.

Yêu cầu:
- Không dùng QMessageBox (hiển thị lỗi nội tuyến)
- Thông số (kích thước, màu, font) lấy từ core/resource.py
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
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
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    TITLE_DIALOG_HEIGHT,
    TITLE_DIALOG_WIDTH,
    UI_FONT,
)


class TitleDialog(QDialog):
    def __init__(
        self,
        mode: str = "add",
        title_name: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._init_ui()
        self.set_title_name(title_name)

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setFixedSize(TITLE_DIALOG_WIDTH, TITLE_DIALOG_HEIGHT)
        self.setWindowTitle("Thêm mới" if self._mode == "add" else "Sửa đổi")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        form_widget = QWidget(self)
        form_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.input_title_name = QLineEdit()
        self.input_title_name.setFont(font_normal)
        self.input_title_name.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_title_name.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.input_title_name.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_title_name.setStyleSheet(
            "\n".join(
                [
                    f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                    f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )

        form.addRow("Tên Chức Danh", self.input_title_name)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(120)
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
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setMinimumWidth(120)
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

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        root.addWidget(form_widget)
        root.addWidget(self.label_status)
        root.addStretch(1)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self.reject)

        # Enter trong input -> Lưu
        self.input_title_name.returnPressed.connect(self.btn_save.click)
        self.input_title_name.setFocus()

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def get_title_name(self) -> str:
        return (self.input_title_name.text() or "").strip()

    def set_title_name(self, value: str) -> None:
        self.input_title_name.setText(value or "")
        self.input_title_name.setCursorPosition(len(self.input_title_name.text()))
