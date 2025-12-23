"""ui.widgets.arrange_schedule_widgets

UI cho màn "Sắp xếp ca theo lịch trình".

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

from PySide6.QtCore import QSize, Qt, Signal
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

from ui.dialog.arrange_schedule_dialog import ArrangeScheduleDialog
from ui.widgets.declare_time_widgets import DECLARE_TIME_IN_OUT_MODE_OPTIONS


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
        # Hide ID column
        self.table.setColumnHidden(0, True)

        root.addWidget(title)
        root.addWidget(self.table, 1)

        self.table.itemSelectionChanged.connect(lambda: self.schedule_selected.emit())

    def set_schedules(self, rows: list[tuple[int, str]]) -> None:
        self.table.setRowCount(len(rows))
        for r, (schedule_id, name) in enumerate(rows):
            it_id = QTableWidgetItem(str(schedule_id))
            it_id.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.table.setItem(r, 0, it_id)

            it_name = QTableWidgetItem(str(name or ""))
            it_name.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
            self.table.setItem(r, 1, it_name)

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

    def clear_selection(self) -> None:
        self.table.clearSelection()


class MainRight(QWidget):
    arrange_clicked = Signal()
    refresh_clicked = Signal()
    save_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
        for label, value in DECLARE_TIME_IN_OUT_MODE_OPTIONS:
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
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        # Click open dialog as requested
        self.btn_arrange.clicked.connect(self._open_arrange_dialog)

    def _open_arrange_dialog(self) -> None:
        self.arrange_clicked.emit()
        dlg = ArrangeScheduleDialog(self)
        dlg.exec()

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


class ArrangeScheduleView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title = TitleBar1("Sắp xếp ca theo lịch trình", None, self)

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
