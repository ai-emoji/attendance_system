"""ui.dialog.backup_dialog

Dialog "Sao lưu Dữ liệu".
- Chọn file .sql để lưu
- Nút Sao lưu / Thoát
- Không dùng QMessageBox
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
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
    FONT_WEIGHT_SEMIBOLD,
    INPUT_HEIGHT_DEFAULT,
    UI_FONT,
)

from core.ui_settings import get_last_save_dir, set_last_save_dir


class BackupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _normalize_sql_path(self, raw: str) -> str:
        s = str(raw or "").strip().strip('"').strip("'")
        if not s:
            return ""
        try:
            p = Path(s)
            if p.suffix.lower() != ".sql":
                p = p.with_suffix(".sql")
            return str(p)
        except Exception:
            # Fallback: minimal normalization
            return s if s.lower().endswith(".sql") else f"{s}.sql"

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Sao lưu Dữ liệu")
        self.setFixedSize(620, 220)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_label = QFont(UI_FONT, CONTENT_FONT)
        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        row = QWidget(self)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lbl = QLabel("File .sql")
        lbl.setFont(font_label)
        lbl.setFixedWidth(120)

        self.inp_path = QLineEdit()
        self.inp_path.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.inp_path.setPlaceholderText("backup.sql")

        self.btn_browse = QPushButton("Chọn")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.btn_browse.setFixedWidth(90)

        lay.addWidget(lbl)
        lay.addWidget(self.inp_path, 1)
        lay.addWidget(self.btn_browse)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(10)

        self.btn_backup = QPushButton("Sao lưu")
        self.btn_backup.setFont(font_button)
        self.btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_backup.setFixedHeight(36)
        self.btn_backup.setDefault(True)
        self.btn_backup.setStyleSheet(
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

        self.btn_backup.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_exit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn_lay.addWidget(self.btn_backup, 1)
        btn_lay.addWidget(self.btn_exit, 1)

        root.addWidget(row)
        root.addWidget(self.label_status)
        root.addWidget(btn_row)

        self.btn_browse.clicked.connect(self._on_browse)
        self.btn_exit.clicked.connect(self.reject)
        self.inp_path.editingFinished.connect(self._on_path_edited)

    def _on_path_edited(self) -> None:
        self.inp_path.setText(self._normalize_sql_path(self.inp_path.text()))

    def _on_browse(self) -> None:
        current = self._normalize_sql_path(self.inp_path.text())
        initial = current or str(Path(get_last_save_dir()) / "backup.sql")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Chọn file backup",
            initial,
            "SQL (*.sql)",
        )
        if file_path:
            self.inp_path.setText(self._normalize_sql_path(file_path))
            try:
                set_last_save_dir(str(Path(file_path).parent))
            except Exception:
                pass

    def set_status(self, message: str, ok: bool) -> None:
        self.label_status.setText(message)
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )

    def get_path(self) -> str:
        return self._normalize_sql_path(self.inp_path.text())

    def set_path(self, path: str) -> None:
        self.inp_path.setText(self._normalize_sql_path(path))
