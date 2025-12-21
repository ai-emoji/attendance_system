"""ui.widgets.declare_work_shift_widgets

Widget cho màn "Khai báo Ca làm việc".

Yêu cầu:
- Sao chép pattern TitleBar1/TitleBar2 giống các module khác.
- TitleBar2 gồm: Làm mới / Lưu / Xóa và hiển thị Tổng.
- MainContent chia 2 bên 50%:
  - Trái: bảng gồm id, mã ca, giờ vào, giờ ra (cột id ẩn)
  - Phải: form gồm các input:
      mã ca làm việc
      giờ vào làm việc
      giờ kết thúc làm việc
      giờ bắt đầu ăn trưa
      giờ kết thúc ăn trưa
      tổng giờ <phút>
      đếm công <công>
      giờ bắt đầu vào để hiểu ca
      giờ kết thúc vào để hiểu ca
      bắt đầu giờ ra để hiểu ca
      kết thúc giờ ra để hiểu ca

Ghi chú:
- Các ô giờ nhập theo định dạng HH:MM.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtGui import QDoubleValidator, QFont, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    ICON_DELETE,
    ICON_REFRESH,
    ICON_SAVE,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    MAIN_CONTENT_BG_COLOR,
    MAIN_CONTENT_MIN_HEIGHT,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    TITLE_2_HEIGHT,
    TITLE_HEIGHT,
    UI_FONT,
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
    refresh_clicked = Signal()
    save_clicked = Signal()
    delete_clicked = Signal()
    time_format_changed = Signal(bool)  # True: HH:MM:SS, False: HH:MM

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Chọn định dạng giờ (bên trái nút Làm mới)
        self.btn_format_hm = QPushButton("Giờ:Phút")
        self.btn_format_hms = QPushButton("Giờ:Phút:Giây")
        self.btn_format_hm.setCheckable(True)
        self.btn_format_hms.setCheckable(True)
        self.btn_format_hm.setChecked(True)

        self.btn_refresh = QPushButton("Làm mới")
        self.btn_save = QPushButton("Lưu")
        self.btn_delete = QPushButton("Xóa")

        self.btn_refresh.setIcon(QIcon(resource_path(ICON_REFRESH)))
        self.btn_save.setIcon(QIcon(resource_path(ICON_SAVE)))
        self.btn_delete.setIcon(QIcon(resource_path(ICON_DELETE)))

        # Nút chọn định dạng không dùng icon
        self.btn_format_hm.setIcon(QIcon())
        self.btn_format_hms.setIcon(QIcon())

        for btn in (
            self.btn_format_hm,
            self.btn_format_hms,
            self.btn_refresh,
            self.btn_save,
            self.btn_delete,
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                        "QPushButton::icon { margin-right: 10px; }",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: #FFFFFF; }}",
                        f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: #FFFFFF; }}",
                    ]
                )
            )

        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        def _set_format(show_seconds: bool) -> None:
            # đảm bảo 2 nút hoạt động như radio
            self.btn_format_hm.setChecked(not show_seconds)
            self.btn_format_hms.setChecked(show_seconds)
            self.time_format_changed.emit(bool(show_seconds))

        self.btn_format_hm.clicked.connect(lambda: _set_format(False))
        self.btn_format_hms.clicked.connect(lambda: _set_format(True))

        self.label_total = QLabel(text or "Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font.setWeight(QFont.Weight.Normal)
        self.label_total.setFont(font)

        layout.addStretch(1)
        layout.addWidget(self.btn_format_hm)
        layout.addWidget(self.btn_format_hms)
        layout.addWidget(self.btn_refresh)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_delete)
        layout.addWidget(self.label_total)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainContent(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(MAIN_CONTENT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        self._font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        self._show_seconds: bool = False
        self._time_inputs: list[tuple[QLineEdit, QLineEdit, QLineEdit, QLabel]] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -----------------
        # Left: table (50%)
        # -----------------
        left = QWidget(self)
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.table = QTableWidget(left)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Mã ca", "Giờ vào", "Giờ ra"])
        self.table.setColumnHidden(0, True)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(40)
        header.setSectionsMovable(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        header_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            header_font.setWeight(QFont.Weight.DemiBold)
        header.setFont(header_font)

        self._last_selected_row: int = -1
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        # Cột Mã ca / Giờ vào / Giờ ra bằng nhau
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID (ẩn)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
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

        left_layout.addWidget(self.table, 1)
        root.addWidget(left, 1)

        # -----------------
        # Right: form (50%)
        # -----------------
        right = QWidget(self)
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(8)

        label_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            label_font.setWeight(QFont.Weight.Normal)

        LABEL_WIDTH = 240

        def _mk_label(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setFont(label_font)
            lb.setFixedWidth(LABEL_WIDTH)
            return lb

        def _mk_input(placeholder: str = "") -> QLineEdit:
            inp = QLineEdit()
            inp.setFont(self._font_normal)
            inp.setFixedHeight(INPUT_HEIGHT_DEFAULT)
            inp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            inp.setPlaceholderText(placeholder)
            inp.setCursor(Qt.CursorShape.IBeamCursor)
            inp.setStyleSheet(
                "\n".join(
                    [
                        f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                        f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    ]
                )
            )
            return inp

        def _mk_field_row(label_text: str, field_widget: QWidget) -> QWidget:
            row = QWidget(right)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            row_layout.addWidget(_mk_label(label_text))
            row_layout.addWidget(field_widget, 1)
            return row

        def _mk_time_input() -> tuple[QWidget, QLineEdit, QLineEdit, QLineEdit, QLabel]:
            """Tạo input giờ dạng 3 ô: HH : MM (: SS tuỳ chọn)."""

            wrap = QWidget(right)
            layout = QHBoxLayout(wrap)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            hour = _mk_input("Giờ")
            minute = _mk_input("Phút")
            second = _mk_input("Giây")
            hour.setFixedWidth(60)
            minute.setFixedWidth(60)
            second.setFixedWidth(60)
            hour.setAlignment(Qt.AlignmentFlag.AlignCenter)
            minute.setAlignment(Qt.AlignmentFlag.AlignCenter)
            second.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hour.setMaxLength(2)
            minute.setMaxLength(2)
            second.setMaxLength(2)
            hour.setValidator(QIntValidator(0, 23, self))
            minute.setValidator(QIntValidator(0, 59, self))
            second.setValidator(QIntValidator(0, 59, self))

            colon = QLabel(":")
            colon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            colon.setFixedWidth(10)
            colon.setFont(self._font_normal)

            colon2 = QLabel(":")
            colon2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            colon2.setFixedWidth(10)
            colon2.setFont(self._font_normal)

            def _pad_2digits(inp: QLineEdit) -> None:
                txt = (inp.text() or "").strip()
                if not txt:
                    return
                try:
                    inp.setText(f"{int(txt):02d}")
                except Exception:
                    return

            def _auto_next() -> None:
                if len((hour.text() or "").strip()) >= 2:
                    minute.setFocus()

            def _auto_next2() -> None:
                if not self._show_seconds:
                    return
                if len((minute.text() or "").strip()) >= 2:
                    second.setFocus()

            hour.textChanged.connect(lambda _t: _auto_next())
            minute.textChanged.connect(lambda _t: _auto_next2())
            hour.editingFinished.connect(lambda: _pad_2digits(hour))
            minute.editingFinished.connect(lambda: _pad_2digits(minute))
            second.editingFinished.connect(lambda: _pad_2digits(second))

            layout.addWidget(hour)
            layout.addWidget(colon)
            layout.addWidget(minute)
            layout.addWidget(colon2)
            layout.addWidget(second)
            layout.addStretch(1)

            colon2.setVisible(self._show_seconds)
            second.setVisible(self._show_seconds)
            self._time_inputs.append((hour, minute, second, colon2))
            return wrap, hour, minute, second, colon2

        # Mã ca
        self.input_shift_code = _mk_input("(ví dụ: HC)")
        right_layout.addWidget(_mk_field_row("Mã ca làm việc:", self.input_shift_code))

        # Giờ vào
        (
            self.input_time_in,
            self.time_in_h,
            self.time_in_m,
            self.time_in_s,
            self.time_in_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(_mk_field_row("Giờ vào làm việc:", self.input_time_in))

        # Giờ ra
        (
            self.input_time_out,
            self.time_out_h,
            self.time_out_m,
            self.time_out_s,
            self.time_out_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Giờ kết thúc làm việc:", self.input_time_out)
        )

        # Ăn trưa
        (
            self.input_lunch_start,
            self.lunch_start_h,
            self.lunch_start_m,
            self.lunch_start_s,
            self.lunch_start_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Giờ bắt đầu ăn trưa:", self.input_lunch_start)
        )

        (
            self.input_lunch_end,
            self.lunch_end_h,
            self.lunch_end_m,
            self.lunch_end_s,
            self.lunch_end_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Giờ kết thúc ăn trưa:", self.input_lunch_end)
        )

        # Tổng giờ (phút)
        self.input_total_minutes = _mk_input("(ví dụ: 480)")
        self.input_total_minutes.setValidator(QIntValidator(0, 100000, self))
        right_layout.addWidget(
            _mk_field_row("Tổng giờ <phút>:", self.input_total_minutes)
        )

        # Đếm công
        self.input_work_count = _mk_input("(ví dụ: 1.0)")
        self.input_work_count.setValidator(QDoubleValidator(0.0, 1000000.0, 2, self))
        right_layout.addWidget(_mk_field_row("Đếm công <công>:", self.input_work_count))

        # Cửa sổ vào/ra để hiểu ca
        (
            self.input_in_window_start,
            self.in_window_start_h,
            self.in_window_start_m,
            self.in_window_start_s,
            self.in_window_start_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Giờ bắt đầu vào để hiểu ca:", self.input_in_window_start)
        )

        (
            self.input_in_window_end,
            self.in_window_end_h,
            self.in_window_end_m,
            self.in_window_end_s,
            self.in_window_end_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Giờ kết thúc vào để hiểu ca:", self.input_in_window_end)
        )

        (
            self.input_out_window_start,
            self.out_window_start_h,
            self.out_window_start_m,
            self.out_window_start_s,
            self.out_window_start_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Bắt đầu giờ ra để hiểu ca:", self.input_out_window_start)
        )

        (
            self.input_out_window_end,
            self.out_window_end_h,
            self.out_window_end_m,
            self.out_window_end_s,
            self.out_window_end_colon2,
        ) = _mk_time_input()
        right_layout.addWidget(
            _mk_field_row("Kết thúc giờ ra để hiểu ca:", self.input_out_window_end)
        )

        right_layout.addStretch(1)
        root.addWidget(right, 1)

        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    # -----------------
    # Table helpers
    # -----------------
    def _on_current_cell_changed(
        self, current_row: int, _current_col: int, previous_row: int, _previous_col: int
    ) -> None:
        if previous_row is not None and previous_row >= 0:
            self._apply_row_font(previous_row, self._font_normal)
        if current_row is not None and current_row >= 0:
            self._apply_row_font(current_row, self._font_semibold)
        self._last_selected_row = current_row

    def _apply_row_font(self, row: int, font: QFont) -> None:
        for col in (0, 1, 2, 3):
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
            self.table.setCurrentCell(needed - 1, 1)

    def _init_row_items(self, row: int) -> None:
        id_item = QTableWidgetItem("")
        id_item.setFont(self._font_normal)
        code_item = QTableWidgetItem("")
        code_item.setFont(self._font_normal)
        in_item = QTableWidgetItem("")
        in_item.setFont(self._font_normal)
        out_item = QTableWidgetItem("")
        out_item.setFont(self._font_normal)

        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        in_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        out_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.setItem(row, 0, id_item)
        self.table.setItem(row, 1, code_item)
        self.table.setItem(row, 2, in_item)
        self.table.setItem(row, 3, out_item)

    def _set_row_data(
        self,
        row: int,
        shift_id: int | None,
        shift_code: str,
        time_in: str,
        time_out: str,
    ) -> None:
        if self.table.item(row, 0) is None:
            self._init_row_items(row)

        self.table.item(row, 0).setText("" if shift_id is None else str(int(shift_id)))
        self.table.item(row, 1).setText(shift_code or "")

        in_item = self.table.item(row, 2)
        out_item = self.table.item(row, 3)
        if in_item is not None:
            in_item.setData(Qt.ItemDataRole.UserRole, time_in or "")
            in_item.setText(self._format_time_for_display(time_in or ""))
        if out_item is not None:
            out_item.setData(Qt.ItemDataRole.UserRole, time_out or "")
            out_item.setText(self._format_time_for_display(time_out or ""))

    def _format_time_for_display(self, raw: str) -> str:
        value = (raw or "").strip()
        if not value:
            return ""

        parts = value.split(":")
        if self._show_seconds:
            if len(parts) == 2:
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
            return value

        # HH:MM
        if len(parts) >= 2:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        return value

    def set_show_seconds(self, show_seconds: bool) -> None:
        self._show_seconds = bool(show_seconds)

        for _h, _m, s, colon2 in self._time_inputs:
            colon2.setVisible(self._show_seconds)
            s.setVisible(self._show_seconds)

        # update table display according to new format
        for row in range(self.table.rowCount()):
            for col in (2, 3):
                item = self.table.item(row, col)
                if item is None:
                    continue
                raw = item.data(Qt.ItemDataRole.UserRole)
                if raw is None:
                    raw = item.text()
                item.setText(self._format_time_for_display(str(raw)))

    def set_work_shifts(self, rows: list[tuple[int, str, str, str]]) -> None:
        """rows: [(id, shift_code, time_in, time_out)]"""

        self._rows_data_count = len(rows or [])

        viewport_h = self.table.viewport().height()
        desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
        needed = max(desired, self._rows_data_count, 1)
        self._ensure_row_count(needed)

        for r in range(self.table.rowCount()):
            if r < self._rows_data_count:
                shift_id, code, time_in, time_out = rows[r]
                self._set_row_data(r, shift_id, code, time_in, time_out)
            else:
                self._set_row_data(r, None, "", "", "")

    def get_selected_work_shift(self) -> tuple[int, str] | None:
        """Trả về (id, shift_code) của dòng đang chọn."""

        row = self.table.currentRow()
        if row < 0:
            return None

        id_item = self.table.item(row, 0)
        code_item = self.table.item(row, 1)
        if id_item is None:
            return None

        raw_id = (id_item.text() or "").strip()
        if not raw_id:
            return None

        try:
            shift_id = int(raw_id)
        except Exception:
            return None

        return shift_id, (code_item.text() if code_item is not None else "")

    def select_work_shift_by_id(self, shift_id: int) -> None:
        try:
            target = str(int(shift_id))
        except Exception:
            return

        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (item.text() or "").strip() == target:
                self.table.setCurrentCell(row, 1)
                return

    # -----------------
    # Form helpers
    # -----------------
    def _get_time_value(
        self, hour: QLineEdit, minute: QLineEdit, second: QLineEdit
    ) -> str:
        hh = (hour.text() or "").strip()
        mm = (minute.text() or "").strip()
        ss = (second.text() or "").strip()
        if not hh and not mm and not ss:
            return ""
        if self._show_seconds:
            if not ss:
                ss = "00"
            return f"{hh}:{mm}:{ss}"
        return f"{hh}:{mm}"

    def _set_time_value(
        self, value: str, hour: QLineEdit, minute: QLineEdit, second: QLineEdit
    ) -> None:
        raw = (value or "").strip()
        if not raw:
            hour.setText("")
            minute.setText("")
            second.setText("")
            return

        parts = raw.split(":")
        if len(parts) >= 2:
            hour.setText(parts[0].zfill(2))
            minute.setText(parts[1].zfill(2))
            if len(parts) >= 3:
                second.setText(parts[2].zfill(2))
            else:
                second.setText("00")
            return

        # Fallback: nếu value chỉ là "HH" hoặc format lạ
        hour.setText(raw[:2])
        minute.setText("")
        second.setText("")

    def clear_form(self) -> None:
        self.input_shift_code.setText("")
        self.time_in_h.setText("")
        self.time_in_m.setText("")
        self.time_in_s.setText("")
        self.time_out_h.setText("")
        self.time_out_m.setText("")
        self.time_out_s.setText("")
        self.lunch_start_h.setText("")
        self.lunch_start_m.setText("")
        self.lunch_start_s.setText("")
        self.lunch_end_h.setText("")
        self.lunch_end_m.setText("")
        self.lunch_end_s.setText("")
        self.input_total_minutes.setText("")
        self.input_work_count.setText("")
        self.in_window_start_h.setText("")
        self.in_window_start_m.setText("")
        self.in_window_start_s.setText("")
        self.in_window_end_h.setText("")
        self.in_window_end_m.setText("")
        self.in_window_end_s.setText("")
        self.out_window_start_h.setText("")
        self.out_window_start_m.setText("")
        self.out_window_start_s.setText("")
        self.out_window_end_h.setText("")
        self.out_window_end_m.setText("")
        self.out_window_end_s.setText("")

    def get_form_data(self) -> dict:
        return {
            "shift_code": (self.input_shift_code.text() or ""),
            "time_in": self._get_time_value(
                self.time_in_h, self.time_in_m, self.time_in_s
            ),
            "time_out": self._get_time_value(
                self.time_out_h, self.time_out_m, self.time_out_s
            ),
            "lunch_start": self._get_time_value(
                self.lunch_start_h, self.lunch_start_m, self.lunch_start_s
            ),
            "lunch_end": self._get_time_value(
                self.lunch_end_h, self.lunch_end_m, self.lunch_end_s
            ),
            "total_minutes": (self.input_total_minutes.text() or ""),
            "work_count": (self.input_work_count.text() or ""),
            "in_window_start": self._get_time_value(
                self.in_window_start_h, self.in_window_start_m, self.in_window_start_s
            ),
            "in_window_end": self._get_time_value(
                self.in_window_end_h, self.in_window_end_m, self.in_window_end_s
            ),
            "out_window_start": self._get_time_value(
                self.out_window_start_h,
                self.out_window_start_m,
                self.out_window_start_s,
            ),
            "out_window_end": self._get_time_value(
                self.out_window_end_h, self.out_window_end_m, self.out_window_end_s
            ),
        }

    def set_form(
        self,
        shift_code: str,
        time_in: str,
        time_out: str,
        lunch_start: str,
        lunch_end: str,
        total_minutes: int | None,
        work_count: float | None,
        in_window_start: str,
        in_window_end: str,
        out_window_start: str,
        out_window_end: str,
    ) -> None:
        self.input_shift_code.setText(shift_code or "")
        self._set_time_value(
            time_in or "", self.time_in_h, self.time_in_m, self.time_in_s
        )
        self._set_time_value(
            time_out or "", self.time_out_h, self.time_out_m, self.time_out_s
        )
        self._set_time_value(
            lunch_start or "",
            self.lunch_start_h,
            self.lunch_start_m,
            self.lunch_start_s,
        )
        self._set_time_value(
            lunch_end or "", self.lunch_end_h, self.lunch_end_m, self.lunch_end_s
        )
        self.input_total_minutes.setText(
            "" if total_minutes is None else str(int(total_minutes))
        )
        self.input_work_count.setText("" if work_count is None else str(work_count))
        self._set_time_value(
            in_window_start or "",
            self.in_window_start_h,
            self.in_window_start_m,
            self.in_window_start_s,
        )
        self._set_time_value(
            in_window_end or "",
            self.in_window_end_h,
            self.in_window_end_m,
            self.in_window_end_s,
        )
        self._set_time_value(
            out_window_start or "",
            self.out_window_start_h,
            self.out_window_start_m,
            self.out_window_start_s,
        )
        self._set_time_value(
            out_window_end or "",
            self.out_window_end_h,
            self.out_window_end_m,
            self.out_window_end_s,
        )
