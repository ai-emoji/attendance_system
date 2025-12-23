"""ui.dialog.absence_symbol_dialog

Dialog "Ký hiệu Vắng".

Yêu cầu:
- Bảng gồm: ID (ẩn), Mã, Mô tả (input), Ký hiệu (input), Sử dụng (checkbox), Tính công (checkbox)
- Mã hiển thị từ A01 đến A15
- Nút Lưu và Thoát nằm dưới cùng
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
    QLineEdit,
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
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    UI_FONT,
)


class AbsenceSymbolDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_row: int | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Ký hiệu Vắng")
        self.setFixedSize(900, 620)

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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Mã", "Mô tả", "Ký hiệu", "Sử dụng", "Tính công"]
        )
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
        # Không stretch cột cuối để giữ W của 2 cột checkbox bằng nhau
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
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)  # Mô tả
        header.setSectionResizeMode(3, header.ResizeMode.Fixed)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        header.setSectionResizeMode(5, header.ResizeMode.Fixed)

        self.table.setColumnWidth(1, 70)  # Mã
        self.table.setColumnWidth(3, 140)  # Ký hiệu
        self.table.setColumnWidth(4, 120)  # Sử dụng
        self.table.setColumnWidth(5, 120)  # Tính công

        # Tạo 15 dòng A01..A15
        self.table.setRowCount(15)
        for i in range(15):
            code = f"A{i+1:02d}"
            self._init_row(i, code, font_normal)

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

    def _mk_line_edit(self, placeholder: str = "") -> QLineEdit:
        inp = QLineEdit()
        inp.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        inp.setPlaceholderText(placeholder)
        inp.setCursor(Qt.CursorShape.IBeamCursor)
        inp.setStyleSheet(
            "\n".join(
                [
                    "QLineEdit { background: transparent; border: none; padding: 0 8px; border-radius: 0px; }",
                    "QLineEdit:focus { border: none; }",
                ]
            )
        )
        return inp

    def _format_description_text(self, text: str) -> str:
        # Viết hoa chữ cái đầu mỗi từ, giữ nguyên phần còn lại (không ép lower)
        out: list[str] = []
        cap_next = True
        for ch in text:
            if ch.isspace():
                cap_next = True
                out.append(ch)
                continue
            if cap_next:
                out.append(ch.upper())
                cap_next = False
            else:
                out.append(ch)
        return "".join(out)

    def _format_symbol_text(self, text: str) -> str:
        # Chỉ viết hoa ký tự đầu tiên (bỏ qua khoảng trắng đầu), phần sau giữ nguyên
        out: list[str] = []
        done = False
        for ch in text:
            if not done and not ch.isspace():
                out.append(ch.upper())
                done = True
            else:
                out.append(ch)
        return "".join(out)

    def _apply_formatted_text(self, inp: QLineEdit, formatted: str) -> None:
        current = inp.text()
        if formatted == current:
            return

        cursor_pos = inp.cursorPosition()
        inp.blockSignals(True)
        inp.setText(formatted)
        inp.blockSignals(False)
        inp.setCursorPosition(min(cursor_pos, len(formatted)))

    def _mk_center_checkbox(self) -> QCheckBox:
        chk = QCheckBox("")
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_emoji_checkbox(chk)
        return chk

    @staticmethod
    def _emoji_checked(checked: bool) -> str:
        return "✅" if checked else "❌"

    def _setup_emoji_checkbox(self, chk: QCheckBox) -> None:
        # Hide old checkbox indicator, show emoji only
        chk.setStyleSheet(
            "\n".join(
                [
                    "QCheckBox { spacing: 0px; padding: 0px; margin: 0px; background: transparent; }",
                    "QCheckBox::indicator { image: none; width: 0px; height: 0px; }",
                ]
            )
        )
        chk.setText(self._emoji_checked(chk.isChecked()))
        chk.toggled.connect(lambda v, c=chk: c.setText(self._emoji_checked(v)))

    def _mk_center_widget(self, w: QWidget) -> QWidget:
        wrap = QWidget(self.table)
        wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(w)
        lay.addStretch(1)
        return wrap

    def _init_row(self, row: int, code: str, font: QFont) -> None:
        # ID hidden
        id_item = QTableWidgetItem("")
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setFont(font)
        self.table.setItem(row, 0, id_item)

        code_item = QTableWidgetItem(code)
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        code_item.setFont(font)
        self.table.setItem(row, 1, code_item)

        # Placeholder items để hover tô đủ cả hàng (cellWidget cần nền phía sau)
        for col in (2, 3, 4, 5):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFont(font)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        desc = self._mk_line_edit("Mô tả")
        sym = self._mk_line_edit("Ký hiệu")
        desc.setFont(font)
        sym.setFont(font)

        desc.textEdited.connect(
            lambda text, w=desc: self._apply_formatted_text(
                w, self._format_description_text(text)
            )
        )
        sym.textEdited.connect(
            lambda text, w=sym: self._apply_formatted_text(
                w, self._format_symbol_text(text)
            )
        )
        used = self._mk_center_checkbox()
        paid = self._mk_center_checkbox()

        self.table.setCellWidget(row, 2, desc)
        self.table.setCellWidget(row, 3, sym)
        self.table.setCellWidget(row, 4, self._mk_center_widget(used))
        self.table.setCellWidget(row, 5, self._mk_center_widget(paid))

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

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def set_rows(self, rows_by_code: dict[str, dict]) -> None:
        for row in range(self.table.rowCount()):
            code_item = self.table.item(row, 1)
            code = (code_item.text() if code_item is not None else "").strip()
            data = rows_by_code.get(code) or {}

            # ID
            id_item = self.table.item(row, 0)
            if id_item is not None:
                id_item.setText(
                    "" if data.get("id") is None else str(int(data.get("id")))
                )

            desc = self.table.cellWidget(row, 2)
            sym = self.table.cellWidget(row, 3)
            used_wrap = self.table.cellWidget(row, 4)
            paid_wrap = self.table.cellWidget(row, 5)

            if isinstance(desc, QLineEdit):
                desc.setText(str(data.get("description") or ""))
            if isinstance(sym, QLineEdit):
                sym.setText(str(data.get("symbol") or ""))

            used_chk = used_wrap.findChild(QCheckBox) if used_wrap is not None else None
            paid_chk = paid_wrap.findChild(QCheckBox) if paid_wrap is not None else None

            if used_chk is not None:
                used_chk.setChecked(bool(int(data.get("is_used") or 0)))
            if paid_chk is not None:
                paid_chk.setChecked(bool(int(data.get("is_paid") or 0)))

    def collect_rows(self) -> list[dict]:
        items: list[dict] = []
        for row in range(self.table.rowCount()):
            code_item = self.table.item(row, 1)
            code = (code_item.text() if code_item is not None else "").strip()

            desc_w = self.table.cellWidget(row, 2)
            sym_w = self.table.cellWidget(row, 3)
            used_wrap = self.table.cellWidget(row, 4)
            paid_wrap = self.table.cellWidget(row, 5)

            description = (
                desc_w.text() if isinstance(desc_w, QLineEdit) else ""
            ).strip()
            symbol = (sym_w.text() if isinstance(sym_w, QLineEdit) else "").strip()

            used_chk = used_wrap.findChild(QCheckBox) if used_wrap is not None else None
            paid_chk = paid_wrap.findChild(QCheckBox) if paid_wrap is not None else None

            items.append(
                {
                    "code": code,
                    "description": description,
                    "symbol": symbol,
                    "is_used": (
                        bool(used_chk.isChecked()) if used_chk is not None else False
                    ),
                    "is_paid": (
                        bool(paid_chk.isChecked()) if paid_chk is not None else False
                    ),
                }
            )
        return items
