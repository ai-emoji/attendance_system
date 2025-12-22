"""ui.widgets.shift_attendance_widgets

UI cho màn "Chấm công theo lịch/ca" (Shift Attendance).

Yêu cầu (tóm tắt):
- Sao chép TitleBar1
- Tạo MainContent1:
  - Header: combobox phòng ban, combobox tìm kiếm (Mã NV/Tên NV/Họ và tên), input tìm kiếm,
    button Làm mới, hiển thị Tổng
  - Bảng cột: Mã NV, Tên nhân viên, Mã chấm công, Lịch trình, Chức vụ, Phòng Ban, Ngày vào làm
  - Footer: chọn Từ ngày/Đến ngày + button Xem công
- Tạo MainContent2:
  - Header: button Xuất lưới, button Chi tiết, combobox chọn cột hiển thị
  - Bảng cột: Mã nv, Tên nhân viên, Ngày, Thứ, Vào 1, Ra 1, Vào 2, Ra 2, Vào 3, Ra 3,
    Trễ, Sớm, Giờ, Công, KH, Giờ +, Công +, KH +, TC1, TC2, TC3, Tổng

Ghi chú:
- File này chỉ dựng UI (widget + signal). Xử lý nghiệp vụ nằm ở controller/services.
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QLocale, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QHeaderView

from core.resource import (
    ICON_CHECK,
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
    get_shift_attendance_table_ui,
    ui_settings_bus,
    update_shift_attendance_table_ui,
)
from ui.dialog.shift_attendance_settings_dialog import ShiftAttendanceSettingsDialog


_BTN_HOVER_BG = COLOR_BUTTON_PRIMARY_HOVER


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
                f"QDateEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; padding-right: 30px; border-radius: 6px; }}",
                f"QDateEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                f"QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border-left: 1px solid {COLOR_BORDER}; background: #FFFFFF; }}",
                f'QDateEdit::down-arrow {{ image: url("{dropdown_icon_url}"); width: 10px; height: 10px; }}',
            ]
        )
    )
    return de


def _mk_btn_outline(text: str, icon_path: str | None = None, height: int = 32) -> QPushButton:
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
                f"QPushButton:hover {{ background: {_BTN_HOVER_BG}; color: {COLOR_TEXT_PRIMARY}; }}",
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


class MainContent1(QWidget):
    refresh_clicked = Signal()
    view_clicked = Signal()
    search_changed = Signal()
    department_changed = Signal()

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

        self.cbo_search_by = _mk_combo(self)
        self.cbo_search_by.setMinimumWidth(160)
        self.cbo_search_by.addItem("Mã nhân viên", "employee_code")
        self.cbo_search_by.addItem("Tên nhân viên", "full_name")
        self.cbo_search_by.addItem("Mã chấm công", "mcc_code")
        self.cbo_search_by.setCurrentIndex(0)

        self.inp_search_text = _mk_line_edit(self)
        self.inp_search_text.setPlaceholderText("Tìm kiếm...")

        self.btn_refresh = _mk_btn_outline("Làm mới", ICON_REFRESH)

        self.total_icon = QLabel("")
        self.total_icon.setFixedSize(18, 18)
        self.total_icon.setPixmap(QIcon(resource_path(ICON_TOTAL)).pixmap(QSize(18, 18)))

        self.label_total = QLabel("Tổng: 0")
        self.label_total.setFont(_mk_font_normal())
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        h.addWidget(self.cbo_department)
        h.addWidget(self.cbo_search_by)
        h.addWidget(self.inp_search_text, 1)
        h.addWidget(self.btn_refresh)
        h.addStretch(1)
        h.addWidget(self.total_icon)
        h.addWidget(self.label_total)

        # Table
        self.table = QTableWidget(self)
        _setup_table(
            self.table,
            [
                "Mã NV",
                "Tên nhân viên",
                "Mã chấm công",
                "Lịch trình",
                "Chức vụ",
                "Phòng Ban",
                "Ngày vào làm",
            ],
            stretch_last=True,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )

        # Chia đều kích thước các cột theo chiều rộng bảng
        _h = self.table.horizontalHeader()
        _h.setStretchLastSection(True)
        for _col in range(self.table.columnCount()):
            _h.setSectionResizeMode(_col, QHeaderView.ResizeMode.Stretch)

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
        layout.addWidget(self.table, 1)
        layout.addWidget(footer)

        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        self.btn_view.clicked.connect(self.view_clicked.emit)
        self.cbo_department.currentIndexChanged.connect(
            lambda *_: self.department_changed.emit()
        )
        self.cbo_search_by.currentIndexChanged.connect(lambda *_: self.search_changed.emit())
        self.inp_search_text.textChanged.connect(lambda *_: self.search_changed.emit())

        # Apply UI settings and live-update when changed.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

    def apply_ui_settings(self) -> None:
        ui = get_shift_attendance_table_ui()

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
        header_font = QFont(UI_FONT, int(ui.font_size))
        if ui.font_weight == "bold":
            header_font.setWeight(QFont.Weight.DemiBold)
        else:
            header_font.setWeight(QFont.Weight.Normal)
        try:
            self.table.horizontalHeader().setFont(header_font)
        except Exception:
            pass

        # Column visibility
        for idx in range(ncols):
            k, _label = self._COLUMNS[int(idx)]
            visible = bool((ui.column_visible or {}).get(k, True))
            try:
                self.table.setColumnHidden(int(idx), not visible)
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
                align_map[ks] = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            elif vs == "center":
                align_map[ks] = Qt.AlignmentFlag.AlignCenter
            elif vs == "right":
                align_map[ks] = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        for row in range(self.table.rowCount()):
            for col in range(ncols):
                key, _label = self._COLUMNS[int(col)]
                item = self.table.item(int(row), int(col))
                if item is None:
                    continue

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

        self.label_columns = _mk_label("Hiển thị cột")

        # Nút chọn cột hiển thị (checkbox trong menu) - như cũ
        self.btn_columns = QToolButton(self)
        self.btn_columns.setText("Chọn cột")
        self.btn_columns.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_columns.setFixedHeight(32)
        self.btn_columns.setPopupMode(QToolButton.ToolButtonPopupMode.DelayedPopup)
        self.btn_columns.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.btn_columns.setIcon(QIcon(resource_path(ICON_DROPDOWN)))
        self.btn_columns.setIconSize(QSize(14, 14))
        self.btn_columns.setStyleSheet(
            "\n".join(
                [
                    f"QToolButton {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 10px; border-radius: 6px; }}",
                    f"QToolButton:hover {{ background: {_BTN_HOVER_BG}; color: {COLOR_TEXT_PRIMARY}; }}",
                ]
            )
        )

        h.addWidget(self.btn_export_grid)
        h.addWidget(self.btn_detail)
        h.addStretch(1)
        h.addWidget(self.label_columns)
        h.addWidget(self.btn_columns)

        self.table = QTableWidget(self)
        _setup_table(
            self.table,
            [
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
            ],
            stretch_last=False,
            horizontal_scroll=Qt.ScrollBarPolicy.ScrollBarAsNeeded,
            column_widths=[
                110,
                200,
                110,
                70,
                80,
                80,
                80,
                80,
                80,
                80,
                70,
                70,
                70,
                70,
                70,
                70,
                70,
                70,
                60,
                60,
                60,
                70,
            ],
        )

        layout.addWidget(header)
        layout.addWidget(self.table, 1)

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

    def _open_columns_buttons_window(self) -> None:
        dlg = _ColumnsButtonsDialog(columns=self._COLUMNS, parent=self)
        dlg.exec()

    def _open_columns_dialog(self) -> None:
        # Kept for compatibility (other entry points may still open the full settings dialog)
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
        header_font = QFont(UI_FONT, int(ui.font_size))
        if ui.font_weight == "bold":
            header_font.setWeight(QFont.Weight.DemiBold)
        else:
            header_font.setWeight(QFont.Weight.Normal)
        try:
            self.table.horizontalHeader().setFont(header_font)
        except Exception:
            pass

        # Column visibility
        for idx in range(ncols):
            k, _label = self._COLUMNS[int(idx)]
            visible = bool((ui.column_visible or {}).get(k, True))
            try:
                self.table.setColumnHidden(int(idx), not visible)
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
                align_map[ks] = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            elif vs == "center":
                align_map[ks] = Qt.AlignmentFlag.AlignCenter
            elif vs == "right":
                align_map[ks] = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

        for row in range(self.table.rowCount()):
            for col in range(ncols):
                key, _label = self._COLUMNS[int(col)]
                item = self.table.item(int(row), int(col))
                if item is None:
                    continue

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


# Keep in sync with ShiftAttendanceSettingsDialog
MainContent2._COLUMNS = [
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
    ("leave", "KH"),
    ("hours_plus", "Giờ +"),
    ("work_plus", "Công +"),
    ("leave_plus", "KH +"),
    ("tc1", "TC1"),
    ("tc2", "TC2"),
    ("tc3", "TC3"),
    ("total", "Tổng"),
]


# Keep in sync with ShiftAttendanceSettingsDialog
MainContent1._COLUMNS = [
    ("employee_code", "Mã NV"),
    ("full_name", "Tên nhân viên"),
    ("mcc_code", "Mã chấm công"),
    ("schedule", "Lịch trình"),
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
                    f"QPushButton#col_btn {{ background: #FFFFFF; border: 1px solid {COLOR_BORDER}; border-radius: 6px; color: {COLOR_TEXT_PRIMARY}; }}",
                    f"QPushButton#col_btn:hover {{ background: {HOVER_ROW_BG_COLOR}; }}",
                    f"QPushButton#col_btn[col_active='true'] {{ background: {HOVER_ROW_BG_COLOR}; border: 1px solid {COLOR_BUTTON_PRIMARY}; }}",
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
                    f"QScrollArea {{ border: 1px solid {COLOR_BORDER}; background: {MAIN_CONTENT_BG_COLOR}; border-radius: 6px; }}",
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

            visible = bool((ui.column_visible or {}).get(str(key), True))
            btn.setProperty("col_active", bool(visible))

            def _on_clicked(*_a, _key: str = str(key), _btn: QPushButton = btn) -> None:
                new_visible = not bool(_btn.property("col_active"))
                _btn.setProperty("col_active", bool(new_visible))
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
                    f"QToolButton#col_item {{ background: #FFFFFF; border: 1px solid {COLOR_BORDER}; border-radius: 6px; margin: 2px; padding: 6px 10px; color: {COLOR_TEXT_PRIMARY}; text-align: left; }}",
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
                    "QScrollArea { border-radius: 6px; }",
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
