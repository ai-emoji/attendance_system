"""ui.widgets.employee_widgets

Màn "Thông tin Nhân viên".

Yêu cầu:
- Sao chép style/structure từ title_widgets.py (TitleBar1 + MainContent)
- MainContent chia 2 phần:
    - Trái: cây phòng ban (preview nguyên cấu trúc), min width ~30%
    - Phải: min width ~70%, người dùng co kéo 2 bên
- Bên phải gồm header tìm kiếm + nút Xuất danh sách + nút Nhập nhân viên + label Tổng
- Bên dưới header là bảng nhiều cột; cột ID ẩn
- Bên dưới header là bảng nhiều cột; cột ID ẩn
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date as _date
from datetime import datetime as _datetime

from PySide6.QtCore import (
    QAbstractTableModel,
    QCoreApplication,
    QEvent,
    QObject,
    QModelIndex,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    QSortFilterProxyModel,
)
from PySide6.QtGui import QFont, QIcon, QActionGroup
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QSizePolicy,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from PySide6.QtWidgets import QHeaderView

import pandas as pd

from core.resource import (
    BG_TITLE_1_HEIGHT,
    BG_TITLE_2_HEIGHT,
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    MAIN_CONTENT_BG_COLOR,
    MAIN_CONTENT_MIN_HEIGHT,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
    ICON_EXCEL,
    ICON_IMPORT,
    ICON_DROPDOWN,
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


class DepartmentTreePreview(QWidget):
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        self._font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        self._dept_icon = QIcon(resource_path("assets/images/department.svg"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget(self)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(0)
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
                    f"QTreeWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QTreeWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    "QTreeWidget::item:focus { outline: none; }",
                    "QTreeWidget:focus { outline: none; }",
                ]
            )
        )

        layout.addWidget(self.tree, 1)

        self._last_selected_id: int | None = None
        self.tree.currentItemChanged.connect(self._on_current_item_changed)
        self.tree.viewport().installEventFilter(self)

    def set_departments(self, rows: list[tuple[int, int | None, str, str]]) -> None:
        self.tree.clear()

        by_parent: dict[int | None, list[tuple[int, int | None, str]]] = defaultdict(
            list
        )
        for dept_id, parent_id, name, _note in rows or []:
            dept_id_i = int(dept_id)
            parent_id_i = int(parent_id) if parent_id is not None else None
            by_parent[parent_id_i].append((dept_id_i, parent_id_i, name or ""))

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

    def clear_selection(self) -> None:
        self.tree.clearSelection()
        self.tree.setCurrentItem(None)
        self.selection_changed.emit()

    def _on_current_item_changed(
        self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None
    ) -> None:
        if previous is not None:
            previous.setFont(0, self._font_normal)

        if current is None:
            self._last_selected_id = None
            self.selection_changed.emit()
            return

        current.setFont(0, self._font_semibold)

        try:
            dept_id = int(current.data(0, Qt.ItemDataRole.UserRole) or 0)
        except Exception:
            dept_id = 0
        self._last_selected_id = dept_id if dept_id > 0 else None
        self.selection_changed.emit()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.tree.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                item = self.tree.itemAt(event.pos())
                if item is None:
                    self.tree.clearSelection()
                    self.tree.setCurrentItem(None)
                    self.selection_changed.emit()
                    return True
        return super().eventFilter(obj, event)


class _EmployeeFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent: QObject | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self._column_filters: dict[int, str | None] = {}

    def set_column_filter(self, column: int, value: str | None) -> None:
        self._column_filters[int(column)] = str(value) if value is not None else None
        self.invalidateFilter()

    def clear_column_filter(self, column: int) -> None:
        if int(column) in self._column_filters:
            self._column_filters.pop(int(column), None)
            self.invalidateFilter()

    def clear_all_filters(self) -> None:
        if not self._column_filters:
            return
        self._column_filters.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True

        for col, wanted in self._column_filters.items():
            if not wanted:
                continue
            idx = model.index(source_row, int(col), source_parent)
            got = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "").strip()
            if got != str(wanted).strip():
                return False
        return True


class _LeftPaddingDelegate(QStyledItemDelegate):
    def __init__(self, left_padding_px: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pad = max(0, int(left_padding_px))

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)
        if self._pad > 0:
            option.rect.adjust(self._pad, 0, 0, 0)


class _EmployeeTableModel(QAbstractTableModel):
    # model columns: id (hidden), stt, employee_code, full_name, ...
    COLUMNS: list[tuple[str, str]] = [
        ("id", "ID"),
        ("stt", "STT"),
        ("employee_code", "MÃ NV"),
        ("full_name", "HỌ VÀ TÊN"),
        ("start_date", "Ngày vào làm"),
        ("title_name", "Chức Vụ"),
        ("department_name", "Phòng Ban"),
        ("date_of_birth", "Ngày tháng năm sinh"),
        ("gender", "Giới tính"),
        ("national_id", "CCCD/CMT"),
        ("id_issue_date", "Ngày Cấp"),
        ("id_issue_place", "Nơi Cấp"),
        ("address", "Địa chỉ"),
        ("phone", "Số điện thoại"),
        ("insurance_no", "Số Bảo Hiểm"),
        ("tax_code", "Mã số Thuế TNCN"),
        ("degree", "Bằng cấp"),
        ("major", "Chuyên ngành"),
        ("contract1_term", "HĐLĐ (ký lần 1)"),
        ("contract1_no", "Số HĐLĐ (lần 1)"),
        ("contract1_sign_date", "Ngày ký (lần 1)"),
        ("contract1_expire_date", "Ngày hết hạn (lần 1)"),
        ("contract2_indefinite", "HĐLĐ ký không thời hạn"),
        ("contract2_no", "Số HĐLĐ (không thời hạn)"),
        ("contract2_sign_date", "Ngày ký (không thời hạn)"),
        ("children_count", "Số con"),
        ("child_dob_1", "Ngày sinh con 1"),
        ("child_dob_2", "Ngày sinh con 2"),
        ("child_dob_3", "Ngày sinh con 3"),
        ("child_dob_4", "Ngày sinh con 4"),
        ("note", "Ghi chú"),
    ]

    def __init__(self, parent: QObject | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self._df: pd.DataFrame = pd.DataFrame(columns=[k for k, _ in self.COLUMNS])

        self._date_keys: set[str] = {
            "start_date",
            "date_of_birth",
            "id_issue_date",
            "contract1_sign_date",
            "contract1_expire_date",
            "contract2_sign_date",
            "child_dob_1",
            "child_dob_2",
            "child_dob_3",
            "child_dob_4",
        }

    def _format_vn_date(self, value) -> str:
        if value is None:
            return ""

        # pandas Timestamp support
        if hasattr(value, "to_pydatetime"):
            try:
                value = value.to_pydatetime()
            except Exception:
                pass

        if isinstance(value, _datetime):
            d = value.date()
            return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"
        if isinstance(value, _date):
            return f"{value.day:02d}/{value.month:02d}/{value.year:04d}"

        s = str(value or "").strip()
        if not s:
            return ""

        # accept YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
        head = s.split(" ", 1)[0].strip()
        if "-" in head:
            parts = head.split("-")
            if len(parts) == 3:
                try:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    return f"{d:02d}/{m:02d}/{y:04d}"
                except Exception:
                    return s

        # accept DD/MM/YYYY
        if "/" in head:
            parts2 = head.split("/")
            if len(parts2) == 3:
                try:
                    d, m, y = int(parts2[0]), int(parts2[1]), int(parts2[2])
                    return f"{d:02d}/{m:02d}/{y:04d}"
                except Exception:
                    return s

        return s

    def set_rows(self, rows: list[dict]) -> None:
        cols = [k for k, _ in self.COLUMNS]
        if not rows:
            self.beginResetModel()
            self._df = pd.DataFrame(columns=cols)
            self.endResetModel()
            return

        norm: list[dict] = []
        for idx, r in enumerate(rows, start=1):
            item = {k: r.get(k) for k in cols}
            stt_val = r.get("stt")
            if stt_val is None or str(stt_val).strip() == "":
                stt_val = r.get("sort_order")
            item["stt"] = (
                stt_val if stt_val is not None and str(stt_val).strip() != "" else idx
            )
            norm.append(item)

        self.beginResetModel()
        self._df = pd.DataFrame(norm, columns=cols)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return int(len(self._df))

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            try:
                return self.COLUMNS[int(section)][1]
            except Exception:
                return ""
        return None

    def data(
        self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ):  # noqa: N802
        if not index.isValid():
            return None

        row = int(index.row())
        col = int(index.column())

        if role == Qt.ItemDataRole.TextAlignmentRole:
            key = self.COLUMNS[col][0]
            if key in {"stt", "employee_code"}:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if row >= len(self._df):
            return ""

        key = self.COLUMNS[col][0]
        v = self._df.iloc[row].get(key)
        if v is None:
            return ""
        if key in self._date_keys:
            return self._format_vn_date(v)
        return str(v)

    def get_row_dict(self, row: int) -> dict | None:
        if int(row) < 0 or int(row) >= int(len(self._df)):
            return None
        s = self._df.iloc[int(row)]
        return {k: s.get(k) for k, _ in self.COLUMNS}


class _FilterHeaderView(QHeaderView):
    def __init__(
        self, proxy: _EmployeeFilterProxy, model: _EmployeeTableModel, parent=None
    ) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._proxy = proxy
        self._model = model
        self._dropdown_icon = QIcon(resource_path(ICON_DROPDOWN))
        self._dropdown_icon_size = 14
        self._dropdown_icon_pad = 6
        self._resize_handle_margin = 4
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        # Only open filter menu when clicking the dropdown icon.
        # (Do not open menu when clicking the header text.)

    def _is_over_resize_handle(self, pos: QPoint) -> bool:
        # When we override cursor, we must preserve the resize-handle cursor.
        # QHeaderView typically shows SplitHCursor near section borders.
        try:
            col = int(self.logicalIndexAt(pos))
        except Exception:
            return False
        if col < 0:
            return False

        margin = int(self._resize_handle_margin)
        x = int(self.sectionViewportPosition(int(col)))
        w = int(self.sectionSize(int(col)))
        left = x
        right = x + w
        px = int(pos.x())

        # Near the right edge of this section
        if abs(px - right) <= margin:
            return True
        # Near the left edge (resize handle belongs to boundary between previous/current)
        if col > 0 and abs(px - left) <= margin:
            return True
        return False

    def _is_over_dropdown_icon(self, pos: QPoint) -> bool:
        try:
            col = int(self.logicalIndexAt(pos))
        except Exception:
            return False
        if col <= 0:
            return False
        x = int(self.sectionViewportPosition(int(col)))
        w = int(self.sectionSize(int(col)))
        sec_rect = QRect(x, 0, w, int(self.height()))
        icon_rect = self._dropdown_rect_for_section(sec_rect)
        return icon_rect.contains(pos)

    def _dropdown_rect_for_section(self, section_rect: QRect) -> QRect:
        size = int(self._dropdown_icon_size)
        pad = int(self._dropdown_icon_pad)
        x = int(section_rect.right() - pad - size)
        y = int(section_rect.center().y() - (size // 2))
        return QRect(x, y, size, size)

    def _exec_filter_menu(self, col: int, global_pos: QPoint | None = None) -> None:
        # Ignore ID column
        if int(col) == 0:
            return

        key = self._model.COLUMNS[int(col)][0]
        if key not in self._model._df.columns:
            return

        series = self._model._df[key]
        try:
            values = [str(v) for v in series.dropna().astype(str).unique().tolist()]
        except Exception:
            values = []
        values = [v.strip() for v in values if str(v).strip()]
        if key in {"stt", "sort_order"}:

            def _to_int_or_none(s: str) -> int | None:
                try:
                    return int(float(str(s).strip()))
                except Exception:
                    return None

            nums: list[tuple[int, str]] = []
            others: list[str] = []
            for s in values:
                n = _to_int_or_none(s)
                if n is None:
                    others.append(s)
                else:
                    nums.append((n, str(n)))
            nums.sort(key=lambda t: t[0])
            others.sort()
            values = [t[1] for t in nums] + others
        else:
            values.sort()

        current_filter = self._proxy._column_filters.get(int(col))  # type: ignore[attr-defined]

        menu = QMenu(self)
        # Set menu height to 90% of the screen height and center vertically
        screen = (
            self.window().windowHandle().screen()
            if self.window() and self.window().windowHandle()
            else None
        )
        if screen:
            screen_height = screen.geometry().height()
            menu.setFixedHeight(int(screen_height * 0.9))
            # Move menu to vertical center of the screen
            if global_pos is None:
                # Calculate center Y position
                menu_height = int(screen_height * 0.9)
                screen_geom = screen.geometry()
                center_y = screen_geom.top() + (screen_height - menu_height) // 2
                x = int(self.sectionViewportPosition(int(col)))
                w = int(self.sectionSize(int(col)))
                sec_rect = QRect(x, 0, w, int(self.height()))
                icon_rect = self._dropdown_rect_for_section(sec_rect)
                global_pos = self.mapToGlobal(icon_rect.bottomLeft() + QPoint(0, 2))
                # Adjust Y to center
                global_pos.setY(center_y)
        menu.setStyleSheet(
            "\n".join(
                [
                    f"QMenu {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QMenu::item {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; padding: 6px 12px; border-bottom: 0px; }}",
                    f"QMenu::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QMenu::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QMenu::separator {{ height: 1px; background: {COLOR_BORDER}; margin: 4px 8px; }}",
                ]
            )
        )

        group = QActionGroup(menu)
        group.setExclusive(True)

        act_all = menu.addAction("(Tất cả)")
        act_all.setCheckable(True)
        act_all.setChecked(current_filter is None)
        group.addAction(act_all)
        menu.addSeparator()

        for v in values:
            act = menu.addAction(v)
            act.setCheckable(True)
            act.setChecked(str(current_filter or "").strip() == str(v).strip())
            group.addAction(act)

        if global_pos is None:
            x = int(self.sectionViewportPosition(int(col)))
            w = int(self.sectionSize(int(col)))
            sec_rect = QRect(x, 0, w, int(self.height()))
            icon_rect = self._dropdown_rect_for_section(sec_rect)
            global_pos = self.mapToGlobal(icon_rect.bottomLeft() + QPoint(0, 2))
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == act_all:
            self._proxy.clear_column_filter(int(col))
            return
        self._proxy.set_column_filter(int(col), chosen.text())

    def paintSection(
        self, painter, rect: QRect, logicalIndex: int
    ) -> None:  # noqa: N802
        super().paintSection(painter, rect, logicalIndex)
        if int(logicalIndex) == 0:
            return
        if rect.width() < (self._dropdown_icon_size + self._dropdown_icon_pad * 2):
            return
        icon_rect = self._dropdown_rect_for_section(rect)
        pix = self._dropdown_icon.pixmap(
            QSize(self._dropdown_icon_size, self._dropdown_icon_size)
        )
        painter.drawPixmap(icon_rect, pix)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        try:
            col = int(self.logicalIndexAt(event.pos()))
        except Exception:
            col = -1

        if col > 0:
            x = int(self.sectionViewportPosition(int(col)))
            w = int(self.sectionSize(int(col)))
            sec_rect = QRect(x, 0, w, int(self.height()))
            icon_rect = self._dropdown_rect_for_section(sec_rect)
            if icon_rect.contains(event.pos()):
                gp = self.mapToGlobal(icon_rect.bottomLeft() + QPoint(0, 2))
                self._exec_filter_menu(col, gp)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        try:
            pos = event.pos()
        except Exception:
            super().mouseMoveEvent(event)
            return

        if self._is_over_dropdown_icon(pos):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        elif self._is_over_resize_handle(pos):
            self.setCursor(Qt.CursorShape.SplitHCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def event(self, event) -> bool:  # noqa: N802
        et = event.type()
        if et == QEvent.Type.HoverMove:
            try:
                pos = event.position().toPoint()
            except Exception:
                try:
                    pos = event.pos()
                except Exception:
                    pos = None

            if pos is not None and self._is_over_dropdown_icon(pos):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif pos is not None and self._is_over_resize_handle(pos):
                self.setCursor(Qt.CursorShape.SplitHCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return True

        if et in {QEvent.Type.HoverLeave, QEvent.Type.Leave}:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        return super().event(event)

    # Intentionally no sectionClicked handler.


class EmployeeTable(QTableView):
    """Unified table (single QTableView).

    - Column ID is hidden.
    - No frozen columns.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = _EmployeeTableModel(self)
        self._proxy = _EmployeeFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        # Main view setup
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Allow selecting multiple rows for bulk delete (Ctrl/Shift).
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setModel(self._proxy)

        # Header font & header dropdown on main header
        header_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            header_font.setWeight(QFont.Weight.DemiBold)

        main_header = _FilterHeaderView(self._proxy, self._model, self)
        main_header.setFont(header_font)
        self.setHorizontalHeader(main_header)
        self.horizontalHeader().setVisible(True)
        self.horizontalHeader().setFixedHeight(ROW_HEIGHT)

        # Delegate for main (padding-left 10px)
        self.setItemDelegate(_LeftPaddingDelegate(10, self))

        # Unified style (single table)
        self._apply_table_style_main()

        self._configure_columns()

    def _apply_table_style_main(self) -> None:
        self.setStyleSheet(
            "\n".join(
                [
                    f"QTableView {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 0px; border-right: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; padding-right: 22px; }}",
                    f"QTableView::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QTableView::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    f"QTableView::item:selected:active {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    "QTableView::item { padding-left: 10px; padding-right: 0px; border: 0px; }",
                    "QTableView::item:focus { outline: none; }",
                    "QTableView:focus { outline: none; }",
                ]
            )
        )

    def _configure_columns(self) -> None:
        # Hide ID
        self.setColumnHidden(0, True)

        # Column widths
        self.setColumnWidth(1, 70)  # STT
        self.setColumnWidth(2, 120)  # MÃ NV
        self.setColumnWidth(3, 220)  # HỌ VÀ TÊN

        # Main columns sizing
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setDefaultSectionSize(160)
        # Some wider columns
        self.setColumnWidth(12, 240)  # address
        self.setColumnWidth(30, 260)  # note

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def clear(self) -> None:
        self._model.set_rows([])

    def get_selected_employee(self) -> tuple[int, str, str] | None:
        row = self.currentIndex().row()
        if row is None or int(row) < 0:
            return None

        src_idx = self._proxy.mapToSource(self._proxy.index(int(row), 0))
        src_row = int(src_idx.row())
        data = self._model.get_row_dict(src_row)
        if not data:
            return None

        try:
            emp_id = int(str(data.get("id") or "0") or 0)
        except Exception:
            emp_id = 0
        if emp_id <= 0:
            return None

        code = str(data.get("employee_code") or "").strip()
        name = str(data.get("full_name") or "").strip()
        return emp_id, code, name

    def get_selected_employees(self) -> list[tuple[int, str, str]]:
        """Return selected employees in current view order.

        Each item is (id, employee_code, full_name).
        """

        sm = self.selectionModel()
        if sm is None:
            one = self.get_selected_employee()
            return [one] if one else []

        # Users may drag-select multiple cells; selectedRows() can be empty.
        # Use selectedIndexes() to collect unique rows robustly.
        selected_indexes = sm.selectedIndexes()  # type: ignore[call-arg]
        if not selected_indexes:
            one = self.get_selected_employee()
            return [one] if one else []

        proxy_rows = sorted({int(i.row()) for i in selected_indexes if i.isValid()})
        if not proxy_rows:
            one = self.get_selected_employee()
            return [one] if one else []

        out: list[tuple[int, str, str]] = []
        seen: set[int] = set()
        proxy_row_count = int(self._proxy.rowCount())
        for proxy_row in proxy_rows:
            if proxy_row < 0 or proxy_row >= proxy_row_count:
                continue

            src_idx = self._proxy.mapToSource(self._proxy.index(int(proxy_row), 0))
            src_row = int(src_idx.row())

            data = self._model.get_row_dict(src_row)
            if not data:
                continue

            try:
                emp_id = int(str(data.get("id") or "0") or 0)
            except Exception:
                emp_id = 0
            if emp_id <= 0 or emp_id in seen:
                continue
            seen.add(emp_id)

            code = str(data.get("employee_code") or "").strip()
            name = str(data.get("full_name") or "").strip()
            out.append((emp_id, code, name))

        return out

    def set_rows(self, rows: list[dict]) -> None:
        self._model.set_rows(rows)

    def clear_column_filters(self) -> None:
        self._proxy.clear_all_filters()


class MainContent(QWidget):
    search_changed = Signal()
    export_clicked = Signal()
    import_clicked = Signal()
    add_clicked = Signal()
    edit_clicked = Signal()
    delete_clicked = Signal()
    refresh_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(MAIN_CONTENT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        # Left: department tree
        self.department_tree = DepartmentTreePreview(splitter)
        self.department_tree.setMinimumWidth(320)

        # Right: header + table
        right = QWidget(splitter)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(10)

        header = QWidget(right)
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        self.inp_search_code = QLineEdit()
        self.inp_search_code.setPlaceholderText("Tìm Mã NV...")
        self.inp_search_code.setFixedHeight(32)
        self.inp_search_code.setFont(font_normal)

        self.inp_search_name = QLineEdit()
        self.inp_search_name.setPlaceholderText("Tìm Họ và tên...")
        self.inp_search_name.setFixedHeight(32)
        self.inp_search_name.setFont(font_normal)

        self.btn_export = QPushButton("Xuất danh sách")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.setFixedHeight(32)
        self.btn_export.setIcon(QIcon(resource_path(ICON_EXCEL)))
        self.btn_export.setIconSize(QSize(18, 18))
        self.btn_export.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                    "QPushButton::icon { margin-right: 10px; }",
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: {COLOR_TEXT_PRIMARY}; }}",
                ]
            )
        )

        self.btn_import = QPushButton("Nhập nhân viên")
        self.btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_import.setFixedHeight(32)
        self.btn_import.setIcon(QIcon(resource_path(ICON_IMPORT)))
        self.btn_import.setIconSize(QSize(18, 18))
        self.btn_import.setStyleSheet(self.btn_export.styleSheet())

        btn_style = self.btn_export.styleSheet()

        self.btn_add = QPushButton("Thêm NV")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedHeight(32)
        self.btn_add.setIcon(QIcon(resource_path("assets/images/add.svg")))
        self.btn_add.setIconSize(QSize(18, 18))
        self.btn_add.setStyleSheet(btn_style)

        self.btn_edit = QPushButton("Sửa")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setFixedHeight(32)
        self.btn_edit.setIcon(QIcon(resource_path("assets/images/edit.svg")))
        self.btn_edit.setIconSize(QSize(18, 18))
        self.btn_edit.setStyleSheet(btn_style)

        self.btn_delete = QPushButton("Xóa")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setFixedHeight(32)
        self.btn_delete.setIcon(QIcon(resource_path("assets/images/delete.svg")))
        self.btn_delete.setIconSize(QSize(18, 18))
        self.btn_delete.setStyleSheet(btn_style)

        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedHeight(32)
        self.btn_refresh.setIcon(QIcon(resource_path("assets/images/refresh.svg")))
        self.btn_refresh.setIconSize(QSize(18, 18))
        self.btn_refresh.setStyleSheet(btn_style)

        self.label_total = QLabel("Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self.label_total.setFont(font_normal)

        h.addWidget(self.inp_search_code, 0)
        h.addWidget(self.inp_search_name, 1)
        h.addWidget(self.btn_add, 0)
        h.addWidget(self.btn_edit, 0)
        h.addWidget(self.btn_delete, 0)
        h.addWidget(self.btn_refresh, 0)
        h.addWidget(self.btn_export, 0)
        h.addWidget(self.btn_import, 0)
        h.addSpacing(8)
        h.addWidget(self.label_total, 0)

        self.table = EmployeeTable(right)

        right_layout.addWidget(header, 0)
        right_layout.addWidget(self.table, 1)

        splitter.addWidget(self.department_tree)
        splitter.addWidget(right)

        # Initial splitter ratio ~30/70
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        root.addWidget(splitter, 1)

        # Signals
        self.inp_search_code.textChanged.connect(lambda _t: self.search_changed.emit())
        self.inp_search_name.textChanged.connect(lambda _t: self.search_changed.emit())
        self.department_tree.selection_changed.connect(self.search_changed.emit)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        self.btn_import.clicked.connect(self.import_clicked.emit)
        self.btn_add.clicked.connect(self.add_clicked.emit)
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")

    def _on_refresh_clicked(self) -> None:
        try:
            self.table.clear_column_filters()
        except Exception:
            pass
        self.refresh_clicked.emit()

    def get_filters(self) -> dict:
        dept = self.department_tree.get_selected_department()
        return {
            "employee_code": self.inp_search_code.text().strip(),
            "full_name": self.inp_search_name.text().strip(),
            "department_id": dept[0] if dept else None,
        }
