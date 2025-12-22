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
    QHBoxLayout,
    QLabel,
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

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
                        f"QComboBox {{ border: 1px solid {COLOR_BORDER}; background: #FFFFFF; padding: 0 8px; border-radius: 6px; }}",
                        f"QComboBox:focus {{ border: 1px solid {COLOR_BORDER}; }}",
                    ]
                )
            )
            return cb

        self.label_from = _mk_label("Từ ngày")
        self.date_from = _mk_date()
        self.label_to = _mk_label("Đến ngày")
        self.date_to = _mk_date()
        self.label_device = _mk_label("Máy")
        self.cbo_device = _mk_combo()

        # Default dates: luôn hiển thị tháng/năm hiện tại
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)

        self.btn_download = QPushButton("Tải dữ liệu chấm công")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setFixedHeight(28)
        self.btn_download.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; padding: 0 12px; border-radius: 6px; }}",
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                ]
            )
        )
        self.btn_download.clicked.connect(self.download_clicked.emit)

        layout.addWidget(self.label_from)
        layout.addWidget(self.date_from)
        layout.addSpacing(6)
        layout.addWidget(self.label_to)
        layout.addWidget(self.date_to)
        layout.addSpacing(6)
        layout.addWidget(self.label_device)
        layout.addWidget(self.cbo_device, 1)
        layout.addWidget(self.btn_download)
        layout.addStretch(1)

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

    def get_date_range(self) -> tuple[date, date]:
        d1 = self.date_from.date().toPython()
        d2 = self.date_to.date().toPython()
        return d1, d2


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
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "Mã chấm công",
                "Ngày tháng năm",
                "Giờ vào 1",
                "Giờ ra 1",
                "Giờ vào 2",
                "Giờ ra 2",
                "Giờ vào 3",
                "Giờ ra 3",
                "Tên máy",
            ]
        )

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(True)
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
        for c in range(0, 9):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)

        header.setSectionsClickable(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
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
        layout.addWidget(self.table, 1)

        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def _on_current_cell_changed(
        self, current_row: int, _current_col: int, previous_row: int, _previous_col: int
    ) -> None:
        if previous_row is not None and previous_row >= 0:
            self._apply_row_font(previous_row, self._font_normal)
        if current_row is not None and current_row >= 0:
            self._apply_row_font(current_row, self._font_semibold)
        self._last_selected_row = current_row

    def _apply_row_font(self, row: int, font: QFont) -> None:
        for col in range(0, 9):
            item = self.table.item(row, col)
            if item is not None:
                item.setFont(font)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def _ensure_rows_fit_viewport(self) -> None:
        viewport_h = self.table.viewport().height()
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
        rows: list[tuple[str, str, str, str, str, str, str, str, str]],
    ) -> None:
        """rows: [(code, date_str, in1, out1, in2, out2, in3, out3, device_name)]"""

        self._rows_data_count = len(rows or [])

        viewport_h = self.table.viewport().height()
        desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
        needed = max(desired, self._rows_data_count, 1)
        self._ensure_row_count(needed)

        for r in range(self.table.rowCount()):
            if r < self._rows_data_count:
                self._set_row_data(r, *rows[r])
            else:
                self._set_row_data(r, "", "", "", "", "", "", "", "", "")

    def _set_row_data(
        self,
        row: int,
        code: str,
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
        for col in range(0, 9):
            item = QTableWidgetItem("")
            item.setFont(self._font_normal)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        self.table.setRowHeight(row, ROW_HEIGHT)
