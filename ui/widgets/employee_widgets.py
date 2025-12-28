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
import unicodedata

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
    QTimer,
)
from PySide6.QtGui import QFont, QIcon, QActionGroup
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFrame,
    QSizePolicy,
    QSplitter,
    QStyle,
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

from core.ui_settings import get_employee_table_ui, ui_settings_bus

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
    ICON_LIST,
    ICON_IMPORT,
    ICON_DROPDOWN,
    COLOR_TEXT_LIGHT,
    resource_path,
)


# In-memory state cache to avoid losing Employee UI state when the main window
# recreates widgets while switching tabs.
_EMPLOYEE_VIEW_STATE: dict[str, object] = {}

# Tránh treo khi chuyển tab: không cache/restore danh sách quá lớn (pandas + modelReset rất nặng).
_STATE_ROWS_MAX = 800


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
        self._title_icon = QIcon(resource_path("assets/images/job_title.svg"))

        # Cache for quick lookup
        self._dept_parent_by_id: dict[int, int | None] = {}
        self._dept_name_by_id: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget(self)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(0)
        # We render the hierarchy using ASCII connectors (├──/└──), so disable
        # the built-in expand/collapse decoration to make clicks consistently select rows.
        self.tree.setRootIsDecorated(False)
        self.tree.setExpandsOnDoubleClick(False)
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
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.viewport().installEventFilter(self)

    def _on_item_clicked(self, _item: QTreeWidgetItem, _column: int) -> None:
        # Ensure filtering triggers even when the user clicks the same item again.
        self.selection_changed.emit()

    def set_departments(
        self,
        rows: list[tuple[int, int | None, str, str]],
        titles: list[tuple[int, int | None, str]] | None = None,
    ) -> None:
        self.tree.clear()
        titles = titles or []

        # Build lookup maps for parent/name
        self._dept_parent_by_id.clear()
        self._dept_name_by_id.clear()
        for dept_id, parent_id, name, _note in rows or []:
            try:
                did = int(dept_id)
            except Exception:
                continue
            pid = int(parent_id) if parent_id is not None else None
            self._dept_parent_by_id[did] = pid
            self._dept_name_by_id[did] = str(name or "").strip()

        by_parent: dict[int | None, list[tuple[int, int | None, str]]] = defaultdict(
            list
        )
        for dept_id, parent_id, name, _note in rows or []:
            dept_id_i = int(dept_id)
            parent_id_i = int(parent_id) if parent_id is not None else None
            by_parent[parent_id_i].append((dept_id_i, parent_id_i, name or ""))

        for k in list(by_parent.keys()):
            by_parent[k].sort(key=lambda x: x[0])

        titles_by_department: dict[int | None, list[tuple[int, str]]] = defaultdict(
            list
        )
        for title_id, department_id, title_name in titles or []:
            try:
                tid = int(title_id)
            except Exception:
                continue
            did = int(department_id) if department_id is not None else None
            titles_by_department[did].append((tid, str(title_name or "").strip()))

        for k in list(titles_by_department.keys()):
            titles_by_department[k].sort(key=lambda x: x[0])

        def build(
            parent_item: QTreeWidgetItem | None,
            parent_id: int | None,
            prefix_parts: list[str],
        ) -> None:
            dept_children = by_parent.get(parent_id, [])
            title_children = titles_by_department.get(parent_id, [])

            combined: list[tuple[str, int, str]] = []
            combined.extend(
                [("dept", d_id, d_name) for (d_id, _p, d_name) in dept_children]
            )
            combined.extend(
                [("title", t_id, t_name) for (t_id, t_name) in title_children]
            )

            for idx, (node_type, node_id, name) in enumerate(combined):
                is_last = idx == (len(combined) - 1)
                connector = "└── " if is_last else "├── "

                prefix = "".join(prefix_parts) + connector
                display_name = f"{prefix}{name}"

                item = QTreeWidgetItem([display_name])
                item.setFont(0, self._font_normal)
                item.setIcon(
                    0, self._dept_icon if node_type == "dept" else self._title_icon
                )
                item.setData(0, Qt.ItemDataRole.UserRole, int(node_id))
                item.setData(0, Qt.ItemDataRole.UserRole + 1, name or "")
                item.setData(0, Qt.ItemDataRole.UserRole + 2, node_type)
                item.setData(0, Qt.ItemDataRole.UserRole + 3, parent_id)

                if parent_item is None:
                    self.tree.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                next_prefix_parts = list(prefix_parts)
                if prefix_parts:
                    next_prefix_parts.append("    " if is_last else "│   ")
                else:
                    next_prefix_parts = ["    " if is_last else "│   "]

                if node_type == "dept":
                    build(item, int(node_id), next_prefix_parts)

        build(None, None, [])
        self.tree.expandAll()

    def get_selected_department(self) -> tuple[int, str] | None:
        ctx = self.get_selected_node_context()
        if not ctx or ctx.get("type") != "dept":
            return None
        return int(ctx["id"]), str(ctx["name"])

    def get_selected_title(self) -> tuple[int, str] | None:
        ctx = self.get_selected_node_context()
        if not ctx or ctx.get("type") != "title":
            return None
        return int(ctx["id"]), str(ctx["name"])

    @staticmethod
    def _norm_text(s: str) -> str:
        s0 = " ".join(str(s or "").strip().split()).lower()
        # Remove accents for robust comparisons
        return "".join(
            ch
            for ch in unicodedata.normalize("NFKD", s0)
            if not unicodedata.combining(ch)
        )

    def get_selected_node_context(self) -> dict | None:
        """Return selection context used for filtering.

        Keys:
        - type: 'dept' | 'title'
        - id, name
        - parent_id (for dept)
        - department_id (for title)
        """
        item = self.tree.currentItem()
        if item is None:
            return None

        try:
            node_id = int(item.data(0, Qt.ItemDataRole.UserRole) or 0)
        except Exception:
            return None
        if node_id <= 0:
            return None

        name = str(item.data(0, Qt.ItemDataRole.UserRole + 1) or "").strip()

        node_type = str(item.data(0, Qt.ItemDataRole.UserRole + 2) or "dept")
        if node_type not in ("dept", "title"):
            node_type = "dept"

        parent_id_raw = item.data(0, Qt.ItemDataRole.UserRole + 3)
        try:
            parent_id = int(parent_id_raw) if parent_id_raw is not None else None
        except Exception:
            parent_id = None

        if node_type == "dept":
            return {
                "type": "dept",
                "id": node_id,
                "name": name,
                "parent_id": parent_id,
            }

        # title
        return {
            "type": "title",
            "id": node_id,
            "name": name,
            "department_id": parent_id,
        }

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
    filters_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self._column_filters: dict[int, str | None] = {}

    @staticmethod
    def _norm_text(s: str) -> str:
        s0 = " ".join(str(s or "").strip().split()).lower()
        return "".join(
            ch
            for ch in unicodedata.normalize("NFKD", s0)
            if not unicodedata.combining(ch)
        )

    def set_column_filter(self, column: int, value: str | None) -> None:
        self._column_filters[int(column)] = str(value) if value is not None else None
        self.invalidateFilter()
        try:
            self.filters_changed.emit()
        except Exception:
            pass

    def clear_column_filter(self, column: int) -> None:
        if int(column) in self._column_filters:
            self._column_filters.pop(int(column), None)
            self.invalidateFilter()
        try:
            self.filters_changed.emit()
        except Exception:
            pass

    def clear_all_filters(self) -> None:
        if not self._column_filters:
            return
        self._column_filters.clear()
        self.invalidateFilter()
        try:
            self.filters_changed.emit()
        except Exception:
            pass

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()
        if model is None:
            return True

        for col, wanted in self._column_filters.items():
            if not wanted:
                continue
            idx = model.index(source_row, int(col), source_parent)
            got = str(model.data(idx, Qt.ItemDataRole.DisplayRole) or "").strip()
            if self._norm_text(got) != self._norm_text(str(wanted)):
                return False
        return True


class _LeftPaddingDelegate(QStyledItemDelegate):
    def __init__(
        self,
        left_padding_px: int = 0,
        selected_weight: QFont.Weight | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pad = max(0, int(left_padding_px))
        self._selected_weight = selected_weight

    def initStyleOption(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().initStyleOption(option, index)

        if self._selected_weight is not None and (
            option.state & QStyle.StateFlag.State_Selected
        ):
            f = QFont(option.font)
            f.setWeight(self._selected_weight)
            option.font = f

        if self._pad > 0:
            option.rect.adjust(self._pad, 0, 0, 0)


class _EmployeeTableModel(QAbstractTableModel):
    # model columns: id (hidden), stt, employee_code, full_name, ...
    # Each tuple: (key, header_label, min_width_px)
    COLUMNS: list[tuple[str, str, int]] = [
        ("id", "ID", 0),
        ("stt", "STT", 0),
        ("employee_code", "MÃ NV", 0),
        ("mcc_code", "Mã CC", 0),
        ("full_name", "HỌ VÀ TÊN", 0),
        ("schedule", "Lịch làm việc", 0),
        ("name_on_mcc", "Tên trên MCC", 0),
        ("start_date", "Ngày vào làm", 0),
        ("title_name", "Chức Vụ", 0),
        ("department_name", "Phòng Ban", 0),
        ("date_of_birth", "Ngày Sinh", 0),
        ("gender", "Giới tính", 0),
        ("national_id", "CCCD/CMND", 0),
        ("id_issue_date", "Ngày Cấp", 0),
        ("id_issue_place", "Nơi Cấp", 0),
        ("address", "Địa chỉ", 0),
        ("phone", "Số điện thoại", 0),
        ("insurance_no", "Số Bảo Hiểm", 0),
        ("tax_code", "Mã số Thuế TNCN", 0),
        ("degree", "Bằng cấp", 0),
        ("major", "Chuyên ngành", 0),
        ("contract1_term", "HĐLĐ (ký lần 1)", 0),
        ("contract1_no", "Số HĐLĐ (lần 1)", 0),
        ("contract1_sign_date", "Ngày ký (lần 1)", 0),
        ("contract1_expire_date", "Ngày hết hạn (lần 1)", 0),
        ("contract2_indefinite", "HĐLĐ ký không thời hạn", 0),
        ("contract2_no", "Số HĐLĐ (không thời hạn)", 0),
        ("contract2_sign_date", "Ngày ký (không thời hạn)", 0),
        ("children_count", "Số con", 0),
        ("child_dob_1", "Ngày sinh con 1", 0),
        ("child_dob_2", "Ngày sinh con 2", 0),
        ("child_dob_3", "Ngày sinh con 3", 0),
        ("child_dob_4", "Ngày sinh con 4", 0),
        ("employment_status", "Hiện trạng", 0),
        ("note", "Ghi chú", 0),
    ]

    def __init__(self, parent: QObject | None = None) -> None:  # type: ignore[name-defined]
        super().__init__(parent)
        self._df: pd.DataFrame = pd.DataFrame(
            columns=[k for k, _label, _minw in self.COLUMNS]
        )

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

        self._align_overrides: dict[str, Qt.AlignmentFlag] = {}
        self._default_font_size: int | None = None
        self._default_font_weight: QFont.Weight | None = None
        self._column_bold_overrides: dict[str, bool] = {}

    def set_ui_overrides(
        self,
        *,
        align_by_key: dict[str, Qt.AlignmentFlag] | None = None,
        font_size: int | None = None,
        font_weight: QFont.Weight | None = None,
        column_bold: dict[str, bool] | None = None,
    ) -> None:
        self._align_overrides = dict(align_by_key or {})
        self._default_font_size = int(font_size) if font_size is not None else None
        self._default_font_weight = font_weight
        self._column_bold_overrides = dict(column_bold or {})

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
        cols = [k for k, _label, _minw in self.COLUMNS]
        if not rows:
            self.beginResetModel()
            self._df = pd.DataFrame(columns=cols)
            self.endResetModel()
            return

        norm: list[dict] = []
        for idx, r in enumerate(rows, start=1):
            item = {k: r.get(k) for k in cols}

            # Backward/forward compatibility:
            # Excel/template and some code paths use `contract1_signed`, while the table
            # column is `contract1_term` (label: HĐLĐ (ký lần 1)).
            # Fill the display column from `contract1_signed` when missing.
            c1_term = item.get("contract1_term")
            if c1_term is None or str(c1_term).strip() == "":
                c1_signed = r.get("contract1_signed")
                if (
                    c1_signed is not None
                    and not isinstance(c1_signed, bool)
                    and str(c1_signed).strip() != ""
                ):
                    item["contract1_term"] = str(c1_signed).strip()

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
            if key in self._align_overrides:
                try:
                    return int(self._align_overrides[key])
                except Exception:
                    pass
            if key in {"stt", "employee_code"}:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        if role == Qt.ItemDataRole.FontRole:
            key = self.COLUMNS[col][0]
            size = self._default_font_size
            weight = self._default_font_weight
            col_bold = self._column_bold_overrides.get(str(key), None)
            try:
                f = QFont()
                if size is not None and int(size) > 0:
                    f.setPointSize(int(size))
                if col_bold is True:
                    f.setWeight(QFont.Weight.DemiBold)
                elif col_bold is False:
                    f.setWeight(QFont.Weight.Normal)
                elif weight is not None:
                    f.setWeight(weight)
                return f
            except Exception:
                return None

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

        if key == "children_count":
            # Normalize Excel-style numbers (e.g. 1.0) and hide 0.
            try:
                if isinstance(v, bool):
                    return ""
                if isinstance(v, int):
                    return "" if v <= 0 else str(v)
                if isinstance(v, float):
                    if v <= 0:
                        return ""
                    if float(v).is_integer():
                        return str(int(v))
                    return ""
                s = str(v).strip()
                if not s:
                    return ""
                try:
                    f = float(s)
                    if f <= 0:
                        return ""
                    if f.is_integer():
                        return str(int(f))
                    return ""
                except Exception:
                    return s
            except Exception:
                return ""

        if key == "contract2_indefinite":
            # Show as text, avoid displaying False/0.
            try:
                if isinstance(v, bool):
                    return "Không xác định thời hạn" if v else ""
                if isinstance(v, (int, float)):
                    return "Không xác định thời hạn" if int(v) == 1 else ""
                s = str(v).strip().lower()
                if s in {
                    "1",
                    "true",
                    "yes",
                    "x",
                    "co",
                    "có",
                    "không xác định thời hạn",
                    "khong xac dinh thoi han",
                }:
                    return "Không xác định thời hạn"
                return ""
            except Exception:
                return ""

        return str(v)

    def get_row_dict(self, row: int) -> dict | None:
        if int(row) < 0 or int(row) >= int(len(self._df)):
            return None
        s = self._df.iloc[int(row)]
        return {k: s.get(k) for k, _label, _minw in self.COLUMNS}


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
            raw_values = series.dropna().tolist()
            if key in getattr(self._model, "_date_keys", set()):
                values = [self._model._format_vn_date(v) for v in raw_values]
            else:
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

        self._always_hidden_keys: set[str] = {"id", "mcc_code", "name_on_mcc"}
        self._saved_column_widths: dict[str, int] = {}

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

        # Table font (data rows)
        body_font = QFont(UI_FONT, int(CONTENT_FONT) + 1)
        if FONT_WEIGHT_NORMAL >= 400:
            body_font.setWeight(QFont.Weight.Normal)
        self.setFont(body_font)

        # Header font & header dropdown on main header
        header_font = QFont(UI_FONT, int(CONTENT_FONT) + 1)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            header_font.setWeight(QFont.Weight.DemiBold)

        main_header = _FilterHeaderView(self._proxy, self._model, self)
        main_header.setFont(header_font)
        self.setHorizontalHeader(main_header)
        self.horizontalHeader().setVisible(True)
        self.horizontalHeader().setFixedHeight(ROW_HEIGHT)
        self._enforcing_min_width = False
        try:
            self.horizontalHeader().sectionResized.connect(self._on_section_resized)
        except Exception:
            pass

        # Delegate for main (padding-left 10px)
        self.setItemDelegate(
            _LeftPaddingDelegate(0, selected_weight=QFont.Weight.Medium, parent=self)
        )

        # Unified style (single table)
        self._apply_table_style_main()

        self._configure_columns()

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def _col_index(self, key: str) -> int:
        k = str(key or "").strip()
        for i, (col_key, _label, _minw) in enumerate(self._model.COLUMNS):
            if col_key == k:
                return int(i)
        return -1

    def show_all_columns(self) -> None:
        """Show all visible columns (keep some technical columns hidden)."""
        for i, (k, _label, _minw) in enumerate(self._model.COLUMNS):
            self.setColumnHidden(int(i), False)
        for k in self._always_hidden_keys:
            self.setColumnHidden(self._col_index(k), True)

    def _min_width_for_column(self, col: int) -> int:
        try:
            if self.isColumnHidden(int(col)):
                return 0
            key = str(self._model.COLUMNS[int(col)][0] or "").strip()
            if key in self._always_hidden_keys:
                return 0
            minw = int(self._model.COLUMNS[int(col)][2])
            if minw <= 0:
                return 0
            return max(20, minw)
        except Exception:
            return 0

    def _on_section_resized(
        self, logicalIndex: int, _oldSize: int, newSize: int
    ) -> None:
        if self._enforcing_min_width:
            return
        try:
            col = int(logicalIndex)
        except Exception:
            return
        if col < 0:
            return
        min_w = self._min_width_for_column(col)
        if min_w <= 0:
            return
        if int(newSize) < int(min_w):
            try:
                self._enforcing_min_width = True
                self.setColumnWidth(col, int(min_w))
            finally:
                self._enforcing_min_width = False

    def _apply_table_style_main(self) -> None:
        self.setStyleSheet(
            "\n".join(
                [
                    f"QTableView {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 0px; border-right: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; padding-right: 22px; }}",
                    f"QHeaderView::section:first {{ border-left: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableCornerButton::section {{ background-color: {BG_TITLE_2_HEIGHT}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 1px solid {GRID_LINES_COLOR}; border-right: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableView::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QTableView::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    f"QTableView::item:selected:active {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    "QTableView::item { padding-left: 0px; padding-right: 0px; border: 0px; }",
                    "QTableView::item:focus { outline: none; }",
                    "QTableView:focus { outline: none; }",
                ]
            )
        )

    def _configure_columns(self) -> None:
        # Hide ID + MCC columns in the main table.
        for k in self._always_hidden_keys:
            self.setColumnHidden(self._col_index(k), True)

        # Column widths (use min widths as baseline)
        for i, (k, _label, minw) in enumerate(self._model.COLUMNS):
            try:
                if str(k or "").strip() in self._always_hidden_keys:
                    continue
                if int(minw) <= 0:
                    continue
                self.setColumnWidth(int(i), int(minw))
            except Exception:
                pass

        # Main columns sizing
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setDefaultSectionSize(160)
        # Some wider columns (override baseline)
        self.setColumnWidth(self._col_index("address"), 240)
        self.setColumnWidth(self._col_index("note"), 260)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def apply_ui_settings(self) -> None:
        ui = get_employee_table_ui()

        # Table body font
        body_font = QFont(UI_FONT, int(ui.font_size))
        if ui.font_weight == "bold":
            body_font.setWeight(QFont.Weight.DemiBold)
        else:
            body_font.setWeight(QFont.Weight.Normal)
        self.setFont(body_font)

        # Header font
        header_font = QFont(UI_FONT, int(ui.header_font_size))
        header_font.setWeight(
            QFont.Weight.DemiBold
            if ui.header_font_weight == "bold"
            else QFont.Weight.Normal
        )
        try:
            self.horizontalHeader().setFont(header_font)
            # Ensure header font is not overridden by QSS.
            w = 600 if ui.header_font_weight == "bold" else 400
            self.horizontalHeader().setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {int(w)}; }}"
            )
        except Exception:
            pass

        # Per-column alignment/bold
        align_map: dict[str, Qt.AlignmentFlag] = {}
        for k, v in (ui.column_align or {}).items():
            ks = str(k or "").strip()
            vs = str(v or "").strip().lower()
            if not ks:
                continue
            if vs == "left":
                align_map[ks] = (
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
            elif vs == "center":
                align_map[ks] = Qt.AlignmentFlag.AlignCenter
            elif vs == "right":
                align_map[ks] = (
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                )

        self._model.set_ui_overrides(
            align_by_key=align_map,
            font_size=int(ui.font_size),
            font_weight=(
                QFont.Weight.DemiBold
                if ui.font_weight == "bold"
                else QFont.Weight.Normal
            ),
            column_bold=ui.column_bold,
        )

        # Per-column visibility
        try:
            visible_map = ui.column_visible or {}
        except Exception:
            visible_map = {}

        for i, (k, _label, _minw) in enumerate(self._model.COLUMNS):
            key = str(k or "").strip()
            if not key:
                continue
            if key in self._always_hidden_keys:
                try:
                    self.setColumnHidden(int(i), True)
                    self.setColumnWidth(int(i), 0)
                except Exception:
                    pass
                continue

            is_visible = bool(visible_map.get(key, True))
            if not is_visible:
                # Save width before collapsing, then set hidden + width=0.
                try:
                    cur_w = int(self.columnWidth(int(i)))
                except Exception:
                    cur_w = 0
                if cur_w > 0:
                    self._saved_column_widths[key] = cur_w
                else:
                    min_w = self._min_width_for_column(int(i))
                    if min_w > 0:
                        self._saved_column_widths[key] = int(min_w)

                try:
                    self.setColumnHidden(int(i), True)
                    self.setColumnWidth(int(i), 0)
                except Exception:
                    pass
                continue

            # Visible
            try:
                was_hidden = bool(self.isColumnHidden(int(i)))
            except Exception:
                was_hidden = False

            try:
                self.setColumnHidden(int(i), False)
            except Exception:
                pass

            # Restore width when coming back from hidden/collapsed.
            try:
                cur_w2 = int(self.columnWidth(int(i)))
            except Exception:
                cur_w2 = 0
            if was_hidden or cur_w2 <= 1:
                desired = int(self._saved_column_widths.get(key, 0) or 0)
                min_w2 = self._min_width_for_column(int(i))
                if desired <= 0:
                    desired = int(min_w2 or 0)
                if min_w2 > 0:
                    desired = max(int(min_w2), int(desired))
                if desired > 0:
                    try:
                        self.setColumnWidth(int(i), int(desired))
                    except Exception:
                        pass

        # Trigger refresh
        try:
            if self._model.rowCount() > 0 and self._model.columnCount() > 0:
                top_left = self._model.index(0, 0)
                bottom_right = self._model.index(
                    self._model.rowCount() - 1, self._model.columnCount() - 1
                )
                self._model.dataChanged.emit(top_left, bottom_right)
        except Exception:
            pass

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

    def get_selected_row_dicts(self) -> list[dict]:
        """Return selected rows as dictionaries in current view order."""

        sm = self.selectionModel()
        if sm is None:
            return []

        selected_indexes = sm.selectedIndexes()  # type: ignore[call-arg]
        if not selected_indexes:
            return []

        proxy_rows = sorted({int(i.row()) for i in selected_indexes if i.isValid()})
        if not proxy_rows:
            return []

        out: list[dict] = []
        seen_ids: set[int] = set()
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
            if emp_id > 0:
                if emp_id in seen_ids:
                    continue
                seen_ids.add(emp_id)

            out.append(dict(data))

        return out

    def set_rows(self, rows: list[dict]) -> None:
        self._model.set_rows(rows)

        # Save latest loaded rows for restore-on-tab-switch.
        try:
            if rows is not None and len(rows) <= int(_STATE_ROWS_MAX):
                _EMPLOYEE_VIEW_STATE["rows"] = list(rows or [])
            else:
                _EMPLOYEE_VIEW_STATE["rows"] = None
        except Exception:
            pass

    def get_column_filters_payload(self) -> dict[str, str] | None:
        """Return active column filters as mapping: column_key -> filter_value."""
        try:
            raw = getattr(self._proxy, "_column_filters", None)
            if not isinstance(raw, dict):
                return None
            out: dict[str, str] = {}
            for col, wanted in raw.items():
                try:
                    c = int(col)
                except Exception:
                    continue
                if c <= 0:
                    continue
                if wanted is None or str(wanted).strip() == "":
                    continue
                try:
                    key = str(self._model.COLUMNS[int(c)][0] or "").strip()
                except Exception:
                    key = ""
                if not key:
                    continue
                out[key] = str(wanted).strip()
            return out
        except Exception:
            return None

    def set_column_filters_payload(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        try:
            self._proxy.clear_all_filters()
        except Exception:
            pass

        for key, wanted in payload.items():
            if wanted is None or str(wanted).strip() == "":
                continue
            try:
                col = self._col_index(str(key))
            except Exception:
                col = -1
            if col <= 0:
                continue
            try:
                self._proxy.set_column_filter(int(col), str(wanted).strip())
            except Exception:
                continue

    def clear_column_filters(self) -> None:
        self._proxy.clear_all_filters()

    def set_title_name_filter(self, title_name: str | None) -> None:
        """Filter by the 'Chức Vụ' column (title_name) on the client side."""

        col = self._col_index("title_name")
        if col < 0:
            return
        if title_name is None or str(title_name).strip() == "":
            self._proxy.clear_column_filter(col)
            return
        self._proxy.set_column_filter(col, str(title_name).strip())


class MainContent(QWidget):
    search_changed = Signal()
    export_clicked = Signal()
    import_clicked = Signal()
    view_list_clicked = Signal()
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

        self.cbo_search_by = QComboBox()
        self.cbo_search_by.setFixedHeight(32)
        self.cbo_search_by.setFont(font_normal)
        self.cbo_search_by.addItem("Tự động", "auto")
        self.cbo_search_by.addItem("STT", "stt")
        self.cbo_search_by.addItem("Mã NV", "employee_code")
        self.cbo_search_by.addItem("Họ và tên", "full_name")
        self.cbo_search_by.setCurrentIndex(0)

        self.inp_search_text = QLineEdit()
        self.inp_search_text.setPlaceholderText("Tìm kiếm...")
        self.inp_search_text.setFixedHeight(32)
        self.inp_search_text.setFont(font_normal)

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
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: {COLOR_TEXT_LIGHT}; }}",
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

        self.btn_view_list = QPushButton("Xem danh sách")
        self.btn_view_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_list.setFixedHeight(32)
        self.btn_view_list.setIcon(QIcon(resource_path(ICON_LIST)))
        self.btn_view_list.setIconSize(QSize(18, 18))
        self.btn_view_list.setStyleSheet(btn_style)

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

        h.addWidget(self.cbo_search_by, 0)
        h.addWidget(self.inp_search_text, 1)
        h.addWidget(self.btn_view_list, 0)
        h.addWidget(self.btn_add, 0)
        h.addWidget(self.btn_edit, 0)
        h.addWidget(self.btn_delete, 0)
        h.addWidget(self.btn_refresh, 0)
        h.addWidget(self.btn_export, 0)
        h.addWidget(self.btn_import, 0)
        h.addSpacing(8)
        h.addWidget(self.label_total, 0)

        self.table = EmployeeTable(right)

        # table.mb: QFrame vẽ viền ngoài, view không vẽ border ngoài
        self.table_frame = QFrame(right)
        try:
            self.table_frame.setObjectName("employee_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#employee_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        right_layout.addWidget(header, 0)
        right_layout.addWidget(self.table_frame, 1)

        splitter.addWidget(self.department_tree)
        splitter.addWidget(right)

        # Initial splitter ratio ~30/70
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        root.addWidget(splitter, 1)

        self._restoring_state: bool = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(150)
        self._save_timer.timeout.connect(self._save_state)

        # Signals
        self.inp_search_text.textChanged.connect(lambda _t: self.search_changed.emit())
        self.cbo_search_by.currentIndexChanged.connect(
            lambda _i: self.search_changed.emit()
        )
        self.department_tree.selection_changed.connect(self.search_changed.emit)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        self.btn_import.clicked.connect(self.import_clicked.emit)
        self.btn_view_list.clicked.connect(self.view_list_clicked.emit)
        self.btn_add.clicked.connect(self.add_clicked.emit)
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)

        # Autosave triggers (debounced)
        try:
            self.inp_search_text.textChanged.connect(
                lambda *_a: self._schedule_save_state()
            )
            self.cbo_search_by.currentIndexChanged.connect(
                lambda *_a: self._schedule_save_state()
            )
            self.department_tree.selection_changed.connect(self._schedule_save_state)
        except Exception:
            pass
        try:
            # Column filter changes from header dropdown
            self.table._proxy.filters_changed.connect(self._schedule_save_state)  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            # When controller loads new data
            self.table._model.modelReset.connect(self._schedule_save_state)  # type: ignore[attr-defined]
        except Exception:
            pass

        # Restore previous state after tree + widgets are constructed.
        try:
            QTimer.singleShot(0, self.restore_cached_state_if_any)
        except Exception:
            pass

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")

        try:
            _EMPLOYEE_VIEW_STATE["total_text"] = str(self.label_total.text() or "")
        except Exception:
            pass

    def _on_refresh_clicked(self) -> None:
        # User intent: refresh should reset everything and clear cached state.
        try:
            _EMPLOYEE_VIEW_STATE.clear()
        except Exception:
            pass

        try:
            self.table.clear_column_filters()
        except Exception:
            pass

        # Reset search inputs
        try:
            self.inp_search_text.blockSignals(True)
            self.inp_search_text.setText("")
        finally:
            try:
                self.inp_search_text.blockSignals(False)
            except Exception:
                pass

        # Default search_by: Tự động
        try:
            self.cbo_search_by.blockSignals(True)
            self.cbo_search_by.setCurrentIndex(0)
        finally:
            try:
                self.cbo_search_by.blockSignals(False)
            except Exception:
                pass

        # Trigger a refresh after resetting UI state
        self.refresh_clicked.emit()

    def _schedule_save_state(self) -> None:
        try:
            if bool(getattr(self, "_restoring_state", False)):
                return
            self._save_timer.start()
        except Exception:
            try:
                self._save_state()
            except Exception:
                pass

    def _save_state(self) -> None:
        if bool(getattr(self, "_restoring_state", False)):
            return

        try:
            ctx = self.department_tree.get_selected_node_context()
        except Exception:
            ctx = None

        try:
            col_filters = self.table.get_column_filters_payload()
        except Exception:
            col_filters = None

        state = {
            "search_by": self.cbo_search_by.currentData(),
            "search_text": str(self.inp_search_text.text() or ""),
            "tree_ctx": ctx,
            "column_filters": col_filters,
            "rows": _EMPLOYEE_VIEW_STATE.get("rows"),
            "total_text": _EMPLOYEE_VIEW_STATE.get("total_text"),
        }
        _EMPLOYEE_VIEW_STATE["state"] = state

    def restore_cached_state_if_any(self) -> bool:
        state = _EMPLOYEE_VIEW_STATE.get("state")
        if not isinstance(state, dict) or not state:
            return False

        self._restoring_state = True
        try:
            # Block signals to avoid triggering controller refresh.
            try:
                self.inp_search_text.blockSignals(True)
                self.cbo_search_by.blockSignals(True)
                self.department_tree.tree.blockSignals(True)
            except Exception:
                pass

            # Restore search_by by data
            try:
                target = state.get("search_by")
                idx = -1
                for i in range(self.cbo_search_by.count()):
                    if self.cbo_search_by.itemData(i) == target:
                        idx = i
                        break
                if idx >= 0:
                    self.cbo_search_by.setCurrentIndex(int(idx))
            except Exception:
                pass

            try:
                self.inp_search_text.setText(str(state.get("search_text") or ""))
            except Exception:
                pass

            # Restore tree selection by (type,id)
            try:
                ctx = state.get("tree_ctx")
                if isinstance(ctx, dict):
                    node_id = int(ctx.get("id") or 0)
                    node_type = str(ctx.get("type") or "dept")
                    if node_id > 0:
                        found = None
                        stack: list[QTreeWidgetItem] = []
                        for i in range(self.department_tree.tree.topLevelItemCount()):
                            it = self.department_tree.tree.topLevelItem(i)
                            if it is not None:
                                stack.append(it)
                        while stack:
                            it = stack.pop(0)
                            try:
                                it_id = int(it.data(0, Qt.ItemDataRole.UserRole) or 0)
                                it_type = str(
                                    it.data(0, Qt.ItemDataRole.UserRole + 2) or "dept"
                                )
                            except Exception:
                                it_id, it_type = (0, "dept")
                            if it_id == node_id and it_type == node_type:
                                found = it
                                break
                            for j in range(it.childCount()):
                                stack.append(it.child(j))
                        if found is not None:
                            self.department_tree.tree.setCurrentItem(found)
                        else:
                            # If not found, clear selection
                            self.department_tree.tree.setCurrentItem(None)
                            self.department_tree.tree.clearSelection()
            except Exception:
                pass

            # Restore column filters and rows
            try:
                self.table.setColumnHidden(0, True)  # keep ID hidden
            except Exception:
                pass
            try:
                col_filters = state.get("column_filters")
                if isinstance(col_filters, dict):
                    self.table.set_column_filters_payload(col_filters)
            except Exception:
                pass
            restored_rows = False
            try:
                rows = state.get("rows")
                if isinstance(rows, list) and len(rows) <= int(_STATE_ROWS_MAX):
                    self.table.set_rows(rows)
                    restored_rows = True
            except Exception:
                restored_rows = False

            try:
                total_txt = str(state.get("total_text") or "")
                if total_txt:
                    self.label_total.setText(total_txt)
            except Exception:
                pass

            # Nếu không restore được rows (do quá lớn/không có), trả False để controller tự refresh.
            return bool(restored_rows)
        finally:
            try:
                self.inp_search_text.blockSignals(False)
                self.cbo_search_by.blockSignals(False)
                self.department_tree.tree.blockSignals(False)
            except Exception:
                pass
            self._restoring_state = False

    def get_filters(self) -> dict:
        dept = self.department_tree.get_selected_department()
        title = None
        try:
            title = self.department_tree.get_selected_title()
        except Exception:
            title = None

        search_text = self.inp_search_text.text().strip()
        search_by = self.cbo_search_by.currentData()
        search_by = str(search_by).strip() if search_by is not None else ""
        return {
            "search_by": search_by,
            "search_text": search_text,
            "department_id": dept[0] if dept else None,
            "title_id": title[0] if title else None,
        }
