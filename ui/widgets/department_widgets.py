"""ui.widgets.department_widgets

Các widget cho màn "Khai báo Phòng ban".

Yêu cầu:
- Sao chép cấu trúc TitleBar1 / TitleBar2 / MainContent
- MainContent chia 2 phần: trái 70% (cây nhiều cấp), phải 30% (ghi chú)
- Cây hiển thị các nhánh bằng ký tự └── │ ├── để nối các cấp cha
- Tên phòng ban không được trùng ở mọi cấp: xử lý ở service/DB (unique)
- Kích thước row giống title_widgets.py (ROW_HEIGHT)
"""

from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import QEvent, QTimer, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    CONTENT_FONT,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ICON_ADD,
    ICON_DELETE,
    ICON_EDIT,
    ICON_TOTAL,
    UI_FONT,
    COLOR_BUTTON_PRIMARY_HOVER,
    TITLE_HEIGHT,
    TITLE_2_HEIGHT,
    BG_TITLE_2_HEIGHT,
    MAIN_CONTENT_MIN_HEIGHT,
    MAIN_CONTENT_BG_COLOR,
    ODD_ROW_BG_COLOR,
    EVEN_ROW_BG_COLOR,
    ROW_HEIGHT,
    BG_TITLE_1_HEIGHT,
    resource_path,
)


class TitleBar1(QWidget):
    def __init__(
        self,
        name: str = "",
        icon_svg: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_1_HEIGHT};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 12, 0)
        layout.setSpacing(0)

        self.icon = QLabel("")
        self.icon.setFixedSize(22, 22)
        self.icon.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self.label = QLabel(name)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font.setWeight(QFont.Weight.Normal)
        self.label.setFont(font)

        if icon_svg:
            self.set_icon(icon_svg)

        layout.addWidget(self.icon)
        layout.addSpacing(10)
        layout.addWidget(self.label, 1)

    def set_icon(self, icon_svg: str) -> None:
        icon = QIcon(resource_path(icon_svg))
        pix = icon.pixmap(QSize(22, 22))
        self.icon.setPixmap(pix)

    def set_name(self, name: str) -> None:
        self.label.setText(name or "")


class TitleBar2(QWidget):
    add_clicked = Signal()
    edit_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.btn_add = QPushButton("Thêm mới")
        self.btn_edit = QPushButton("Sửa đổi")
        self.btn_delete = QPushButton("Xóa")

        for btn, icon_path in (
            (self.btn_add, ICON_ADD),
            (self.btn_edit, ICON_EDIT),
            (self.btn_delete, ICON_DELETE),
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(QIcon(resource_path(icon_path)))
            btn.setIconSize(QSize(18, 18))
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                        "QPushButton::icon { margin-right: 10px; }",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: #FFFFFF; }}",
                    ]
                )
            )

        self.btn_add.clicked.connect(self.add_clicked.emit)
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        self.total_icon = QLabel("")
        self.total_icon.setFixedSize(18, 18)
        self.total_icon.setPixmap(
            QIcon(resource_path(ICON_TOTAL)).pixmap(QSize(18, 18))
        )

        self.label_total = QLabel(text or "Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font.setWeight(QFont.Weight.Normal)
        self.label_total.setFont(font)

        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)
        layout.addSpacing(12)
        layout.addWidget(self.total_icon)
        layout.addWidget(self.label_total)
        layout.addStretch(1)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainContent(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(MAIN_CONTENT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        self._font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._dept_icon = QIcon(resource_path("assets/images/department.svg"))

        self.tree = QTreeWidget(self)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setColumnCount(1)
        # Không hiển thị header (xóa bỏ setHeaderLabels)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(0)  # dùng ký tự └── │ ├── thay vì indent mặc định

        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setIconSize(QSize(18, 18))

        self.tree.header().setStretchLastSection(True)

        self.tree.setStyleSheet(
            "\n".join(
                [
                    f"QTreeWidget {{ background-color: {MAIN_CONTENT_BG_COLOR}; color: {COLOR_TEXT_PRIMARY};}}",
                    f"QTreeWidget::item {{ padding-left: 8px; padding-right: 8px; height: {ROW_HEIGHT}px; }}",
                    f"QTreeWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    f"QTreeWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    "QTreeWidget::item:focus { outline: none; }",
                    "QTreeWidget:focus { outline: none; }",
                ]
            )
        )

        # Trái: cây phòng ban (70%)
        layout.addWidget(self.tree, 7)

        # Phải: hướng dẫn (30%)
        right = QWidget(self)
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right.setStyleSheet(f"border-left: 1px solid {COLOR_BORDER};")

        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(8)

        self.text_guide = QTextEdit()
        self.text_guide.setReadOnly(True)
        self.text_guide.setFont(self._font_normal)
        self.text_guide.setStyleSheet(
            f"QTextEdit {{ border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 6px 8px; background: transparent; }}"
        )
        self.text_guide.setPlainText(
            "📌 Ví dụ bạn có thể trả lời:\n\n"
            "\u201cHướng dẫn sử dụng XAMPP để truy cập phpMyAdmin qua LAN\u201d\n\n"
            "\u201cHướng dẫn sử dụng phần mềm chấm công (UI PySide6)\u201d\n\n"
            "\u201cHướng dẫn sử dụng bảng chấm công trong MySQL\u201d"
        )
        right_layout.addWidget(self.text_guide, 1)

        layout.addWidget(right, 3)

        self._rows_data_count = 0
        self._last_selected_id: int | None = None

        self.tree.currentItemChanged.connect(self._on_current_item_changed)

        # Click vào khoảng trống -> bỏ chọn
        self.tree.viewport().installEventFilter(self)

    def set_departments(self, rows: list[tuple[int, int | None, str, str]]) -> None:
        """Nạp dữ liệu phòng ban vào cây.

        rows: (id, parent_id, name, note)
        """

        self.tree.clear()
        self._rows_data_count = len(rows or [])

        by_parent: dict[int | None, list[tuple[int, int | None, str]]] = defaultdict(
            list
        )
        for dept_id, parent_id, name, _note in rows or []:
            dept_id_i = int(dept_id)
            parent_id_i = int(parent_id) if parent_id is not None else None
            by_parent[parent_id_i].append((dept_id_i, parent_id_i, name or ""))

        # sort theo id để ổn định
        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda x: x[0])

        def build(
            parent_item: QTreeWidgetItem | None,
            parent_id: int | None,
            prefix_parts: list[str],
        ) -> None:
            children = by_parent.get(parent_id, [])
            for idx, (dept_id, _p, name) in enumerate(children):
                is_last = idx == (len(children) - 1)
                connector = "└── " if is_last else "├── "

                # Luôn hiển thị connector (kể cả root) theo yêu cầu
                prefix = "".join(prefix_parts) + connector
                display_name = f"{prefix}{name}"

                item = QTreeWidgetItem([display_name])
                item.setFont(0, self._font_normal)
                item.setIcon(0, self._dept_icon)
                item.setData(0, Qt.ItemDataRole.UserRole, int(dept_id))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, name or "")

                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                next_prefix_parts = list(prefix_parts)
                if prefix_parts:
                    next_prefix_parts.append("    " if is_last else "│   ")
                else:
                    next_prefix_parts = ["    " if is_last else "│   "]

                build(item, dept_id, next_prefix_parts)

        build(None, None, [])
        self.tree.expandAll()
        self._sync_selected_row_font()

    def _sync_selected_row_font(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        self._apply_item_font(item, selected=True)

    def _on_current_item_changed(
        self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None
    ) -> None:
        if previous is not None:
            self._apply_item_font(previous, selected=False)

        if current is None:
            self._last_selected_id = None
            return

        self._apply_item_font(current, selected=True)

        try:
            dept_id = int(current.data(0, Qt.ItemDataRole.UserRole) or 0)
        except Exception:
            dept_id = 0

        self._last_selected_id = dept_id if dept_id > 0 else None

    def _apply_item_font(self, item: QTreeWidgetItem, selected: bool) -> None:
        font = self._font_semibold if selected else self._font_normal
        item.setFont(0, font)

    def get_selected_department(self) -> tuple[int, str] | None:
        item = self.tree.currentItem()
        if item is None:
            return None

        try:
            dept_id = int(item.data(0, Qt.ItemDataRole.UserRole) or 0)
        except Exception:
            return None

        raw_name = str(item.data(0, Qt.ItemDataRole.UserRole + 1) or "")
        return dept_id, raw_name

    def eventFilter(self, obj, event) -> bool:
        if obj is self.tree.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.tree.itemAt(event.pos())
                if item is None:
                    self.tree.clearSelection()
                    self.tree.setCurrentItem(None)
                    return True
        return super().eventFilter(obj, event)
