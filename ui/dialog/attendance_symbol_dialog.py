"""ui.dialog.attendance_symbol_dialog Dialog cấu hình "Ký hiệu Chấm công".

Lưu ý hiệu năng:
- Không load DB trong __init__ (tránh treo UI khi DB chậm/không kết nối).
- Load/Save chạy nền bằng BackgroundTaskRunner.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, Qt, QTimer
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
    COLOR_BG_HEADER,
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    ODD_ROW_BG_COLOR,
    EVEN_ROW_BG_COLOR,
    ROW_HEIGHT,
    UI_FONT,
)
from core.attendance_symbol_bus import attendance_symbol_bus
from core.threads import BackgroundTaskRunner

if TYPE_CHECKING:
    from services.attendance_symbol_services import AttendanceSymbolService


class AttendanceSymbolDialog(QDialog):
    def __init__(
        self, parent=None, service: AttendanceSymbolService | None = None
    ) -> None:
        super().__init__(parent)
        self._service: AttendanceSymbolService | None = service
        self._load_runner = BackgroundTaskRunner(self, name="attendance_symbol_load")
        self._save_runner = BackgroundTaskRunner(self, name="attendance_symbol_save")
        self._hover_row: int | None = None
        self._init_ui()
        # Defer load so the dialog can paint immediately.
        self.set_status("Đang tải...", ok=True)
        try:
            QTimer.singleShot(0, self._load_async)
        except Exception:
            self._load_async()

    def _get_service(self) -> AttendanceSymbolService:
        if self._service is None:
            from services.attendance_symbol_services import AttendanceSymbolService

            self._service = AttendanceSymbolService()
        return self._service

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Ký hiệu Chấm công")
        self.setFixedSize(900, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)
        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)
        font_header = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_header.setWeight(QFont.Weight.DemiBold)

        self.table = QTableWidget(self)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Mã", "Mô tả", "Ký hiệu", "Hiện"])
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
        header.setFont(font_header)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        self.table.setStyleSheet(
            "\n".join(
                [
                    f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; border: 1px solid {COLOR_BORDER}; }}",
                    f"QHeaderView::section {{ background-color: {INPUT_COLOR_BG}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                    f"QHeaderView::section:first {{ border-left: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableCornerButton::section {{ background-color: {INPUT_COLOR_BG}; border: 1px solid {GRID_LINES_COLOR}; }}",
                    f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.viewport().installEventFilter(self)

        header.setSectionResizeMode(0, header.ResizeMode.Fixed)
        header.setSectionResizeMode(1, header.ResizeMode.Fixed)
        header.setSectionResizeMode(2, header.ResizeMode.Stretch)
        header.setSectionResizeMode(3, header.ResizeMode.Fixed)
        header.setSectionResizeMode(4, header.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 70)  # Mã
        self.table.setColumnWidth(3, 140)  # Ký hiệu
        self.table.setColumnWidth(4, 120)  # Hiện

        # Các dòng cố định C01..C10
        row_defs: list[tuple[str, str]] = [
            ("C01", "Ký hiệu đi trễ"),
            ("C02", "Ký hiệu về sớm"),
            ("C03", "Ký hiệu đúng giờ"),
            ("C04", "Ký hiệu tăng ca"),
            ("C05", "Ký hiệu thiếu giờ ra"),
            ("C06", "Ký hiệu thiếu giờ vào"),
            ("C07", "Ký hiệu vắng (mặc định không chấm công)"),
            ("C08", "Ký hiệu đúng giờ ca có qua đêm"),
            ("C09", "Ký hiệu ngày không xếp ca"),
            ("C10", "Ký hiệu nghỉ lễ"),
        ]
        self.table.setRowCount(len(row_defs))
        for i, (code, desc) in enumerate(row_defs):
            self._init_row(i, code=code, description=desc, font=font_normal)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setAutoDefault(True)
        self.btn_save.setDefault(True)
        self.btn_save.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_cancel = QPushButton("Thoát")
        self.btn_cancel.setFont(font_button)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setStyleSheet(
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
        self.btn_cancel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        btn_layout.addWidget(self.btn_save, 1)
        btn_layout.addWidget(self.btn_cancel, 1)

        root.addWidget(self.table, 1)
        root.addWidget(self.label_status)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._on_save)

    def _mk_line_edit(
        self, font: QFont, placeholder: str = "", row: int = -1
    ) -> QLineEdit:
        inp = QLineEdit()
        inp.setFont(font)
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
        # Thêm event filter để xử lý click
        if row >= 0:
            original_mouse_press = inp.mousePressEvent

            def _mouse_press_event(e, r=row, w=inp, original=original_mouse_press):
                self._on_lineedit_clicked(r, e, w)
                original(e)

            inp.mousePressEvent = _mouse_press_event
        return inp

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

    def _init_row(self, row: int, code: str, description: str, font: QFont) -> None:
        id_item = QTableWidgetItem("")
        id_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        id_item.setFont(font)
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, id_item)

        code_item = QTableWidgetItem(code)
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        code_item.setFont(font)
        code_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 1, code_item)

        # Placeholder items để hover tô đủ cả hàng (cellWidget cần nền phía sau)
        for col in (2, 3, 4):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item.setFont(font)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        desc_inp = self._mk_line_edit(font, "Mô tả", row=row)
        desc_inp.setText(description)
        # Cột 2 (Mô tả) không cho phép sửa
        desc_inp.setReadOnly(True)
        desc_inp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        desc_inp.setCursor(Qt.CursorShape.ArrowCursor)

        sym_inp = self._mk_line_edit(font, "(ví dụ: T)", row=row)
        # Khóa ký hiệu mặc định, chỉ mở khi user click vào row
        sym_inp.setReadOnly(True)
        sym_inp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sym_inp.setCursor(Qt.CursorShape.ArrowCursor)

        chk = QCheckBox("")
        chk.setCursor(Qt.CursorShape.PointingHandCursor)
        chk.setChecked(True)
        self._setup_emoji_checkbox(chk)

        self.table.setCellWidget(row, 2, desc_inp)
        self.table.setCellWidget(row, 3, sym_inp)
        self.table.setCellWidget(row, 4, self._mk_center_widget(chk))

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

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Khi click vào row, cho phép chỉnh sửa cột Ký hiệu"""
        sym_inp = self.table.cellWidget(row, 3)
        if isinstance(sym_inp, QLineEdit):
            sym_inp.setReadOnly(False)
            sym_inp.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            sym_inp.setCursor(Qt.CursorShape.IBeamCursor)
            # Nếu click vào cột ký hiệu, tự động focus và select text
            if col == 3:
                sym_inp.setFocus()
                sym_inp.selectAll()

    def _on_lineedit_clicked(self, row: int, event, clicked_widget: QWidget) -> None:
        """Xử lý khi click vào QLineEdit trong bảng"""
        # Mở khóa cột ký hiệu cho row này
        sym_inp = self.table.cellWidget(row, 3)
        if isinstance(sym_inp, QLineEdit):
            sym_inp.setReadOnly(False)
            sym_inp.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            sym_inp.setCursor(Qt.CursorShape.IBeamCursor)
            # Nếu click vào chính cột ký hiệu, focus và select
            if clicked_widget is sym_inp:
                QTimer.singleShot(0, sym_inp.setFocus)
                QTimer.singleShot(10, sym_inp.selectAll)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._center_dialog()
        # Tránh tự focus vào QLineEdit trong bảng ngay khi mở dialog
        QTimer.singleShot(0, self._ensure_no_input_autofocus)

    def _ensure_no_input_autofocus(self) -> None:
        # Clear focus/selection from any input
        for row in range(self.table.rowCount()):
            for col in (2, 3):
                w = self.table.cellWidget(row, col)
                if isinstance(w, QLineEdit):
                    w.deselect()
                    w.clearFocus()
        # Focus a non-input widget (button) instead
        if hasattr(self, "btn_save") and self.btn_save is not None:
            self.btn_save.setFocus(Qt.FocusReason.OtherFocusReason)

    def _center_dialog(self) -> None:
        # Center on parent if possible; otherwise center on screen
        parent = self.parentWidget()
        if parent is not None:
            pg = parent.frameGeometry()
            center = pg.center()
            fg = self.frameGeometry()
            fg.moveCenter(center)
            self.move(fg.topLeft())
            return
        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        fg = self.frameGeometry()
        fg.moveCenter(geo.center())
        self.move(fg.topLeft())

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def _apply_loaded(self, rows_by_code: dict[str, dict]) -> None:
        for row in range(self.table.rowCount()):
            code_item = self.table.item(row, 1)
            code = (code_item.text() if code_item is not None else "").strip()
            data = rows_by_code.get(code) or {}

            id_item = self.table.item(row, 0)
            if id_item is not None:
                id_item.setText(
                    "" if data.get("id") is None else str(int(data.get("id")))
                )

            desc = self.table.cellWidget(row, 2)
            sym = self.table.cellWidget(row, 3)
            vis_wrap = self.table.cellWidget(row, 4)

            if isinstance(desc, QLineEdit):
                desc.setText(str(data.get("description") or desc.text() or ""))
            if isinstance(sym, QLineEdit):
                sym.setText(str(data.get("symbol") or ""))
            vis_chk = vis_wrap.findChild(QCheckBox) if vis_wrap is not None else None
            if vis_chk is not None:
                vis_chk.setChecked(bool(int(data.get("is_visible") or 0)))

    def _load_async(self) -> None:
        def _fn() -> object:
            svc = self._get_service()
            return svc.list_rows_by_code()

        def _ok(result: object) -> None:
            rows_by_code = result if isinstance(result, dict) else {}
            self._apply_loaded(rows_by_code)
            self.set_status("", ok=True)

        def _err(msg: str) -> None:
            # Không chặn UI nếu DB lỗi; chỉ thông báo.
            self.set_status(str(msg or "Không thể tải dữ liệu"), ok=False)

        try:
            self._load_runner.run(fn=_fn, on_success=_ok, on_error=_err)
        except Exception as e:
            self.set_status(str(e), ok=False)

    def _collect_rows(self) -> list[dict]:
        items: list[dict] = []
        for row in range(self.table.rowCount()):
            code_item = self.table.item(row, 1)
            code = (code_item.text() if code_item is not None else "").strip()

            desc_w = self.table.cellWidget(row, 2)
            sym_w = self.table.cellWidget(row, 3)
            vis_wrap = self.table.cellWidget(row, 4)

            description = (
                desc_w.text() if isinstance(desc_w, QLineEdit) else ""
            ).strip()
            symbol = (sym_w.text() if isinstance(sym_w, QLineEdit) else "").strip()

            vis_chk = vis_wrap.findChild(QCheckBox) if vis_wrap is not None else None

            items.append(
                {
                    "code": code,
                    "description": description,
                    "symbol": symbol,
                    "is_visible": (
                        bool(vis_chk.isChecked()) if vis_chk is not None else True
                    ),
                }
            )
        return items

    def _on_save(self) -> None:
        rows = self._collect_rows()

        # Disable to prevent double-submit
        try:
            self.btn_save.setEnabled(False)
            self.btn_cancel.setEnabled(False)
        except Exception:
            pass

        self.set_status("Đang lưu...", ok=True)

        def _fn() -> object:
            svc = self._get_service()
            return svc.save_rows(rows)

        def _ok(result: object) -> None:
            ok = False
            msg = ""
            if isinstance(result, tuple) and len(result) >= 2:
                ok = bool(result[0])
                msg = str(result[1] or "")
            self.set_status(msg, ok=ok)
            try:
                self.btn_save.setEnabled(True)
                self.btn_cancel.setEnabled(True)
            except Exception:
                pass
            if ok:
                try:
                    attendance_symbol_bus.changed.emit()
                except Exception:
                    pass

        def _err(msg: str) -> None:
            self.set_status(str(msg or "Không thể lưu dữ liệu"), ok=False)
            try:
                self.btn_save.setEnabled(True)
                self.btn_cancel.setEnabled(True)
            except Exception:
                pass

        try:
            self._save_runner.run(fn=_fn, on_success=_ok, on_error=_err)
        except Exception as e:
            _err(str(e))
