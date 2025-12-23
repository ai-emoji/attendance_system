"""ui.widgets.declare_time_widgets

UI cho màn "Khai báo giờ Vào/Ra".

Yêu cầu:
- Sao chép TitleBar1
- TitleBar2 gồm: Làm mới / Lưu / Xóa và hiển thị Tổng
- MainContent1: form (Mã, Mô tả, Kiểu sắp xếp) + group "Thông số chung"
- MainContent2: bảng danh sách (ID ẩn, MÃ, Mô tả)

Ghi chú:
- File này chỉ dựng UI (widget + signal). Nghiệp vụ nằm ở controller/services.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
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


# Single source of truth for "Kiểu sắp xếp" / "Chọn vào/ra" options.
# Other screens (e.g. Arrange Schedule) can import and reuse this list.
DECLARE_TIME_IN_OUT_MODE_OPTIONS: list[tuple[str, str | None]] = [
    ("Chưa chọn", None),
    ("Sắp xếp giờ Vào/Ra theo tự động", "auto"),
    ("Theo giờ Vào/Ra trên máy chấm công", "device"),
    (
        "Giờ vào là Giờ đầu tiên và giờ Ra là Giờ cuối cùng trong ngày",
        "first_last",
    ),
]


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


def _mk_line_edit(parent: QWidget | None = None, height: int = 32) -> QLineEdit:
    le = QLineEdit(parent)
    le.setFixedHeight(height)
    le.setFont(_mk_font_normal())
    le.setStyleSheet(
        "\n".join(
            [
                f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )
    )
    return le


def _mk_combo(parent: QWidget | None = None, height: int = 32) -> QComboBox:
    cb = QComboBox(parent)
    cb.setFixedHeight(height)
    cb.setFont(_mk_font_normal())
    cb.setStyleSheet(
        "\n".join(
            [
                f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )
    )
    return cb


def _mk_group_box(title: str, parent: QWidget | None = None) -> QGroupBox:
    gb = QGroupBox(title, parent)
    gb.setFont(_mk_font_semibold())
    gb.setStyleSheet(
        "\n".join(
            [
                f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; color: {COLOR_TEXT_PRIMARY}; }}",
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }",
            ]
        )
    )
    return gb


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

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(TITLE_2_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"background-color: {BG_TITLE_2_HEIGHT};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self.btn_refresh = QPushButton("Làm mới")
        self.btn_save = QPushButton("Lưu")
        self.btn_delete = QPushButton("Xóa")

        self.btn_refresh.setIcon(QIcon(resource_path(ICON_REFRESH)))
        self.btn_save.setIcon(QIcon(resource_path(ICON_SAVE)))
        self.btn_delete.setIcon(QIcon(resource_path(ICON_DELETE)))

        for btn in (self.btn_refresh, self.btn_save, self.btn_delete):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                        "QPushButton::icon { margin-right: 10px; }",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: #FFFFFF; }}",
                    ]
                )
            )

        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        self.btn_save.clicked.connect(self.save_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        self.label_total = QLabel(text or "Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self.label_total.setFont(_mk_font_normal())

        layout.addWidget(self.btn_refresh)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_delete)
        layout.addWidget(self.label_total)
        layout.addStretch(1)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainContent1(QWidget):
    """Form khai báo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(380)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Row 1: Mã / Mô tả / Kiểu sắp xếp (1 cột, mỗi dòng label + input)
        row1 = QWidget(self)
        row1_layout = QVBoxLayout(row1)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(10)

        _TOP_LABEL_W = 120

        def _mk_row(label: str) -> QHBoxLayout:
            w = QWidget(row1)
            l = QHBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(8)
            lb = _mk_label(label)
            lb.setFixedWidth(_TOP_LABEL_W)
            l.addWidget(lb, 0)
            row1_layout.addWidget(w)
            return l

        l_code = _mk_row("Mã")
        self.inp_code = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
        self.inp_code.setFixedWidth(250)
        l_code.addWidget(self.inp_code, 0)
        l_code.addStretch(1)

        l_desc = _mk_row("Mô tả")
        self.inp_desc = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
        self.inp_desc.setFixedWidth(250)
        l_desc.addWidget(self.inp_desc, 0)
        l_desc.addStretch(1)

        l_sort = _mk_row("Kiểu sắp xếp")
        self.cbo_sort_type = _mk_combo(self, INPUT_HEIGHT_DEFAULT)
        self.cbo_sort_type.setFixedWidth(700)
        for label, value in DECLARE_TIME_IN_OUT_MODE_OPTIONS:
            self.cbo_sort_type.addItem(label, value)
        l_sort.addWidget(self.cbo_sort_type, 0)
        l_sort.addStretch(1)

        # Group: Thông số chung
        group = _mk_group_box("Thông số chung", self)
        g_layout = QVBoxLayout(group)
        g_layout.setContentsMargins(10, 14, 10, 10)
        g_layout.setSpacing(10)

        top = QWidget(group)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.setSpacing(20)

        # Left side
        left = QWidget(top)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(10)

        _LEFT_LABEL_W = 330

        def _mk_minute_row(label: str) -> QLineEdit:
            row = QWidget(group)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            lb = _mk_label(label)
            lb.setFixedWidth(_LEFT_LABEL_W)
            rl.addWidget(lb, 0)
            inp = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
            inp.setValidator(QIntValidator(0, 999999, inp))
            inp.setPlaceholderText("phút")
            inp.setFixedWidth(160)
            rl.addWidget(inp, 0)
            rl.addStretch(1)
            left_l.addWidget(row)
            return inp

        self.inp_min_between_in_out = _mk_minute_row(
            "Thời gian nhỏ nhất giữa giờ Vào/Ra"
        )
        self.inp_max_between_in_out = _mk_minute_row(
            "Thời gian lớn nhất giữa giờ Vào/Ra"
        )
        self.inp_gap_between_pairs = _mk_minute_row(
            "Thời gian cho phép giữa 2 cặp ra vào"
        )

        # Right side
        right = QWidget(top)
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(10)

        _RIGHT_LABEL_W = 220

        def _mk_int_row(label: str, default: str | None = None) -> QLineEdit:
            row = QWidget(group)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            lb = _mk_label(label)
            lb.setFixedWidth(_RIGHT_LABEL_W)
            rl.addWidget(lb, 0)
            inp = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
            inp.setValidator(QIntValidator(0, 999999, inp))
            inp.setFixedWidth(160)
            if default is not None:
                inp.setText(default)
            rl.addWidget(inp, 0)
            rl.addStretch(1)
            right_l.addWidget(row)
            return inp

        def _mk_time_row(label: str) -> QLineEdit:
            row = QWidget(group)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(8)
            lb = _mk_label(label)
            lb.setFixedWidth(_RIGHT_LABEL_W)
            rl.addWidget(lb, 0)
            inp = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
            inp.setPlaceholderText("HH:MM")
            inp.setFixedWidth(160)
            rl.addWidget(inp, 0)
            rl.addStretch(1)
            right_l.addWidget(row)
            return inp

        self.inp_cycle_days = _mk_int_row("Số ngày chu trình", default="0")
        self.inp_cycle_end_time = _mk_time_row("Thời gian kết thúc chu trình")

        def _normalize_time_text(le: QLineEdit) -> None:
            raw = str(le.text() or "").strip()
            if not raw:
                return
            if ":" in raw:
                parts = [p.strip() for p in raw.split(":")]
                if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                    try:
                        hh = int(parts[0])
                        mm = int(parts[1])
                        if 0 <= hh <= 23 and 0 <= mm <= 59:
                            le.setText(f"{hh:02d}:{mm:02d}")
                    except Exception:
                        return
                return

            digits = "".join([c for c in raw if c.isdigit()])
            if not digits:
                return
            try:
                if len(digits) == 4:
                    hh = int(digits[:2])
                    mm = int(digits[2:])
                elif len(digits) == 3:
                    hh = int(digits[:1])
                    mm = int(digits[1:])
                elif len(digits) in (1, 2):
                    hh = int(digits)
                    mm = 0
                else:
                    return
                if 0 <= hh <= 23 and 0 <= mm <= 59:
                    le.setText(f"{hh:02d}:{mm:02d}")
            except Exception:
                return

        self.inp_cycle_end_time.editingFinished.connect(
            lambda: _normalize_time_text(self.inp_cycle_end_time)
        )

        top_l.addWidget(left, 1)
        top_l.addWidget(right, 1)

        # Bottom: checkbox + time range (trên cùng 1 hàng, trái -> phải)
        bottom = QWidget(group)
        b = QHBoxLayout(bottom)
        b.setContentsMargins(0, 0, 0, 0)
        b.setSpacing(10)

        self.chk_remove_prev_night = QCheckBox(bottom)
        self.chk_remove_prev_night.setFont(_mk_font_normal())
        self.chk_remove_prev_night.setStyleSheet(
            "\n".join(
                [
                    f"QCheckBox {{ color: {COLOR_TEXT_PRIMARY}; }}",
                    "QCheckBox::indicator { width: 0px; height: 0px; }",
                ]
            )
        )

        base = "Loại bỏ ca đêm trước 1 ngày so với ngày bắt đầu tính công"
        _apply_chk_text = lambda: self.chk_remove_prev_night.setText(
            f"✅ {base}" if self.chk_remove_prev_night.isChecked() else f"❌ {base}"
        )
        self.chk_remove_prev_night.stateChanged.connect(
            lambda _=None: _apply_chk_text()
        )
        _apply_chk_text()

        self.inp_calc_from = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
        self.inp_calc_from.setPlaceholderText("HH:MM")
        self.inp_calc_from.setFixedWidth(120)

        self.inp_calc_to = _mk_line_edit(self, INPUT_HEIGHT_DEFAULT)
        self.inp_calc_to.setPlaceholderText("HH:MM")
        self.inp_calc_to.setFixedWidth(120)

        self.inp_calc_from.editingFinished.connect(
            lambda: _normalize_time_text(self.inp_calc_from)
        )
        self.inp_calc_to.editingFinished.connect(
            lambda: _normalize_time_text(self.inp_calc_to)
        )

        b.addWidget(self.chk_remove_prev_night, 0)
        b.addSpacing(10)
        b.addWidget(_mk_label("Từ"), 0)
        b.addWidget(self.inp_calc_from, 0)
        b.addWidget(_mk_label("Đến"), 0)
        b.addWidget(self.inp_calc_to, 0)
        b.addStretch(1)

        g_layout.addWidget(top)
        g_layout.addWidget(bottom)

        root.addWidget(row1)
        root.addWidget(group)

    def clear_form(self) -> None:
        self.inp_code.setText("")
        self.inp_desc.setText("")
        self.cbo_sort_type.setCurrentIndex(0)

        for inp in (
            self.inp_min_between_in_out,
            self.inp_max_between_in_out,
            self.inp_gap_between_pairs,
            self.inp_cycle_end_time,
            self.inp_calc_from,
            self.inp_calc_to,
        ):
            inp.setText("")

        # Default not empty
        self.inp_cycle_days.setText("0")
        self.chk_remove_prev_night.setChecked(False)

    def get_form_data(self) -> dict:
        return {
            "code": self.inp_code.text(),
            "description": self.inp_desc.text(),
            "sort_type": self.cbo_sort_type.currentData(),
            "min_between_in_out": self.inp_min_between_in_out.text(),
            "max_between_in_out": self.inp_max_between_in_out.text(),
            "gap_between_pairs": self.inp_gap_between_pairs.text(),
            "cycle_days": self.inp_cycle_days.text(),
            "cycle_end_time": self.inp_cycle_end_time.text(),
            "remove_prev_night": self.chk_remove_prev_night.isChecked(),
            "calc_from": self.inp_calc_from.text(),
            "calc_to": self.inp_calc_to.text(),
        }

    def set_form(self, data: dict) -> None:
        self.inp_code.setText(str(data.get("code") or ""))
        self.inp_desc.setText(str(data.get("description") or ""))

        # sort_type
        st = data.get("sort_type")
        idx = 0
        for i in range(self.cbo_sort_type.count()):
            if self.cbo_sort_type.itemData(i) == st:
                idx = i
                break
        self.cbo_sort_type.setCurrentIndex(idx)

        self.inp_min_between_in_out.setText(str(data.get("min_between_in_out") or ""))
        self.inp_max_between_in_out.setText(str(data.get("max_between_in_out") or ""))
        self.inp_gap_between_pairs.setText(str(data.get("gap_between_pairs") or ""))
        cd = data.get("cycle_days")
        self.inp_cycle_days.setText(
            "0" if cd is None or str(cd).strip() == "" else str(cd)
        )
        self.inp_cycle_end_time.setText(str(data.get("cycle_end_time") or ""))
        self.chk_remove_prev_night.setChecked(bool(data.get("remove_prev_night")))
        self.inp_calc_from.setText(str(data.get("calc_from") or ""))
        self.inp_calc_to.setText(str(data.get("calc_to") or ""))


class MainContent2(QWidget):
    """Bảng danh sách cấu hình."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(168)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 0, 12, 12)
        root.setSpacing(0)

        self.table = QTableWidget(self)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "MÃ", "Mô tả", "Kiểu sắp xếp"])
        self.table.setColumnHidden(0, True)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

        # Set kích thước cột ban đầu (có thể kéo co giãn)
        # ID (ẩn)
        self.table.setColumnWidth(0, 0)
        # MÃ
        self.table.setColumnWidth(1, 150)
        # Mô tả
        self.table.setColumnWidth(2, 300)
        # Kiểu sắp xếp
        self.table.setColumnWidth(3, 400)

        # Style giống các bảng khác
        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QTableWidget::item {{ padding-left: 8px; padding-right: 8px; height: {ROW_HEIGHT}px; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border-radius: 0px; border: 0px; }}",
                ]
            )
        )

        root.addWidget(self.table, 1)

    def set_rows(self, rows: list[tuple]) -> None:
        self.table.setRowCount(0)
        for r_idx, r in enumerate(rows or []):
            try:
                if len(r) >= 4:
                    rec_id, code, desc, sort_type = r[0], r[1], r[2], r[3]
                else:
                    rec_id, code, desc = r
                    sort_type = ""
            except Exception:
                continue
            self.table.insertRow(r_idx)

            it_id = QTableWidgetItem(str(rec_id))
            it_code = QTableWidgetItem(str(code or ""))
            it_desc = QTableWidgetItem(str(desc or ""))
            it_sort = QTableWidgetItem(str(sort_type or ""))

            it_id.setFlags(it_id.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it_code.setFlags(it_code.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it_desc.setFlags(it_desc.flags() & ~Qt.ItemFlag.ItemIsEditable)
            it_sort.setFlags(it_sort.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(r_idx, 0, it_id)
            self.table.setItem(r_idx, 1, it_code)
            self.table.setItem(r_idx, 2, it_desc)
            self.table.setItem(r_idx, 3, it_sort)

    def clear_selection(self) -> None:
        self.table.clearSelection()

    def get_selected_id(self) -> int | None:
        items = self.table.selectedItems() or []
        if not items:
            return None
        it = self.table.item(items[0].row(), 0)
        if it is None:
            return None
        try:
            return int(str(it.text()).strip())
        except Exception:
            return None

    def select_by_id(self, rec_id: int) -> None:
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it is None:
                continue
            try:
                if int(str(it.text()).strip()) == int(rec_id):
                    self.table.selectRow(r)
                    return
            except Exception:
                continue


class DeclareTimeView(QWidget):
    """Gói 2 phần nội dung vào 1 widget (dùng trong Container)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.setChildrenCollapsible(False)

        self.content1 = MainContent1(splitter)
        self.content2 = MainContent2(splitter)
        splitter.addWidget(self.content1)
        splitter.addWidget(self.content2)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        try:
            splitter.setSizes([380, 168])
        except Exception:
            pass

        root.addWidget(splitter, 1)
