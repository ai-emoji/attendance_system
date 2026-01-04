"""ui.widgets.shift_attendance_widgets

UI cho màn "Chấm công theo lịch/ca" (Shift Attendance).

Yêu cầu (tóm tắt):
- Sao chép TitleBar1
- Tạo MainContent1:
  - Header: combobox phòng ban, combobox tìm kiếm (Mã NV/Tên NV/Họ và tên), input tìm kiếm,
    button Làm mới, hiển thị Tổng
    - Bảng cột: Mã NV, Tên nhân viên, Mã chấm công, Lịch làm việc, Chức vụ, Phòng Ban, Ngày vào làm
  - Footer: chọn Từ ngày/Đến ngày + button Xem công
- Tạo MainContent2:
  - Header: button Xuất lưới, button Chi tiết, combobox chọn cột hiển thị
  - Bảng cột: Mã nv, Tên nhân viên, Ngày, Thứ, Vào 1, Ra 1, Vào 2, Ra 2, Vào 3, Ra 3,
    Trễ, Sớm, Giờ, Công, KH, Giờ +, Công +, KH +, TC1, TC2, TC3, Tổng

Ghi chú:
- File này chỉ dựng UI (widget + signal). Xử lý nghiệp vụ nằm ở controller/services.
"""

from __future__ import annotations

import datetime as _dt
import time as _time

from PySide6.QtCore import (
    QDate,
    QLocale,
    QSize,
    Qt,
    Signal,
    QTimer,
    QItemSelectionModel,
    QEvent,
)
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QHeaderView

from core.resource import (
    COLOR_BUTTON_SAVE,
    COLOR_BUTTON_SAVE_HOVER,
    ICON_CHECK,
    ICON_CLOCK,
    BG_TITLE_1_HEIGHT,
    BG_TITLE_2_HEIGHT,
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_TEXT_LIGHT,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ICON_DROPDOWN,
    ICON_EXCEL,
    ICON_REFRESH,
    ICON_TOTAL,
    MAIN_CONTENT_BG_COLOR,
    CONTAINER_SHIFT_ATTENDANCE,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
    resource_path,
)

from core.ui_settings import (
    get_shift_attendance_state,
    get_shift_attendance_table_ui,
    ui_settings_bus,
    update_shift_attendance_state,
    update_shift_attendance_table_ui,
)
from core.db_connection_bus import db_connection_bus


_BTN_HOVER_BG = COLOR_BUTTON_PRIMARY_HOVER


def _fmt_date_ddmmyyyy(value: object | None) -> str:
    """Format a date-like value to dd/MM/yyyy for UI display."""

    if value is None:
        return ""

    try:
        if isinstance(value, QDate):
            return str(value.toString("dd/MM/yyyy") or "")
    except Exception:
        pass

    try:
        if isinstance(value, (_dt.datetime, _dt.date)):
            return str(value.strftime("%d/%m/%Y"))
    except Exception:
        pass

    s = str(value or "").strip()
    if not s:
        return ""

    # Already dd/MM/yyyy
    try:
        if (
            len(s) >= 10
            and s[2] == "/"
            and s[5] == "/"
            and s[:10].replace("/", "").isdigit()
        ):
            return s[:10]
    except Exception:
        pass

    # Normalize: keep only date token, accept yyyy-mm-dd or dd-mm-yyyy
    token = s.split(" ", 1)[0].strip().replace("/", "-")
    try:
        if len(token) == 10 and token[4] == "-" and token[7] == "-":
            yy, mm, dd = token.split("-")
            d = _dt.date(int(yy), int(mm), int(dd))
            return d.strftime("%d/%m/%Y")
    except Exception:
        pass

    try:
        if len(token) == 10 and token[2] == "-" and token[5] == "-":
            dd, mm, yy = token.split("-")
            d = _dt.date(int(yy), int(mm), int(dd))
            return d.strftime("%d/%m/%Y")
    except Exception:
        pass

    return s


def _apply_check_item_style(item, *, checked: bool) -> None:
    """Style ✅/❌ cells to be readable (white text)."""
    try:
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    except Exception:
        pass

    try:
        if bool(checked):
            item.setForeground(QColor(COLOR_TEXT_LIGHT))
            item.setBackground(QColor(COLOR_BUTTON_PRIMARY))
        else:
            item.setForeground(QColor(COLOR_TEXT_LIGHT))
            item.setBackground(QColor(COLOR_BUTTON_SAVE))
    except Exception:
        pass


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
    font_normal = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_NORMAL >= 400:
        font_normal.setWeight(QFont.Weight.Normal)
    return font_normal


def _mk_font_semibold() -> QFont:
    font_semibold = QFont(UI_FONT, CONTENT_FONT)
    if FONT_WEIGHT_SEMIBOLD >= 500:
        font_semibold.setWeight(QFont.Weight.DemiBold)
    return font_semibold


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
                f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 0px; }}",
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
                f"QLineEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 0px; }}",
                f"QLineEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
            ]
        )
    )
    return le


def _mk_date(parent: QWidget | None = None, height: int = 32) -> QDateEdit:
    de = QDateEdit(parent)
    de.setDisplayFormat("dd/MM/yyyy")
    de.setCalendarPopup(True)
    de.setFixedHeight(height)

    dropdown_icon_url = resource_path(ICON_DROPDOWN).replace("\\", "/")

    # Đủ chỗ cho dd/MM/yyyy + dropdown
    try:
        de.setMinimumContentsLength(10)
    except Exception:
        pass

    try:
        fm = de.fontMetrics()
        sample = "88/88/8888"
        text_w = int(fm.horizontalAdvance(sample))
        target_w = text_w + (8 * 2) + 34
        de.setFixedWidth(max(180, target_w))
    except Exception:
        de.setFixedWidth(190)

    # Text giữa
    try:
        le = de.lineEdit()
        if le is not None:
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
    except Exception:
        pass

    # Locale Việt
    vi_locale = QLocale(QLocale.Language.Vietnamese, QLocale.Country.Vietnam)
    de.setLocale(vi_locale)
    try:
        cw = de.calendarWidget()
        if cw is not None:
            cw.setLocale(vi_locale)
            cw.setNavigationBarVisible(True)
            cw.setVerticalHeaderFormat(
                QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
            )
            cw.setHorizontalHeaderFormat(
                QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
            )
            cw.setStyleSheet(
                "\n".join(
                    [
                        f"QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {BG_TITLE_2_HEIGHT}; }}",
                        f"QCalendarWidget QToolButton#qt_calendar_monthbutton, QCalendarWidget QToolButton#qt_calendar_yearbutton {{ color: {COLOR_TEXT_PRIMARY}; font-weight: 600; }}",
                        f"QCalendarWidget QToolButton#qt_calendar_prevmonth, QCalendarWidget QToolButton#qt_calendar_nextmonth {{ color: {COLOR_TEXT_PRIMARY}; }}",
                        f"QCalendarWidget QSpinBox {{ color: {COLOR_TEXT_PRIMARY}; }}",
                        "QCalendarWidget QToolButton { background: transparent; border: none; padding: 2px 6px; }",
                    ]
                )
            )
    except Exception:
        pass

    de.setStyleSheet(
        "\n".join(
            [
                f"QDateEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; padding-right: 30px; border-radius: 0px; }}",
                f"QDateEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                f"QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border-left: 1px solid {COLOR_BORDER}; background: #FFFFFF; }}",
                f'QDateEdit::down-arrow {{ image: url("{dropdown_icon_url}"); width: 10px; height: 10px; }}',
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


def _mk_btn_primary(text: str, height: int = 32) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFixedHeight(height)
    btn.setStyleSheet(
        "\n".join(
            [
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; padding: 0 12px; border-radius: 0px; }}",
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
    horizontal_scroll: Qt.ScrollBarPolicy,
    column_widths: list[int] | None = None,
) -> None:
    # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
    try:
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setLineWidth(0)
    except Exception:
        pass

    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)

    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setShowGrid(True)
    try:
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    except Exception:
        pass
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(horizontal_scroll)

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(40)
    header.setSectionsMovable(False)

    header.setFont(_mk_font_semibold())

    # Default resize: Interactive (cho phép kéo); tuỳ chọn stretch cột cuối
    for col in range(len(headers)):
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
    if stretch_last and len(headers) > 0:
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)

    # Initial widths (để tạo/không tạo overflow ngang theo ý)
    if column_widths:
        for idx, w in enumerate(column_widths[: len(headers)]):
            if int(w) > 0:
                table.setColumnWidth(int(idx), int(w))

    header.setSectionsClickable(False)
    table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

    table.setStyleSheet(
        "\n".join(
            [
                f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                "QTableWidget::pane { border: 0px; }",
                f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                f"QHeaderView::section:first {{ border-left: 1px solid {GRID_LINES_COLOR}; }}",
                f"QTableCornerButton::section {{ background-color: {BG_TITLE_2_HEIGHT}; border: 1px solid {GRID_LINES_COLOR}; }}",
                f"QTableWidget::item {{ padding-left: 8px; padding-right: 8px; }}",
                f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; }}",
                "QTableWidget::item:focus { outline: none; }",
                "QTableWidget:focus { outline: none; }",
            ]
        )
    )


def _wrap_table_in_frame(
    parent: QWidget, table: QTableWidget, object_name: str
) -> QFrame:
    frame = QFrame(parent)
    try:
        frame.setObjectName(object_name)
    except Exception:
        pass
    try:
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setFrameShadow(QFrame.Shadow.Plain)
        frame.setLineWidth(1)
    except Exception:
        pass
    frame.setStyleSheet(
        f"QFrame#{object_name} {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
    )
    root = QVBoxLayout(frame)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(table)
    return frame


class MainContent1(QWidget):
    refresh_clicked = Signal()
    view_clicked = Signal()
    search_changed = Signal()
    department_changed = Signal()
    title_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(CONTAINER_SHIFT_ATTENDANCE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Header
        header = QWidget(self)
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self.cbo_department = _mk_combo(self)
        self.cbo_department.setMinimumWidth(220)
        self.cbo_department.addItem("Tất cả phòng ban", None)

        self.cbo_title = _mk_combo(self)
        self.cbo_title.setMinimumWidth(220)
        self.cbo_title.addItem("Tất cả chức vụ", None)

        self.cbo_search_by = _mk_combo(self)
        self.cbo_search_by.setMinimumWidth(160)
        self.cbo_search_by.addItem("Tự động", "auto")
        self.cbo_search_by.addItem("Mã nhân viên", "employee_code")
        self.cbo_search_by.addItem("Tên nhân viên", "full_name")
        self.cbo_search_by.addItem("Mã chấm công", "mcc_code")
        self.cbo_search_by.setCurrentIndex(0)

        self.inp_search_text = _mk_line_edit(self)
        self.inp_search_text.setPlaceholderText("Tìm kiếm...")

        # Add search icon inside the line edit (leading position)
        try:
            search_icon = QIcon.fromTheme("edit-find")
            if not search_icon.isNull():
                action = self.inp_search_text.addAction(
                    search_icon, QLineEdit.ActionPosition.LeadingPosition
                )
                action.setEnabled(False)  # purely decorative
        except Exception:
            pass

        self.btn_refresh = _mk_btn_outline("Làm mới", ICON_REFRESH)

        # Filter: employment status (default: Đi làm)
        self.cbo_employment_status = _mk_combo(self)
        self.cbo_employment_status.setMinimumWidth(160)
        self.cbo_employment_status.addItem("Đi làm", "1")
        self.cbo_employment_status.addItem("Nghỉ thai sản", "2")
        self.cbo_employment_status.addItem("Đã nghỉ việc", "3")
        self.cbo_employment_status.setCurrentIndex(0)

        self.btn_import = _mk_btn_outline("Import dữ liệu chấm công")

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

        h.addWidget(self.cbo_department)
        h.addWidget(self.cbo_title)
        h.addWidget(self.cbo_search_by)
        h.addWidget(self.inp_search_text, 1)
        h.addWidget(self.btn_refresh)
        h.addWidget(self.cbo_employment_status)
        h.addWidget(self.btn_import)
        h.addStretch(1)
        h.addWidget(self.total_icon)
        h.addWidget(self.label_total)

        # Table
        self.table = QTableWidget(self)
        _setup_table(
            self.table,
            [
                "",
                "STT",
                "Mã NV",
                "Tên nhân viên",
                "Mã chấm công",
                "Lịch làm việc",
                "Chức vụ",
                "Phòng Ban",
                "Ngày vào làm",
            ],
            stretch_last=True,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        try:
            self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass

        self.table_frame = _wrap_table_in_frame(
            self, self.table, "shift_attendance_table1_frame"
        )

        # Keep checkbox + STT compact; stretch the rest.
        _h = self.table.horizontalHeader()
        _h.setStretchLastSection(True)
        try:
            _h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            _h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(0, 42)
            self.table.setColumnWidth(1, 60)
            for _col in range(2, self.table.columnCount()):
                _h.setSectionResizeMode(_col, QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass

        # Footer
        footer = QWidget(self)
        f = QHBoxLayout(footer)
        f.setContentsMargins(0, 0, 0, 0)
        f.setSpacing(8)

        self.label_from = _mk_label("Từ ngày")
        self.date_from = _mk_date(self)
        self.label_to = _mk_label("Đến ngày")
        self.date_to = _mk_date(self)

        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)

        self.btn_view = _mk_btn_primary("Xem công")

        f.addWidget(self.label_from)
        f.addWidget(self.date_from)
        f.addSpacing(6)
        f.addWidget(self.label_to)
        f.addWidget(self.date_to)
        f.addWidget(self.btn_view)
        f.addStretch(1)

        layout.addWidget(header)
        layout.addWidget(self.table_frame, 1)
        layout.addWidget(footer)

        # Persist only filter state (no table cache) to avoid stale UI data.
        self._persist_timer: QTimer | None = None

        self.btn_refresh.clicked.connect(self._on_refresh_clicked)
        self.btn_import.clicked.connect(self._open_import_dialog)
        self.btn_view.clicked.connect(self.view_clicked.emit)

        self.cbo_department.currentIndexChanged.connect(self._on_department_changed)
        self.cbo_title.currentIndexChanged.connect(self._on_title_changed)
        self.cbo_search_by.currentIndexChanged.connect(self._on_search_changed)
        self.inp_search_text.textChanged.connect(self._on_search_changed)
        self.cbo_employment_status.currentIndexChanged.connect(self._on_search_changed)
        self.date_from.dateChanged.connect(self._on_date_changed)
        self.date_to.dateChanged.connect(self._on_date_changed)

        # Emoji checkbox toggle on click
        self.table.cellClicked.connect(self._on_cell_clicked)

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

        # Restore previous state after the controller has finished initial binding.
        try:
            QTimer.singleShot(0, self._restore_state_if_any)
        except Exception:
            pass

    def _on_refresh_clicked(self) -> None:
        # User explicitly requests refresh: reset ALL filters to defaults.
        # Block signals to avoid triggering multiple refreshes while resetting.
        def _block(on: bool) -> None:
            try:
                self.cbo_department.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_title.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_search_by.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.inp_search_text.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_employment_status.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.date_from.blockSignals(bool(on))
                self.date_to.blockSignals(bool(on))
            except Exception:
                pass

        today = QDate.currentDate()

        _block(True)
        try:
            # Comboboxes: back to "All" / default.
            try:
                self.cbo_department.setCurrentIndex(0)
            except Exception:
                pass
            try:
                self.cbo_title.setCurrentIndex(0)
            except Exception:
                pass
            try:
                self.cbo_search_by.setCurrentIndex(0)  # auto
            except Exception:
                pass
            try:
                self.cbo_employment_status.setCurrentIndex(0)  # "Đi làm"
            except Exception:
                pass

            # Search text
            try:
                self.inp_search_text.setText("")
            except Exception:
                pass

            # Date range: reset to today.
            try:
                self.date_from.setDate(today)
                self.date_to.setDate(today)
            except Exception:
                pass

            # Clear desired IDs so dropdown reload won't re-select old values.
            try:
                self._desired_department_id = None  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                self._desired_title_id = None  # type: ignore[attr-defined]
            except Exception:
                pass
        finally:
            _block(False)

        # Persist defaults so navigation won't restore old filters.
        try:
            update_shift_attendance_state(
                content1={
                    "department_id": None,
                    "title_id": None,
                    "search_by_data": "auto",
                    "search_text": "",
                    "employment_status": "1",
                    "date_from": today.toString("yyyy-MM-dd"),
                    "date_to": today.toString("yyyy-MM-dd"),
                }
            )
        except Exception:
            pass

        self.refresh_clicked.emit()

    def _on_department_changed(self, *_args) -> None:
        self.department_changed.emit()
        self._schedule_persist_state()

    def _on_title_changed(self, *_args) -> None:
        self.title_changed.emit()
        self._schedule_persist_state()

    def _on_search_changed(self, *_args) -> None:
        self.search_changed.emit()
        self._schedule_persist_state()

    def _on_date_changed(self, *_args) -> None:
        self._schedule_persist_state()

    def _schedule_persist_state(self) -> None:
        try:
            if self._persist_timer is None:
                self._persist_timer = QTimer(self)
                self._persist_timer.setSingleShot(True)
                self._persist_timer.timeout.connect(self._persist_state)
            # Debounce to avoid writing to disk on every key stroke.
            self._persist_timer.start(250)
        except Exception:
            pass

    def restore_cached_state_if_any(self) -> bool:
        """Public wrapper so controller can restore state before resetting fields."""
        try:
            return bool(self._restore_state_if_any())
        except Exception:
            return False

    def hideEvent(self, event) -> None:
        try:
            self._persist_state()
        except Exception:
            pass

        try:
            super().hideEvent(event)
        except Exception:
            return

    def _persist_state(self) -> None:
        try:
            df = self.date_from.date().toString("yyyy-MM-dd")
        except Exception:
            df = ""
        try:
            dt = self.date_to.date().toString("yyyy-MM-dd")
        except Exception:
            dt = ""
        try:
            update_shift_attendance_state(
                content1={
                    "department_id": self.cbo_department.currentData(),
                    "title_id": self.cbo_title.currentData(),
                    "search_by_data": self.cbo_search_by.currentData(),
                    "search_text": str(self.inp_search_text.text() or ""),
                    "employment_status": self.cbo_employment_status.currentData(),
                    "date_from": str(df or ""),
                    "date_to": str(dt or ""),
                }
            )
        except Exception:
            pass

    def _restore_state_if_any(self) -> bool:
        st = get_shift_attendance_state()
        state = st.get("content1") if isinstance(st, dict) else None
        if not isinstance(state, dict) or not state:
            return False

        restored_any = False

        # Keep desired IDs so controller dropdown reload can restore selection.
        try:
            self._desired_department_id = state.get("department_id")  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            self._desired_title_id = state.get("title_id")  # type: ignore[attr-defined]
        except Exception:
            pass

        def _block(on: bool) -> None:
            try:
                self.cbo_department.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_title.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_search_by.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.inp_search_text.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.cbo_employment_status.blockSignals(bool(on))
            except Exception:
                pass
            try:
                self.date_from.blockSignals(bool(on))
                self.date_to.blockSignals(bool(on))
            except Exception:
                pass

        _block(True)
        try:
            # Prefer restoring by itemData (stable across reloads), fallback to index.
            dep_id = state.get("department_id")
            if dep_id not in (None, "", 0, "0"):
                target = dep_id
                try:
                    target = int(target)
                except Exception:
                    target = dep_id
                for i in range(self.cbo_department.count()):
                    if self.cbo_department.itemData(i) == target:
                        self.cbo_department.setCurrentIndex(int(i))
                        restored_any = True
                        break
            else:
                dep_idx = int(state.get("department_index") or 0)
                if 0 <= dep_idx < self.cbo_department.count():
                    self.cbo_department.setCurrentIndex(dep_idx)
                    if int(dep_idx) != 0:
                        restored_any = True
        except Exception:
            pass
        try:
            title_id = state.get("title_id")
            if title_id not in (None, "", 0, "0"):
                target = title_id
                try:
                    target = int(target)
                except Exception:
                    target = title_id
                for i in range(self.cbo_title.count()):
                    if self.cbo_title.itemData(i) == target:
                        self.cbo_title.setCurrentIndex(int(i))
                        restored_any = True
                        break
            else:
                title_idx = int(state.get("title_index") or 0)
                if 0 <= title_idx < self.cbo_title.count():
                    self.cbo_title.setCurrentIndex(title_idx)
                    if int(title_idx) != 0:
                        restored_any = True
        except Exception:
            pass
        try:
            # Match by itemData when possible.
            target = state.get("search_by_data")
            idx = -1
            for i in range(self.cbo_search_by.count()):
                if self.cbo_search_by.itemData(i) == target:
                    idx = i
                    break
            if idx >= 0:
                self.cbo_search_by.setCurrentIndex(int(idx))
                restored_any = True
        except Exception:
            pass
        try:
            self.inp_search_text.setText(str(state.get("search_text") or ""))
            if str(state.get("search_text") or "") != "":
                restored_any = True
        except Exception:
            pass

        try:
            target = str(state.get("employment_status") or "").strip()
            if target:
                for i in range(self.cbo_employment_status.count()):
                    if (
                        str(self.cbo_employment_status.itemData(i) or "").strip()
                        == target
                    ):
                        self.cbo_employment_status.setCurrentIndex(int(i))
                        restored_any = True
                        break
        except Exception:
            pass
        try:
            df_s = str(state.get("date_from") or "").strip()
            dt_s = str(state.get("date_to") or "").strip()
            if df_s:
                qd = QDate.fromString(df_s, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_from.setDate(qd)
                    restored_any = True
            if dt_s:
                qd2 = QDate.fromString(dt_s, "yyyy-MM-dd")
                if qd2.isValid():
                    self.date_to.setDate(qd2)
                    restored_any = True
        except Exception:
            pass
        finally:
            _block(False)

        return bool(restored_any)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if int(col) != 0:
            return
        try:
            item = self.table.item(int(row), 0)
            if item is None:
                return
            cur = str(item.text() or "").strip()
            new_checked = cur != "✅"
            restored_any = True
            item.setText("✅" if new_checked else "❌")
            _apply_check_item_style(item, checked=bool(new_checked))
        except Exception:
            pass
            restored_any = True

    def get_checked_employee_keys(self) -> tuple[list[int], list[str]]:
        """Returns (employee_ids, attendance_codes) for checked rows."""
        emp_ids: list[int] = []
        codes: list[str] = []
        try:
            for r in range(self.table.rowCount()):
                item = self.table.item(int(r), 0)
                if item is None:
                    continue
                if str(item.text() or "").strip() != "✅":
                    continue

                emp_id = item.data(Qt.ItemDataRole.UserRole)
                if emp_id is not None:
                    try:
                        emp_ids.append(int(emp_id))
                    except Exception:
                        pass

                code = item.data(Qt.ItemDataRole.UserRole + 1)
                if code is not None:
                    s = str(code or "").strip()
                    if s:
                        codes.append(s)
        except Exception:
            return ([], [])

        # De-dup while keeping order
        seen_i: set[int] = set()
        uniq_ids: list[int] = []
        for i in emp_ids:
            if i in seen_i:
                continue
            seen_i.add(i)
            uniq_ids.append(i)

        seen_s: set[str] = set()
        uniq_codes: list[str] = []
        for s in codes:
            if s in seen_s:
                continue
            seen_s.add(s)
            uniq_codes.append(s)

        return (uniq_ids, uniq_codes)

    def _open_import_dialog(self) -> None:
        from ui.controllers.import_shift_attendance_controllers import (
            ImportShiftAttendanceController,
        )

        imported = False
        try:
            imported = bool(ImportShiftAttendanceController(parent=self).open())
        except Exception:
            try:
                ImportShiftAttendanceController(parent=self).open()
            except Exception:
                pass
            imported = False

        # If import updated DB, force a real reload instead of restoring cached grid.
        if imported:
            try:
                self._on_refresh_clicked()
            except Exception:
                pass

    def apply_ui_settings(self) -> None:
        ui = get_shift_attendance_table_ui()

        # Shift Attendance screen: allow hiding the import button via UI settings.
        try:
            btn = getattr(self, "btn_import", None)
            if btn is not None:
                btn.setVisible(bool(getattr(ui, "show_import_button", True)))
        except Exception:
            pass

        column_count = int(self.table.columnCount())
        defined_count = int(len(self._COLUMNS))
        ncols = min(column_count, defined_count)

        # Table body font
        body_font = QFont(UI_FONT, int(ui.font_size))
        if ui.font_weight == "bold":
            body_font.setWeight(QFont.Weight.DemiBold)
        else:
            body_font.setWeight(QFont.Weight.Normal)
        self.table.setFont(body_font)

        # Header font
        header_font = QFont(UI_FONT, int(ui.header_font_size))
        header_font.setWeight(
            QFont.Weight.DemiBold
            if ui.header_font_weight == "bold"
            else QFont.Weight.Normal
        )
        try:
            self.table.horizontalHeader().setFont(header_font)
            w = 600 if ui.header_font_weight == "bold" else 400
            self.table.horizontalHeader().setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {int(w)}; }}"
            )
        except Exception:
            pass

        # Column visibility
        for idx in range(ncols):
            k, _label = self._COLUMNS[int(idx)]
            # Fixed columns: always keep visible.
            if str(k) in {"__check", "stt"}:
                visible = True
            else:
                visible = bool((ui.column_visible or {}).get(k, True))
            try:
                self.table.setColumnHidden(int(idx), not visible)
            except Exception:
                pass

        # Safety: never allow the table to have all columns hidden.
        try:
            any_visible = any(
                not bool(self.table.isColumnHidden(int(i))) for i in range(int(ncols))
            )
            if not any_visible and ncols > 0:
                self.table.setColumnHidden(0, False)
                if ncols > 1:
                    self.table.setColumnHidden(1, False)
        except Exception:
            pass

        # Alignment & per-column bold overrides (apply to existing items)
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

        for row in range(self.table.rowCount()):
            for col in range(ncols):
                key, _label = self._COLUMNS[int(col)]
                item = self.table.item(int(row), int(col))
                if item is None:
                    continue

                # Ensure date columns show dd/MM/yyyy
                if str(key) == "start_date":
                    try:
                        raw = item.data(Qt.ItemDataRole.UserRole)
                        if raw is None:
                            raw = item.text()
                        item.setText(_fmt_date_ddmmyyyy(raw))
                    except Exception:
                        pass

                if str(key) == "__check":
                    _apply_check_item_style(
                        item, checked=(str(item.text() or "").strip() == "✅")
                    )

                if key in align_map:
                    try:
                        item.setTextAlignment(align_map[key])
                    except Exception:
                        pass

                if key in (ui.column_bold or {}):
                    try:
                        f = item.font()
                        f.setWeight(
                            QFont.Weight.DemiBold
                            if bool(ui.column_bold.get(key))
                            else QFont.Weight.Normal
                        )
                        item.setFont(f)
                    except Exception:
                        pass
                else:
                    # Inherit table setting
                    try:
                        f = item.font()
                        f.setWeight(
                            QFont.Weight.DemiBold
                            if ui.font_weight == "bold"
                            else QFont.Weight.Normal
                        )
                        item.setFont(f)
                    except Exception:
                        pass

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainContent2(QWidget):
    export_grid_clicked = Signal()
    detail_clicked = Signal()
    columns_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(CONTAINER_SHIFT_ATTENDANCE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QWidget(self)
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        self.btn_export_grid = _mk_btn_outline("Xuất lưới", ICON_EXCEL)
        self.btn_detail = _mk_btn_outline("Xuất chi tiết", ICON_EXCEL)

        # Time format buttons (HH:MM / HH:MM:SS)
        self._show_seconds: bool = True

        def _mk_time_btn(text: str) -> QPushButton:
            b = QPushButton(text, self)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(32)
            b.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 0px; }}",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                        f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; }}",
                        f"QPushButton:checked:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                    ]
                )
            )
            try:
                b.setIcon(QIcon(resource_path(ICON_CLOCK)))
                b.setIconSize(QSize(16, 16))
            except Exception:
                pass
            return b

        self.btn_hhmm = _mk_time_btn("HH:MM")
        self.btn_hhmmss = _mk_time_btn("HH:MM:SS")
        self.btn_hhmmss.setChecked(True)

        def _set_time_mode(show_seconds: bool) -> None:
            self.btn_hhmm.blockSignals(True)
            self.btn_hhmmss.blockSignals(True)
            try:
                self.btn_hhmm.setChecked(not show_seconds)
                self.btn_hhmmss.setChecked(bool(show_seconds))
            finally:
                self.btn_hhmm.blockSignals(False)
                self.btn_hhmmss.blockSignals(False)
            self.set_time_show_seconds(bool(show_seconds))
            self._schedule_persist_state()

        self.btn_hhmm.clicked.connect(lambda: _set_time_mode(False))
        self.btn_hhmmss.clicked.connect(lambda: _set_time_mode(True))

        # Persist small UI state only (no table cache).
        self._persist_timer: QTimer | None = None

        self.label_columns = _mk_label("Hiển thị cột")

        # Nút chọn cột hiển thị (checkbox trong menu) - như cũ
        self.btn_columns = QToolButton(self)
        self.btn_columns.setText("Chọn cột")
        self.btn_columns.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_columns.setFixedHeight(32)
        self.btn_columns.setPopupMode(QToolButton.ToolButtonPopupMode.DelayedPopup)
        self.btn_columns.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btn_columns.setIcon(QIcon(resource_path(ICON_DROPDOWN)))
        self.btn_columns.setIconSize(QSize(14, 14))
        self.btn_columns.setStyleSheet(
            "\n".join(
                [
                    f"QToolButton {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 10px; border-radius: 0px; }}",
                    f"QToolButton:hover {{ background: {_BTN_HOVER_BG}; color: {COLOR_TEXT_LIGHT}; }}",
                ]
            )
        )

        h.addWidget(self.btn_export_grid)
        h.addWidget(self.btn_detail)
        h.addStretch(1)
        h.addWidget(self.label_columns)
        h.addWidget(self.btn_hhmm)
        h.addWidget(self.btn_hhmmss)
        h.addWidget(self.btn_columns)

        self.table = QTableWidget(self)
        _setup_table(
            self.table,
            [
                "",
                "STT",
                "Mã nv",
                "Tên nhân viên",
                "Ngày",
                "Thứ",
                "Vào 1",
                "Ra 1",
                "Vào 2",
                "Ra 2",
                "Vào 3",
                "Ra 3",
                "Trễ",
                "Sớm",
                "Giờ",
                "Công",
                "KH",
                "Giờ +",
                "Công +",
                "KH +",
                "TC1",
                "TC2",
                "TC3",
                "Tổng",
                "Lịch làm việc",
                "Ca",
            ],
            stretch_last=False,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
            column_widths=[
                57,  # 42 + 15
                75,  # 60 + 15
                125,  # 110 + 15
                215,  # 200 + 15
                125,  # 110 + 15
                85,  # 70 + 15
                95,  # 80 + 15
                95,  # 80 + 15
                95,  # 80 + 15
                95,  # 80 + 15
                95,  # 80 + 15
                95,  # 80 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                85,  # 70 + 15
                75,  # 60 + 15
                75,  # 60 + 15
                75,  # 60 + 15
                60,  # Min W=60
                130,  # 115 + 15
                95,  # 80 + 15
            ],
        )
        try:
            self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass

        # Center header text (align similar to table.md).
        try:
            self.table.horizontalHeader().setDefaultAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
        except Exception:
            pass

        # Freeze first 3 columns (checkbox, STT, Mã nv) like a Grid's FreezeTo(0, 3).
        self._frozen_cols: tuple[int, ...] = (0, 1, 2, 3)
        self._frozen_view: QTableView | None = None
        self._syncing_scroll = False
        self._setup_frozen_view()

        # Cột "Tổng" yêu cầu Min W=60
        try:
            total_col = self._col_index("total")
            if total_col >= 0:
                h2 = self.table.horizontalHeader()
                h2.setSectionResizeMode(int(total_col), QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(int(total_col), 60)
        except Exception:
            pass

        # Allow selecting multiple rows in MainContent2.
        try:
            self.table.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
        except Exception:
            pass

        # Emoji checkbox toggle on click
        self.table.cellClicked.connect(self._on_cell_clicked)

        self.table_frame = _wrap_table_in_frame(
            self, self.table, "shift_attendance_table2_frame"
        )

        layout.addWidget(header)
        layout.addWidget(self.table_frame, 1)

        self.btn_export_grid.clicked.connect(self.export_grid_clicked.emit)
        self.btn_detail.clicked.connect(self.detail_clicked.emit)
        # columns_changed được emit khi tick/untick checkbox

        # Open columns window (buttons)
        self.btn_columns.clicked.connect(self._open_columns_buttons_window)

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

        # Restore small UI state after binding (time format only).
        try:
            QTimer.singleShot(0, self._restore_view_state)
        except Exception:
            pass

    def _setup_frozen_view(self) -> None:
        # Use an overlay QTableView to freeze left columns for a QTableWidget.
        if not self._frozen_cols:
            return

        try:
            model = self.table.model()
        except Exception:
            model = None
        if model is None:
            return

        frozen = QTableView(self.table)
        frozen.setFrameShape(QFrame.Shape.NoFrame)
        frozen.setLineWidth(0)
        frozen.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        frozen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        frozen.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        frozen.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        frozen.setAlternatingRowColors(True)
        frozen.setWordWrap(False)
        frozen.setShowGrid(True)
        frozen.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        frozen.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        frozen.verticalHeader().setVisible(False)
        frozen.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        frozen.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        try:
            frozen.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            frozen.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        except Exception:
            pass

        frozen.setModel(model)

        # Keep base fonts consistent with the main table.
        try:
            frozen.setFont(self.table.font())
        except Exception:
            pass

        # Share selection model so selection looks identical.
        try:
            sm = self.table.selectionModel()
            if sm is not None:
                frozen.setSelectionModel(sm)
            else:
                self.table.setSelectionModel(QItemSelectionModel(model))
                frozen.setSelectionModel(self.table.selectionModel())
        except Exception:
            pass

        # Styling: reuse QTableWidget stylesheet, adapted for QTableView.
        try:
            qss = str(self.table.styleSheet() or "")
            qss = qss.replace("QTableWidget", "QTableView")
            frozen.setStyleSheet(qss)
        except Exception:
            pass

        # Header mirrors
        try:
            frozen.horizontalHeader().setFont(self.table.horizontalHeader().font())
            frozen.horizontalHeader().setFixedHeight(
                self.table.horizontalHeader().height()
            )
            frozen.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
            # Mirror header stylesheet (font-size/font-weight) when present.
            hs = str(self.table.horizontalHeader().styleSheet() or "").strip()
            if hs:
                frozen.horizontalHeader().setStyleSheet(hs)
        except Exception:
            pass

        # Make it purely visual: allow click/scroll events to pass through.
        try:
            frozen.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        except Exception:
            pass

        # Sync vertical scrolling.
        try:
            self.table.verticalScrollBar().valueChanged.connect(self._on_main_vscroll)
        except Exception:
            pass

        # Sync widths when user resizes columns in the main header.
        try:
            self.table.horizontalHeader().sectionResized.connect(
                lambda *_args: self._sync_frozen_view()
            )
        except Exception:
            pass

        # Keep geometry in sync.
        try:
            self.table.installEventFilter(self)
        except Exception:
            pass

        self._frozen_view = frozen
        self._sync_frozen_view()

    def _sync_frozen_fonts(self, *, body_font: QFont, header_font: QFont) -> None:
        fv = self._frozen_view
        if fv is None:
            return
        try:
            fv.setFont(QFont(body_font))
        except Exception:
            pass
        try:
            hh = fv.horizontalHeader()
            if hh is not None:
                hh.setFont(QFont(header_font))
                hs = str(self.table.horizontalHeader().styleSheet() or "").strip()
                if hs:
                    hh.setStyleSheet(hs)
                try:
                    hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_main_vscroll(self, value: int) -> None:
        if self._syncing_scroll:
            return
        fv = self._frozen_view
        if fv is None:
            return
        try:
            self._syncing_scroll = True
            fv.verticalScrollBar().setValue(int(value))
        finally:
            self._syncing_scroll = False

    def _sync_frozen_view(self) -> None:
        fv = self._frozen_view
        if fv is None:
            return

        w = 0
        any_visible = False
        col_count = int(self.table.columnCount())

        for c in range(col_count):
            is_frozen = int(c) in set(int(x) for x in self._frozen_cols)
            try:
                hidden = bool(self.table.isColumnHidden(int(c)))
            except Exception:
                hidden = False

            if is_frozen and not hidden:
                any_visible = True
                try:
                    fv.setColumnHidden(int(c), False)
                    cw = int(self.table.columnWidth(int(c)))
                    fv.setColumnWidth(int(c), cw)
                    w += cw
                except Exception:
                    pass
            else:
                try:
                    fv.setColumnHidden(int(c), True)
                    fv.setColumnWidth(int(c), 0)
                except Exception:
                    pass

        fv.setVisible(bool(any_visible and w > 0))
        if not fv.isVisible():
            return

        # Overlay on the left including header.
        try:
            fv.setGeometry(0, 0, int(w) + 2, int(self.table.height()))
            fv.raise_()
        except Exception:
            pass

    def eventFilter(self, obj, event) -> bool:
        # Keep frozen overlay geometry synced with table size.
        try:
            if obj is self.table and event is not None:
                if event.type() in {QEvent.Type.Resize, QEvent.Type.Show}:
                    self._sync_frozen_view()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def restore_cached_state_if_any(self) -> bool:
        """Không restore bảng từ cache; luôn để controller reload dữ liệu."""
        try:
            self._restore_view_state()
        except Exception:
            pass
        return False

    def hideEvent(self, event) -> None:
        try:
            self._persist_state()
        except Exception:
            pass

        try:
            super().hideEvent(event)
        except Exception:
            return

    def _schedule_persist_state(self) -> None:
        try:
            if self._persist_timer is None:
                self._persist_timer = QTimer(self)
                self._persist_timer.setSingleShot(True)
                self._persist_timer.timeout.connect(self._persist_state)
            self._persist_timer.start(200)
        except Exception:
            pass

    def _persist_state(self) -> None:
        try:
            update_shift_attendance_state(
                content2={"show_seconds": bool(getattr(self, "_show_seconds", True))}
            )
        except Exception:
            pass

    def _restore_view_state(self) -> None:
        st = get_shift_attendance_state()
        c2 = st.get("content2") if isinstance(st, dict) else None
        if not isinstance(c2, dict):
            c2 = {}

        show_seconds = bool(c2.get("show_seconds", True))

        try:
            self.set_time_show_seconds(show_seconds)
        except Exception:
            pass

        # Sync button check state without emitting.
        try:
            self.btn_hhmm.blockSignals(True)
            self.btn_hhmmss.blockSignals(True)
            self.btn_hhmm.setChecked(not show_seconds)
            self.btn_hhmmss.setChecked(bool(show_seconds))
        finally:
            try:
                self.btn_hhmm.blockSignals(False)
                self.btn_hhmmss.blockSignals(False)
            except Exception:
                pass

    def _format_time_value(self, value: object | None) -> str:
        s = "" if value is None else str(value)
        s = s.strip()
        if not s:
            return ""

        # Non-time labels (e.g. 'Nghỉ Lễ', 'OFF', 'V') should be displayed as-is.
        # Only attempt datetime/time normalization when the value looks like it contains a time.
        looks_like_time = ":" in s

        # If datetime-like, keep last token (HH:MM:SS)
        if looks_like_time and " " in s:
            s = s.split()[-1].strip()

        # Defensive: remove trailing colon
        while s.endswith(":"):
            s = s[:-1]

        parts = [p.strip() for p in s.split(":") if p.strip() != ""]
        if len(parts) < 2:
            return s

        def _to_int(p: str) -> int:
            try:
                return int(p)
            except Exception:
                # handle '00.000000'
                try:
                    return int(float(p))
                except Exception:
                    return 0

        hh = _to_int(parts[0])
        mm = _to_int(parts[1])
        ss = _to_int(parts[2][:2]) if len(parts) >= 3 else 0

        if self._show_seconds:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        return f"{hh:02d}:{mm:02d}"

    def set_time_show_seconds(self, show_seconds: bool) -> None:
        self._show_seconds = bool(show_seconds)

        # Reformat existing table items for time columns.
        time_keys = {"in_1", "out_1", "in_2", "out_2", "in_3", "out_3"}
        col_map: dict[str, int] = {}
        for k in time_keys:
            idx = self._col_index(k)
            if idx >= 0:
                col_map[k] = idx

        if not col_map:
            return

        for row in range(self.table.rowCount()):
            for _k, col in col_map.items():
                item = self.table.item(int(row), int(col))
                if item is None:
                    continue
                raw = item.data(Qt.ItemDataRole.UserRole)
                if raw is None:
                    raw = item.text()
                item.setText(self._format_time_value(raw))

    def _open_columns_buttons_window(self) -> None:
        # Exclude fixed columns (checkbox + STT) from column chooser.
        cols = [c for c in self._COLUMNS if c[0] not in {"__check", "stt"}]
        dlg = _ColumnsButtonsDialog(columns=cols, parent=self)
        dlg.exec()

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if int(col) != 0:
            return
        try:
            item = self.table.item(int(row), 0)
            if item is None:
                return
            cur = str(item.text() or "").strip()
            new_checked = cur != "✅"
            item.setText("✅" if new_checked else "❌")
            _apply_check_item_style(item, checked=bool(new_checked))
        except Exception:
            pass

    def _open_columns_dialog(self) -> None:
        # Kept for compatibility (other entry points may still open the full settings dialog)
        from ui.dialog.shift_attendance_settings_dialog import (
            ShiftAttendanceSettingsDialog,
        )

        dlg = ShiftAttendanceSettingsDialog(self)
        dlg.exec()

    def _col_index(self, key: str) -> int:
        k = str(key or "").strip()
        for i, (col_key, _label) in enumerate(self._COLUMNS):
            if col_key == k:
                return int(i)
        return -1

    def apply_ui_settings(self) -> None:
        ui = get_shift_attendance_table_ui()

        # Shift Attendance screen: allow hiding the import button via UI settings.
        # (This class may not have the button; keep this best-effort.)
        try:
            btn = getattr(self, "btn_import", None)
            if btn is not None:
                btn.setVisible(bool(getattr(ui, "show_import_button", True)))
        except Exception:
            pass

        column_count = int(self.table.columnCount())
        defined_count = int(len(self._COLUMNS))
        ncols = min(column_count, defined_count)

        # Table body font
        body_font = QFont(UI_FONT, int(ui.font_size))
        if ui.font_weight == "bold":
            body_font.setWeight(QFont.Weight.DemiBold)
        else:
            body_font.setWeight(QFont.Weight.Normal)
        self.table.setFont(body_font)

        # Header font
        header_font = QFont(UI_FONT, int(ui.header_font_size))
        header_font.setWeight(
            QFont.Weight.DemiBold
            if ui.header_font_weight == "bold"
            else QFont.Weight.Normal
        )
        try:
            self.table.horizontalHeader().setFont(header_font)
            w = 600 if ui.header_font_weight == "bold" else 400
            self.table.horizontalHeader().setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {int(w)}; }}"
            )
        except Exception:
            pass

        # Keep frozen overlay fonts in sync with UI settings.
        self._sync_frozen_fonts(body_font=body_font, header_font=header_font)

        # Column visibility
        for idx in range(ncols):
            k, _label = self._COLUMNS[int(idx)]
            # Fixed columns: always keep visible.
            if str(k) in {"__check", "stt"}:
                visible = True
            else:
                visible = bool((ui.column_visible or {}).get(k, True))
            try:
                self.table.setColumnHidden(int(idx), not visible)
            except Exception:
                pass

        # Safety: never allow the table to have all columns hidden.
        try:
            any_visible = any(
                not bool(self.table.isColumnHidden(int(i))) for i in range(int(ncols))
            )
            if not any_visible and ncols > 0:
                self.table.setColumnHidden(0, False)
                if ncols > 1:
                    self.table.setColumnHidden(1, False)
        except Exception:
            pass

        # Alignment & per-column bold overrides (apply to existing items)
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

        for row in range(self.table.rowCount()):
            for col in range(ncols):
                key, _label = self._COLUMNS[int(col)]
                item = self.table.item(int(row), int(col))
                if item is None:
                    continue

                # Ensure date column shows dd/MM/yyyy
                if str(key) == "date":
                    try:
                        raw = item.data(Qt.ItemDataRole.UserRole)
                        if raw is None:
                            raw = item.text()
                        item.setText(_fmt_date_ddmmyyyy(raw))
                    except Exception:
                        pass

                if str(key) == "__check":
                    _apply_check_item_style(
                        item, checked=(str(item.text() or "").strip() == "✅")
                    )

                if key in align_map:
                    try:
                        item.setTextAlignment(align_map[key])
                    except Exception:
                        pass

                if key in (ui.column_bold or {}):
                    try:
                        f = item.font()
                        f.setWeight(
                            QFont.Weight.DemiBold
                            if bool(ui.column_bold.get(key))
                            else QFont.Weight.Normal
                        )
                        item.setFont(f)
                    except Exception:
                        pass
                else:
                    # Inherit table setting
                    try:
                        f = item.font()
                        f.setWeight(
                            QFont.Weight.DemiBold
                            if ui.font_weight == "bold"
                            else QFont.Weight.Normal
                        )
                        item.setFont(f)
                    except Exception:
                        pass

        self.columns_changed.emit()

        # Keep frozen overlay in sync with current visibility/width.
        self._sync_frozen_view()


# Keep in sync with ShiftAttendanceSettingsDialog
MainContent2._COLUMNS = [
    ("__check", ""),
    ("stt", "STT"),
    ("employee_code", "Mã nv"),
    ("full_name", "Tên nhân viên"),
    ("date", "Ngày"),
    ("weekday", "Thứ"),
    ("in_1", "Vào 1"),
    ("out_1", "Ra 1"),
    ("in_2", "Vào 2"),
    ("out_2", "Ra 2"),
    ("in_3", "Vào 3"),
    ("out_3", "Ra 3"),
    ("late", "Trễ"),
    ("early", "Sớm"),
    ("hours", "Giờ"),
    ("work", "Công"),
    ("kh", "KH"),
    ("hours_plus", "Giờ +"),
    ("work_plus", "Công +"),
    ("leave_plus", "KH +"),
    ("tc1", "TC1"),
    ("tc2", "TC2"),
    ("tc3", "TC3"),
    ("total", "Tổng"),
    ("schedule", "Lịch làm việc"),
    ("shift_code", "Ca"),
]


# Keep in sync with ShiftAttendanceSettingsDialog
MainContent1._COLUMNS = [
    ("__check", ""),
    ("stt", "STT"),
    ("employee_code", "Mã NV"),
    ("full_name", "Tên nhân viên"),
    ("mcc_code", "Mã chấm công"),
    ("schedule", "Lịch làm việc"),
    ("title_name", "Chức vụ"),
    ("department_name", "Phòng Ban"),
    ("start_date", "Ngày vào làm"),
]


class _ColumnsButtonsDialog(QDialog):
    def __init__(
        self,
        *,
        columns: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chọn cột hiển thị")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setMinimumHeight(700)

        self._columns = list(columns or [])
        self._buttons: dict[str, QPushButton] = {}

        self.setStyleSheet(
            "\n".join(
                [
                    f"QDialog {{ background: {MAIN_CONTENT_BG_COLOR}; }}",
                    f"QLabel {{ color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QPushButton#col_btn {{ border: 1px solid {COLOR_BORDER}; border-radius: 0px; color: {COLOR_TEXT_LIGHT}; text-align: left; padding-left: 10px; }}",
                    f"QPushButton#col_btn[col_active='true'] {{ background: {COLOR_BUTTON_PRIMARY}; }}",
                    f"QPushButton#col_btn[col_active='true']:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    f"QPushButton#col_btn[col_active='false'] {{ background: {COLOR_BUTTON_SAVE}; }}",
                    f"QPushButton#col_btn[col_active='false']:hover {{ background: {COLOR_BUTTON_SAVE_HOVER}; }}",
                ]
            )
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Chọn các cột cần hiển thị", self)
        title.setFont(_mk_font_semibold())
        root.addWidget(title)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "\n".join(
                [
                    f"QScrollArea {{ border: 1px solid {COLOR_BORDER}; background: {MAIN_CONTENT_BG_COLOR}; border-radius: 0px; }}",
                    f"QScrollArea QWidget#qt_scrollarea_viewport {{ background: {MAIN_CONTENT_BG_COLOR}; }}",
                ]
            )
        )

        content = QWidget(scroll)
        grid = QGridLayout(content)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        ui = get_shift_attendance_table_ui()

        # Fixed size for every column button
        btn_w = 200
        btn_h = 40
        cols_per_row = 2

        row = 0
        col = 0
        for key, label in self._columns:
            btn = QPushButton(str(label), content)
            btn.setObjectName("col_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(btn_w, btn_h)
            btn.setFont(_mk_font_normal())
            btn.setCheckable(False)

            btn.setProperty("col_label", str(label))

            visible = bool((ui.column_visible or {}).get(str(key), True))
            btn.setProperty("col_active", bool(visible))
            btn.setText(f"{'✅' if bool(visible) else '❌'} {str(label)}")

            def _on_clicked(*_a, _key: str = str(key), _btn: QPushButton = btn) -> None:
                new_visible = not bool(_btn.property("col_active"))
                _btn.setProperty("col_active", bool(new_visible))
                base_label = str(_btn.property("col_label") or "").strip()
                _btn.setText(
                    f"{'✅' if bool(new_visible) else '❌'} {base_label if base_label else str(_key)}"
                )
                try:
                    _btn.style().unpolish(_btn)
                    _btn.style().polish(_btn)
                except Exception:
                    pass

                try:
                    update_shift_attendance_table_ui(
                        column_key=_key,
                        column_visible=bool(new_visible),
                    )
                except Exception:
                    pass

            btn.clicked.connect(_on_clicked)

            self._buttons[str(key)] = btn
            grid.addWidget(btn, row, col)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

        grid.setRowStretch(row + 1, 1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.btn_close = _mk_btn_outline("Đóng")
        self.btn_close.clicked.connect(self.reject)
        root.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignRight)


class _ColumnsSelectorDialog(QDialog):
    def __init__(
        self,
        *,
        headers: list[str],
        checked: list[bool],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chọn cột hiển thị")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._items: list[_ColumnsSelectorItem] = []

        self.setStyleSheet(
            "\n".join(
                [
                    f"QDialog {{ background: {MAIN_CONTENT_BG_COLOR}; }}",
                    f"QLabel {{ color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QToolButton#col_item {{ background: #FFFFFF; border: 1px solid {COLOR_BORDER}; border-radius: 0px; margin: 2px; padding: 6px 10px; color: {COLOR_TEXT_PRIMARY}; text-align: left; }}",
                    f"QToolButton#col_item:hover {{ background: {HOVER_ROW_BG_COLOR}; }}",
                    f"QToolButton#col_item:checked {{ background: {HOVER_ROW_BG_COLOR}; }}",
                ]
            )
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Chọn các cột cần hiển thị")
        title.setFont(_mk_font_semibold())
        root.addWidget(title)

        # List area (scroll)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "\n".join(
                [
                    f"QScrollArea {{ border: 1px solid {COLOR_BORDER}; background: {MAIN_CONTENT_BG_COLOR}; }}",
                    "QScrollArea { border-radius: 0px; }",
                    f"QScrollArea QWidget#qt_scrollarea_viewport {{ background: {MAIN_CONTENT_BG_COLOR}; }}",
                ]
            )
        )

        content = QWidget(scroll)
        grid = QGridLayout(content)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        # Hiển thị dạng lưới 2 cột để dễ chọn
        columns = 2
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        row = 0
        col = 0
        for idx, header in enumerate(headers or []):
            item = _ColumnsSelectorItem(
                text=str(header),
                checked=(bool(checked[idx]) if idx < len(checked) else True),
                parent=content,
            )
            item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._items.append(item)
            grid.addWidget(item, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1

        # Đẩy các widget lên trên
        grid.setRowStretch(row + 1, 1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        self.btn_apply = _mk_btn_primary("Áp dụng")
        self.btn_close = _mk_btn_outline("Đóng")

        self.btn_apply.clicked.connect(self.accept)
        self.btn_close.clicked.connect(self.reject)

        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_apply)
        root.addLayout(btn_row)

    def get_checked(self) -> list[bool]:
        return [bool(it.isChecked()) for it in self._items]


class _ColumnsSelectorItem(QToolButton):
    def __init__(
        self,
        *,
        text: str,
        checked: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("col_item")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setText(str(text))
        self.setIcon(QIcon(resource_path(ICON_CHECK)))
        self.setIconSize(QSize(14, 14))
        self._sync_icon_visible()
        self.toggled.connect(lambda _on: self._sync_icon_visible())

    def _sync_icon_visible(self) -> None:
        # Nếu không check thì ẩn icon (để bố cục gọn, giống checkbox)
        self.setIcon(QIcon(resource_path(ICON_CHECK)) if self.isChecked() else QIcon())
