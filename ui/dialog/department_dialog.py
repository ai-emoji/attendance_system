"""ui.dialog.department_dialog

Dialog thêm mới / sửa đổi Phòng ban.

Yêu cầu:
- Không dùng QMessageBox (hiển thị lỗi nội tuyến)
- Thông số (kích thước, màu, font) lấy từ core/resource.py
- Có 2 trường input + 1 trường hiển thị phòng ban cha
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QComboBox,
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
    DEPARTMENT_DIALOG_HEIGHT,
    DEPARTMENT_DIALOG_WIDTH,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    ICON_DROPDOWN,
    UI_FONT,
    resource_path,
)


class DepartmentDialog(QDialog):
    def __init__(
        self,
        mode: str = "add",
        parent_options: list[tuple[int, int | None, str]] | None = None,
        selected_parent_id: int | None = None,
        exclude_parent_ids: set[int] | None = None,
        department_name: str = "",
        scope: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._is_formatting_text = False
        self._exclude_parent_ids = exclude_parent_ids or set()
        self._init_ui()
        self.set_scope(scope)
        self.set_parent_options(parent_options or [], selected_parent_id)
        self.set_department_name(department_name)

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setFixedSize(DEPARTMENT_DIALOG_WIDTH, DEPARTMENT_DIALOG_HEIGHT)
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

        dropdown_url = resource_path(ICON_DROPDOWN).replace("\\", "/")

        form_widget = QWidget(self)
        form_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        form = QFormLayout(form_widget)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.input_department_name = QLineEdit()
        self.input_department_name.setFont(font_normal)
        self.input_department_name.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_department_name.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.input_department_name.setPlaceholderText(
            "Nhập tên phòng ban (ví dụ: Phòng Kế Toán)"
        )
        self.input_department_name.setToolTip(
            "Tên phòng ban sẽ tự viết hoa chữ cái đầu mỗi từ"
        )
        self.input_department_name.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_department_name.setStyleSheet(
            "\n".join(
                [
                    f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                    f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )
        self.input_department_name.textEdited.connect(
            lambda _t: self._ensure_title_case(self.input_department_name)
        )

        # Dropdown phòng ban cha
        self.combo_parent = QComboBox()
        self.combo_parent.setFont(font_normal)
        self.combo_parent.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.combo_parent.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.combo_parent.setToolTip("Chọn phòng ban cha (nếu có).")
        self.combo_parent.setIconSize(QSize(18, 18))
        self.combo_parent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_parent.setStyleSheet(
            "\n".join(
                [
                    f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 28px 0 8px; border-radius: 0px; }}",
                    f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border-left: 0px; }}",
                    f'QComboBox::down-arrow {{ image: url("{dropdown_url}"); width: 14px; height: 14px; }}',
                ]
            )
        )

        # Labels (đồng bộ width)
        self.label_name = QLabel("Tên")
        self.label_name.setFont(font_normal)
        self.label_parent = QLabel("Phòng ban cha")
        self.label_parent.setFont(font_normal)
        self.label_scope = QLabel("Loại")
        self.label_scope.setFont(font_normal)

        form.addRow(self.label_name, self.input_department_name)
        form.addRow(self.label_parent, self.combo_parent)

        # Dropdown chọn loại (thay cho checkbox)
        self.combo_scope = QComboBox()
        self.combo_scope.setFont(font_normal)
        self.combo_scope.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.combo_scope.setMinimumWidth(INPUT_WIDTH_DEFAULT)
        self.combo_scope.setToolTip(
            "Chọn: Phòng ban hoặc Chức danh (mặc định chưa chọn)."
        )
        self.combo_scope.setIconSize(QSize(18, 18))
        self.combo_scope.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_scope.setStyleSheet(
            "\n".join(
                [
                    f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 28px 0 8px; border-radius: 0px; }}",
                    f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 24px; border-left: 0px; }}",
                    f'QComboBox::down-arrow {{ image: url("{dropdown_url}"); width: 14px; height: 14px; }}',
                ]
            )
        )
        self.combo_scope.addItem("— Chưa chọn —", None)
        self.combo_scope.addItem("Phòng ban", "department")
        self.combo_scope.addItem("Chức danh", "title")
        form.addRow(self.label_scope, self.combo_scope)

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

        # Enter trong input tên -> Lưu
        self.input_department_name.returnPressed.connect(self.btn_save.click)
        self.input_department_name.setFocus()

        self._apply_scope_ui(self.get_scope())
        self.combo_scope.currentIndexChanged.connect(
            lambda *_: self._apply_scope_ui(self.get_scope())
        )

        # Sync label widths after layout is computed
        QTimer.singleShot(0, self._sync_form_label_widths)

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def set_parent_options(
        self,
        rows: list[tuple[int, int | None, str]],
        selected_parent_id: int | None,
    ) -> None:
        """Render dropdown phòng ban cha theo dạng cây (├──/└── + icon + tên)."""

        self.combo_parent.clear()

        # Option: không có cha
        self.combo_parent.addItem("— Không có —")
        self.combo_parent.setItemData(0, None)

        # Ensure stable order (old -> new) regardless of caller order.
        try:
            rows = sorted(rows, key=lambda x: int(x[0]))
        except Exception:
            rows = list(rows or [])

        by_parent: dict[int | None, list[tuple[int, int | None, str]]] = {}
        for dept_id, parent_id, name in rows:
            if int(dept_id) in self._exclude_parent_ids:
                continue
            key = int(parent_id) if parent_id is not None else None
            by_parent.setdefault(key, []).append((int(dept_id), key, name or ""))

        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda x: x[0])

        dept_qicon = QIcon(resource_path("assets/images/department.svg"))

        def add_children(parent_id: int | None, prefix_parts: list[str]) -> None:
            children = by_parent.get(parent_id, [])
            for idx, (dept_id, _p, name) in enumerate(children):
                is_last = idx == (len(children) - 1)
                connector = "└── " if is_last else "├── "
                prefix = "".join(prefix_parts) + connector
                text = f"{prefix}{name}"

                self.combo_parent.addItem(dept_qicon, text)
                self.combo_parent.setItemData(self.combo_parent.count() - 1, dept_id)

                next_prefix_parts = list(prefix_parts)
                if prefix_parts:
                    next_prefix_parts.append("    " if is_last else "│   ")
                else:
                    next_prefix_parts = ["    " if is_last else "│   "]
                add_children(dept_id, next_prefix_parts)

        add_children(None, [])

        # set selected
        if selected_parent_id is None:
            self.combo_parent.setCurrentIndex(0)
            return

        for i in range(self.combo_parent.count()):
            if self.combo_parent.itemData(i) == int(selected_parent_id):
                self.combo_parent.setCurrentIndex(i)
                return

        self.combo_parent.setCurrentIndex(0)

    def get_parent_id(self) -> int | None:
        data = self.combo_parent.currentData()
        try:
            return int(data) if data is not None else None
        except Exception:
            return None

    def get_scope(self) -> str | None:
        data = self.combo_scope.currentData()
        s = str(data).strip() if data is not None else ""
        return s or None

    def set_scope(self, scope: str | None) -> None:
        scope = str(scope or "").strip() or None
        # Keep default state if invalid
        if scope not in ("department", "title"):
            return
        for i in range(self.combo_scope.count()):
            if self.combo_scope.itemData(i) == scope:
                try:
                    self.combo_scope.blockSignals(True)
                    self.combo_scope.setCurrentIndex(i)
                finally:
                    try:
                        self.combo_scope.blockSignals(False)
                    except Exception:
                        pass
                self._apply_scope_ui(self.get_scope())
                return

    def get_department_name(self) -> str:
        return (self.input_department_name.text() or "").strip()

    def _apply_scope_ui(self, scope: str | None) -> None:
        scope = str(scope or "").strip() or None

        if scope == "department":
            self.label_name.setText("Tên Phòng ban")
            self.input_department_name.setPlaceholderText(
                "Nhập tên phòng ban (ví dụ: Phòng Kế Toán)"
            )
            self.input_department_name.setToolTip(
                "Tên phòng ban sẽ tự viết hoa chữ cái đầu mỗi từ"
            )
            return

        if scope == "title":
            self.label_name.setText("Tên Chức danh")
            self.input_department_name.setPlaceholderText("(ví dụ: Trưởng Phòng)")
            self.input_department_name.setToolTip(
                "Tên chức danh sẽ tự viết hoa chữ cái đầu mỗi từ"
            )
            return

        # Default: chưa chọn
        self.label_name.setText("Tên")
        self.input_department_name.setPlaceholderText(
            "Chọn Loại: Phòng ban hoặc Chức danh"
        )
        self.input_department_name.setToolTip("")

    def _sync_form_label_widths(self) -> None:
        labels = [
            getattr(self, "label_name", None),
            getattr(self, "label_parent", None),
            getattr(self, "label_scope", None),
        ]
        labels = [lb for lb in labels if isinstance(lb, QLabel)]
        if not labels:
            return

        try:
            max_w = max(int(lb.sizeHint().width()) for lb in labels)
        except Exception:
            return

        # Add a small padding so Vietnamese diacritics don't clip
        max_w = int(max_w) + 6
        for lb in labels:
            lb.setFixedWidth(max_w)

    def set_department_name(self, value: str) -> None:
        self.input_department_name.setText(value or "")
        self.input_department_name.setCursorPosition(
            len(self.input_department_name.text())
        )

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
