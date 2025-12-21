"""ui.dialog.weekend_dialog

Dialog "Chọn ngày Cuối tuần".

Yêu cầu:
- Bảng gồm 3 cột: ID (ẩn), Thứ, Cuối tuần (checkbox)
- Thứ hiển thị cố định từ Thứ 2 đến Chủ nhật
- Hiển thị cửa sổ giữa màn hình (controller thực hiện)
- Không dùng QMessageBox
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    BG_TITLE_2_HEIGHT,
    COLOR_BG_HEADER,
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    UI_FONT,
)


class WeekendDialog(QDialog):
    DAY_NAMES: list[str] = [
        "Thứ 2",
        "Thứ 3",
        "Thứ 4",
        "Thứ 5",
        "Thứ 6",
        "Thứ 7",
        "Chủ nhật",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_row: int | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Chọn ngày Cuối tuần")
        self.setFixedSize(300, 425)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_semibold.setWeight(QFont.Weight.DemiBold)

        # Table
        self.table = QTableWidget(self)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Thứ", "Cuối tuần"])
        self.table.setColumnHidden(0, True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsMovable(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFont(font_semibold)

        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {BG_TITLE_2_HEIGHT}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        # Hover cả row (kể cả cột có widget)
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.viewport().installEventFilter(self)

        # Cấu hình kích thước cột
        header.setSectionResizeMode(0, header.ResizeMode.Fixed)
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)  # Thứ
        header.setSectionResizeMode(2, header.ResizeMode.Fixed)  # Cuối tuần
        self.table.setColumnWidth(2, 140)

        # Rows Thứ 2..Chủ nhật
        self.table.setRowCount(len(self.DAY_NAMES))
        for i, day in enumerate(self.DAY_NAMES):
            self._init_row(i, day, font_normal)

        # Status
        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        # Buttons
        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_exit = QPushButton("Thoát")
        self.btn_exit.setFont(font_button)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setFixedHeight(36)
        self.btn_exit.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_CANCEL}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_CANCEL_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_save.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_exit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn_layout.addWidget(self.btn_save, 1)
        btn_layout.addWidget(self.btn_exit, 1)

        root.addWidget(self.table, 1)
        root.addWidget(self.label_status)
        root.addWidget(btn_row)

        self.btn_exit.clicked.connect(self.reject)

    def _mk_center_widget(self, w: QWidget) -> QWidget:
        wrap = QWidget(self.table)
        wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(w)
        lay.addStretch(1)
        return wrap

    def _init_row(self, row: int, day_name: str, font: QFont) -> None:
        # ID hidden
        id_item = QTableWidgetItem("")
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setFont(font)
        self.table.setItem(row, 0, id_item)

        day_item = QTableWidgetItem(day_name)
        day_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        day_item.setFont(font)
        self.table.setItem(row, 1, day_item)

        # Placeholder item for hover background under widget
        item = QTableWidgetItem("")
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setFont(font)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, item)

        chk = QCheckBox("")
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.table.setCellWidget(row, 2, self._mk_center_widget(chk))

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def set_rows(self, rows_by_day: dict[str, dict]) -> None:
        for row in range(self.table.rowCount()):
            day_item = self.table.item(row, 1)
            day = (day_item.text() if day_item is not None else "").strip()
            data = rows_by_day.get(day) or {}

            id_item = self.table.item(row, 0)
            if id_item is not None:
                id_item.setText(
                    "" if data.get("id") is None else str(int(data.get("id")))
                )

            wrap = self.table.cellWidget(row, 2)
            chk = wrap.findChild(QCheckBox) if wrap is not None else None
            if chk is not None:
                chk.setChecked(bool(int(data.get("is_weekend") or 0)))

    def collect_rows(self) -> list[dict]:
        items: list[dict] = []
        for row in range(self.table.rowCount()):
            day_item = self.table.item(row, 1)
            day = (day_item.text() if day_item is not None else "").strip()

            id_item = self.table.item(row, 0)
            id_val = None
            if id_item is not None and (id_item.text() or "").strip():
                try:
                    id_val = int(id_item.text())
                except Exception:
                    id_val = None

            wrap = self.table.cellWidget(row, 2)
            chk = wrap.findChild(QCheckBox) if wrap is not None else None

            items.append(
                {
                    "id": id_val,
                    "day_name": day,
                    "is_weekend": bool(chk.isChecked()) if chk is not None else False,
                }
            )
        return items

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Type.Leave:
            self._clear_row_hover()
            return False

        return super().eventFilter(obj, event)

    def _clear_row_hover(self) -> None:
        if self._hover_row is None:
            return

        row = self._hover_row
        self._hover_row = None
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item is not None:
                item.setData(Qt.ItemDataRole.BackgroundRole, None)

    def _on_cell_entered(self, row: int, _col: int) -> None:
        if self._hover_row == row:
            return

        self._clear_row_hover()
        self._hover_row = row

        brush = QBrush(QColor(HOVER_ROW_BG_COLOR))
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item is not None:
                item.setBackground(brush)
