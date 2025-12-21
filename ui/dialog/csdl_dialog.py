"""ui.dialog.csdl_dialog

Dialog "Kết nối CSDL SQL".

Yêu cầu (ngầm định từ UI hệ thống):
- Không dùng QMessageBox
- Hiển thị trạng thái bằng label
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
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
    FONT_WEIGHT_SEMIBOLD,
    INPUT_HEIGHT_DEFAULT,
    UI_FONT,
)


class CSDLDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Kết nối CSDL SQL")
        self.setFixedSize(560, 320)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_label = QFont(UI_FONT, CONTENT_FONT)
        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        def mk_row(label_text: str, field: QWidget) -> QWidget:
            row = QWidget(self)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)

            lbl = QLabel(label_text)
            lbl.setFont(font_label)
            lbl.setFixedWidth(120)

            lay.addWidget(lbl)
            lay.addWidget(field, 1)
            return row

        self.inp_host = QLineEdit()
        self.inp_host.setFixedHeight(INPUT_HEIGHT_DEFAULT)

        self.inp_port = QSpinBox()
        self.inp_port.setRange(1, 65535)
        self.inp_port.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.inp_port.setValue(3306)

        self.inp_user = QLineEdit()
        self.inp_user.setFixedHeight(INPUT_HEIGHT_DEFAULT)

        self.inp_password = QLineEdit()
        self.inp_password.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.inp_database = QLineEdit()
        self.inp_database.setFixedHeight(INPUT_HEIGHT_DEFAULT)

        root.addWidget(mk_row("Host", self.inp_host))
        root.addWidget(mk_row("Port", self.inp_port))
        root.addWidget(mk_row("User", self.inp_user))
        root.addWidget(mk_row("Password", self.inp_password))
        root.addWidget(mk_row("Database", self.inp_database))

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)
        root.addWidget(self.label_status)

        btn_row = QWidget(self)
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(10)

        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setFont(font_button)
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setFixedHeight(36)
        self.btn_connect.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_exit = QPushButton("Thoát")
        self.btn_exit.setFont(font_button)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setFixedHeight(36)
        self.btn_exit.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_CANCEL}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_CANCEL_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_connect.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_exit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn_lay.addWidget(self.btn_connect, 1)
        btn_lay.addWidget(self.btn_exit, 1)

        root.addWidget(btn_row)

        self.btn_exit.clicked.connect(self.reject)

    def set_status(self, message: str, ok: bool) -> None:
        self.label_status.setText(message)
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )

    def set_form(
        self, host: str, port: int, user: str, password: str, database: str
    ) -> None:
        self.inp_host.setText(host or "")
        self.inp_port.setValue(int(port) if port else 3306)
        self.inp_user.setText(user or "")
        self.inp_password.setText(password or "")
        self.inp_database.setText(database or "")

    def get_form(self) -> dict:
        return {
            "host": self.inp_host.text().strip(),
            "port": int(self.inp_port.value()),
            "user": self.inp_user.text().strip(),
            "password": self.inp_password.text(),
            "database": self.inp_database.text().strip(),
        }
