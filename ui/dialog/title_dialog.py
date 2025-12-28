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
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
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
    ICON_DROPDOWN,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    TITLE_DIALOG_HEIGHT,
    TITLE_DIALOG_WIDTH,
    UI_FONT,
    resource_path,
)


class TitleDialog(QDialog):
    def __init__(
        self,
        mode: str = "add",
        title_name: str = "",
        departments: list[tuple[int, str]] | None = None,
        department_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._is_formatting_text = False
        self._departments: list[tuple[int, str]] = list(departments or [])
        self._init_ui()
        self.set_title_name(title_name)
        self._load_departments()
        self.set_department_id(department_id)

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

        self.input_title_name = QLineEdit()
        self.input_title_name.setFont(font_normal)
        self.input_title_name.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_title_name.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.input_title_name.setPlaceholderText("(ví dụ: Trưởng Phòng)")
        self.input_title_name.setToolTip(
            "Tên chức danh sẽ tự viết hoa chữ cái đầu mỗi từ"
        )
        self.input_title_name.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_title_name.setStyleSheet(
            "\n".join(
                [
                    f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                    f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )

        # Auto viết hoa chữ cái đầu mỗi từ (ví dụ: "xin chào" -> "Xin Chào")
        self.input_title_name.textEdited.connect(
            lambda _t: self._ensure_title_case(self.input_title_name)
        )

        form.addRow("Tên Chức Danh", self.input_title_name)

        dropdown_icon_url = resource_path(ICON_DROPDOWN).replace("\\", "/")

        combo_style = "\n".join(
            [
                # Chừa chỗ bên phải cho nút dropdown
                f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; padding-right: 30px; border-radius: 6px; }}",
                f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border-left: 1px solid {INPUT_COLOR_BORDER}; background: {INPUT_COLOR_BG}; }}",
                f'QComboBox::down-arrow {{ image: url("{dropdown_icon_url}"); width: 10px; height: 10px; }}',
            ]
        )

        self.cbo_department = QComboBox()
        self.cbo_department.setFont(font_normal)
        self.cbo_department.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_department.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.cbo_department.setStyleSheet(combo_style)
        form.addRow("Phòng ban", self.cbo_department)

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
        self.btn_cancel.setFont(font_button)
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

        # 2 nút chiếm 100% chiều ngang (mỗi nút ~50%)
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

    def get_department_id(self) -> int | None:
        try:
            value = self.cbo_department.currentData()
            return int(value) if value is not None else None
        except Exception:
            return None

    def set_title_name(self, value: str) -> None:
        self.input_title_name.setText(value or "")
        self.input_title_name.setCursorPosition(len(self.input_title_name.text()))

    def set_department_id(self, department_id: int | None) -> None:
        # Match by itemData
        try:
            target = int(department_id) if department_id is not None else None
        except Exception:
            target = None

        for i in range(self.cbo_department.count()):
            if self.cbo_department.itemData(i) == target:
                self.cbo_department.setCurrentIndex(i)
                return
        # fallback: first item
        if self.cbo_department.count() > 0:
            self.cbo_department.setCurrentIndex(0)

    def _load_departments(self) -> None:
        if not hasattr(self, "cbo_department"):
            return

        self.cbo_department.clear()
        self.cbo_department.addItem("Chưa chọn", None)

        items = list(self._departments or [])
        try:
            items.sort(key=lambda x: str(x[1]).lower())
        except Exception:
            pass

        for dept_id, dept_name in items:
            try:
                self.cbo_department.addItem(str(dept_name), int(dept_id))
            except Exception:
                continue
        self.cbo_department.setCurrentIndex(0)

    def _ensure_title_case(self, line_edit: QLineEdit) -> None:
        if self._is_formatting_text:
            return

        text = line_edit.text()
        if not text:
            return

        def title_case_keep_spaces(value: str) -> str:
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


class MessageDialog(QDialog):
    """Dialog dùng chung để hiển thị thông báo / xác nhận.

    - Không dùng QMessageBox
    - 1 nút (info) hoặc 2 nút (confirm)
    """

    def __init__(
        self,
        title: str,
        message: str,
        ok_text: str = "OK",
        cancel_text: str | None = None,
        destructive: bool = False,
        parent=None,
        *,
        fixed_size: tuple[int, int] | None = None,
        scrollable: bool = False,
    ) -> None:
        super().__init__(parent)
        self._ok_clicked = False

        self.setModal(True)
        if fixed_size is not None:
            try:
                w, h = fixed_size
                self.setFixedSize(int(w), int(h))
            except Exception:
                self.setFixedSize(TITLE_DIALOG_WIDTH, TITLE_DIALOG_HEIGHT)
        else:
            self.setFixedSize(TITLE_DIALOG_WIDTH, TITLE_DIALOG_HEIGHT)
        self.setWindowTitle(title or "")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_title = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_title.setWeight(QFont.Weight.DemiBold)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        header = QLabel(title or "")
        header.setFont(font_title)

        msg_widget: QWidget
        if scrollable:
            box = QPlainTextEdit(self)
            box.setReadOnly(True)
            box.setPlainText(message or "")
            box.setFont(font_normal)
            # Keep wrapping pleasant for long reports
            try:
                box.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            except Exception:
                pass
            try:
                box.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
            except Exception:
                pass
            msg_widget = box
        else:
            lbl = QLabel(message or "")
            lbl.setFont(font_normal)
            lbl.setWordWrap(True)
            msg_widget = lbl

        # Nút
        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_ok = QPushButton(ok_text or "OK")
        self.btn_ok.setFont(font_button)
        self.btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ok.setFixedHeight(36)
        self.btn_ok.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_ok.setAutoDefault(True)
        self.btn_ok.setDefault(True)

        ok_bg = COLOR_BUTTON_CANCEL if destructive else COLOR_BUTTON_PRIMARY
        ok_hover = (
            COLOR_BUTTON_CANCEL_HOVER if destructive else COLOR_BUTTON_PRIMARY_HOVER
        )
        self.btn_ok.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {ok_bg}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {ok_hover}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_ok.clicked.connect(self._on_ok)

        if cancel_text is None:
            # 1 nút: full width
            btn_layout.addWidget(self.btn_ok, 1)
        else:
            self.btn_cancel = QPushButton(cancel_text)
            self.btn_cancel.setFont(font_button)
            self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_cancel.setFixedHeight(36)
            self.btn_cancel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self.btn_cancel.setAutoDefault(False)
            self.btn_cancel.setDefault(False)
            self.btn_cancel.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ background-color: {COLOR_BG_HEADER}; color: #000000; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                        f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER};color: {COLOR_BG_HEADER}; }}",
                        "QPushButton:pressed { opacity: 0.85; }",
                    ]
                )
            )
            self.btn_cancel.clicked.connect(self.reject)

            # 2 nút: tổng 100%, mỗi nút ~50%
            btn_layout.addWidget(self.btn_ok, 1)
            btn_layout.addWidget(self.btn_cancel, 1)

        root.addWidget(header, 0)
        if scrollable:
            # Let the scroll area take all remaining space.
            root.addWidget(msg_widget, 1)
        else:
            root.addWidget(msg_widget, 0)
            root.addStretch(1)
        root.addWidget(btn_row, 0)

    def _on_ok(self) -> None:
        self._ok_clicked = True
        self.accept()

    @property
    def ok_clicked(self) -> bool:
        return self._ok_clicked

    @classmethod
    def info(cls, parent, title: str, message: str, ok_text: str = "OK") -> None:
        dlg = cls(
            title=title,
            message=message,
            ok_text=ok_text,
            cancel_text=None,
            parent=parent,
        )
        dlg.exec()

    @classmethod
    def info_scroll(
        cls,
        parent,
        title: str,
        message: str,
        ok_text: str = "OK",
        *,
        width: int = 600,
        height: int = 500,
    ) -> None:
        dlg = cls(
            title=title,
            message=message,
            ok_text=ok_text,
            cancel_text=None,
            parent=parent,
            fixed_size=(int(width), int(height)),
            scrollable=True,
        )
        dlg.exec()

    @classmethod
    def confirm(
        cls,
        parent,
        title: str,
        message: str,
        ok_text: str = "Đồng ý",
        cancel_text: str = "Hủy",
        destructive: bool = False,
    ) -> bool:
        dlg = cls(
            title=title,
            message=message,
            ok_text=ok_text,
            cancel_text=cancel_text,
            destructive=destructive,
            parent=parent,
        )
        dlg.exec()
        return dlg.ok_clicked
