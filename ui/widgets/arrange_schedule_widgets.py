"""ui.widgets.arrange_schedule_widgets

UI cho màn "Khai báo lịch làm việc".

Yêu cầu (tóm tắt):
- TitleBar1
- MainLeft: danh sách lịch trình (2 cột: ID, Lịch trình). Cột ID ẩn. Width 400px.
- MainRight:
  - Header1: button "Sắp xếp ca cho lịch trình", "Làm mới", "Lưu", "Xóa", hiển thị Tổng
  - Header2:
    - Bên trái: input tên lịch trình, combobox cách chọn vào ra
    - Bên phải: các checkbox
      - Không xét vắng ngày thứ 7 khi có xếp ca
      - Không xét vắng ngày Chủ Nhật khi có xếp ca
      - Không xét vắng ngày Lễ khi có xếp ca
      - Ngày Lễ được tính 1 công (một ngày làm việc cho trường hợp không đi làm)
      - Ngày là ngày của giờ ra
  - Bảng bên dưới: cột ID (ẩn), Ngày, Tên ca 1, Tên ca 2, Tên ca 3
    - Cột Ngày gồm: Thứ 2..Chủ nhật, Ngày lễ

Ghi chú:
- File này chỉ dựng UI (widget + signal). Nghiệp vụ nằm ở controller/services.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QHeaderView

from core.ui_settings import get_arrange_schedule_table_ui, ui_settings_bus

from core.resource import (
    BG_TITLE_1_HEIGHT,
    BG_TITLE_2_HEIGHT,
    COLOR_BORDER,
    COLOR_BUTTON_ACTIVE,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ICON_ARRANGE_SCHEDULE,
    ICON_DELETE,
    ICON_REFRESH,
    ICON_SAVE,
    ICON_TOTAL,
    MAIN_CONTENT_BG_COLOR,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
    resource_path,
)


ARRANGE_SCHEDULE_IN_OUT_MODE_OPTIONS: list[tuple[str, str | None]] = [
    ("Chưa chọn", None),
    ("Sắp xếp giờ Vào/Ra theo tự động", "auto"),
    ("Theo giờ Vào/Ra trên máy chấm công", "device"),
    (
        "Giờ vào là Giờ đầu tiên và giờ Ra là Giờ cuối cùng trong ngày",
        "first_last",
    ),
]


_BTN_HOVER_BG = COLOR_BUTTON_PRIMARY_HOVER


# In-memory state cache to avoid losing Arrange Schedule UI state when the main
# window recreates widgets while switching tabs.
_ARRANGE_SCHEDULE_STATE: dict[str, object] = {}


def _capture_table_payload(table: QTableWidget) -> dict[str, object] | None:
    try:
        rows = int(table.rowCount())
        cols = int(table.columnCount())
    except Exception:
        return None
    if cols <= 0:
        return None

    headers: list[str] = []
    for c in range(cols):
        hi = table.horizontalHeaderItem(int(c))
        headers.append(str(hi.text() if hi is not None else ""))

    data: list[list[dict[str, object]]] = []
    for r in range(rows):
        row_cells: list[dict[str, object]] = []
        for c in range(cols):
            it = table.item(int(r), int(c))
            if it is None:
                row_cells.append({"text": "", "user": None})
                continue
            row_cells.append(
                {
                    "text": str(it.text() or ""),
                    "user": it.data(Qt.ItemDataRole.UserRole),
                }
            )
        data.append(row_cells)
    return {"headers": headers, "rows": data}


def _restore_table_payload(
    table: QTableWidget, payload: object, *, editable: bool = False
) -> None:
    if not isinstance(payload, dict):
        return
    headers = payload.get("headers")
    rows = payload.get("rows")
    if not isinstance(headers, list) or not isinstance(rows, list):
        return

    table.setRowCount(0)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(h or "") for h in headers])
    table.setRowCount(len(rows))

    for r, row_cells in enumerate(rows):
        if not isinstance(row_cells, list):
            continue
        for c in range(min(len(headers), len(row_cells))):
            cell = row_cells[c]
            if not isinstance(cell, dict):
                continue
            it = QTableWidgetItem(str(cell.get("text") or ""))
            if not editable:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            try:
                it.setData(Qt.ItemDataRole.UserRole, cell.get("user"))
            except Exception:
                pass
            table.setItem(int(r), int(c), it)


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


def _mk_font_normal() -> QFont:
    f = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_NORMAL >= 400:
        f.setWeight(QFont.Weight.Normal)
    return f


def _mk_font_semibold() -> QFont:
    f = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_SEMIBOLD >= 500:
        f.setWeight(QFont.Weight.DemiBold)
    return f


def _mk_label(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setFont(_mk_font_normal())
    lb.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
    return lb


def _mk_combo(parent: QWidget | None = None, height: int = 32) -> QComboBox:
    cb = QComboBox(parent)
    cb.setFixedHeight(height)
    cb.setFont(_mk_font_normal())
    cb.setStyleSheet(
        "\n".join(
            [
                f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 6px; }}",
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
                f"QLineEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 6px; }}",
                f"QLineEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
            ]
        )
    )
    return le


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


def _mk_btn_primary(text: str, height: int = 32) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
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


def _setup_table(
    table: QTableWidget,
    headers: list[str],
    *,
    stretch_last: bool,
    stretch_all: bool = False,
    horizontal_scroll: Qt.ScrollBarPolicy,
    column_widths: list[int] | None = None,
) -> None:
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)

    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setShowGrid(True)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(horizontal_scroll)

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(40)
    header.setSectionsMovable(False)
    header.setFont(_mk_font_semibold())
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    for col in range(len(headers)):
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)

    if stretch_all:
        for col in range(len(headers)):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    elif stretch_last and len(headers) > 0:
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)

    if column_widths:
        for idx, w in enumerate(column_widths[: len(headers)]):
            if int(w) > 0:
                table.setColumnWidth(int(idx), int(w))

    header.setSectionsClickable(False)
    table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

    table.setStyleSheet(
        "\n".join(
            [
                f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                f"QTableWidget::item {{ padding-left: 8px; padding-right: 8px; }}",
                f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                "QTableWidget::item:focus { outline: none; }",
                "QTableWidget:focus { outline: none; }",
            ]
        )
    )


class MainLeft(QWidget):
    schedule_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        title = _mk_label("Danh sách lịch trình")
        title.setFont(_mk_font_semibold())

        self.table = QTableWidget(self)
        _setup_table(
            self.table,
            ["ID", "Lịch trình"],
            stretch_last=False,
            stretch_all=True,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Hide ID column
        self.table.setColumnHidden(0, True)

        root.addWidget(title)
        root.addWidget(self.table, 1)

        self.table.itemSelectionChanged.connect(lambda: self.schedule_selected.emit())

        # Debounced autosave
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(120)
        self._save_timer.timeout.connect(self._save_cached_state)
        try:
            self.table.itemSelectionChanged.connect(lambda: self._save_timer.start())
        except Exception:
            pass

        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def apply_ui_settings(self) -> None:
        ui = get_arrange_schedule_table_ui()

        def _to_qt_align(s: str) -> Qt.AlignmentFlag:
            v = str(s or "").strip().lower()
            if v == "right":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            if v == "center":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        body_font = QFont(UI_FONT, int(ui.font_size))
        if str(ui.font_weight or "normal").strip().lower() == "bold":
            body_font.setWeight(QFont.Weight.Bold)
        else:
            body_font.setWeight(QFont.Weight.Normal)

        header_font = QFont(UI_FONT, int(ui.header_font_size))
        if str(ui.header_font_weight or "bold").strip().lower() == "bold":
            header_font.setWeight(QFont.Weight.Bold)
        else:
            header_font.setWeight(QFont.Weight.Normal)

        try:
            header = self.table.horizontalHeader()
            header.setFont(header_font)
            fw_num = 700 if header_font.weight() >= QFont.Weight.DemiBold else 400
            header.setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {fw_num}; }}"
            )
        except Exception:
            pass

        try:
            self.table.setFont(body_font)
        except Exception:
            pass

        try:
            key = "list_schedule_name"
            align_s = (ui.column_align or {}).get(key, "center")
            for r in range(int(self.table.rowCount())):
                it = self.table.item(int(r), 1)
                if it is None:
                    continue
                it.setTextAlignment(int(_to_qt_align(align_s)))
                f = QFont(body_font)
                if key in (ui.column_bold or {}):
                    f.setWeight(
                        QFont.Weight.Bold
                        if bool(ui.column_bold.get(key))
                        else QFont.Weight.Normal
                    )
                it.setFont(f)
        except Exception:
            pass

    def set_schedules(self, rows: list[tuple[int, str]]) -> None:
        # Add extra option: "Chưa sắp xếp" (id=0)
        all_rows: list[tuple[int, str]] = [(0, "Chưa sắp xếp"), *list(rows or [])]

        # Large list render can freeze UI; render in time slices when needed.
        try:
            self.table.blockSignals(True)
        except Exception:
            pass
        try:
            self.table.setUpdatesEnabled(False)
        except Exception:
            pass

        try:
            self.table.setRowCount(0)
            self.table.setRowCount(len(all_rows))
        except Exception:
            pass

        # Cancel any previous render timer.
        try:
            tmr = getattr(self, "_render_timer", None)
            if tmr is not None:
                try:
                    tmr.stop()
                except Exception:
                    pass
        except Exception:
            pass

        def _render_range(start: int, end: int) -> None:
            for r in range(int(start), int(end)):
                try:
                    schedule_id, name = all_rows[int(r)]
                except Exception:
                    continue
                it_id = QTableWidgetItem(str(schedule_id))
                it_id.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
                self.table.setItem(int(r), 0, it_id)

                it_name = QTableWidgetItem(str(name or ""))
                it_name.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
                self.table.setItem(int(r), 1, it_name)

        # Small list: render sync.
        if len(all_rows) <= 200:
            _render_range(0, len(all_rows))
            try:
                self.table.clearSelection()
                self.table.setCurrentCell(-1, -1)
            except Exception:
                pass
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
            self.apply_ui_settings()
            try:
                self._save_timer.start()
            except Exception:
                self._save_cached_state()
            return

        # Large list: render in slices (~10ms budget).
        self._render_state = {"i": 0, "n": len(all_rows)}

        timer = QTimer(self)
        timer.setInterval(0)
        self._render_timer = timer

        def _tick() -> None:
            st = getattr(self, "_render_state", None) or {}
            i = int(st.get("i", 0))
            n = int(st.get("n", 0))
            if i >= n:
                try:
                    timer.stop()
                except Exception:
                    pass
                try:
                    self.table.clearSelection()
                    self.table.setCurrentCell(-1, -1)
                except Exception:
                    pass
                try:
                    self.table.setUpdatesEnabled(True)
                except Exception:
                    pass
                try:
                    self.table.blockSignals(False)
                except Exception:
                    pass
                self.apply_ui_settings()
                try:
                    self._save_timer.start()
                except Exception:
                    self._save_cached_state()
                return

            t0 = time.perf_counter()
            # Render until budget.
            while i < n and (time.perf_counter() - t0) * 1000.0 < 10.0:
                end = min(n, i + 40)
                _render_range(i, end)
                i = end

            st["i"] = i
            self._render_state = st
            try:
                self.table.viewport().update()
            except Exception:
                pass
            try:
                timer.start(0)
            except Exception:
                QTimer.singleShot(0, _tick)

        try:
            timer.timeout.connect(_tick)
            timer.start()
        except Exception:
            # Fallback: sync
            _render_range(0, len(all_rows))
            try:
                self.table.setUpdatesEnabled(True)
            except Exception:
                pass
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
            self.apply_ui_settings()

    def get_selected_schedule_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)
        try:
            return int(str(it.text()).strip()) if it is not None else None
        except Exception:
            return None

    def get_selected_schedule_name(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 1)
        return str(it.text() if it is not None else "").strip() or None

    def select_schedule_id(self, schedule_id: int) -> None:
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            try:
                if it is not None and int(str(it.text()).strip()) == int(schedule_id):
                    self.table.setCurrentCell(r, 1)
                    return
            except Exception:
                continue

    def _save_cached_state(self) -> None:
        try:
            items: list[tuple[int, str]] = []
            for r in range(int(self.table.rowCount())):
                it_id = self.table.item(int(r), 0)
                it_name = self.table.item(int(r), 1)
                if it_id is None:
                    continue
                try:
                    sid = int(str(it_id.text() or "").strip() or 0)
                except Exception:
                    sid = 0
                # Do not store the synthetic "Chưa sắp xếp" row; set_schedules will add it.
                if sid == 0:
                    continue
                items.append((sid, str(it_name.text() if it_name is not None else "")))
            _ARRANGE_SCHEDULE_STATE["left_rows"] = items
            _ARRANGE_SCHEDULE_STATE["left_selected_id"] = (
                self.get_selected_schedule_id()
            )
        except Exception:
            pass

    def restore_cached_state_if_any(self) -> dict[str, object] | None:
        """Restore cached schedules and selection.

        Returns a small info dict when restored, else None.
        """
        rows = _ARRANGE_SCHEDULE_STATE.get("left_rows")
        sel = _ARRANGE_SCHEDULE_STATE.get("left_selected_id")
        if not isinstance(rows, list):
            return None

        try:
            self.table.blockSignals(True)
        except Exception:
            pass
        try:
            self.set_schedules(rows)
            try:
                if sel is not None:
                    self.select_schedule_id(int(sel))
            except Exception:
                pass
        finally:
            try:
                self.table.blockSignals(False)
            except Exception:
                pass
        try:
            return {
                "restored": True,
                "selected_id": self.get_selected_schedule_id(),
            }
        except Exception:
            return {"restored": True, "selected_id": None}

    def clear_selection(self) -> None:
        self.table.clearSelection()


class MainRight(QWidget):
    arrange_clicked = Signal()
    refresh_clicked = Signal()
    save_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Current schedule id currently being edited (set by controller).
        # This is persisted in the in-memory cache to avoid accidental "create new"
        # when the left list selection is not restored.
        self.current_schedule_id: int | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # Header1
        header1 = QWidget(self)
        h1 = QHBoxLayout(header1)
        h1.setContentsMargins(0, 0, 0, 0)
        h1.setSpacing(8)

        self.btn_arrange = _mk_btn_outline("Sắp xếp ca cho lịch trình")
        self.btn_refresh = _mk_btn_outline("Làm mới", ICON_REFRESH)
        self.btn_save = _mk_btn_outline("Lưu", ICON_SAVE)
        self.btn_delete = _mk_btn_outline("Xóa", ICON_DELETE)

        # Icons
        self.btn_arrange.setIcon(
            QIcon(resource_path("assets/images/arrange_schedule.svg"))
        )
        self.btn_arrange.setIconSize(QSize(18, 18))

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

        h1.addWidget(self.btn_arrange)
        h1.addWidget(self.btn_refresh)
        h1.addWidget(self.btn_save)
        h1.addWidget(self.btn_delete)
        h1.addWidget(self.total_icon)
        h1.addWidget(self.label_total)
        h1.addStretch(1)

        # Header2
        header2 = QWidget(self)
        h2 = QHBoxLayout(header2)
        h2.setContentsMargins(0, 0, 0, 0)
        h2.setSpacing(16)

        left_box = QWidget(header2)
        left = QVBoxLayout(left_box)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)

        self.inp_schedule_name = _mk_line_edit(self)
        self.inp_schedule_name.setPlaceholderText("Tên lịch trình")

        self.cbo_in_out_mode = _mk_combo(self)
        self.cbo_in_out_mode.setMinimumWidth(200)
        for label, value in ARRANGE_SCHEDULE_IN_OUT_MODE_OPTIONS:
            self.cbo_in_out_mode.addItem(label, value)

        # "Tên lịch trình" + "Chọn vào/ra" trên 1 cột (2 dòng)
        row_name = QHBoxLayout()
        row_name.setContentsMargins(0, 0, 0, 0)
        row_name.setSpacing(8)
        row_name.addWidget(_mk_label("Tên lịch trình"))
        row_name.addWidget(self.inp_schedule_name, 1)

        row_inout = QHBoxLayout()
        row_inout.setContentsMargins(0, 0, 0, 0)
        row_inout.setSpacing(8)
        row_inout.addWidget(_mk_label("Chọn vào/ra"))
        row_inout.addWidget(self.cbo_in_out_mode, 1)

        left.addLayout(row_name)
        left.addLayout(row_inout)

        right_box = QWidget(header2)
        right = QVBoxLayout(right_box)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)

        def _mk_cb(text: str) -> QCheckBox:
            cb = QCheckBox(text, right_box)
            cb.setFont(_mk_font_normal())
            cb.setStyleSheet(
                "\n".join(
                    [
                        f"QCheckBox {{ color: {COLOR_TEXT_PRIMARY}; spacing: 0px; padding-left: 0px; margin-left: 0px; }}",
                        "QCheckBox::indicator { width: 0px; height: 0px; image: none; }",
                        "QCheckBox::indicator:checked { image: none; }",
                        "QCheckBox::indicator:unchecked { image: none; }",
                    ]
                )
            )
            cb.setCursor(Qt.CursorShape.PointingHandCursor)

            base_text = str(text or "").strip()

            def _refresh_emoji() -> None:
                cb.setText(f"{'✅' if cb.isChecked() else '❌'} {base_text}")

            cb.toggled.connect(lambda _v: _refresh_emoji())
            _refresh_emoji()
            return cb

        self.chk_ignore_sat = _mk_cb("Không xét vắng ngày Thứ 7 khi có xếp ca")
        self.chk_ignore_sun = _mk_cb("Không xét vắng ngày Chủ Nhật khi có xếp ca")
        self.chk_ignore_holiday = _mk_cb("Không xét vắng ngày Lễ khi có xếp ca")
        self.chk_holiday_as_work = _mk_cb(
            "Ngày Lễ được tính 1 công (một ngày làm việc cho trường hợp không đi làm)"
        )
        self.chk_day_is_out = _mk_cb("Ngày là ngày của giờ ra")

        right.addWidget(self.chk_ignore_sat)
        right.addWidget(self.chk_ignore_sun)
        right.addWidget(self.chk_ignore_holiday)
        right.addWidget(self.chk_holiday_as_work)
        right.addWidget(self.chk_day_is_out)
        right.addStretch(1)

        h2.addWidget(left_box, 1)
        h2.addWidget(right_box, 1)

        # Table detail
        self.table = QTableWidget(self)
        # Bảng chỉ "được tạo" (setup headers/rows) khi Áp dụng hoặc khi load lịch trình.
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QTableWidget::item {{ padding-left: 8px; padding-right: 8px; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        root.addWidget(header1)
        root.addWidget(header2)
        root.addWidget(self.table, 1)

        # Signals
        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        # Click open dialog as requested
        self.btn_arrange.clicked.connect(self._open_arrange_dialog)

        # Debounced autosave
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(150)
        self._save_timer.timeout.connect(self._save_cached_state)
        for signal in (
            self.inp_schedule_name.textChanged,
            self.cbo_in_out_mode.currentIndexChanged,
            self.chk_ignore_sat.toggled,
            self.chk_ignore_sun.toggled,
            self.chk_ignore_holiday.toggled,
            self.chk_holiday_as_work.toggled,
            self.chk_day_is_out.toggled,
        ):
            try:
                signal.connect(lambda *_a: self._save_timer.start())
            except Exception:
                pass
        try:
            self.table.itemChanged.connect(lambda *_a: self._save_timer.start())
        except Exception:
            pass

        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def apply_ui_settings(self) -> None:
        ui = get_arrange_schedule_table_ui()

        def _to_qt_align(s: str) -> Qt.AlignmentFlag:
            v = str(s or "").strip().lower()
            if v == "right":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            if v == "center":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        body_font = QFont(UI_FONT, int(ui.font_size))
        if str(ui.font_weight or "normal").strip().lower() == "bold":
            body_font.setWeight(QFont.Weight.Bold)
        else:
            body_font.setWeight(QFont.Weight.Normal)

        header_font = QFont(UI_FONT, int(ui.header_font_size))
        if str(ui.header_font_weight or "bold").strip().lower() == "bold":
            header_font.setWeight(QFont.Weight.Bold)
        else:
            header_font.setWeight(QFont.Weight.Normal)

        try:
            header = self.table.horizontalHeader()
            header.setFont(header_font)
            fw_num = 700 if header_font.weight() >= QFont.Weight.DemiBold else 400
            header.setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {fw_num}; }}"
            )
        except Exception:
            pass

        try:
            for c in range(int(self.table.columnCount())):
                it_h = self.table.horizontalHeaderItem(int(c))
                if it_h is not None:
                    it_h.setFont(header_font)
        except Exception:
            pass

        try:
            self.table.setFont(body_font)
        except Exception:
            pass

        try:
            # Apply per-column settings only for detail table cells (col 1..).
            for r in range(int(self.table.rowCount())):
                for c in range(int(self.table.columnCount())):
                    it = self.table.item(int(r), int(c))
                    if it is None:
                        continue
                    if int(c) == 0:
                        it.setTextAlignment(
                            int(
                                Qt.AlignmentFlag.AlignVCenter
                                | Qt.AlignmentFlag.AlignCenter
                            )
                        )
                        it.setFont(body_font)
                        continue

                    if int(c) == 1:
                        key = "detail_day"
                    else:
                        key = f"detail_shift_{int(c - 1)}"

                    align_s = (ui.column_align or {}).get(key, "center")
                    it.setTextAlignment(int(_to_qt_align(align_s)))

                    f = QFont(body_font)
                    if key in (ui.column_bold or {}):
                        f.setWeight(
                            QFont.Weight.Bold
                            if bool(ui.column_bold.get(key))
                            else QFont.Weight.Normal
                        )
                    it.setFont(f)
        except Exception:
            pass

    def _open_arrange_dialog(self) -> None:
        self.arrange_clicked.emit()
        from ui.dialog.arrange_schedule_dialog import ArrangeScheduleDialog

        dlg = ArrangeScheduleDialog(self)
        dlg.exec()

        # Arrange dialog can change table values -> save state
        try:
            self._save_timer.start()
        except Exception:
            self._save_cached_state()

    def _on_refresh_clicked(self) -> None:
        try:
            _ARRANGE_SCHEDULE_STATE.clear()
        except Exception:
            pass
        self.refresh_clicked.emit()

    def build_table(self, shift_count: int) -> None:
        """Tạo (rebuild) bảng chi tiết theo số cột ca cần hiển thị.

        - Luôn có cột ID (ẩn)
        - Luôn có cột Ngày
        - Có n cột Tên ca 1..n (0..5)
        """

        try:
            n = int(shift_count)
        except Exception:
            n = 0
        if n < 0:
            n = 0

        headers = ["ID", "Ngày"] + [f"Tên ca {i}" for i in range(1, n + 1)]
        _setup_table(
            self.table,
            headers,
            stretch_last=False,
            stretch_all=False,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self.table.setColumnHidden(0, True)

        days = [
            "Thứ 2",
            "Thứ 3",
            "Thứ 4",
            "Thứ 5",
            "Thứ 6",
            "Thứ 7",
            "Chủ nhật",
            "Ngày lễ",
        ]

        self.table.setRowCount(len(days))
        for r, name in enumerate(days):
            it_id = QTableWidgetItem("")
            it_id.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.table.setItem(r, 0, it_id)

            it_day = QTableWidgetItem(name)
            it_day.setFlags(it_day.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it_day.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.table.setItem(r, 1, it_day)

            for c in range(2, self.table.columnCount()):
                it = QTableWidgetItem("")
                it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
                self.table.setItem(r, c, it)

        self._apply_day_row_colors()
        self.apply_ui_settings()

        try:
            self._save_timer.start()
        except Exception:
            self._save_cached_state()

    def _apply_day_row_colors(self) -> None:
        """Giữ màu chữ: Chủ nhật (đỏ), Ngày lễ (xanh) cho toàn bộ cột đang có."""
        for r in range(self.table.rowCount()):
            day_item = self.table.item(r, 1)
            day_name = str(day_item.text() if day_item else "").strip()

            row_color: str | None = None
            if day_name == "Chủ nhật":
                row_color = COLOR_ERROR
            elif day_name.casefold() == "ngày lễ".casefold():
                row_color = COLOR_BUTTON_ACTIVE

            if not row_color:
                continue

            brush = QBrush(QColor(row_color))
            for col in range(self.table.columnCount()):
                item = self.table.item(r, col)
                if item is not None:
                    item.setForeground(brush)

    def set_shift_column_count(self, count: int) -> None:
        # Backward compatible wrapper
        self.build_table(int(count))

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")

        try:
            _ARRANGE_SCHEDULE_STATE["right_total"] = str(self.label_total.text() or "")
        except Exception:
            pass

    def set_current_schedule_id(self, schedule_id: int | None) -> None:
        try:
            self.current_schedule_id = int(schedule_id) if schedule_id else None
        except Exception:
            self.current_schedule_id = None
        try:
            _ARRANGE_SCHEDULE_STATE["right_schedule_id"] = self.current_schedule_id
        except Exception:
            pass

        try:
            self._save_timer.start()
        except Exception:
            self._save_cached_state()

    def _save_cached_state(self) -> None:
        try:
            _ARRANGE_SCHEDULE_STATE["right_schedule_id"] = self.current_schedule_id
            _ARRANGE_SCHEDULE_STATE["right_schedule_name"] = str(
                self.inp_schedule_name.text() or ""
            )
            _ARRANGE_SCHEDULE_STATE["right_in_out_mode"] = (
                self.cbo_in_out_mode.currentData()
            )
            _ARRANGE_SCHEDULE_STATE["right_chk_ignore_sat"] = bool(
                self.chk_ignore_sat.isChecked()
            )
            _ARRANGE_SCHEDULE_STATE["right_chk_ignore_sun"] = bool(
                self.chk_ignore_sun.isChecked()
            )
            _ARRANGE_SCHEDULE_STATE["right_chk_ignore_holiday"] = bool(
                self.chk_ignore_holiday.isChecked()
            )
            _ARRANGE_SCHEDULE_STATE["right_chk_holiday_as_work"] = bool(
                self.chk_holiday_as_work.isChecked()
            )
            _ARRANGE_SCHEDULE_STATE["right_chk_day_is_out"] = bool(
                self.chk_day_is_out.isChecked()
            )
            _ARRANGE_SCHEDULE_STATE["right_total"] = str(self.label_total.text() or "")

            payload = _capture_table_payload(self.table)
            if payload is not None:
                _ARRANGE_SCHEDULE_STATE["right_table"] = payload
                try:
                    _ARRANGE_SCHEDULE_STATE["right_shift_count"] = max(
                        0, int(self.table.columnCount()) - 2
                    )
                except Exception:
                    pass
        except Exception:
            pass

    def restore_cached_state_if_any(self) -> bool:
        if not _ARRANGE_SCHEDULE_STATE:
            return False

        try:
            self.blockSignals(True)
            self.table.blockSignals(True)
        except Exception:
            pass
        try:
            try:
                sid = _ARRANGE_SCHEDULE_STATE.get("right_schedule_id")
                self.current_schedule_id = int(sid) if sid is not None else None
                if (
                    self.current_schedule_id is not None
                    and self.current_schedule_id <= 0
                ):
                    self.current_schedule_id = None
            except Exception:
                self.current_schedule_id = None

            try:
                self.inp_schedule_name.setText(
                    str(_ARRANGE_SCHEDULE_STATE.get("right_schedule_name") or "")
                )
            except Exception:
                pass

            # restore combobox by data
            try:
                target = _ARRANGE_SCHEDULE_STATE.get("right_in_out_mode")
                idx = -1
                for i in range(self.cbo_in_out_mode.count()):
                    if self.cbo_in_out_mode.itemData(i) == target:
                        idx = i
                        break
                if idx >= 0:
                    self.cbo_in_out_mode.setCurrentIndex(int(idx))
            except Exception:
                pass

            for key, cb in (
                ("right_chk_ignore_sat", self.chk_ignore_sat),
                ("right_chk_ignore_sun", self.chk_ignore_sun),
                ("right_chk_ignore_holiday", self.chk_ignore_holiday),
                ("right_chk_holiday_as_work", self.chk_holiday_as_work),
                ("right_chk_day_is_out", self.chk_day_is_out),
            ):
                try:
                    cb.setChecked(bool(_ARRANGE_SCHEDULE_STATE.get(key)))
                except Exception:
                    pass

            try:
                total_txt = str(_ARRANGE_SCHEDULE_STATE.get("right_total") or "")
                if total_txt:
                    self.label_total.setText(total_txt)
            except Exception:
                pass

            # restore detail table
            payload = _ARRANGE_SCHEDULE_STATE.get("right_table")
            shift_count = _ARRANGE_SCHEDULE_STATE.get("right_shift_count")
            try:
                if shift_count is not None:
                    self.build_table(int(shift_count))
            except Exception:
                pass
            try:
                if payload is not None:
                    _restore_table_payload(self.table, payload)
                    # keep ID column hidden
                    try:
                        self.table.setColumnHidden(0, True)
                    except Exception:
                        pass
                    self._apply_day_row_colors()
                    self.apply_ui_settings()
            except Exception:
                pass
        finally:
            try:
                self.table.blockSignals(False)
                self.blockSignals(False)
            except Exception:
                pass

        return True


class ArrangeScheduleView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title = TitleBar1("Khai báo lịch làm việc", ICON_ARRANGE_SCHEDULE, self)

        content = QWidget(self)
        row = QHBoxLayout(content)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.left = MainLeft(content)
        self.right = MainRight(content)

        row.addWidget(self.left)
        row.addWidget(self.right, 1)

        root.addWidget(self.title)
        root.addWidget(content, 1)
