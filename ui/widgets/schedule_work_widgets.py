"""ui.widgets.schedule_work_widgets

UI cho màn "Sắp xếp lịch Làm việc".

Yêu cầu (UI-only, chưa có nghiệp vụ):
- Sao chép TitleBar1
- TitleBar2: input tìm kiếm + combobox chọn tìm kiếm theo (Mã NV/Tên nhân viên)
    + button Tìm kiếm + button Làm mới + button Xóa lịch NV + hiển thị Tổng
- MainContent chia 2 phần:
    - Bên trái: fixed width 400, min height 254, hiển thị cây Phòng ban/Chức danh
    - Bên phải: min width 1200, min height 254, để trống (placeholder)
"""

from __future__ import annotations

from collections import defaultdict
import datetime as _dt
import time
import unicodedata

from PySide6.QtCore import (
    QDate,
    QEvent,
    QLocale,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
    QTimer,
)
from PySide6.QtGui import QFont, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    BG_TITLE_1_HEIGHT,
    BG_TITLE_2_HEIGHT,
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ICON_BIG_TO_SMALL,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    ICON_DROPDOWN,
    ICON_FILTER,
    ICON_DELETE,
    ICON_REFRESH,
    ICON_SEARCH,
    ICON_SMALL_TO_LARGE,
    ICON_TOTAL,
    INPUT_COLOR_BG,
    MAIN_CONTENT_BG_COLOR,
    TITLE_2_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
    resource_path,
)

from core.ui_settings import get_schedule_work_table_ui, ui_settings_bus
from PySide6.QtGui import QAction


_BTN_HOVER_BG = COLOR_BUTTON_PRIMARY_HOVER


# In-memory state cache to avoid losing Schedule Work filters/tables when the main
# window recreates the view while switching tabs.
_SCHEDULE_WORK_STATE: dict[str, object] = {}

# Tránh lag khi view bị recreate: không lưu/restore bảng quá lớn.
_STATE_TABLE_MAX_ROWS = 3000


def _strip_diacritics(text: str) -> str:
    try:
        decomposed = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    except Exception:
        return text


def _norm_text(v: object) -> str:
    s = str(v or "")
    s = " ".join(s.strip().split())
    s = _strip_diacritics(s)
    return s.casefold()


class _TableWidgetFilterHeaderView(QHeaderView):
    """HeaderView that draws a dropdown icon and emits a signal when it is clicked."""

    filter_icon_clicked = Signal(int)

    def __init__(
        self,
        *,
        filterable_columns: set[int] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        try:
            self.setSectionsClickable(True)
        except Exception:
            pass
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        try:
            self.setHighlightSections(False)
        except Exception:
            pass
        self._filterable_columns: set[int] = set(filterable_columns or set())
        self._dropdown_icon = QIcon(resource_path(ICON_DROPDOWN))
        self._filter_icon = QIcon(resource_path(ICON_FILTER))
        self._dropdown_icon_size = 14
        self._dropdown_icon_pad = 6
        self._resize_handle_margin = 4
        self._active_filtered_columns: set[int] = set()

    def set_active_filtered_columns(self, cols: set[int]) -> None:
        self._active_filtered_columns = set(int(c) for c in (cols or set()))
        try:
            self.viewport().update()
        except Exception:
            pass

    @staticmethod
    def _event_pos_to_point(event) -> object:
        # PySide6/Qt6: QMouseEvent.position() -> QPointF
        try:
            return event.position().toPoint()
        except Exception:
            pass
        # Older bindings: pos()
        try:
            return event.pos()
        except Exception:
            pass
        return None

    def set_filterable_columns(self, cols: set[int]) -> None:
        self._filterable_columns = set(cols or set())
        try:
            self.viewport().update()
        except Exception:
            pass

    def _dropdown_rect_for_section(self, section_rect: QRect) -> QRect:
        size = int(self._dropdown_icon_size)
        pad = int(self._dropdown_icon_pad)
        x = int(section_rect.right() - pad - size)
        y = int(section_rect.center().y() - (size // 2))
        return QRect(x, y, size, size)

    def _is_over_dropdown_icon(self, pos: QPoint) -> bool:
        try:
            col = int(self.logicalIndexAt(pos))
        except Exception:
            return False
        if col not in self._filterable_columns:
            return False
        x = int(self.sectionViewportPosition(int(col)))
        w = int(self.sectionSize(int(col)))
        sec_rect = QRect(x, 0, w, int(self.height()))
        icon_rect = self._dropdown_rect_for_section(sec_rect)
        return icon_rect.contains(pos)

    def _is_over_resize_handle(self, pos: QPoint) -> bool:
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

        if abs(px - right) <= margin:
            return True
        if col > 0 and abs(px - left) <= margin:
            return True
        return False

    def paintSection(
        self, painter: QPainter, rect, logical_index: int
    ) -> None:  # noqa: N802
        super().paintSection(painter, rect, int(logical_index))
        try:
            li = int(logical_index)
        except Exception:
            return
        if li not in self._filterable_columns:
            return
        if int(rect.width()) < (
            int(self._dropdown_icon_size) + int(self._dropdown_icon_pad) * 2
        ):
            return
        try:
            if bool(self.isSectionHidden(li)):
                return
        except Exception:
            pass
        try:
            icon_rect = self._dropdown_rect_for_section(QRect(rect))
            icon = (
                self._filter_icon
                if int(li) in set(self._active_filtered_columns or set())
                else self._dropdown_icon
            )
            pix = icon.pixmap(
                QSize(int(self._dropdown_icon_size), int(self._dropdown_icon_size))
            )
            painter.drawPixmap(icon_rect, pix)
        except Exception:
            pass

    def mousePressEvent(self, event) -> None:  # noqa: N802
        try:
            if event.button() == Qt.MouseButton.LeftButton:
                pos = self._event_pos_to_point(event)
                if pos is None:
                    return super().mousePressEvent(event)
                col = int(self.logicalIndexAt(pos))
                if col in self._filterable_columns and not self._is_over_resize_handle(
                    pos
                ):
                    x = int(self.sectionViewportPosition(int(col)))
                    w = int(self.sectionSize(int(col)))
                    sec_rect = QRect(x, 0, w, int(self.height()))
                    icon_rect = self._dropdown_rect_for_section(sec_rect)
                    if icon_rect.contains(pos):
                        try:
                            self.filter_icon_clicked.emit(int(col))
                        except Exception:
                            pass
                        event.accept()
                        return
        except Exception:
            pass
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        try:
            pos = self._event_pos_to_point(event)
            if pos is None:
                return super().mouseMoveEvent(event)
            if self._is_over_dropdown_icon(pos):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self._is_over_resize_handle(pos):
                self.setCursor(Qt.CursorShape.SplitHCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception:
            try:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            except Exception:
                pass
        return super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        try:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception:
            pass
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
            try:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            except Exception:
                pass

        return super().event(event)


class _TableWidgetColumnFilterPopup(QFrame):
    """Excel-like column filter popup: sort, search, ✅/❌ multi-select."""

    _ROLE_RAW_VALUE = int(Qt.ItemDataRole.UserRole)
    _ROLE_CHECKED = int(Qt.ItemDataRole.UserRole + 1)

    def __init__(
        self,
        parent: QWidget,
        *,
        title: str,
        values: list[str],
        selected: set[str] | None,
        on_apply,
        on_clear,
        on_sort_asc,
        on_sort_desc,
    ) -> None:
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            "\n".join(
                [
                    f"QFrame {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QLineEdit {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; padding: 6px 10px; }}",
                    f"QTreeWidget {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QTreeWidget::item {{ padding: 4px 10px; }}",
                    f"QTreeWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    f"QPushButton {{ background-color: white; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; padding: 6px 10px; }}",
                    f"QPushButton:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                ]
            )
        )

        self._title = str(title or "")
        self._all_values = [
            str(v or "").strip() for v in (values or []) if str(v or "").strip()
        ]
        self._on_apply = on_apply
        self._on_clear = on_clear
        self._on_sort_asc = on_sort_asc
        self._on_sort_desc = on_sort_desc

        self._busy = False
        self._value_items: dict[str, QTreeWidgetItem] = {}
        self._item_all: QTreeWidgetItem | None = None
        self._selected_initial: set[str] | None = None
        if selected is None:
            self._selected_initial = None
        else:
            self._selected_initial = set(
                str(v or "").strip()
                for v in (selected or set())
                if str(v or "").strip()
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        sort_row = QHBoxLayout()
        sort_row.setContentsMargins(0, 0, 0, 0)
        sort_row.setSpacing(8)

        self.btn_sort_asc = QPushButton("Sắp xếp tăng dần")
        self.btn_sort_desc = QPushButton("Sắp xếp giảm dần")
        try:
            self.btn_sort_asc.setIcon(QIcon(resource_path(ICON_SMALL_TO_LARGE)))
            self.btn_sort_desc.setIcon(QIcon(resource_path(ICON_BIG_TO_SMALL)))
            self.btn_sort_asc.setIconSize(QSize(16, 16))
            self.btn_sort_desc.setIconSize(QSize(16, 16))
        except Exception:
            pass

        sort_row.addWidget(self.btn_sort_asc, 1)
        sort_row.addWidget(self.btn_sort_desc, 1)
        root.addLayout(sort_row)

        self.inp_search = QLineEdit(self)
        self.inp_search.setPlaceholderText("Tìm kiếm...")
        self.inp_search.setMinimumHeight(32)

        # NOTE: When a QLineEdit has a stylesheet with padding, the leading action
        # can appear "missing" (clipped/overlapped). Use a QAction + text margins.
        search_icon = QIcon(resource_path(ICON_SEARCH))
        try:
            act = self.inp_search.addAction(
                search_icon,
                QLineEdit.ActionPosition.LeadingPosition,
            )
        except Exception:
            act = None
            try:
                act = QAction(search_icon, "", self.inp_search)
                self.inp_search.addAction(act, QLineEdit.ActionPosition.LeadingPosition)
            except Exception:
                pass

        # Reserve space so the icon isn't hidden by padding / text drawing
        try:
            self.inp_search.setTextMargins(28, 0, 0, 0)
        except Exception:
            pass

        root.addWidget(self.inp_search)

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setItemsExpandable(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        root.addWidget(self.tree, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        self.btn_clear = QPushButton("Xoá bộ lọc")
        self.btn_ok = QPushButton("Đồng ý")
        self.btn_cancel = QPushButton("Hủy")
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_ok)
        btn_row.addWidget(self.btn_cancel)
        root.addLayout(btn_row)

        # Keep it compact but scrollable
        self.setMinimumWidth(300)
        self.resize(300, 520)

        self._populate()

        try:
            self.btn_sort_asc.clicked.connect(self._on_sort_asc_clicked)
            self.btn_sort_desc.clicked.connect(self._on_sort_desc_clicked)
            self.inp_search.textChanged.connect(self._apply_search)
            self.tree.itemClicked.connect(self._on_item_clicked)
            self.btn_clear.clicked.connect(self._clear)
            self.btn_ok.clicked.connect(self._apply)
            self.btn_cancel.clicked.connect(self.close)
        except Exception:
            pass

    @staticmethod
    def _label_for(value: str, checked: bool) -> str:
        return f"{'✅' if checked else '❌'} {value}"

    @staticmethod
    def _set_checked(it: QTreeWidgetItem, checked: bool, raw_value: str) -> None:
        it.setData(0, _TableWidgetColumnFilterPopup._ROLE_RAW_VALUE, str(raw_value))
        it.setData(0, _TableWidgetColumnFilterPopup._ROLE_CHECKED, 1 if checked else 0)
        it.setText(
            0,
            _TableWidgetColumnFilterPopup._label_for(str(raw_value), bool(checked)),
        )

    @staticmethod
    def _is_checked(it: QTreeWidgetItem) -> bool:
        try:
            return (
                int(it.data(0, _TableWidgetColumnFilterPopup._ROLE_CHECKED) or 0) == 1
            )
        except Exception:
            return False

    def _populate(self) -> None:
        self.tree.clear()
        self._value_items.clear()

        current = self._selected_initial
        if current is None:
            selected_values = set(self._all_values)
        else:
            selected_values = set(current)

        self._busy = True
        try:
            it_all = QTreeWidgetItem(self.tree, [""])
            it_all.setFlags(
                it_all.flags()
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            _TableWidgetColumnFilterPopup._set_checked(
                it_all, bool(current is None), "(Chọn tất cả)"
            )
            self._item_all = it_all

            for v in self._all_values:
                it = QTreeWidgetItem(self.tree, [""])
                it.setFlags(
                    it.flags()
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                checked = str(v) in selected_values
                _TableWidgetColumnFilterPopup._set_checked(it, bool(checked), str(v))
                self._value_items[str(v)] = it
        finally:
            self._busy = False

    def _sync_select_all_indicator(self) -> None:
        it_all = self._item_all
        if it_all is None:
            return
        all_checked = True
        for it in self._value_items.values():
            if not _TableWidgetColumnFilterPopup._is_checked(it):
                all_checked = False
                break
        self._busy = True
        try:
            _TableWidgetColumnFilterPopup._set_checked(
                it_all, bool(all_checked), "(Chọn tất cả)"
            )
        finally:
            self._busy = False

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        if self._busy or item is None:
            return
        raw = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if raw == "(Chọn tất cả)":
            want_check = not _TableWidgetColumnFilterPopup._is_checked(item)
            self._busy = True
            try:
                _TableWidgetColumnFilterPopup._set_checked(
                    item, bool(want_check), "(Chọn tất cả)"
                )
                for v, it in self._value_items.items():
                    _TableWidgetColumnFilterPopup._set_checked(
                        it, bool(want_check), str(v)
                    )
            finally:
                self._busy = False
            return

        v = str(item.data(0, Qt.ItemDataRole.UserRole) or "").strip()
        if not v:
            return
        next_state = not _TableWidgetColumnFilterPopup._is_checked(item)
        self._busy = True
        try:
            _TableWidgetColumnFilterPopup._set_checked(item, bool(next_state), v)
        finally:
            self._busy = False
        self._sync_select_all_indicator()

    def _collect_selected(self) -> set[str]:
        selected: set[str] = set()
        for v, it in self._value_items.items():
            if _TableWidgetColumnFilterPopup._is_checked(it):
                selected.add(str(v).strip())
        return {v for v in selected if v}

    def _apply_search(self, text: str) -> None:
        q = _norm_text(text)
        for v, it in self._value_items.items():
            it.setHidden(bool(q) and (q not in _norm_text(v)))

    def _on_sort_asc_clicked(self) -> None:
        try:
            self._on_sort_asc()
        except Exception:
            pass

    def _on_sort_desc_clicked(self) -> None:
        try:
            self._on_sort_desc()
        except Exception:
            pass

    def _clear(self) -> None:
        try:
            self._on_clear()
        finally:
            self.close()

    def _apply(self) -> None:
        try:
            selected = self._collect_selected()
            all_values = set(self._all_values)
            if selected == all_values:
                self._on_apply(None)
            else:
                self._on_apply(set(selected))
        finally:
            self.close()


def _to_alignment_flag(align: str) -> Qt.AlignmentFlag:
    a = str(align or "").strip().lower()
    if a == "center":
        return Qt.AlignmentFlag.AlignCenter
    if a == "right":
        return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
    return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


def _apply_schedule_work_table_ui(
    table: QTableWidget,
    *,
    column_key_by_index: dict[int, str],
    skip_font_keys: set[str] | None = None,
) -> None:
    ui = get_schedule_work_table_ui()

    body_font_normal = QFont(UI_FONT, int(ui.font_size))
    body_font_normal.setWeight(QFont.Weight.Normal)
    body_font_bold = QFont(UI_FONT, int(ui.font_size))
    body_font_bold.setWeight(QFont.Weight.DemiBold)

    base_body = body_font_bold if ui.font_weight == "bold" else body_font_normal
    table.setFont(base_body)

    header_font = QFont(UI_FONT, int(ui.header_font_size))
    header_font.setWeight(
        QFont.Weight.DemiBold
        if ui.header_font_weight == "bold"
        else QFont.Weight.Normal
    )
    try:
        table.horizontalHeader().setFont(header_font)
        w = 600 if ui.header_font_weight == "bold" else 400
        table.horizontalHeader().setStyleSheet(
            f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {int(w)}; }}"
        )
    except Exception:
        pass

    skip_font_keys = set(skip_font_keys or set())

    # Header alignment per column (when header item exists)
    for c in range(int(table.columnCount())):
        key = column_key_by_index.get(int(c), "")
        if not key:
            continue
        flag = _to_alignment_flag((ui.column_align or {}).get(key, "left"))
        try:
            hi = table.horizontalHeaderItem(int(c))
            if hi is not None:
                hi.setTextAlignment(flag)
        except Exception:
            pass

    # Body alignment + weight per column
    for r in range(int(table.rowCount())):
        for c in range(int(table.columnCount())):
            key = column_key_by_index.get(int(c), "")
            if not key:
                continue
            it = table.item(int(r), int(c))
            if it is None:
                continue

            flag = _to_alignment_flag((ui.column_align or {}).get(key, "left"))
            try:
                it.setTextAlignment(flag)
            except Exception:
                pass

            if key in skip_font_keys:
                continue

            if key in (ui.column_bold or {}):
                use_bold = bool(ui.column_bold.get(key))
                it.setFont(body_font_bold if use_bold else body_font_normal)
            else:
                it.setFont(base_body)


class ScheduleWorkView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title1 = TitleBar1(
            "Sắp xếp lịch Làm việc", "assets/images/schedule_work.svg", self
        )
        self.title2 = TitleBar2(self)
        self.content = MainContent(self)

        root.addWidget(self.title1)
        root.addWidget(self.title2)
        root.addWidget(self.content, 1)

        # Debounced auto-save so the latest state is always available before view is destroyed.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(150)
        try:
            self._save_timer.timeout.connect(self._save_state)
        except Exception:
            pass

        def _hook_save(signal) -> None:
            try:
                signal.connect(self._schedule_save_state)
            except Exception:
                pass

        # TitleBar2 filters
        try:
            _hook_save(self.title2.cbo_search_by.currentIndexChanged)
            _hook_save(self.title2.inp_search.textChanged)
        except Exception:
            pass

        # Left tree selection
        try:
            _hook_save(self.content.left.selection_changed)
        except Exception:
            pass

        # MainRight changes
        try:
            _hook_save(self.content.right.cbo_schedule.currentIndexChanged)
        except Exception:
            pass
        try:
            self.content.right.table.itemChanged.connect(
                lambda *_: self._schedule_save_state()
            )
        except Exception:
            pass
        try:
            self.content.right.table.cellClicked.connect(
                lambda *_: self._schedule_save_state()
            )
        except Exception:
            pass

        # TempScheduleContent changes (dates + schedule + toggle + table)
        try:
            _hook_save(self.content.temp.inp_from.dateChanged)
            _hook_save(self.content.temp.inp_to.dateChanged)
            _hook_save(self.content.temp.cbo_schedule.currentIndexChanged)
            _hook_save(self.content.temp.chk_update_by_selected.toggled)
        except Exception:
            pass
        try:
            self.content.temp.table.itemChanged.connect(
                lambda *_: self._schedule_save_state()
            )
        except Exception:
            pass
        try:
            self.content.temp.table.cellClicked.connect(
                lambda *_: self._schedule_save_state()
            )
        except Exception:
            pass

        # Clear cache on explicit refresh.
        try:
            self.title2.refresh_clicked.connect(self._clear_cached_state)
        except Exception:
            pass

        # Restore previous state after controllers have had a chance to bind.
        self._did_restore_cached_state = False
        try:
            QTimer.singleShot(0, self.restore_cached_state_if_any)
        except Exception:
            pass

    def restore_cached_state_if_any(self) -> dict[str, bool]:
        """Restore cached UI state.

        Returns flags so controller can avoid overwriting restored tables on bind.
        """
        if bool(getattr(self, "_did_restore_cached_state", False)):
            return {
                "restored_right_table": False,
                "restored_temp_table": False,
                "restored_any": False,
            }
        flags = self._restore_state_if_any()
        try:
            self._did_restore_cached_state = True
        except Exception:
            pass
        return flags

    def hideEvent(self, event) -> None:  # noqa: N802
        # When switching tabs, the view may be destroyed quickly; ensure filters are saved.
        try:
            self._save_timer.stop()
        except Exception:
            pass
        try:
            self._save_state()
        except Exception:
            pass
        return super().hideEvent(event)

    def _schedule_save_state(self, *_a) -> None:
        try:
            self._save_timer.start()
        except Exception:
            try:
                self._save_state()
            except Exception:
                pass

    def _clear_cached_state(self) -> None:
        try:
            _SCHEDULE_WORK_STATE.pop("view", None)
        except Exception:
            pass

    @staticmethod
    def _capture_table(table: QTableWidget) -> list[list[dict[str, object]]] | None:
        try:
            rows = int(table.rowCount())
            cols = int(table.columnCount())
        except Exception:
            return None

        try:
            if rows > int(_STATE_TABLE_MAX_ROWS):
                return None
        except Exception:
            return None
        data: list[list[dict[str, object]]] = []
        for r in range(rows):
            row_items: list[dict[str, object]] = []
            for c in range(cols):
                it = table.item(int(r), int(c))
                if it is None:
                    row_items.append({"text": ""})
                    continue
                row_items.append({"text": str(it.text() or "")})
            data.append(row_items)
        return data

    @staticmethod
    def _restore_table(
        table: QTableWidget,
        payload: object,
        *,
        check_col: int | None = None,
    ) -> None:
        if not isinstance(payload, list):
            return
        try:
            cols = int(table.columnCount())
        except Exception:
            return

        # Restoring lots of items can freeze UI; do incremental restore when large.
        total_cells = 0
        try:
            for row_items in payload:
                if isinstance(row_items, list):
                    total_cells += min(cols, len(row_items))
        except Exception:
            total_cells = 0

        def _restore_sync() -> None:
            table.setRowCount(0)
            table.setRowCount(len(payload))
            for r, row_items in enumerate(payload):
                if not isinstance(row_items, list):
                    continue
                for c in range(min(cols, len(row_items))):
                    cell = row_items[c]
                    if not isinstance(cell, dict):
                        continue
                    txt = str(cell.get("text") or "")
                    it = QTableWidgetItem(txt)
                    it.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    if check_col is not None and int(c) == int(check_col):
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        try:
                            f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                            it.setFont(f)
                        except Exception:
                            pass
                    table.setItem(int(r), int(c), it)

        if total_cells <= 500:
            _restore_sync()
            return

        table.setRowCount(0)
        table.setRowCount(len(payload))
        try:
            table.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            table.blockSignals(True)
        except Exception:
            pass

        rows = len(payload)
        budget_ms = 10.0
        r = 0
        c = 0

        timer = QTimer(table)
        timer.setInterval(0)
        try:
            setattr(table, "_restore_state_timer", timer)
        except Exception:
            pass

        def _tick() -> None:
            nonlocal r, c
            start = time.perf_counter()
            while r < rows:
                row_items = payload[r] if isinstance(payload[r], list) else None
                if not row_items:
                    r += 1
                    c = 0
                    continue

                limit = min(cols, len(row_items))
                while c < limit:
                    cell = row_items[c]
                    if isinstance(cell, dict):
                        txt = str(cell.get("text") or "")
                        it = QTableWidgetItem(txt)
                        it.setFlags(
                            Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                        )
                        if check_col is not None and int(c) == int(check_col):
                            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            try:
                                f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                                it.setFont(f)
                            except Exception:
                                pass
                        table.setItem(int(r), int(c), it)

                    c += 1
                    if (time.perf_counter() - start) * 1000.0 >= budget_ms:
                        return

                r += 1
                c = 0

            try:
                timer.stop()
            except Exception:
                pass
            try:
                table.blockSignals(False)
            except Exception:
                pass
            try:
                table.setUpdatesEnabled(True)
            except Exception:
                pass
            try:
                delattr(table, "_restore_state_timer")
            except Exception:
                pass

        try:
            timer.timeout.connect(_tick)
        except Exception:
            _restore_sync()
            return
        timer.start()
        _tick()

    def _save_state(self) -> None:
        try:
            left_ctx = self.content.left.get_selected_node_context()
        except Exception:
            left_ctx = None

        state = {
            "title2": {
                "search_by": self.title2.cbo_search_by.currentData(),
                "search_text": str(self.title2.inp_search.text() or ""),
                "total": str(self.title2.label_total.text() or ""),
            },
            "left": {"selected": left_ctx},
            "right": {
                "schedule_data": self.content.right.cbo_schedule.currentData(),
                "header_check": str(
                    (
                        self.content.right.table.horizontalHeaderItem(
                            self.content.right.COL_CHECK
                        ).text()
                        if self.content.right.table.horizontalHeaderItem(
                            self.content.right.COL_CHECK
                        )
                        is not None
                        else ""
                    )
                ),
                "filters": (
                    self.content.right.get_column_filters_payload()
                    if hasattr(self.content.right, "get_column_filters_payload")
                    else {}
                ),
                "table": self._capture_table(self.content.right.table),
            },
            "temp": {
                "from": self.content.temp.inp_from.date(),
                "to": self.content.temp.inp_to.date(),
                "schedule_data": self.content.temp.cbo_schedule.currentData(),
                "update_by_selected": bool(
                    self.content.temp.chk_update_by_selected.isChecked()
                ),
                "header_check": str(
                    (
                        self.content.temp.table.horizontalHeaderItem(
                            self.content.temp.COL_CHECK
                        ).text()
                        if self.content.temp.table.horizontalHeaderItem(
                            self.content.temp.COL_CHECK
                        )
                        is not None
                        else ""
                    )
                ),
                "filters": (
                    self.content.temp.get_column_filters_payload()
                    if hasattr(self.content.temp, "get_column_filters_payload")
                    else {}
                ),
                "table": self._capture_table(self.content.temp.table),
            },
        }
        _SCHEDULE_WORK_STATE["view"] = state

    def _restore_state_if_any(self) -> dict[str, bool]:
        state = _SCHEDULE_WORK_STATE.get("view")
        restored_right_table = False
        restored_temp_table = False
        if not isinstance(state, dict) or not state:
            return {
                "restored_right_table": False,
                "restored_temp_table": False,
                "restored_any": False,
            }

        def _block_all(on: bool) -> None:
            try:
                self.title2.cbo_search_by.blockSignals(bool(on))
                self.title2.inp_search.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.content.left.tree.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.content.right.cbo_schedule.blockSignals(bool(on))
                self.content.right.table.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.content.temp.inp_from.blockSignals(bool(on))
                self.content.temp.inp_to.blockSignals(bool(on))
                self.content.temp.cbo_schedule.blockSignals(bool(on))
                self.content.temp.chk_update_by_selected.blockSignals(bool(on))
                self.content.temp.table.blockSignals(bool(on))
            except Exception:
                pass

        _block_all(True)
        try:
            t2 = state.get("title2") or {}
            target = t2.get("search_by")
            try:
                idx = -1
                for i in range(self.title2.cbo_search_by.count()):
                    if self.title2.cbo_search_by.itemData(i) == target:
                        idx = i
                        break
                if idx >= 0:
                    self.title2.cbo_search_by.setCurrentIndex(int(idx))
            except Exception:
                pass
            try:
                self.title2.inp_search.setText(str(t2.get("search_text") or ""))
            except Exception:
                pass
            try:
                total_txt = str(t2.get("total") or "")
                if total_txt:
                    self.title2.label_total.setText(total_txt)
            except Exception:
                pass

            # Left selection restore by node id/type.
            try:
                sel = (state.get("left") or {}).get("selected")
                if isinstance(sel, dict):
                    # Store desired ctx so it can be applied after tree data loads.
                    try:
                        self.content.left.set_desired_selection_ctx(sel)
                    except Exception:
                        pass
                    node_id = int(sel.get("id") or 0)
                    node_type = str(sel.get("type") or "dept")
                    if node_id > 0:
                        # Find matching item in tree.
                        def _iter_items(parent: QTreeWidgetItem | None):
                            if parent is None:
                                for i in range(
                                    self.content.left.tree.topLevelItemCount()
                                ):
                                    yield self.content.left.tree.topLevelItem(i)
                            else:
                                for i in range(parent.childCount()):
                                    yield parent.child(i)

                        stack: list[QTreeWidgetItem] = []
                        stack.extend([it for it in _iter_items(None) if it is not None])
                        found = None
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
                            stack.extend([it.child(i) for i in range(it.childCount())])
                        if found is not None:
                            self.content.left.tree.setCurrentItem(found)
            except Exception:
                pass

            # Right panel
            try:
                right = state.get("right") or {}
                target = right.get("schedule_data")
                try:
                    self.content.right.set_desired_schedule_data(target)
                except Exception:
                    pass
                idx = -1
                for i in range(self.content.right.cbo_schedule.count()):
                    if self.content.right.cbo_schedule.itemData(i) == target:
                        idx = i
                        break
                if idx >= 0:
                    self.content.right.cbo_schedule.setCurrentIndex(int(idx))
            except Exception:
                pass
            try:
                self._restore_table(
                    self.content.right.table,
                    (state.get("right") or {}).get("table"),
                    check_col=self.content.right.COL_CHECK,
                )
                restored_right_table = isinstance(
                    (state.get("right") or {}).get("table"), list
                )
                # Restore header checkbox text
                header_txt = str((state.get("right") or {}).get("header_check") or "")
                if header_txt in {"✅", "❌"}:
                    self.content.right._set_header_check_text(header_txt)
            except Exception:
                pass
            try:
                self.content.right.set_column_filters_payload(
                    (state.get("right") or {}).get("filters")
                )
            except Exception:
                pass

            # Temp panel
            try:
                temp = state.get("temp") or {}
                df = temp.get("from")
                dt = temp.get("to")
                if isinstance(df, QDate):
                    self.content.temp.inp_from.setDate(df)
                if isinstance(dt, QDate):
                    self.content.temp.inp_to.setDate(dt)
            except Exception:
                pass
            try:
                target = (state.get("temp") or {}).get("schedule_data")
                try:
                    self.content.temp.set_desired_schedule_data(target)
                except Exception:
                    pass
                idx = -1
                for i in range(self.content.temp.cbo_schedule.count()):
                    if self.content.temp.cbo_schedule.itemData(i) == target:
                        idx = i
                        break
                if idx >= 0:
                    self.content.temp.cbo_schedule.setCurrentIndex(int(idx))
            except Exception:
                pass
            try:
                self.content.temp.chk_update_by_selected.setChecked(
                    bool((state.get("temp") or {}).get("update_by_selected"))
                )
            except Exception:
                pass
            try:
                self._restore_table(
                    self.content.temp.table,
                    (state.get("temp") or {}).get("table"),
                    check_col=self.content.temp.COL_CHECK,
                )
                restored_temp_table = isinstance(
                    (state.get("temp") or {}).get("table"), list
                )
                header_txt = str((state.get("temp") or {}).get("header_check") or "")
                if header_txt in {"✅", "❌"}:
                    self.content.temp._set_header_check_text(header_txt)
            except Exception:
                pass
            try:
                self.content.temp.set_column_filters_payload(
                    (state.get("temp") or {}).get("filters")
                )
            except Exception:
                pass

            def _apply_filters_when_ready() -> None:
                try:
                    t1 = getattr(self.content.right.table, "_restore_state_timer", None)
                    t2 = getattr(self.content.temp.table, "_restore_state_timer", None)
                    if (t1 is not None and t1.isActive()) or (
                        t2 is not None and t2.isActive()
                    ):
                        QTimer.singleShot(30, _apply_filters_when_ready)
                        return
                except Exception:
                    pass
                try:
                    self.content.right._apply_column_filters()
                except Exception:
                    pass
                try:
                    self.content.temp._apply_column_filters()
                except Exception:
                    pass

            try:
                QTimer.singleShot(0, _apply_filters_when_ready)
            except Exception:
                pass
        finally:
            _block_all(False)

        return {
            "restored_right_table": bool(restored_right_table),
            "restored_temp_table": bool(restored_temp_table),
            "restored_any": bool(restored_right_table or restored_temp_table),
        }


def _mk_font_normal() -> QFont:
    font_normal = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_NORMAL >= 400:
        font_normal.setWeight(QFont.Weight.Normal)
    return font_normal


def _mk_font_semibold() -> QFont:
    font_semibold = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_SEMIBOLD >= 500:
        font_semibold.setWeight(QFont.Weight.DemiBold)
    return font_semibold


def _mk_combo(parent: QWidget | None = None, height: int = 32) -> QComboBox:
    cb = QComboBox(parent)
    cb.setFixedHeight(height)
    cb.setFont(_mk_font_normal())
    cb.setStyleSheet(
        "\n".join(
            [
                f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 0px; }}",
                f"QComboBox:focus {{ border: 1px solid {COLOR_BORDER}; }}",
            ]
        )
    )
    return cb


def _mk_line_edit(parent: QWidget | None = None, height: int = 32) -> QLineEdit:
    le = QLineEdit(parent)
    le.setFixedHeight(height)
    le.setFont(_mk_font_normal())
    le.setStyleSheet(
        "\n".join(
            [
                f"QLineEdit {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 0px; }}",
                f"QLineEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
            ]
        )
    )
    return le


def _mk_date_edit(parent: QWidget | None = None, height: int = 32) -> QDateEdit:
    de = QDateEdit(parent)
    de.setFixedHeight(height)
    de.setCalendarPopup(True)
    de.setDisplayFormat("dd/MM/yyyy")
    try:
        de.setDate(QDate.currentDate())
    except Exception:
        pass
    try:
        vi_locale = QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam)
        de.setLocale(vi_locale)
        # Force calendar widget so navigation bar is always shown
        cal = QCalendarWidget(de)
        cal.setLocale(vi_locale)
        # Tháng/năm luôn hiển thị (không phụ thuộc hover)
        cal.setNavigationBarVisible(True)
        # Một số global QSS có thể làm chữ tháng/năm bị "mất" (màu trùng nền).
        # Set QSS cục bộ cho calendar để month/year luôn nhìn thấy.
        cal.setStyleSheet(
            "\n".join(
                [
                    f"QCalendarWidget QWidget {{ color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QCalendarWidget QToolButton {{ color: {COLOR_TEXT_PRIMARY}; background: transparent; border: 0px; padding: 0 6px; }}",
                    f"QCalendarWidget QSpinBox {{ color: {COLOR_TEXT_PRIMARY}; background: {INPUT_COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 0px; padding: 0 6px; }}",
                    f"QCalendarWidget QComboBox {{ color: {COLOR_TEXT_PRIMARY}; background: {INPUT_COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 0px; padding: 0 6px; }}",
                    "QCalendarWidget QToolButton::menu-indicator { image: none; }",
                ]
            )
        )
        de.setCalendarWidget(cal)
    except Exception:
        pass
    de.setFont(_mk_font_normal())
    de.setStyleSheet(
        "\n".join(
            [
                f"QDateEdit {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 0px; }}",
                f"QDateEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
            ]
        )
    )
    return de


def _mk_btn_outline(
    text: str, icon_path: str | None = None, height: int = 32
) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    if icon_path:
        btn.setIcon(QIcon(resource_path(icon_path)))
        btn.setIconSize(QSize(18, 18))
    btn.setStyleSheet(
        "\n".join(
            [
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 0px; }}",
                "QPushButton::icon { margin-right: 10px; }",
                f"QPushButton:hover {{ background: {_BTN_HOVER_BG}; color: {COLOR_TEXT_LIGHT}; }}",
            ]
        )
    )
    return btn


def _mk_btn_primary(
    text: str, icon_path: str | None = None, height: int = 32
) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    if icon_path:
        btn.setIcon(QIcon(resource_path(icon_path)))
        btn.setIconSize(QSize(18, 18))
    btn.setStyleSheet(
        "\n".join(
            [
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; padding: 0 12px; border-radius: 0px; }}",
                "QPushButton::icon { margin-right: 10px; }",
                f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
            ]
        )
    )
    return btn


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
        self.label.setFont(_mk_font_normal())

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
    search_clicked = Signal()
    refresh_clicked = Signal()
    delete_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 0, 12, 0)
        root.setSpacing(8)

        self.cbo_search_by = _mk_combo(self, height=32)
        self.cbo_search_by.setMinimumWidth(170)
        self.cbo_search_by.addItem("Tự động", "auto")
        self.cbo_search_by.addItem("Mã NV", "employee_code")
        self.cbo_search_by.addItem("Tên nhân viên", "employee_name")
        try:
            self.cbo_search_by.setCurrentIndex(0)
        except Exception:
            pass

        self.inp_search = _mk_line_edit(self, height=32)
        self.inp_search.setPlaceholderText("Nhập mã NV hoặc tên nhân viên...")
        self.inp_search.setMinimumWidth(260)

        # Add search icon inside the line edit (leading)
        try:
            search_icon = QIcon(resource_path(ICON_SEARCH))
            try:
                self.inp_search.addAction(
                    search_icon,
                    QLineEdit.ActionPosition.LeadingPosition,
                )
            except Exception:
                act = QAction(search_icon, "", self.inp_search)
                self.inp_search.addAction(act, QLineEdit.ActionPosition.LeadingPosition)

            # Reserve space so the icon isn't hidden by padding / text drawing
            self.inp_search.setTextMargins(0, 0, 0, 0)
        except Exception:
            pass

        # Auto-search (debounced) instead of a dedicated Search button.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)

        self.btn_refresh = _mk_btn_outline("Làm mới", ICON_REFRESH, height=32)
        self.btn_delete = _mk_btn_outline("Xóa lịch NV", ICON_DELETE, height=32)
        self.btn_settings = _mk_btn_outline("Cài đặt", None, height=32)
        try:
            self.btn_settings.hide()
        except Exception:
            pass

        self.total_icon = QLabel("")
        self.total_icon.setFixedSize(18, 18)
        self.total_icon.setPixmap(
            QIcon(resource_path(ICON_TOTAL)).pixmap(QSize(18, 18))
        )

        self.label_total = QLabel("Tổng: 0")
        self.label_total.setFont(_mk_font_normal())
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        self.label_total.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        # Push the whole search block to the right (next to Total)
        root.addStretch(1)
        root.addWidget(self.cbo_search_by)
        root.addWidget(self.inp_search)
        root.addWidget(self.btn_refresh)
        root.addWidget(self.btn_delete)
        root.addWidget(self.btn_settings)
        root.addWidget(self.total_icon)
        root.addWidget(self.label_total)

        try:
            self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
            self.btn_delete.clicked.connect(self.delete_clicked.emit)
            self.btn_settings.clicked.connect(self.settings_clicked.emit)
        except Exception:
            pass

        # Trigger search automatically when user changes inputs.
        try:
            self._search_timer.timeout.connect(self.search_clicked.emit)
        except Exception:
            pass

        def _debounced_search() -> None:
            try:
                self._search_timer.start()
            except Exception:
                try:
                    self.search_clicked.emit()
                except Exception:
                    pass

        try:
            self.inp_search.textChanged.connect(lambda _="": _debounced_search())
            self.inp_search.returnPressed.connect(self.search_clicked.emit)
        except Exception:
            pass
        try:
            self.cbo_search_by.currentIndexChanged.connect(
                lambda _=0: _debounced_search()
            )
        except Exception:
            pass

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainLeft(QWidget):
    selection_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(400)
        self.setMinimumHeight(548)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        # Add full border so the left-most edge is visible.
        # Keep the right border to separate from the right content.
        self.setStyleSheet(
            f"background-color: {MAIN_CONTENT_BG_COLOR}; border: 1px solid {COLOR_BORDER};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Cây Phòng ban/Chức danh: style giống employee_widgets.py (DepartmentTreePreview)
        self._font_normal = _mk_font_normal()
        self._font_semibold = _mk_font_semibold()
        self._dept_icon = QIcon(resource_path("assets/images/department.svg"))
        self._title_icon = QIcon(resource_path("assets/images/job_title.svg"))

        # Cache for quick lookup
        self._dept_parent_by_id: dict[int, int | None] = {}
        self._dept_name_by_id: dict[int, str] = {}

        # Desired selection context to restore after tree rebuild.
        self._desired_ctx: dict | None = None

        self.tree = QTreeWidget(self)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        self.tree.setExpandsOnDoubleClick(False)
        # Reduce layout/paint overhead for large trees.
        try:
            self.tree.setAnimated(False)
        except Exception:
            pass
        try:
            self.tree.setUniformRowHeights(True)
        except Exception:
            pass
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setIconSize(QSize(18, 18))
        try:
            self.tree.header().setStretchLastSection(True)
        except Exception:
            pass

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

        root.addWidget(self.tree, 1)

        # Apply filter immediately when user selects a department/title node.
        try:
            self.tree.itemSelectionChanged.connect(self.selection_changed.emit)
        except Exception:
            pass

    def set_departments(
        self,
        rows: list[tuple[int, int | None, str, str]],
        titles: list[tuple[int, int | None, str]] | None = None,
    ) -> None:
        # Preserve current/desired selection before rebuilding.
        try:
            desired = self._desired_ctx or self.get_selected_node_context()
        except Exception:
            desired = self._desired_ctx

        try:
            self.tree.blockSignals(True)
        except Exception:
            pass

        # Avoid visible "giật" while clearing/rebuilding the whole tree.
        try:
            self.tree.setUpdatesEnabled(False)
        except Exception:
            pass

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
        try:
            self.tree.expandAll()
        except Exception:
            pass

        # Restore selection by stable ctx (type + id) after rebuild.
        try:
            self._desired_ctx = desired if isinstance(desired, dict) else None
            if isinstance(desired, dict):
                node_id = int(desired.get("id") or 0)
                node_type = str(desired.get("type") or "dept")
                if node_type not in ("dept", "title"):
                    node_type = "dept"
                if node_id > 0:
                    found = None
                    stack: list[QTreeWidgetItem] = []
                    for i in range(self.tree.topLevelItemCount()):
                        it = self.tree.topLevelItem(i)
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
                        self.tree.setCurrentItem(found)
        except Exception:
            pass
        finally:
            try:
                self.tree.blockSignals(False)
            except Exception:
                pass
            try:
                self.tree.setUpdatesEnabled(True)
            except Exception:
                pass
            try:
                self.tree.viewport().update()
            except Exception:
                pass

    def set_desired_selection_ctx(self, ctx: dict | None) -> None:
        self._desired_ctx = ctx if isinstance(ctx, dict) else None

    def get_selected_node_context(self) -> dict | None:
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

        parent_id = item.data(0, Qt.ItemDataRole.UserRole + 3)
        try:
            parent_id_i = int(parent_id) if parent_id is not None else None
        except Exception:
            parent_id_i = None

        if node_type == "dept":
            return {
                "type": "dept",
                "id": int(node_id),
                "name": name,
                "parent_id": parent_id_i,
            }

        # title node: parent_id field stores department_id
        return {
            "type": "title",
            "id": int(node_id),
            "name": name,
            "department_id": parent_id_i,
        }


class MainRight(QWidget):
    DISPLAY_NAME = "Lịch trình mặc định"
    COL_CHECK = 0
    COL_ID = 1
    COL_EMP_CODE = 2
    COL_MCC_CODE = 3
    COL_FULL_NAME = 4
    COL_DEPARTMENT = 5
    COL_TITLE = 6
    COL_SCHEDULE = 7

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Tên section (dùng cho debug/nhận diện và có thể target trong QSS)
        self.display_name = self.DISPLAY_NAME
        try:
            self.setObjectName("mainRight_default_schedule")
        except Exception:
            pass
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(254)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        self._desired_schedule_data: object | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        # Title của panel bên phải
        self.lbl_panel_title = QLabel(self.DISPLAY_NAME)
        self.lbl_panel_title.setFont(_mk_font_semibold())
        self.lbl_panel_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        # Header (trái→phải): label, combobox, button
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self.lbl_schedule = QLabel("Lịch làm việc")
        self.lbl_schedule.setFont(_mk_font_normal())
        self.lbl_schedule.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        self.cbo_schedule = _mk_combo(self, height=32)
        self.cbo_schedule.setFixedWidth(300)

        self.btn_apply = _mk_btn_primary("Áp dụng", None, height=32)
        self.btn_apply.setFixedWidth(100)

        header.addWidget(self.lbl_schedule)
        header.addWidget(self.cbo_schedule)
        header.addWidget(self.btn_apply)
        header.addStretch(1)

        # Bảng nhân viên
        self.table = QTableWidget(self)
        # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
        try:
            self.table.setFrameShape(QFrame.Shape.NoFrame)
            self.table.setLineWidth(0)
        except Exception:
            pass
        self.table.setRowCount(0)
        self.table.setColumnCount(8)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(True)
        try:
            self.table.setVerticalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
            self.table.setHorizontalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
        except Exception:
            pass

        # Reserve scrollbar space up-front to avoid columns "nhảy" when it appears.
        try:
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        except Exception:
            pass

        # Chunked rendering state (always initialized).
        self._render_timer: QTimer | None = None
        self._render_rows: list[dict] | list[object] = []
        self._render_schedule_map: dict[int, str] = {}
        self._render_index: int = 0
        self._is_chunk_rendering: bool = False
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            # Không hiển thị cột số thứ tự bên trái
            self.table.verticalHeader().setVisible(False)
        except Exception:
            pass

        # Match EmployeeTable row sizing
        try:
            self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
            self.table.verticalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Fixed
            )
        except Exception:
            pass

        self.table.setHorizontalHeaderLabels(
            [
                "❌",
                "ID",
                "Mã NV",
                "Mã CC",
                "Tên NV",
                "Phòng ban",
                "Chức danh",
                "Lịch làm việc",
            ]
        )

        # Column filters (Excel-like)
        self._column_filters: dict[int, set[str] | None] = {}
        self._column_filters_norm: dict[int, set[str] | None] = {}
        self._filter_popup: _TableWidgetColumnFilterPopup | None = None
        filterable_cols = {
            int(self.COL_EMP_CODE),
            int(self.COL_MCC_CODE),
            int(self.COL_FULL_NAME),
            int(self.COL_DEPARTMENT),
            int(self.COL_TITLE),
            int(self.COL_SCHEDULE),
        }
        self._filterable_cols = set(filterable_cols)

        try:
            hh_filter = _TableWidgetFilterHeaderView(
                filterable_columns=filterable_cols,
                parent=self.table,
            )
            self.table.setHorizontalHeader(hh_filter)
            self._filter_header = hh_filter
            hh_filter.filter_icon_clicked.connect(self._on_filter_icon_clicked)
        except Exception:
            self._filter_header = None

        # Header toggle-all for checkbox column
        try:
            self._set_header_check_text("❌")
            hh2 = self.table.horizontalHeader()
            hh2.sectionClicked.connect(self._on_header_clicked)
        except Exception:
            pass

        try:
            hh = self.table.horizontalHeader()
            hh.setStretchLastSection(False)
            hh.setFixedHeight(ROW_HEIGHT)
            hh.setMinimumSectionSize(60)
            # Allow user to resize columns, but keep total width within the table viewport.
            hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            try:
                hh.setSectionResizeMode(self.COL_CHECK, QHeaderView.ResizeMode.Fixed)
            except Exception:
                pass
        except Exception:
            hh = None

        try:
            self.table.setColumnWidth(self.COL_CHECK, 40)
            self.table.setColumnWidth(self.COL_ID, 40)
            self.table.setColumnWidth(self.COL_EMP_CODE, 130)
            self.table.setColumnWidth(self.COL_MCC_CODE, 130)
            self.table.setColumnWidth(self.COL_FULL_NAME, 240)
            self.table.setColumnWidth(self.COL_DEPARTMENT, 170)
            self.table.setColumnWidth(self.COL_TITLE, 160)
            self.table.setColumnWidth(self.COL_SCHEDULE, 240)
        except Exception:
            pass

        # Hide ID column per requirement
        try:
            self.table.setColumnHidden(self.COL_ID, True)
        except Exception:
            pass

        # Auto-fit columns to viewport width
        self._fixed_cols: set[int] = {self.COL_CHECK}
        self._base_widths: dict[int, int] = {
            self.COL_CHECK: 40,
            self.COL_EMP_CODE: 130,
            self.COL_MCC_CODE: 130,
            self.COL_FULL_NAME: 240,
            self.COL_DEPARTMENT: 170,
            self.COL_TITLE: 160,
            self.COL_SCHEDULE: 240,
        }
        # Use smaller mins so the table can always fit without horizontal scroll.
        self._min_widths: dict[int, int] = {
            self.COL_CHECK: 34,
            self.COL_EMP_CODE: 70,
            self.COL_MCC_CODE: 70,
            self.COL_FULL_NAME: 110,
            self.COL_DEPARTMENT: 90,
            self.COL_TITLE: 90,
            self.COL_SCHEDULE: 110,
        }

        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    f"QTableWidget::pane {{ border: 0px; }}",
                    f"QTableWidget::viewport {{ background-color: transparent; }}",
                    f"QAbstractScrollArea::corner {{ background-color: {BG_TITLE_2_HEIGHT}; border: 1px solid {GRID_LINES_COLOR}; }}",
                    # Make header borders continuous (fix missing left edge in the screenshot).
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 1px solid {GRID_LINES_COLOR}; border-right: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    # Style the top-left corner (above vertical header) so it doesn't look borderless.
                    f"QTableCornerButton::section {{ background-color: {BG_TITLE_2_HEIGHT}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 1px solid {GRID_LINES_COLOR}; border-right: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableWidget::item {{ background-color: {ODD_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:alternate {{ background-color: {EVEN_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; border-radius: 0px; }}",
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; border-radius: 0px; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._is_adjusting_columns = False
        try:
            if hh is not None:
                hh.sectionResized.connect(self._on_header_section_resized)
        except Exception:
            pass

        # QFrame bọc ngoài để viền không bao giờ mất
        self.table_frame = QFrame(self)
        try:
            self.table_frame.setObjectName("mainRight_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#mainRight_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        try:
            self.table.cellClicked.connect(self._on_cell_clicked)
        except Exception:
            pass

        try:
            self.cbo_schedule.currentIndexChanged.connect(self._update_schedule_label)
        except Exception:
            pass

        # Line separator: ngăn cách nội dung header với bảng
        self.sep_header_table = QFrame(self)
        self.sep_header_table.setFrameShape(QFrame.Shape.HLine)
        self.sep_header_table.setFixedHeight(1)
        self.sep_header_table.setStyleSheet(f"background-color: {COLOR_BORDER};")

        root.addWidget(self.lbl_panel_title)
        root.addLayout(header)
        root.addWidget(self.sep_header_table)
        root.addWidget(self.table_frame, 1)

        try:
            self.table.viewport().installEventFilter(self)
        except Exception:
            pass

        try:
            self._fit_columns_to_viewport()
        except Exception:
            pass

        # Init label text based on current selection
        try:
            self._update_schedule_label()
        except Exception:
            pass

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def get_column_filters_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for col, sel in (self._column_filters or {}).items():
            if sel is None:
                continue
            payload[str(int(col))] = sorted([str(v) for v in sel])
        return payload

    def _persist_filters_to_cached_state(self) -> None:
        """Keep filter state stable across view/table recreations."""
        try:
            state = _SCHEDULE_WORK_STATE.get("view")
            if not isinstance(state, dict):
                state = {}
                _SCHEDULE_WORK_STATE["view"] = state
            right = state.get("right")
            if not isinstance(right, dict):
                right = {}
                state["right"] = right
            right["filters"] = self.get_column_filters_payload()
        except Exception:
            pass

    def set_column_filters_payload(self, payload: object) -> None:
        self._column_filters = {}
        self._column_filters_norm = {}
        if isinstance(payload, dict):
            for k, v in payload.items():
                try:
                    col = int(k)
                except Exception:
                    continue
                if v is None:
                    continue
                if isinstance(v, (list, tuple, set)):
                    raw_set = set(str(x or "") for x in v)
                    self._column_filters[int(col)] = raw_set
                    self._column_filters_norm[int(col)] = set(
                        _norm_text(x) for x in raw_set
                    )
                else:
                    raw_set = {str(v or "")}
                    self._column_filters[int(col)] = raw_set
                    self._column_filters_norm[int(col)] = set(
                        _norm_text(x) for x in raw_set
                    )
        try:
            self._apply_column_filters()
        except Exception:
            pass

    def _get_cell_text(self, row: int, col: int) -> str:
        it = self.table.item(int(row), int(col))
        return str(it.text() or "") if it is not None else ""

    def _row_passes_filters(self, row: int, *, except_col: int | None = None) -> bool:
        for col, sel_norm in (self._column_filters_norm or {}).items():
            c = int(col)
            if except_col is not None and int(except_col) == c:
                continue
            if sel_norm is None:
                continue
            if len(sel_norm) == 0:
                return False
            raw = self._get_cell_text(int(row), int(c))
            if _norm_text(raw) not in sel_norm:
                return False
        return True

    def _apply_column_filters(self) -> None:
        try:
            self.table.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            for r in range(int(self.table.rowCount())):
                ok = self._row_passes_filters(int(r))
                try:
                    self.table.setRowHidden(int(r), not bool(ok))
                except Exception:
                    pass
        finally:
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass

        # Update header icons (dropdown -> filter.svg) based on active filters.
        try:
            hh = getattr(self, "_filter_header", None)
            if hh is not None and hasattr(hh, "set_active_filtered_columns"):
                active: set[int] = set()
                for c, sel in (self._column_filters or {}).items():
                    if sel is not None:
                        active.add(int(c))
                hh.set_active_filtered_columns(active)
        except Exception:
            pass
        try:
            self.table.viewport().update()
        except Exception:
            pass

        # Persist filters so switching table won't reset.
        try:
            self._persist_filters_to_cached_state()
        except Exception:
            pass

    def _collect_values_for_column(self, col: int) -> list[str]:
        values: set[str] = set()
        for r in range(int(self.table.rowCount())):
            if not self._row_passes_filters(int(r), except_col=int(col)):
                continue
            values.add(self._get_cell_text(int(r), int(col)))
        return sorted(list(values), key=lambda s: _norm_text(s))

    def _on_filter_icon_clicked(self, col: int) -> None:
        if int(col) == int(self.COL_CHECK) or int(col) == int(self.COL_ID):
            return
        try:
            if bool(self.table.isColumnHidden(int(col))):
                return
        except Exception:
            pass

        try:
            if self._filter_popup is not None:
                self._filter_popup.close()
        except Exception:
            pass

        header = self.table.horizontalHeader()
        try:
            # Anchor the popup next to the dropdown icon (not the whole column).
            x = int(header.sectionViewportPosition(int(col)))
            w = int(header.sectionSize(int(col)))
            sec_rect = QRect(x, 0, w, int(header.height()))
            icon_rect = None
            try:
                icon_rect = header._dropdown_rect_for_section(sec_rect)  # type: ignore[attr-defined]
            except Exception:
                icon_rect = None

            if icon_rect is None:
                size = 14
                pad = 6
                icon_rect = QRect(
                    int(sec_rect.right() - pad - size),
                    int(sec_rect.center().y() - (size // 2)),
                    int(size),
                    int(size),
                )
            pos = header.viewport().mapToGlobal(icon_rect.bottomLeft() + QPoint(0, 2))
        except Exception:
            pos = self.mapToGlobal(self.rect().bottomLeft())

        title = ""
        values = self._collect_values_for_column(int(col))
        selected = (self._column_filters or {}).get(int(col))

        def _apply(sel: set[str] | None) -> None:
            # None means select all => no filter
            if sel is None:
                self._column_filters[int(col)] = None
                self._column_filters_norm[int(col)] = None
            else:
                raw_set = set(sel)
                self._column_filters[int(col)] = raw_set
                self._column_filters_norm[int(col)] = set(
                    _norm_text(x) for x in raw_set
                )
            self._apply_column_filters()
            try:
                self._persist_filters_to_cached_state()
            except Exception:
                pass

        def _clear() -> None:
            self._column_filters[int(col)] = None
            self._column_filters_norm[int(col)] = None
            self._apply_column_filters()
            try:
                self._persist_filters_to_cached_state()
            except Exception:
                pass

        def _sort_asc() -> None:
            try:
                self.table.sortItems(int(col), Qt.SortOrder.AscendingOrder)
            except Exception:
                pass
            self._apply_column_filters()

        def _sort_desc() -> None:
            try:
                self.table.sortItems(int(col), Qt.SortOrder.DescendingOrder)
            except Exception:
                pass
            self._apply_column_filters()

        self._filter_popup = _TableWidgetColumnFilterPopup(
            self,
            title=title,
            values=values,
            selected=selected,
            on_apply=_apply,
            on_clear=_clear,
            on_sort_asc=_sort_asc,
            on_sort_desc=_sort_desc,
        )
        try:
            screen = (
                self.window().windowHandle().screen()
                if self.window() and self.window().windowHandle()
                else None
            )
            if screen:
                sg = screen.availableGeometry()
                p = QPoint(int(pos.x()), int(pos.y()))
                x = p.x()
                y = p.y()
                if x + self._filter_popup.width() > sg.right():
                    x = max(
                        int(sg.left()), int(sg.right() - self._filter_popup.width())
                    )
                if y + self._filter_popup.height() > sg.bottom():
                    y = max(
                        int(sg.top()), int(sg.bottom() - self._filter_popup.height())
                    )
                self._filter_popup.move(QPoint(x, y))
            else:
                self._filter_popup.move(pos)
        except Exception:
            try:
                self._filter_popup.move(pos)
            except Exception:
                pass
        self._filter_popup.show()

    def apply_ui_settings(self) -> None:
        try:
            mapping = {
                int(self.COL_CHECK): "check",
                int(self.COL_EMP_CODE): "employee_code",
                int(self.COL_MCC_CODE): "mcc_code",
                int(self.COL_FULL_NAME): "full_name",
                int(self.COL_DEPARTMENT): "department_name",
                int(self.COL_TITLE): "title_name",
                int(self.COL_SCHEDULE): "schedule_name",
            }
            _apply_schedule_work_table_ui(
                self.table,
                column_key_by_index=mapping,
                # Keep ✅/❌ larger font as designed
                skip_font_keys={"check"},
            )
        except Exception:
            pass

    def _update_schedule_label(self) -> None:
        try:
            name = str(self.cbo_schedule.currentText() or "").strip()
            data = self.cbo_schedule.currentData()
        except Exception:
            self.lbl_schedule.setText("Lịch làm việc")
            return

        # Placeholder
        if data is None:
            self.lbl_schedule.setText("Lịch làm việc")
            return

        # Clear option
        if str(data) == "0":
            self.lbl_schedule.setText("Lịch làm việc: Chưa sắp xếp ca")
            return

        # Selected schedule
        if name and not name.startswith("--"):
            self.lbl_schedule.setText(f"Lịch làm việc: {name}")
        else:
            self.lbl_schedule.setText("Lịch làm việc")

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        try:
            if obj is self.table.viewport() and event.type() == QEvent.Type.Resize:
                # Avoid repeated re-fit during chunk render (causes visible jitter).
                if not bool(getattr(self, "_is_chunk_rendering", False)):
                    self._fit_columns_to_viewport()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _fit_columns_to_viewport(self) -> None:
        """Auto-resize visible columns to exactly fill the table viewport width."""

        table = self.table
        if table is None:
            return

        # Visible columns
        visible_cols = [
            c
            for c in range(int(table.columnCount()))
            if not bool(table.isColumnHidden(int(c)))
        ]
        if not visible_cols:
            return

        viewport_w = int(table.viewport().width())
        if viewport_w <= 0:
            return

        # Reserve space for vertical scrollbar to avoid last column overflow.
        try:
            sbw = (
                int(table.verticalScrollBar().sizeHint().width())
                if table.verticalScrollBar().isVisible()
                else 0
            )
        except Exception:
            sbw = 0

        fixed_cols = [c for c in visible_cols if int(c) in self._fixed_cols]
        flex_cols = [c for c in visible_cols if int(c) not in self._fixed_cols]

        fixed_sum = 0
        for c in fixed_cols:
            w = int(self._base_widths.get(int(c), int(table.columnWidth(int(c))) or 0))
            w = max(int(self._min_widths.get(int(c), 0)), w)
            table.setColumnWidth(int(c), int(w))
            fixed_sum += int(w)

        available = int(viewport_w - fixed_sum - sbw)
        # Keep a small safety margin for gridlines/frame.
        available = max(0, available - 2)
        if not flex_cols:
            return

        # Use current widths as bases so user-resized proportions are preserved.
        bases = [max(1, int(table.columnWidth(int(c))) or 1) for c in flex_cols]
        base_sum = int(sum(bases))
        if base_sum <= 0:
            base_sum = len(flex_cols)

        widths: dict[int, int] = {}
        for c, b in zip(flex_cols, bases):
            min_w = int(self._min_widths.get(int(c), 0))
            w = int((available * int(b)) / base_sum) if available > 0 else 0
            w = max(min_w, w)
            widths[int(c)] = int(w)

        used = int(sum(widths.values()))

        # If we exceeded available width (small window), shrink columns down to mins.
        excess = int(used - available)
        if excess > 0:
            order = sorted(
                [int(c) for c in flex_cols],
                key=lambda col: int(widths.get(col, 0))
                - int(self._min_widths.get(col, 0)),
                reverse=True,
            )
            for col in order:
                if excess <= 0:
                    break
                min_w = int(self._min_widths.get(col, 0))
                cur = int(widths.get(col, 0))
                reducible = int(cur - min_w)
                if reducible <= 0:
                    continue
                take = min(excess, reducible)
                widths[col] = int(cur - take)
                excess -= int(take)

        # If we have room left, give it to the last flex column.
        used2 = int(sum(widths.values()))
        remainder = int(available - used2)
        if remainder != 0 and flex_cols:
            last = int(flex_cols[-1])
            widths[last] = max(
                int(self._min_widths.get(last, 0)), int(widths.get(last, 0) + remainder)
            )

        for c in flex_cols:
            table.setColumnWidth(
                int(c), int(widths.get(int(c), int(table.columnWidth(int(c)))))
            )

    def _on_header_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ) -> None:
        """Keep total visible column width within viewport when user drags a header."""

        # Ignore resize bookkeeping while we are populating rows.
        if bool(getattr(self, "_is_chunk_rendering", False)):
            return

        if self._is_adjusting_columns:
            return

        table = self.table
        if table is None:
            return

        try:
            li = int(logical_index)
        except Exception:
            return

        if bool(table.isColumnHidden(li)):
            return

        # Compute target total width inside the viewport.
        viewport_w = int(table.viewport().width())
        if viewport_w <= 0:
            return

        try:
            sbw = (
                int(table.verticalScrollBar().sizeHint().width())
                if table.verticalScrollBar().isVisible()
                else 0
            )
        except Exception:
            sbw = 0

        target_total = max(0, int(viewport_w - sbw - 2))

        visible_cols = [
            c
            for c in range(int(table.columnCount()))
            if not bool(table.isColumnHidden(int(c)))
        ]
        if not visible_cols:
            return

        try:
            current_total = int(
                sum(int(table.columnWidth(int(c))) for c in visible_cols)
            )
        except Exception:
            return

        delta = int(current_total - target_total)
        if delta == 0:
            return

        # Pick a companion column (prefer last visible, not the resized one, not fixed).
        companion: int | None = None
        for c in reversed(list(visible_cols)):
            cc = int(c)
            if cc == li:
                continue
            if cc in self._fixed_cols:
                continue
            companion = cc
            break
        if companion is None:
            return

        try:
            self._is_adjusting_columns = True

            cur_comp = int(table.columnWidth(int(companion)))
            min_comp = int(self._min_widths.get(int(companion), 0) or 0)

            if delta > 0:
                # Too wide -> shrink companion first.
                shrinkable = int(cur_comp - min_comp)
                take = int(min(delta, max(0, shrinkable)))
                if take > 0:
                    table.setColumnWidth(int(companion), int(cur_comp - take))
                    delta -= int(take)

                if delta > 0:
                    # Still too wide -> clamp the resized column back.
                    min_li = int(self._min_widths.get(int(li), 0) or 0)
                    allowed = max(min_li, int(new_size) - int(delta))
                    table.setColumnWidth(int(li), int(allowed))
            else:
                # Have spare space -> give it to companion.
                table.setColumnWidth(int(companion), int(cur_comp + (-delta)))
        finally:
            self._is_adjusting_columns = False

    def set_schedules(self, items: list[tuple[int, str]]) -> None:
        try:
            prev = self.cbo_schedule.currentData()
        except Exception:
            prev = None

        self.cbo_schedule.clear()
        # Index 0: placeholder (không áp dụng)
        self.cbo_schedule.addItem("-- Chọn lịch làm việc --", None)
        # Index 1: clear schedule assignment
        self.cbo_schedule.addItem("Chưa sắp xếp ca", 0)
        for sid, name in items or []:
            try:
                self.cbo_schedule.addItem(str(name or ""), int(sid))
            except Exception:
                continue

        # Restore desired/previous selection after repopulating.
        target = self._desired_schedule_data
        if target is None:
            target = prev
        try:
            idx = -1
            for i in range(self.cbo_schedule.count()):
                if self.cbo_schedule.itemData(i) == target:
                    idx = i
                    break
            if idx >= 0:
                self.cbo_schedule.setCurrentIndex(int(idx))
        except Exception:
            pass

    def set_desired_schedule_data(self, data: object) -> None:
        self._desired_schedule_data = data

    def apply_schedule_name_map(self, schedule_by_employee_id: dict[int, str]) -> None:
        if not schedule_by_employee_id:
            return

        for r in range(self.table.rowCount()):
            it_id = self.table.item(r, self.COL_ID)
            if it_id is None:
                continue
            raw = str(it_id.text() or "").strip()
            if not raw:
                continue
            try:
                emp_id = int(raw)
            except Exception:
                continue

            schedule_name = str(schedule_by_employee_id.get(emp_id) or "").strip()
            it_sched = self.table.item(r, self.COL_SCHEDULE)
            if it_sched is None:
                it_sched = QTableWidgetItem("")
                it_sched.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_SCHEDULE, it_sched)
            it_sched.setText(schedule_name)

    def clear_employees(self) -> None:
        self.table.setRowCount(0)

    def set_employees(self, rows: list[dict] | list[object]) -> None:
        """Accept list of dataclass-like objects or dicts.

        Expected fields:
        - id, employee_code, mcc_code, full_name
        """

        self.table.setRowCount(0)
        if not rows:
            try:
                self._set_header_check_text("❌")
            except Exception:
                pass
            return

        # Sắp xếp theo ID tăng dần để ra thứ tự 1,2,3..n ổn định
        def _key(x) -> int:
            try:
                if isinstance(x, dict):
                    return int(x.get("id") or 0)
                return int(getattr(x, "id", None) or 0)
            except Exception:
                return 0

        sorted_rows = sorted(list(rows), key=_key)

        self.table.setRowCount(len(sorted_rows))
        for r, item in enumerate(sorted_rows):

            def _get(key: str, default=""):
                if isinstance(item, dict):
                    return item.get(key, default)
                return getattr(item, key, default)

            emp_id = _get("id")
            emp_code = _get("employee_code")
            mcc_code = _get("mcc_code")
            full_name = _get("full_name")
            department_name = _get("department_name", "")
            title_name = _get("title_name", "")
            schedule_name = _get("schedule_name", "")

            # Checkbox column: default ❌ (toggle to ✅ by click)
            chk = QTableWidgetItem("❌")
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                # Làm biểu tượng ✅/❌ to hơn để dễ nhìn
                f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                chk.setFont(f)
            except Exception:
                pass
            chk.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_CHECK, chk)

            it_id = QTableWidgetItem(str(emp_id if emp_id is not None else ""))
            it_id.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_ID, it_id)

            it_code = QTableWidgetItem(str(emp_code or ""))
            it_code.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_EMP_CODE, it_code)

            it_mcc = QTableWidgetItem(str(mcc_code or ""))
            it_mcc.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_MCC_CODE, it_mcc)

            it_name = QTableWidgetItem(str(full_name or ""))
            it_name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_FULL_NAME, it_name)

            it_dept = QTableWidgetItem(str(department_name or ""))
            it_dept.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_DEPARTMENT, it_dept)

            it_title = QTableWidgetItem(str(title_name or ""))
            it_title.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_TITLE, it_title)

            it_sched = QTableWidgetItem("")
            it_sched.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_SCHEDULE, it_sched)
            try:
                it_sched.setText(str(schedule_name or "").strip())
            except Exception:
                pass

            try:
                self.table.setRowHeight(r, ROW_HEIGHT)
            except Exception:
                pass

        # Re-apply align/bold/font after content is populated.
        self.apply_ui_settings()

        # Reset header state after repopulating.
        try:
            self._set_header_check_text("❌")
        except Exception:
            pass

        try:
            self._apply_column_filters()
        except Exception:
            pass

    def cancel_render(self) -> None:
        try:
            if self._render_timer is not None and self._render_timer.isActive():
                self._render_timer.stop()
        except Exception:
            pass
        try:
            self._is_chunk_rendering = False
        except Exception:
            pass
        self._render_rows = []
        self._render_schedule_map = {}
        self._render_index = 0

    def set_employees_chunked(
        self,
        rows: list[dict] | list[object],
        schedule_by_employee_id: dict[int, str] | None = None,
        *,
        budget_ms: int = 12,
    ) -> None:
        """Render employees incrementally to keep UI responsive."""

        self.cancel_render()
        self.table.setRowCount(0)

        try:
            self._is_chunk_rendering = True
        except Exception:
            pass

        if not rows:
            try:
                self._set_header_check_text("❌")
            except Exception:
                pass
            return

        def _key(x) -> int:
            try:
                if isinstance(x, dict):
                    return int(x.get("id") or 0)
                return int(getattr(x, "id", None) or 0)
            except Exception:
                return 0

        self._render_rows = sorted(list(rows), key=_key)
        self._render_schedule_map = dict(schedule_by_employee_id or {})
        self._render_index = 0

        self.table.setRowCount(len(self._render_rows))

        if self._render_timer is None:
            self._render_timer = QTimer(self)
            self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._render_timer.timeout.connect(lambda: self._render_tick(budget_ms))

        try:
            self._render_timer.start(0)
        except Exception:
            self._render_tick(budget_ms)

    def _render_tick(self, budget_ms: int) -> None:
        if not self._render_rows:
            try:
                if self._render_timer is not None:
                    self._render_timer.stop()
            except Exception:
                pass
            return

        start = time.perf_counter()
        budget_s = max(0.001, float(budget_ms) / 1000.0)

        try:
            self.table.blockSignals(True)
        except Exception:
            pass

        # Reduce repaints while we set many items.
        try:
            self.table.setUpdatesEnabled(False)
        except Exception:
            pass

        try:
            while self._render_index < len(self._render_rows):
                r = int(self._render_index)
                item = self._render_rows[r]

                def _get(key: str, default=""):
                    if isinstance(item, dict):
                        return item.get(key, default)
                    return getattr(item, key, default)

                emp_id_raw = _get("id")
                emp_code = _get("employee_code")
                mcc_code = _get("mcc_code")
                full_name = _get("full_name")
                department_name = _get("department_name", "")
                title_name = _get("title_name", "")

                schedule_name = ""
                try:
                    emp_id_i = int(emp_id_raw or 0)
                    schedule_name = str(
                        self._render_schedule_map.get(emp_id_i) or ""
                    ).strip()
                except Exception:
                    schedule_name = str(_get("schedule_name", "") or "").strip()

                chk = QTableWidgetItem("❌")
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                try:
                    f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                    chk.setFont(f)
                except Exception:
                    pass
                chk.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, self.COL_CHECK, chk)

                it_id = QTableWidgetItem(
                    str(emp_id_raw if emp_id_raw is not None else "")
                )
                it_id.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, self.COL_ID, it_id)

                it_code = QTableWidgetItem(str(emp_code or ""))
                it_code.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_EMP_CODE, it_code)

                it_mcc = QTableWidgetItem(str(mcc_code or ""))
                it_mcc.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_MCC_CODE, it_mcc)

                it_name = QTableWidgetItem(str(full_name or ""))
                it_name.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_FULL_NAME, it_name)

                it_dept = QTableWidgetItem(str(department_name or ""))
                it_dept.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_DEPARTMENT, it_dept)

                it_title = QTableWidgetItem(str(title_name or ""))
                it_title.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_TITLE, it_title)

                it_sched = QTableWidgetItem(str(schedule_name or ""))
                it_sched.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_SCHEDULE, it_sched)

                try:
                    self.table.setRowHeight(r, ROW_HEIGHT)
                except Exception:
                    pass

                # Apply filtering during chunked render so it is visible immediately.
                try:
                    self.table.setRowHidden(
                        int(r), not bool(self._row_passes_filters(int(r)))
                    )
                except Exception:
                    pass

                self._render_index += 1

                if (time.perf_counter() - start) >= budget_s:
                    break
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass

        try:
            self.table.viewport().update()
        except Exception:
            pass

        if self._render_index >= len(self._render_rows):
            try:
                if self._render_timer is not None:
                    self._render_timer.stop()
            except Exception:
                pass

            try:
                self._is_chunk_rendering = False
            except Exception:
                pass

            try:
                self.apply_ui_settings()
            except Exception:
                pass

            try:
                self._set_header_check_text("❌")
            except Exception:
                pass

            # Fit once after render completes (prevents column jitter).
            try:
                self._fit_columns_to_viewport()
            except Exception:
                pass

            try:
                self._apply_column_filters()
            except Exception:
                pass

    def get_checked_employee_ids(self) -> list[int]:
        ids: list[int] = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, self.COL_CHECK)
            if chk is None or chk.text() != "✅":
                continue
            it_id = self.table.item(r, self.COL_ID)
            if it_id is None:
                continue
            raw = str(it_id.text() or "").strip()
            if not raw:
                continue
            try:
                ids.append(int(raw))
            except Exception:
                continue
        return ids

    def apply_schedule_to_checked(self, schedule_name: str) -> int:
        applied = 0
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, self.COL_CHECK)
            if chk is None or chk.text() != "✅":
                continue
            it_sched = self.table.item(r, self.COL_SCHEDULE)
            if it_sched is None:
                it_sched = QTableWidgetItem("")
                it_sched.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_SCHEDULE, it_sched)
            it_sched.setText(str(schedule_name or "").strip())
            applied += 1
        return applied

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col != self.COL_CHECK:
            return
        it = self.table.item(row, col)
        if it is None:
            return
        it.setText("✅" if it.text() != "✅" else "❌")

        try:
            self._sync_header_check_from_rows()
        except Exception:
            pass

    def _set_header_check_text(self, txt: str) -> None:
        # Ensure header shows ✅/❌ clearly.
        if txt not in {"✅", "❌"}:
            txt = "❌"
        try:
            hi = self.table.horizontalHeaderItem(int(self.COL_CHECK))
            if hi is None:
                hi = QTableWidgetItem("")
                self.table.setHorizontalHeaderItem(int(self.COL_CHECK), hi)
            hi.setText(txt)
            hi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                hi.setFont(f)
            except Exception:
                pass
        except Exception:
            pass

    def _sync_header_check_from_rows(self) -> None:
        any_rows = int(self.table.rowCount()) > 0
        any_checked = False
        all_checked = True if any_rows else False
        for r in range(int(self.table.rowCount())):
            it = self.table.item(int(r), int(self.COL_CHECK))
            checked = it is not None and str(it.text() or "").strip() == "✅"
            any_checked = any_checked or checked
            all_checked = all_checked and checked
        self._set_header_check_text("✅" if (any_rows and all_checked) else "❌")

    def _on_header_clicked(self, section: int) -> None:
        # Clicking the check column header toggles all ✅/❌.
        if int(section) != int(self.COL_CHECK):
            return
        try:
            cur = "❌"
            hi = self.table.horizontalHeaderItem(int(self.COL_CHECK))
            if hi is not None:
                cur = str(hi.text() or "❌").strip()
            new_txt = "✅" if cur != "✅" else "❌"
        except Exception:
            new_txt = "✅"

        try:
            self.table.blockSignals(True)
        except Exception:
            pass
        try:
            for r in range(int(self.table.rowCount())):
                it = self.table.item(int(r), int(self.COL_CHECK))
                if it is None:
                    it = QTableWidgetItem("❌")
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    try:
                        f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                        it.setFont(f)
                    except Exception:
                        pass
                    it.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    self.table.setItem(int(r), int(self.COL_CHECK), it)
                it.setText(new_txt)
            self._set_header_check_text(new_txt)
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass


class TempScheduleContent(QWidget):
    add_clicked = Signal()
    delete_clicked = Signal()

    COL_ID = 0
    COL_CHECK = 1
    COL_EMP_CODE = 2
    COL_FULL_NAME = 3
    COL_FROM_DATE = 4
    COL_TO_DATE = 5
    COL_SCHEDULE = 6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        self._desired_schedule_data: object | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        self.lbl_title = QLabel("Lịch trình tạm")
        self.lbl_title.setFont(_mk_font_semibold())
        self.lbl_title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        # Left controls
        self.left = QWidget(self)
        self.left.setFixedWidth(400)
        self.left.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.left.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.left.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        left_root = QVBoxLayout(self.left)
        left_root.setContentsMargins(0, 0, 0, 0)
        left_root.setSpacing(8)

        self.lbl_from = QLabel("Từ ngày")
        self.lbl_from.setFont(_mk_font_normal())
        self.lbl_from.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.inp_from = _mk_date_edit(self.left, height=32)

        self.lbl_to = QLabel("Đến ngày")
        self.lbl_to.setFont(_mk_font_normal())
        self.lbl_to.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.inp_to = _mk_date_edit(self.left, height=32)

        self.lbl_schedule = QLabel("Lịch làm việc")
        self.lbl_schedule.setFont(_mk_font_normal())
        self.lbl_schedule.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.cbo_schedule = _mk_combo(self.left, height=32)
        self.cbo_schedule.setFixedWidth(300)

        # Toggle dạng ❌/✅ (thay thế QCheckBox mặc định)
        self.chk_update_by_selected = QPushButton("❌ Cập nhập theo nhân viên chọn")
        self.chk_update_by_selected.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_update_by_selected.setCheckable(True)
        # Default: unchecked (user can toggle)
        self.chk_update_by_selected.setChecked(False)
        self.chk_update_by_selected.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_update_by_selected.setFont(_mk_font_normal())
        self.chk_update_by_selected.setStyleSheet(
            "\n".join(
                [
                    "QPushButton { border: 0px; background: transparent; text-align: left; padding: 0px; }",
                    f"QPushButton {{ color: {COLOR_TEXT_PRIMARY}; }}",
                ]
            )
        )

        def _sync_update_by_selected_text() -> None:
            prefix = "✅" if bool(self.chk_update_by_selected.isChecked()) else "❌"
            self.chk_update_by_selected.setText(
                f"{prefix} Cập nhập theo nhân viên chọn"
            )

        try:
            self.chk_update_by_selected.toggled.connect(_sync_update_by_selected_text)
        except Exception:
            pass
        _sync_update_by_selected_text()

        # Allow user to toggle
        try:
            self.chk_update_by_selected.setEnabled(True)
        except Exception:
            pass

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(10)

        self.btn_add = _mk_btn_primary("Thêm mới", None, height=32)
        self.btn_add.setFixedWidth(120)
        self.btn_delete = _mk_btn_outline("Xóa bỏ", ICON_DELETE, height=32)
        self.btn_delete.setFixedWidth(120)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)

        left_root.addWidget(self.lbl_from)
        left_root.addWidget(self.inp_from)
        left_root.addWidget(self.lbl_to)
        left_root.addWidget(self.inp_to)
        left_root.addWidget(self.lbl_schedule)
        left_root.addWidget(self.cbo_schedule)
        left_root.addWidget(self.chk_update_by_selected)
        left_root.addLayout(btn_row)
        left_root.addStretch(1)

        # Right table
        self.table = QTableWidget(self)
        # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
        try:
            self.table.setFrameShape(QFrame.Shape.NoFrame)
            self.table.setLineWidth(0)
        except Exception:
            pass
        self.table.setRowCount(0)
        self.table.setColumnCount(7)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(True)
        try:
            self.table.setVerticalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
            self.table.setHorizontalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )
        except Exception:
            pass

        # Reserve scrollbar space up-front to avoid columns "nhảy" when it appears.
        try:
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        except Exception:
            pass

        self._render_timer: QTimer | None = None
        self._render_rows: list[dict] = []
        self._render_index: int = 0
        self._is_chunk_rendering: bool = False
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "❌",
                "Mã NV",
                "Tên Nhân viên",
                "Từ ngày",
                "Đến ngày",
                "Lịch làm việc",
            ]
        )

        # Column filters (Excel-like)
        self._column_filters: dict[int, set[str] | None] = {}
        self._column_filters_norm: dict[int, set[str] | None] = {}
        self._filter_popup: _TableWidgetColumnFilterPopup | None = None
        filterable_cols = {
            int(self.COL_EMP_CODE),
            int(self.COL_FULL_NAME),
            int(self.COL_FROM_DATE),
            int(self.COL_TO_DATE),
            int(self.COL_SCHEDULE),
        }
        self._filterable_cols = set(filterable_cols)
        try:
            hh_filter = _TableWidgetFilterHeaderView(
                filterable_columns=filterable_cols,
                parent=self.table,
            )
            self.table.setHorizontalHeader(hh_filter)
            self._filter_header = hh_filter
            hh_filter.filter_icon_clicked.connect(self._on_filter_icon_clicked)
        except Exception:
            self._filter_header = None

        # Header toggle-all for checkbox column
        try:
            self._set_header_check_text("❌")
            hh2 = self.table.horizontalHeader()
            hh2.sectionClicked.connect(self._on_header_clicked)
        except Exception:
            pass

        try:
            hh = self.table.horizontalHeader()
            hh.setStretchLastSection(True)
            hh.setFixedHeight(ROW_HEIGHT)
            hh.setMinimumSectionSize(80)

            # We will manage column widths ourselves to always fit the viewport.
            hh.setStretchLastSection(False)
            hh.setMinimumSectionSize(60)
            hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        except Exception:
            pass

        try:
            self.table.setColumnWidth(self.COL_ID, 60)
            self.table.setColumnWidth(self.COL_CHECK, 40)
            self.table.setColumnWidth(self.COL_EMP_CODE, 120)
            self.table.setColumnWidth(self.COL_FULL_NAME, 220)
            self.table.setColumnWidth(self.COL_FROM_DATE, 110)
            self.table.setColumnWidth(self.COL_TO_DATE, 110)
            self.table.setColumnWidth(self.COL_SCHEDULE, 220)
        except Exception:
            pass

        try:
            self.table.verticalHeader().setVisible(False)
            self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
            self.table.verticalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Fixed
            )
        except Exception:
            pass

        # Hide ID column (giữ dữ liệu, chỉ ẩn hiển thị)
        try:
            self.table.setColumnHidden(self.COL_ID, True)
        except Exception:
            pass

        # Auto-fit columns to viewport width
        self._fixed_cols: set[int] = set()
        self._base_widths: dict[int, int] = {
            self.COL_CHECK: 40,
            self.COL_EMP_CODE: 120,
            self.COL_FULL_NAME: 220,
            self.COL_FROM_DATE: 110,
            self.COL_TO_DATE: 110,
            self.COL_SCHEDULE: 220,
        }
        # Use smaller mins so the table can always fit without horizontal scroll.
        self._min_widths: dict[int, int] = {
            self.COL_CHECK: 34,
            self.COL_EMP_CODE: 70,
            self.COL_FULL_NAME: 110,
            self.COL_FROM_DATE: 80,
            self.COL_TO_DATE: 80,
            self.COL_SCHEDULE: 110,
        }

        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    f"QTableWidget::pane {{ border: 0px; }}",
                    f"QTableWidget::viewport {{ background-color: transparent; }}",
                    f"QAbstractScrollArea::corner {{ background-color: {BG_TITLE_2_HEIGHT}; border: 1px solid {GRID_LINES_COLOR}; }}",
                    # Make header borders continuous (fix missing left edge in the screenshot).
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 1px solid {GRID_LINES_COLOR}; border-right: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    # Style the top-left corner (above vertical header) so it doesn't look borderless.
                    f"QTableCornerButton::section {{ background-color: {BG_TITLE_2_HEIGHT}; border-top: 1px solid {GRID_LINES_COLOR}; border-bottom: 1px solid {GRID_LINES_COLOR}; border-left: 1px solid {GRID_LINES_COLOR}; border-right: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableWidget::item {{ background-color: {ODD_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:alternate {{ background-color: {EVEN_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; border-radius: 0px; }}",
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; border-radius: 0px; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        # QFrame bọc ngoài để viền không bao giờ mất
        self.table_frame = QFrame(self)
        try:
            self.table_frame.setObjectName("tempSchedule_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#tempSchedule_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        # Vertical separator: ngăn cách phần nhập liệu (trái) với bảng (phải)
        self.sep_left_table = QFrame(self)
        self.sep_left_table.setFrameShape(QFrame.Shape.VLine)
        self.sep_left_table.setFixedWidth(1)
        self.sep_left_table.setStyleSheet(f"background-color: {COLOR_BORDER};")

        row.addWidget(self.left)
        row.addWidget(self.sep_left_table)
        row.addWidget(self.table_frame, 1)

        root.addWidget(self.lbl_title)
        root.addLayout(row)

        try:
            self.btn_add.clicked.connect(self.add_clicked.emit)
            self.btn_delete.clicked.connect(self.delete_clicked.emit)
        except Exception:
            pass

        # Toggle check column (✅/❌)
        try:
            self.table.cellClicked.connect(self._on_cell_clicked)
        except Exception:
            pass

        try:
            self.table.viewport().installEventFilter(self)
        except Exception:
            pass

        self._is_adjusting_columns = False
        try:
            hh = self.table.horizontalHeader()
            hh.sectionResized.connect(self._on_header_section_resized)
        except Exception:
            pass

        try:
            self._fit_columns_to_viewport()
        except Exception:
            pass

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def apply_ui_settings(self) -> None:
        try:
            mapping = {
                int(self.COL_CHECK): "check",
                int(self.COL_EMP_CODE): "employee_code",
                int(self.COL_FULL_NAME): "full_name",
                int(self.COL_FROM_DATE): "from_date",
                int(self.COL_TO_DATE): "to_date",
                int(self.COL_SCHEDULE): "schedule_name",
            }
            _apply_schedule_work_table_ui(
                self.table,
                column_key_by_index=mapping,
                skip_font_keys={"check"},
            )
        except Exception:
            pass

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        try:
            if obj is self.table.viewport() and event.type() == QEvent.Type.Resize:
                if not bool(getattr(self, "_is_chunk_rendering", False)):
                    self._fit_columns_to_viewport()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _fit_columns_to_viewport(self) -> None:
        """Auto-resize visible columns to exactly fill the table viewport width."""

        table = self.table
        if table is None:
            return

        visible_cols = [
            c
            for c in range(int(table.columnCount()))
            if not bool(table.isColumnHidden(int(c)))
        ]
        if not visible_cols:
            return

        viewport_w = int(table.viewport().width())
        if viewport_w <= 0:
            return

        try:
            sbw = (
                int(table.verticalScrollBar().sizeHint().width())
                if table.verticalScrollBar().isVisible()
                else 0
            )
        except Exception:
            sbw = 0

        fixed_cols = [c for c in visible_cols if int(c) in self._fixed_cols]
        flex_cols = [c for c in visible_cols if int(c) not in self._fixed_cols]

        fixed_sum = 0
        for c in fixed_cols:
            w = int(self._base_widths.get(int(c), int(table.columnWidth(int(c))) or 0))
            w = max(int(self._min_widths.get(int(c), 0)), w)
            table.setColumnWidth(int(c), int(w))
            fixed_sum += int(w)

        available = int(viewport_w - fixed_sum - sbw)
        available = max(0, available - 2)
        if not flex_cols:
            return

        # Use current widths as bases so user-resized proportions are preserved.
        bases = [max(1, int(table.columnWidth(int(c))) or 1) for c in flex_cols]
        base_sum = int(sum(bases))
        if base_sum <= 0:
            base_sum = len(flex_cols)

        widths: dict[int, int] = {}
        for c, b in zip(flex_cols, bases):
            min_w = int(self._min_widths.get(int(c), 0))
            w = int((available * int(b)) / base_sum) if available > 0 else 0
            w = max(min_w, w)
            widths[int(c)] = int(w)

        used = int(sum(widths.values()))

        excess = int(used - available)
        if excess > 0:
            order = sorted(
                [int(c) for c in flex_cols],
                key=lambda col: int(widths.get(col, 0))
                - int(self._min_widths.get(col, 0)),
                reverse=True,
            )
            for col in order:
                if excess <= 0:
                    break
                min_w = int(self._min_widths.get(col, 0))
                cur = int(widths.get(col, 0))
                reducible = int(cur - min_w)
                if reducible <= 0:
                    continue
                take = min(excess, reducible)
                widths[col] = int(cur - take)
                excess -= int(take)

        used2 = int(sum(widths.values()))
        remainder = int(available - used2)
        if remainder != 0 and flex_cols:
            last = int(flex_cols[-1])
            widths[last] = max(
                int(self._min_widths.get(last, 0)), int(widths.get(last, 0) + remainder)
            )

        for c in flex_cols:
            table.setColumnWidth(
                int(c), int(widths.get(int(c), int(table.columnWidth(int(c)))))
            )

    def _on_header_section_resized(
        self, logical_index: int, old_size: int, new_size: int
    ) -> None:
        # Ignore resize bookkeeping while we are populating rows.
        if bool(getattr(self, "_is_chunk_rendering", False)):
            return
        if self._is_adjusting_columns:
            return

        table = self.table
        if table is None:
            return

        try:
            li = int(logical_index)
        except Exception:
            return
        if bool(table.isColumnHidden(li)):
            return

        viewport_w = int(table.viewport().width())
        if viewport_w <= 0:
            return

        try:
            sbw = (
                int(table.verticalScrollBar().sizeHint().width())
                if table.verticalScrollBar().isVisible()
                else 0
            )
        except Exception:
            sbw = 0

        target_total = max(0, int(viewport_w - sbw - 2))
        visible_cols = [
            c
            for c in range(int(table.columnCount()))
            if not bool(table.isColumnHidden(int(c)))
        ]
        if not visible_cols:
            return

        try:
            current_total = int(
                sum(int(table.columnWidth(int(c))) for c in visible_cols)
            )
        except Exception:
            return

        delta = int(current_total - target_total)
        if delta == 0:
            return

        companion: int | None = None
        for c in reversed(list(visible_cols)):
            cc = int(c)
            if cc == li:
                continue
            companion = cc
            break
        if companion is None:
            return

        try:
            self._is_adjusting_columns = True

            cur_comp = int(table.columnWidth(int(companion)))
            min_comp = int(self._min_widths.get(int(companion), 0) or 0)

            if delta > 0:
                shrinkable = int(cur_comp - min_comp)
                take = int(min(delta, max(0, shrinkable)))
                if take > 0:
                    table.setColumnWidth(int(companion), int(cur_comp - take))
                    delta -= int(take)

                if delta > 0:
                    min_li = int(self._min_widths.get(int(li), 0) or 0)
                    allowed = max(min_li, int(new_size) - int(delta))
                    table.setColumnWidth(int(li), int(allowed))
            else:
                table.setColumnWidth(int(companion), int(cur_comp + (-delta)))
        finally:
            self._is_adjusting_columns = False

    def _fmt_date(self, v) -> str:
        if v is None:
            return ""
        try:
            if isinstance(v, QDate):
                return str(v.toString("dd/MM/yyyy") or "")
        except Exception:
            pass
        try:
            if isinstance(v, (_dt.datetime, _dt.date)):
                return str(v.strftime("%d/%m/%Y"))
        except Exception:
            pass

        s = str(v or "").strip()
        if not s:
            return ""

        raw = s.split(" ", 1)[0].strip().replace("/", "-")
        try:
            if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
                yy, mm, dd = raw.split("-")
                dt = _dt.date(int(yy), int(mm), int(dd))
                return dt.strftime("%d/%m/%Y")
        except Exception:
            pass

        return s

    def clear_rows(self) -> None:
        self.table.setRowCount(0)

    def set_rows(self, rows: list[dict]) -> None:
        """Render temp schedule assignments into the right table."""

        self.table.setRowCount(0)
        if not rows:
            try:
                self._set_header_check_text("❌")
            except Exception:
                pass
            return

        self.table.setRowCount(len(rows))
        for r, item in enumerate(list(rows)):
            assignment_id = item.get("id")
            emp_code = item.get("employee_code")
            full_name = item.get("full_name")
            from_date = item.get("effective_from")
            to_date = item.get("effective_to")
            schedule_name = item.get("schedule_name")

            it_id = QTableWidgetItem(
                str(assignment_id if assignment_id is not None else "")
            )
            it_id.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_ID, it_id)

            chk = QTableWidgetItem("❌")
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                chk.setFont(f)
            except Exception:
                pass
            chk.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_CHECK, chk)

            it_code = QTableWidgetItem(str(emp_code or ""))
            it_code.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_EMP_CODE, it_code)

            it_name = QTableWidgetItem(str(full_name or ""))
            it_name.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_FULL_NAME, it_name)

            it_from = QTableWidgetItem(self._fmt_date(from_date))
            it_from.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_FROM_DATE, it_from)

            it_to = QTableWidgetItem(self._fmt_date(to_date))
            it_to.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_TO_DATE, it_to)

            it_sched = QTableWidgetItem(str(schedule_name or ""))
            it_sched.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(r, self.COL_SCHEDULE, it_sched)

            try:
                self.table.setRowHeight(r, ROW_HEIGHT)
            except Exception:
                pass

        # Re-apply align/bold/font after content is populated.
        self.apply_ui_settings()

        try:
            self._set_header_check_text("❌")
        except Exception:
            pass

        try:
            self._apply_column_filters()
        except Exception:
            pass

    def cancel_render(self) -> None:
        try:
            if self._render_timer is not None and self._render_timer.isActive():
                self._render_timer.stop()
        except Exception:
            pass
        try:
            self._is_chunk_rendering = False
        except Exception:
            pass
        self._render_rows = []
        self._render_index = 0

    def set_rows_chunked(self, rows: list[dict], *, budget_ms: int = 12) -> None:
        """Render temp assignments incrementally to keep UI responsive."""

        self.cancel_render()
        self.table.setRowCount(0)

        try:
            self._is_chunk_rendering = True
        except Exception:
            pass
        if not rows:
            try:
                self._set_header_check_text("❌")
            except Exception:
                pass
            return

        self._render_rows = list(rows or [])
        self._render_index = 0
        self.table.setRowCount(len(self._render_rows))

        if self._render_timer is None:
            self._render_timer = QTimer(self)
            self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._render_timer.timeout.connect(lambda: self._render_tick(budget_ms))

        try:
            self._render_timer.start(0)
        except Exception:
            self._render_tick(budget_ms)

    def _render_tick(self, budget_ms: int) -> None:
        if not self._render_rows:
            try:
                if self._render_timer is not None:
                    self._render_timer.stop()
            except Exception:
                pass
            return

        start = time.perf_counter()
        budget_s = max(0.001, float(budget_ms) / 1000.0)

        try:
            self.table.blockSignals(True)
        except Exception:
            pass

        try:
            self.table.setUpdatesEnabled(False)
        except Exception:
            pass

        try:
            while self._render_index < len(self._render_rows):
                r = int(self._render_index)
                item = self._render_rows[r] or {}

                assignment_id = item.get("id")
                emp_code = item.get("employee_code")
                full_name = item.get("full_name")
                from_date = item.get("effective_from")
                to_date = item.get("effective_to")
                schedule_name = item.get("schedule_name")

                it_id = QTableWidgetItem(
                    str(assignment_id if assignment_id is not None else "")
                )
                it_id.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, self.COL_ID, it_id)

                chk = QTableWidgetItem("❌")
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                try:
                    f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                    chk.setFont(f)
                except Exception:
                    pass
                chk.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, self.COL_CHECK, chk)

                it_code = QTableWidgetItem(str(emp_code or ""))
                it_code.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_EMP_CODE, it_code)

                it_name = QTableWidgetItem(str(full_name or ""))
                it_name.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_FULL_NAME, it_name)

                it_from = QTableWidgetItem(self._fmt_date(from_date))
                it_from.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_FROM_DATE, it_from)

                it_to = QTableWidgetItem(self._fmt_date(to_date))
                it_to.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, self.COL_TO_DATE, it_to)

                it_sched = QTableWidgetItem(str(schedule_name or ""))
                it_sched.setFlags(
                    Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                )
                self.table.setItem(r, self.COL_SCHEDULE, it_sched)

                try:
                    self.table.setRowHeight(r, ROW_HEIGHT)
                except Exception:
                    pass

                # Apply filtering during chunked render so it is visible immediately.
                try:
                    self.table.setRowHidden(
                        int(r), not bool(self._row_passes_filters(int(r)))
                    )
                except Exception:
                    pass

                self._render_index += 1
                if (time.perf_counter() - start) >= budget_s:
                    break
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass

        try:
            self.table.viewport().update()
        except Exception:
            pass

        if self._render_index >= len(self._render_rows):
            try:
                if self._render_timer is not None:
                    self._render_timer.stop()
            except Exception:
                pass

            try:
                self._is_chunk_rendering = False
            except Exception:
                pass

            try:
                self.apply_ui_settings()
            except Exception:
                pass

            try:
                self._set_header_check_text("❌")
            except Exception:
                pass

            try:
                self._fit_columns_to_viewport()
            except Exception:
                pass

            try:
                self._apply_column_filters()
            except Exception:
                pass

    def get_column_filters_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        for col, sel in (self._column_filters or {}).items():
            if sel is None:
                continue
            payload[str(int(col))] = sorted([str(v) for v in sel])
        return payload

    def _persist_filters_to_cached_state(self) -> None:
        """Keep filter state stable across view/table recreations."""
        try:
            state = _SCHEDULE_WORK_STATE.get("view")
            if not isinstance(state, dict):
                state = {}
                _SCHEDULE_WORK_STATE["view"] = state
            temp = state.get("temp")
            if not isinstance(temp, dict):
                temp = {}
                state["temp"] = temp
            temp["filters"] = self.get_column_filters_payload()
        except Exception:
            pass

    def set_column_filters_payload(self, payload: object) -> None:
        self._column_filters = {}
        self._column_filters_norm = {}
        if isinstance(payload, dict):
            for k, v in payload.items():
                try:
                    col = int(k)
                except Exception:
                    continue
                if v is None:
                    continue
                if isinstance(v, (list, tuple, set)):
                    raw_set = set(str(x or "") for x in v)
                    self._column_filters[int(col)] = raw_set
                    self._column_filters_norm[int(col)] = set(
                        _norm_text(x) for x in raw_set
                    )
                else:
                    raw_set = {str(v or "")}
                    self._column_filters[int(col)] = raw_set
                    self._column_filters_norm[int(col)] = set(
                        _norm_text(x) for x in raw_set
                    )
        try:
            self._apply_column_filters()
        except Exception:
            pass

    def _get_cell_text(self, row: int, col: int) -> str:
        it = self.table.item(int(row), int(col))
        return str(it.text() or "") if it is not None else ""

    def _row_passes_filters(self, row: int, *, except_col: int | None = None) -> bool:
        for col, sel_norm in (self._column_filters_norm or {}).items():
            c = int(col)
            if except_col is not None and int(except_col) == c:
                continue
            if sel_norm is None:
                continue
            if len(sel_norm) == 0:
                return False
            raw = self._get_cell_text(int(row), int(c))
            if _norm_text(raw) not in sel_norm:
                return False
        return True

    def _apply_column_filters(self) -> None:
        try:
            self.table.setUpdatesEnabled(False)
        except Exception:
            pass
        try:
            for r in range(int(self.table.rowCount())):
                ok = self._row_passes_filters(int(r))
                try:
                    self.table.setRowHidden(int(r), not bool(ok))
                except Exception:
                    pass
        finally:
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass

        # Update header icons (dropdown -> filter.svg) based on active filters.
        try:
            hh = getattr(self, "_filter_header", None)
            if hh is not None and hasattr(hh, "set_active_filtered_columns"):
                active: set[int] = set()
                for c, sel in (self._column_filters or {}).items():
                    if sel is not None:
                        active.add(int(c))
                hh.set_active_filtered_columns(active)
        except Exception:
            pass
        try:
            self.table.viewport().update()
        except Exception:
            pass

        # Persist filters so switching table won't reset.
        try:
            self._persist_filters_to_cached_state()
        except Exception:
            pass

    def _collect_values_for_column(self, col: int) -> list[str]:
        values: set[str] = set()
        for r in range(int(self.table.rowCount())):
            if not self._row_passes_filters(int(r), except_col=int(col)):
                continue
            values.add(self._get_cell_text(int(r), int(col)))
        return sorted(list(values), key=lambda s: _norm_text(s))

    def _on_filter_icon_clicked(self, col: int) -> None:
        if int(col) == int(self.COL_CHECK) or int(col) == int(self.COL_ID):
            return
        try:
            if bool(self.table.isColumnHidden(int(col))):
                return
        except Exception:
            pass

        try:
            if self._filter_popup is not None:
                self._filter_popup.close()
        except Exception:
            pass

        header = self.table.horizontalHeader()
        try:
            # Anchor the popup next to the dropdown icon (not the whole column).
            x = int(header.sectionViewportPosition(int(col)))
            w = int(header.sectionSize(int(col)))
            sec_rect = QRect(x, 0, w, int(header.height()))
            icon_rect = None
            try:
                icon_rect = header._dropdown_rect_for_section(sec_rect)  # type: ignore[attr-defined]
            except Exception:
                icon_rect = None

            if icon_rect is None:
                size = 14
                pad = 6
                icon_rect = QRect(
                    int(sec_rect.right() - pad - size),
                    int(sec_rect.center().y() - (size // 2)),
                    int(size),
                    int(size),
                )
            pos = header.viewport().mapToGlobal(icon_rect.bottomLeft() + QPoint(0, 2))
        except Exception:
            pos = self.mapToGlobal(self.rect().bottomLeft())

        title = ""
        values = self._collect_values_for_column(int(col))
        selected = (self._column_filters or {}).get(int(col))

        def _apply(sel: set[str] | None) -> None:
            if sel is None:
                self._column_filters[int(col)] = None
                self._column_filters_norm[int(col)] = None
            else:
                raw_set = set(sel)
                self._column_filters[int(col)] = raw_set
                self._column_filters_norm[int(col)] = set(
                    _norm_text(x) for x in raw_set
                )
            self._apply_column_filters()
            try:
                self._persist_filters_to_cached_state()
            except Exception:
                pass

        def _clear() -> None:
            self._column_filters[int(col)] = None
            self._column_filters_norm[int(col)] = None
            self._apply_column_filters()
            try:
                self._persist_filters_to_cached_state()
            except Exception:
                pass

        def _sort_asc() -> None:
            try:
                self.table.sortItems(int(col), Qt.SortOrder.AscendingOrder)
            except Exception:
                pass
            self._apply_column_filters()

        def _sort_desc() -> None:
            try:
                self.table.sortItems(int(col), Qt.SortOrder.DescendingOrder)
            except Exception:
                pass
            self._apply_column_filters()

        self._filter_popup = _TableWidgetColumnFilterPopup(
            self,
            title=title,
            values=values,
            selected=selected,
            on_apply=_apply,
            on_clear=_clear,
            on_sort_asc=_sort_asc,
            on_sort_desc=_sort_desc,
        )
        try:
            screen = (
                self.window().windowHandle().screen()
                if self.window() and self.window().windowHandle()
                else None
            )
            if screen:
                sg = screen.availableGeometry()
                p = QPoint(int(pos.x()), int(pos.y()))
                x = p.x()
                y = p.y()
                if x + self._filter_popup.width() > sg.right():
                    x = max(
                        int(sg.left()), int(sg.right() - self._filter_popup.width())
                    )
                if y + self._filter_popup.height() > sg.bottom():
                    y = max(
                        int(sg.top()), int(sg.bottom() - self._filter_popup.height())
                    )
                self._filter_popup.move(QPoint(x, y))
            else:
                self._filter_popup.move(pos)
        except Exception:
            try:
                self._filter_popup.move(pos)
            except Exception:
                pass
        self._filter_popup.show()

    def get_selected_assignment_id(self) -> int | None:
        try:
            row = int(self.table.currentRow())
        except Exception:
            return None
        if row < 0:
            return None
        it = self.table.item(row, self.COL_ID)
        if it is None:
            return None
        raw = str(it.text() or "").strip()
        if not raw:
            return None
        try:
            v = int(raw)
        except Exception:
            return None
        return v if v > 0 else None

    def get_checked_assignment_ids(self) -> list[int]:
        ids: list[int] = []
        for r in range(self.table.rowCount()):
            chk = self.table.item(r, self.COL_CHECK)
            if chk is None or chk.text() != "✅":
                continue
            it_id = self.table.item(r, self.COL_ID)
            if it_id is None:
                continue
            raw = str(it_id.text() or "").strip()
            if not raw:
                continue
            try:
                v = int(raw)
            except Exception:
                continue
            if v > 0:
                ids.append(v)
        return ids

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if col != self.COL_CHECK:
            return
        it = self.table.item(row, col)
        if it is None:
            return
        it.setText("✅" if it.text() != "✅" else "❌")

        try:
            self._sync_header_check_from_rows()
        except Exception:
            pass

    def _set_header_check_text(self, txt: str) -> None:
        if txt not in {"✅", "❌"}:
            txt = "❌"
        try:
            hi = self.table.horizontalHeaderItem(int(self.COL_CHECK))
            if hi is None:
                hi = QTableWidgetItem("")
                self.table.setHorizontalHeaderItem(int(self.COL_CHECK), hi)
            hi.setText(txt)
            hi.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            try:
                f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                hi.setFont(f)
            except Exception:
                pass
        except Exception:
            pass

    def _sync_header_check_from_rows(self) -> None:
        any_rows = int(self.table.rowCount()) > 0
        all_checked = True if any_rows else False
        for r in range(int(self.table.rowCount())):
            it = self.table.item(int(r), int(self.COL_CHECK))
            checked = it is not None and str(it.text() or "").strip() == "✅"
            all_checked = all_checked and checked
        self._set_header_check_text("✅" if (any_rows and all_checked) else "❌")

    def _on_header_clicked(self, section: int) -> None:
        if int(section) != int(self.COL_CHECK):
            return
        try:
            cur = "❌"
            hi = self.table.horizontalHeaderItem(int(self.COL_CHECK))
            if hi is not None:
                cur = str(hi.text() or "❌").strip()
            new_txt = "✅" if cur != "✅" else "❌"
        except Exception:
            new_txt = "✅"

        try:
            self.table.blockSignals(True)
        except Exception:
            pass
        try:
            for r in range(int(self.table.rowCount())):
                it = self.table.item(int(r), int(self.COL_CHECK))
                if it is None:
                    it = QTableWidgetItem("❌")
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    try:
                        f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                        it.setFont(f)
                    except Exception:
                        pass
                    it.setFlags(
                        Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
                    )
                    self.table.setItem(int(r), int(self.COL_CHECK), it)
                it.setText(new_txt)
            self._set_header_check_text(new_txt)
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass

    def set_schedules(self, items: list[tuple[int, str]]) -> None:
        try:
            prev = self.cbo_schedule.currentData()
        except Exception:
            prev = None

        self.cbo_schedule.clear()
        self.cbo_schedule.addItem("-- Chọn lịch làm việc --", None)
        self.cbo_schedule.addItem("Chưa sắp xếp ca", 0)
        for sid, name in items or []:
            try:
                self.cbo_schedule.addItem(str(name or ""), int(sid))
            except Exception:
                continue

        target = self._desired_schedule_data
        if target is None:
            target = prev
        try:
            idx = -1
            for i in range(self.cbo_schedule.count()):
                if self.cbo_schedule.itemData(i) == target:
                    idx = i
                    break
            if idx >= 0:
                self.cbo_schedule.setCurrentIndex(int(idx))
        except Exception:
            pass

    def set_desired_schedule_data(self, data: object) -> None:
        self._desired_schedule_data = data


class MainContent(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")
        self.setMinimumHeight(254)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left panel occupies full height
        self.left = MainLeft(self)

        # Right side stacks panels vertically
        right_container = QWidget(self)
        right_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_container.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        right_root = QVBoxLayout(right_container)
        right_root.setContentsMargins(0, 0, 0, 0)
        right_root.setSpacing(0)

        self.right = MainRight(right_container)
        self.temp = TempScheduleContent(right_container)

        # Separator between 2 panels bên phải (MainRight và Lịch trình tạm)
        sep_panels = QFrame(right_container)
        sep_panels.setFrameShape(QFrame.Shape.HLine)
        sep_panels.setFixedHeight(1)
        sep_panels.setStyleSheet(f"background-color: {COLOR_BORDER};")

        right_root.addWidget(self.right, 2)
        right_root.addWidget(sep_panels)
        right_root.addWidget(self.temp, 1)

        root.addWidget(self.left)
        root.addWidget(right_container, 1)
