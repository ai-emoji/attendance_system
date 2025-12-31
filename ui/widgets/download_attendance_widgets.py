"""ui.widgets.download_attendance_widgets

Các widget dùng cho layout phần "Tải dữ liệu Máy chấm công".

Yêu cầu:
- TitleBar1: sao chép từ ui.widgets.title_widgets
- TitleBar2: input chọn Từ ngày / Đến ngày, combobox chọn Máy chấm công,
  button "Tải dữ liệu chấm công"
- MainContent: bảng các cột:
  Mã chấm công, Ngày tháng năm, Giờ vào 1, Giờ ra 1, Giờ vào 2, Giờ ra 2,
  Giờ vào 3, Giờ ra 3, Tên máy

Ghi chú:
- UI chỉ dựng widget + signal; xử lý tải dữ liệu ở controller/services.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QLocale, QTimer, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFrame,
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

from core.resource import (
    CONTENT_FONT,
    COLOR_BORDER,
    ICON_DROPDOWN,
    ICON_CLOCK,
    ICON_TOTAL,
    COLOR_TEXT_PRIMARY,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    MAIN_CONTENT_BG_COLOR,
    MAIN_CONTENT_MIN_HEIGHT,
    ODD_ROW_BG_COLOR,
    EVEN_ROW_BG_COLOR,
    ROW_HEIGHT,
    TITLE_HEIGHT,
    TITLE_2_HEIGHT,
    BG_TITLE_2_HEIGHT,
    BG_TITLE_1_HEIGHT,
    UI_FONT,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_TEXT_LIGHT,
    resource_path,
)

from core.ui_settings import get_download_attendance_ui, ui_settings_bus


ATTENDANCE_HEADERS: list[str] = [
    "Mã chấm công",
    "Tên trên MCC",
    "Ngày tháng năm",
    "Giờ vào 1",
    "Giờ ra 1",
    "Giờ vào 2",
    "Giờ ra 2",
    "Giờ vào 3",
    "Giờ ra 3",
    "Tên máy",
]

# Keep in sync with ui.dialog.download_attendance_settings_dialog
ATTENDANCE_COLUMN_KEYS: list[str] = [
    "attendance_code",
    "name_on_mcc",
    "work_date",
    "in_1",
    "out_1",
    "in_2",
    "out_2",
    "in_3",
    "out_3",
    "device_name",
]


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
    download_clicked = Signal()
    search_changed = Signal()
    time_format_changed = Signal(bool)  # show_seconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 0, 12, 0)
        self._layout.setSpacing(8)
        self._layout_mode: str = "ltr"

        dropdown_icon_url = resource_path(ICON_DROPDOWN).replace("\\", "/")

        def _mk_label(text: str) -> QLabel:
            lb = QLabel(text)
            font = QFont(UI_FONT, CONTENT_FONT)
            if FONT_WEIGHT_NORMAL >= 400:
                font.setWeight(QFont.Weight.Normal)
            lb.setFont(font)
            lb.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
            return lb

        def _mk_date() -> QDateEdit:
            de = QDateEdit(self)
            de.setDisplayFormat("dd/MM/yyyy")
            de.setCalendarPopup(True)
            de.setFixedHeight(28)

            dropdown_icon_url = resource_path(ICON_DROPDOWN).replace("\\", "/")

            # Đủ chỗ cho "dd/MM/yyyy" + nút dropdown (Windows + font lớn dễ bị cắt)
            try:
                de.setMinimumContentsLength(10)  # len("dd/MM/yyyy")
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

            # Text nằm giữa
            try:
                le = de.lineEdit()
                if le is not None:
                    le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                pass

            # Lịch hiển thị tiếng Việt + luôn thấy tháng/năm ở header
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

                    # Fix: month/year text bị "ẩn" (thường do stylesheet/palette làm chữ trắng)
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
                        # Chừa chỗ bên phải cho nút dropdown (calendarPopup)
                        f"QDateEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; padding-right: 30px; border-radius: 6px; }}",
                        f"QDateEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                        # Hiển thị rõ nút dropdown để click mở lịch
                        f"QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border-left: 1px solid {COLOR_BORDER}; background: #FFFFFF; }}",
                        f'QDateEdit::down-arrow {{ image: url("{dropdown_icon_url}"); width: 10px; height: 10px; }}',
                    ]
                )
            )
            return de

        def _mk_combo() -> QComboBox:
            cb = QComboBox(self)
            cb.setFixedHeight(28)
            cb.setStyleSheet(
                "\n".join(
                    [
                        # Chừa chỗ bên phải cho nút dropdown
                        f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; padding-right: 30px; border-radius: 6px; }}",
                        f"QComboBox:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                        f"QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 26px; border-left: 1px solid {COLOR_BORDER}; background: #FFFFFF; }}",
                        f'QComboBox::down-arrow {{ image: url("{dropdown_icon_url}"); width: 10px; height: 10px; }}',
                    ]
                )
            )
            return cb

        def _mk_line_edit() -> QLineEdit:
            le = QLineEdit(self)
            le.setFixedHeight(28)
            le.setStyleSheet(
                "\n".join(
                    [
                        f"QLineEdit {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 6px; }}",
                        f"QLineEdit:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                    ]
                )
            )
            return le

        self.label_from = _mk_label("Từ ngày")
        self.date_from = _mk_date()
        self.label_to = _mk_label("Đến ngày")
        self.date_to = _mk_date()
        self.label_device = _mk_label("Máy")
        self.cbo_device = _mk_combo()
        self.cbo_device.setFixedWidth(220)

        # Search UI (giống employee_widgets.py): combobox "tìm theo" + input text
        self.cbo_search_by = _mk_combo()
        self.cbo_search_by.setFixedWidth(150)
        self.cbo_search_by.addItem("Mã CC", "attendance_code")
        self.cbo_search_by.addItem("Tên trên MCC", "name_on_mcc")
        self.cbo_search_by.setCurrentIndex(0)

        self.inp_search_text = _mk_line_edit()
        self.inp_search_text.setPlaceholderText("Tìm kiếm...")

        self.label_total = _mk_label("Tổng: 0")

        self.total_icon = QLabel("")
        self.total_icon.setFixedSize(18, 18)
        try:
            self.total_icon.setPixmap(
                QIcon(resource_path(ICON_TOTAL)).pixmap(QSize(18, 18))
            )
        except Exception:
            pass

        # Default dates: luôn hiển thị tháng/năm hiện tại
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)

        self.btn_download = QPushButton("Tải dữ liệu chấm công")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setFixedHeight(28)
        try:
            self.btn_download.setIcon(
                QIcon(resource_path("assets/images/download_attendance.svg"))
            )
            self.btn_download.setIconSize(QSize(18, 18))
        except Exception:
            pass
        self.btn_download.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; padding: 0 12px; border-radius: 6px; }}",
                    "QPushButton::icon { margin-right: 10px; }",
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                ]
            )
        )
        self.btn_download.clicked.connect(self.download_clicked.emit)

        # Time format buttons
        def _mk_time_btn(text: str) -> QPushButton:
            b = QPushButton(text, self)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(28)
            b.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                        f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; }}",
                    ]
                )
            )
            return b

        self.btn_hhmm = _mk_time_btn("HH:MM")
        self.btn_hhmmss = _mk_time_btn("HH:MM:SS")
        self.btn_hhmmss.setChecked(True)

        try:
            icon = QIcon(resource_path(ICON_CLOCK))
            self.btn_hhmm.setIcon(icon)
            self.btn_hhmmss.setIcon(icon)
        except Exception:
            pass

        def _set_time_mode(show_seconds: bool) -> None:
            self.btn_hhmm.blockSignals(True)
            self.btn_hhmmss.blockSignals(True)
            try:
                self.btn_hhmm.setChecked(not show_seconds)
                self.btn_hhmmss.setChecked(bool(show_seconds))
            finally:
                self.btn_hhmm.blockSignals(False)
                self.btn_hhmmss.blockSignals(False)
            self.time_format_changed.emit(bool(show_seconds))

        self.btn_hhmm.clicked.connect(lambda: _set_time_mode(False))
        self.btn_hhmmss.clicked.connect(lambda: _set_time_mode(True))

        # search signals
        self.inp_search_text.textChanged.connect(lambda _t: self.search_changed.emit())
        self.cbo_search_by.currentIndexChanged.connect(
            lambda _i: self.search_changed.emit()
        )

        self._rebuild_layout("ltr")

        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

        # Some styles may reset the internal lineEdit font after selecting a date.
        try:
            self.date_from.dateChanged.connect(lambda _d: self.apply_ui_settings())
            self.date_to.dateChanged.connect(lambda _d: self.apply_ui_settings())
        except Exception:
            pass

    def apply_ui_settings(self) -> None:
        ui = get_download_attendance_ui()

        # Layout + sizing
        try:
            self._layout.setContentsMargins(
                int(ui.layout_margin), 0, int(ui.layout_margin), 0
            )
            self._layout.setSpacing(int(ui.layout_spacing))
        except Exception:
            pass

        try:
            self._rebuild_layout(str(ui.layout_mode))
        except Exception:
            pass

        try:
            ih = int(ui.input_height)
            bh = int(ui.button_height)

            for w in (
                self.date_from,
                self.date_to,
                self.cbo_device,
                self.cbo_search_by,
            ):
                w.setFixedHeight(ih)
            self.inp_search_text.setFixedHeight(ih)

            try:
                dw = int(getattr(ui, "date_width", 0) or 0)
                if dw > 0:
                    self.date_from.setFixedWidth(dw)
                    self.date_to.setFixedWidth(dw)
            except Exception:
                pass

            self.cbo_device.setFixedWidth(int(ui.device_width))
            self.cbo_search_by.setFixedWidth(int(ui.search_by_width))
            self.inp_search_text.setMinimumWidth(int(ui.search_text_min_width))

            for b in (self.btn_hhmm, self.btn_hhmmss, self.btn_download):
                b.setFixedHeight(bh)
            self.btn_download.setFixedWidth(int(ui.download_button_width))
            self.btn_hhmm.setFixedWidth(int(ui.time_button_width))
            self.btn_hhmmss.setFixedWidth(int(ui.time_button_width))

            try:
                s = int(ui.clock_icon_size)
                if s < 0:
                    s = 0
                self.btn_hhmm.setIconSize(QSize(s, s))
                self.btn_hhmmss.setIconSize(QSize(s, s))
            except Exception:
                pass
        except Exception:
            pass

        # Combo/input font
        f = QFont(UI_FONT, int(ui.combo_font_size))
        if FONT_WEIGHT_NORMAL >= 400:
            f.setWeight(QFont.Weight.Normal)

        for w in (
            self.cbo_device,
            self.cbo_search_by,
            self.inp_search_text,
        ):
            try:
                w.setFont(f)
            except Exception:
                pass

        # Calendar + DateEdit display font
        cal_f = QFont(UI_FONT, int(ui.calendar_font_size))
        if FONT_WEIGHT_NORMAL >= 400:
            cal_f.setWeight(QFont.Weight.Normal)

        for de in (self.date_from, self.date_to):
            try:
                de.setFont(cal_f)
            except Exception:
                pass

            # Ensure the displayed text (e.g. 23/12/2025) follows the same font.
            try:
                le = de.lineEdit()
                if le is not None:
                    le.setFont(cal_f)
            except Exception:
                pass

        for de in (self.date_from, self.date_to):
            try:
                cw = de.calendarWidget()
                if cw is not None:
                    cw.setFont(cal_f)
            except Exception:
                pass

    def _rebuild_layout(self, mode: str) -> None:
        m = str(mode or "ltr").strip().lower()
        if m not in {"ltr", "rtl", "space_between"}:
            m = "ltr"

        # Avoid unnecessary churn
        if getattr(self, "_layout_mode", "") == m and self._layout.count() > 0:
            try:
                self.setLayoutDirection(
                    Qt.LayoutDirection.RightToLeft
                    if m == "rtl"
                    else Qt.LayoutDirection.LeftToRight
                )
            except Exception:
                pass
            return

        self._layout_mode = m
        try:
            self.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft
                if m == "rtl"
                else Qt.LayoutDirection.LeftToRight
            )
        except Exception:
            pass

        # Clear layout items (keep widgets alive)
        try:
            while self._layout.count() > 0:
                item = self._layout.takeAt(0)
                if item is None:
                    continue
                w = item.widget()
                if w is not None:
                    self._layout.removeWidget(w)
        except Exception:
            pass

        def _add_core_controls() -> None:
            self._layout.addWidget(self.label_from)
            self._layout.addWidget(self.date_from)
            self._layout.addSpacing(6)
            self._layout.addWidget(self.label_to)
            self._layout.addWidget(self.date_to)
            self._layout.addSpacing(6)
            self._layout.addWidget(self.label_device)
            self._layout.addWidget(self.cbo_device)
            self._layout.addSpacing(6)
            self._layout.addWidget(self.cbo_search_by, 0)
            self._layout.addWidget(self.inp_search_text, 1)
            self._layout.addWidget(self.btn_hhmm)
            self._layout.addWidget(self.btn_hhmmss)
            self._layout.addWidget(self.btn_download)

        if m == "space_between":
            _add_core_controls()
            self._layout.addStretch(1)
            self._layout.addSpacing(10)
            self._layout.addWidget(self.total_icon)
            self._layout.addWidget(self.label_total)
        else:
            _add_core_controls()
            self._layout.addSpacing(10)
            self._layout.addWidget(self.total_icon)
            self._layout.addWidget(self.label_total)
            self._layout.addStretch(1)

    def set_devices(self, rows: list[tuple[int, str]]) -> None:
        """rows: [(device_id, device_name)]"""
        self.cbo_device.clear()
        for device_id, device_name in rows or []:
            self.cbo_device.addItem(str(device_name or ""), int(device_id))

    def get_selected_device_id(self) -> int | None:
        data = self.cbo_device.currentData()
        try:
            return int(data)
        except Exception:
            return None

    def get_selected_device_name(self) -> str:
        try:
            return str(self.cbo_device.currentText() or "").strip()
        except Exception:
            return ""

    def get_date_range(self) -> tuple[date, date]:
        d1 = self.date_from.date().toPython()
        d2 = self.date_to.date().toPython()
        return d1, d2

    def set_total(self, count: int) -> None:
        try:
            self.label_total.setText(f"Tổng: {int(count or 0)}")
        except Exception:
            self.label_total.setText("Tổng: 0")

    def get_search_filters(self) -> dict:
        search_by = self.cbo_search_by.currentData()
        search_by = str(search_by).strip() if search_by is not None else ""
        search_text = self.inp_search_text.text().strip()
        return {"search_by": search_by, "search_text": search_text}


class MainContent(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(MAIN_CONTENT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = QTableWidget(self)
        # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
        try:
            self.table.setFrameShape(QFrame.Shape.NoFrame)
            self.table.setLineWidth(0)
        except Exception:
            pass
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(len(ATTENDANCE_HEADERS))
        self.table.setHorizontalHeaderLabels(list(ATTENDANCE_HEADERS))

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
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)
        header.setSectionsMovable(False)

        header_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            header_font.setWeight(QFont.Weight.DemiBold)
        header.setFont(header_font)

        self._font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        self._last_selected_row: int = -1
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        # Chia đều các cột
        for c in range(0, len(ATTENDANCE_HEADERS)):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)

        header.setSectionsClickable(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 0px; }}",
                    "QTableWidget::pane { border: 0px; }",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QHeaderView::section:first {{ border-left: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableCornerButton::section {{ background-color: {BG_TITLE_2_HEIGHT}; border: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableWidget::item {{ padding-left: 8px; padding-right: 8px; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border-radius: 0px; border: 0px; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        self._rows_data_count = 0

        self.table.setRowCount(1)
        self._init_row_items(0)
        self.table_frame = QFrame(self)
        try:
            self.table_frame.setObjectName("download_attendance_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#download_attendance_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        layout.addWidget(self.table_frame, 1)

        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def apply_ui_settings(self) -> None:
        ui = get_download_attendance_ui()

        # Table fonts
        header_font = QFont(UI_FONT, int(ui.table_header_font_size))
        header_font.setWeight(
            QFont.Weight.DemiBold
            if str(ui.table_header_font_weight) == "bold"
            else QFont.Weight.Normal
        )
        try:
            self.table.horizontalHeader().setFont(header_font)
            w = 600 if str(ui.table_header_font_weight) == "bold" else 400
            self.table.horizontalHeader().setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.table_header_font_size)}px; font-weight: {int(w)}; }}"
            )
        except Exception:
            pass

        self._font_normal = QFont(UI_FONT, int(ui.table_font_size))
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, int(ui.table_font_size))
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        # Update existing items fonts
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                it = self.table.item(r, c)
                if it is not None:
                    it.setFont(self._font_normal)

        # Column visibility
        visible_map = ui.column_visible or {}
        for idx, key in enumerate(ATTENDANCE_COLUMN_KEYS):
            try:
                is_visible = bool(visible_map.get(key, True))
                if idx < self.table.columnCount():
                    self.table.setColumnHidden(idx, not is_visible)
            except Exception:
                continue

    def _on_current_cell_changed(
        self, current_row: int, _current_col: int, previous_row: int, _previous_col: int
    ) -> None:
        if previous_row is not None and previous_row >= 0:
            self._apply_row_font(previous_row, self._font_normal)
        if current_row is not None and current_row >= 0:
            self._apply_row_font(current_row, self._font_semibold)
        self._last_selected_row = current_row

    def _apply_row_font(self, row: int, font: QFont) -> None:
        for col in range(0, len(ATTENDANCE_HEADERS)):
            item = self.table.item(row, col)
            if item is not None:
                item.setFont(font)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def _ensure_rows_fit_viewport(self) -> None:
        try:
            viewport_h = self.table.viewport().height()
        except RuntimeError:
            # QTableWidget already deleted (view switched/closed)
            return
        if viewport_h <= 0:
            return
        desired = max(1, int(viewport_h // ROW_HEIGHT))
        data_count = max(0, int(getattr(self, "_rows_data_count", 0) or 0))
        needed = max(desired, data_count, 1)
        self._ensure_row_count(needed)

    def _ensure_row_count(self, needed: int) -> None:
        needed = max(1, int(needed))
        current = self.table.rowCount()
        if current == needed:
            return

        selected_row = self.table.currentRow()

        if current < needed:
            self.table.setRowCount(needed)
            for row in range(current, needed):
                self._init_row_items(row)
        else:
            self.table.setRowCount(needed)

        if selected_row >= needed:
            self.table.clearSelection()
            self.table.setCurrentCell(needed - 1, 0)

    def set_attendance_rows(
        self,
        rows: list[tuple[str, str, str, str, str, str, str, str, str, str]],
    ) -> None:
        """rows: [(code, name_on_mcc, date_str, in1, out1, in2, out2, in3, out3, device_name)]"""

        try:
            self._rows_data_count = len(rows or [])

            viewport_h = self.table.viewport().height()
            desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
            needed = max(desired, self._rows_data_count, 1)
            self._ensure_row_count(needed)

            for r in range(self.table.rowCount()):
                if r < self._rows_data_count:
                    self._set_row_data(r, *rows[r])
                else:
                    self._set_row_data(r, "", "", "", "", "", "", "", "", "", "")
        except RuntimeError:
            # QTableWidget already deleted (view switched/closed)
            return

    def clear_attendance_rows(self) -> None:
        """Xóa dữ liệu (giữ lại placeholder rows theo viewport)."""

        try:
            self._rows_data_count = 0
            self._ensure_rows_fit_viewport()
            # Clear text in all visible rows
            for r in range(self.table.rowCount()):
                self._set_row_data(r, "", "", "", "", "", "", "", "", "", "")
        except RuntimeError:
            return

    def append_attendance_rows(
        self,
        rows: list[tuple[str, str, str, str, str, str, str, str, str, str]],
    ) -> None:
        """Append dữ liệu vào cuối bảng (dùng cho trường hợp streaming)."""

        if not rows:
            return

        try:
            start = int(getattr(self, "_rows_data_count", 0) or 0)
            add = len(rows)
            self._rows_data_count = start + add

            # Ensure enough rows for data + viewport
            viewport_h = self.table.viewport().height()
            desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
            needed = max(desired, self._rows_data_count, 1)
            self._ensure_row_count(needed)

            for i, row in enumerate(rows):
                r = start + i
                self._set_row_data(r, *row)
        except RuntimeError:
            return

    def _set_row_data(
        self,
        row: int,
        code: str,
        name_on_mcc: str,
        date_str: str,
        in1: str,
        out1: str,
        in2: str,
        out2: str,
        in3: str,
        out3: str,
        device_name: str,
    ) -> None:
        if self.table.item(row, 0) is None:
            self._init_row_items(row)

        vals = [
            code or "",
            name_on_mcc or "",
            date_str or "",
            in1 or "",
            out1 or "",
            in2 or "",
            out2 or "",
            in3 or "",
            out3 or "",
            device_name or "",
        ]
        for col, v in enumerate(vals):
            self.table.item(row, col).setText(v)

    def _init_row_items(self, row: int) -> None:
        for col in range(0, len(ATTENDANCE_HEADERS)):
            item = QTableWidgetItem("")
            item.setFont(self._font_normal)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        self.table.setRowHeight(row, ROW_HEIGHT)

    def get_column_headers(self) -> list[str]:
        return list(ATTENDANCE_HEADERS)
