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

from PySide6.QtCore import QDate, QEvent, QLocale, QSize, Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon
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
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    ICON_DELETE,
    ICON_REFRESH,
    ICON_TOTAL,
    INPUT_COLOR_BG,
    MAIN_CONTENT_BG_COLOR,
    TITLE_2_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
    resource_path,
)

from core.ui_settings import get_schedule_work_table_ui, ui_settings_bus


_BTN_HOVER_BG = COLOR_BUTTON_PRIMARY_HOVER


# In-memory state cache to avoid losing Schedule Work filters/tables when the main
# window recreates the view while switching tabs.
_SCHEDULE_WORK_STATE: dict[str, object] = {}


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
        try:
            QTimer.singleShot(0, self._restore_state_if_any)
        except Exception:
            pass

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
                it.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if check_col is not None and int(c) == int(check_col):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    try:
                        f = QFont(UI_FONT, int(CONTENT_FONT) + 0)
                        it.setFont(f)
                    except Exception:
                        pass
                table.setItem(int(r), int(c), it)

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
                "table": self._capture_table(self.content.temp.table),
            },
        }
        _SCHEDULE_WORK_STATE["view"] = state

    def _restore_state_if_any(self) -> None:
        state = _SCHEDULE_WORK_STATE.get("view")
        if not isinstance(state, dict) or not state:
            return

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
                # Restore header checkbox text
                header_txt = str((state.get("right") or {}).get("header_check") or "")
                if header_txt in {"✅", "❌"}:
                    self.content.right._set_header_check_text(header_txt)
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
                header_txt = str((state.get("temp") or {}).get("header_check") or "")
                if header_txt in {"✅", "❌"}:
                    self.content.temp._set_header_check_text(header_txt)
            except Exception:
                pass
        finally:
            _block_all(False)


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
                f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 6px; }}",
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
                f"QLineEdit {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 6px; }}",
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
                    f"QCalendarWidget QSpinBox {{ color: {COLOR_TEXT_PRIMARY}; background: {INPUT_COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0 6px; }}",
                    f"QCalendarWidget QComboBox {{ color: {COLOR_TEXT_PRIMARY}; background: {INPUT_COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; padding: 0 6px; }}",
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
                f"QDateEdit {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; padding: 0 8px; border-radius: 6px; }}",
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
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
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
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; padding: 0 12px; border-radius: 6px; }}",
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

        # Auto-search (debounced) instead of a dedicated Search button.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)

        self.btn_refresh = _mk_btn_outline("Làm mới", ICON_REFRESH, height=32)
        self.btn_delete = _mk_btn_outline("Xóa lịch NV", ICON_DELETE, height=32)
        self.btn_settings = _mk_btn_outline("Cài đặt", None, height=32)

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

        self.tree = QTreeWidget(self)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        self.tree.setExpandsOnDoubleClick(False)
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
        self.cbo_schedule.clear()
        self.cbo_schedule.addItem("-- Chọn lịch làm việc --", None)
        self.cbo_schedule.addItem("Chưa sắp xếp ca", 0)
        for sid, name in items or []:
            try:
                self.cbo_schedule.addItem(str(name or ""), int(sid))
            except Exception:
                continue


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
