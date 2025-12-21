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
    QSize,
    Qt,
    Signal,
    QSortFilterProxyModel,
)
from PySide6.QtGui import QFont, QIcon
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
                    f"QTreeWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
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

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True

        # Do not filter placeholder rows (rows beyond real df length)
        if hasattr(model, "is_placeholder_row") and model.is_placeholder_row(
            source_row
        ):
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
        ("contract1_signed", "HĐLĐ (ký lần 1)"),
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
        self._placeholder_rows: int = 0

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

    def set_placeholder_rows(self, n: int) -> None:
        self._placeholder_rows = max(0, int(n))
        self.layoutChanged.emit()

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
            item["stt"] = r.get("stt") or idx
            norm.append(item)

        self.beginResetModel()
        self._df = pd.DataFrame(norm, columns=cols)
        self.endResetModel()

    def is_placeholder_row(self, row: int) -> bool:
        return int(row) >= int(len(self._df))

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return max(int(len(self._df)), int(self._placeholder_rows))

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
        self.setSectionsClickable(True)
        self.sectionClicked.connect(self._on_section_clicked)

    def _on_section_clicked(self, logical_index: int) -> None:
        col = int(logical_index)

        # Ignore ID column
        if col == 0:
            return

        # Collect unique values from current source df
        key = self._model.COLUMNS[col][0]
        if key not in self._model._df.columns:
            return

        series = self._model._df[key]
        try:
            values = [str(v) for v in series.dropna().astype(str).unique().tolist()]
        except Exception:
            values = []
        values = [v.strip() for v in values if str(v).strip()]
        values.sort()
        values = values[:200]

        menu = QMenu(self)
        act_all = menu.addAction("(Tất cả)")

        for v in values:
            menu.addAction(v)

        pos = self.mapToGlobal(QPoint(self.sectionViewportPosition(col), self.height()))
        chosen = menu.exec(pos)
        if chosen is None:
            return

        if chosen == act_all:
            self._proxy.clear_column_filter(col)
            return

        self._proxy.set_column_filter(col, chosen.text())


class EmployeeTable(QTableView):
    """Unified table (single QTableView).

    - Column ID is hidden.
    - No frozen columns.
    """

    _EMPTY_MIN_ROWS: int = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._is_placeholder: bool = True

        self._model = _EmployeeTableModel(self)
        self._proxy = _EmployeeFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        # Main view setup
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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

        self._update_placeholder_rows_to_viewport()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._is_placeholder:
            self._update_placeholder_rows_to_viewport()

    def _update_placeholder_rows_to_viewport(self) -> None:
        vh = int(self.viewport().height() or 0)
        if vh <= 0:
            if self._model.rowCount() == 0:
                self.set_placeholder_rows(self._EMPTY_MIN_ROWS)
            return
        per = max(1, int((vh + ROW_HEIGHT - 1) / ROW_HEIGHT))
        desired = max(self._EMPTY_MIN_ROWS, per)
        self.set_placeholder_rows(desired)

    def set_placeholder_rows(self, rows_count: int) -> None:
        n = max(0, int(rows_count))
        self._is_placeholder = True
        self._model.set_placeholder_rows(n)

    def _apply_table_style_main(self) -> None:
        self.setStyleSheet(
            "\n".join(
                [
                    f"QTableView {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 0px; border-right: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QTableView::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
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
        self.setColumnWidth(1, 70)   # STT
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
        self._is_placeholder = True
        self._update_placeholder_rows_to_viewport()

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

    def set_rows(self, rows: list[dict]) -> None:
        if not rows:
            self._is_placeholder = True
            self._update_placeholder_rows_to_viewport()
            return

        self._is_placeholder = False
        self._model.set_rows(rows)


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
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: #FFFFFF; }}",
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
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")

    def get_filters(self) -> dict:
        dept = self.department_tree.get_selected_department()
        return {
            "employee_code": self.inp_search_code.text().strip(),
            "full_name": self.inp_search_name.text().strip(),
            "department_id": dept[0] if dept else None,
        }
