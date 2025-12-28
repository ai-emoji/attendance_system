"""ui.dialog.import_shift_attendance_dialog

Dialog "Import dữ liệu chấm công" (màn Chấm công Theo ca).

UI-only:
- Input: đường dẫn file Excel
- Buttons: Xem mẫu, Xem thông tin, Cập nhập vào CSDL
- Bảng preview: hiển thị đủ cột như MainContent2 (Shift Attendance)
- Dòng trạng thái

Nghiệp vụ (đọc/ghi Excel/DB) nằm ở controller/services.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
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
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
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
    MAIN_CONTENT_BG_COLOR,
    ODD_ROW_BG_COLOR,
    ROW_HEIGHT,
    UI_FONT,
    resource_path,
)

from core.ui_settings import (
    get_last_save_dir,
    get_shift_attendance_table_ui,
    set_last_save_dir,
    ui_settings_bus,
)


def _setup_preview_table(
    table: QTableWidget,
    headers: list[str],
    *,
    column_widths: list[int] | None = None,
) -> None:
    # Avoid focus outline when user selects rows/cells.
    table.setFocusPolicy(Qt.NoFocus)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)

    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    table.setShowGrid(True)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    try:
        table.horizontalHeader().setStretchLastSection(False)
    except Exception:
        pass

    if column_widths:
        for idx, w in enumerate(column_widths[: len(headers)]):
            try:
                table.setColumnWidth(int(idx), int(w))
            except Exception:
                pass

    table.setStyleSheet(
        "\n".join(
            [
                f"QTableWidget {{ background-color: {ODD_ROW_BG_COLOR}; alternate-background-color: {EVEN_ROW_BG_COLOR}; gridline-color: {GRID_LINES_COLOR}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {COLOR_BORDER}; }}",
                f"QHeaderView::section {{ background-color: {INPUT_COLOR_BG}; color: {COLOR_TEXT_PRIMARY}; border: 1px solid {GRID_LINES_COLOR}; height: {ROW_HEIGHT}px; }}",
                f"QHeaderView::section:first {{ border-left: 1px solid {GRID_LINES_COLOR}; }}",
                f"QTableCornerButton::section {{ background-color: {INPUT_COLOR_BG}; border: 1px solid {GRID_LINES_COLOR}; }}",
                # Hover/Selected: use the same background and ensure it fills full cell with no rounded corners
                f"QTableWidget::item:hover {{ background-color: {HOVER_ROW_BG_COLOR}; border-radius: 0px; margin: 0px; }}",
                f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border-radius: 0px; margin: 0px; }}",
                f"QTableWidget::item:selected:hover {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border-radius: 0px; margin: 0px; }}",
                "QTableWidget::item { padding-left: 8px; padding-right: 8px; border-radius: 0px; margin: 0px; }",
                "QTableWidget::item:focus { outline: none; }",
                "QTableWidget:focus { outline: none; }",
            ]
        )
    )


class ImportShiftAttendanceDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._init_ui()

        # cache preview rows for controller usage
        self._preview_rows: list[dict] = []

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Import dữ liệu chấm công")
        self.setMinimumSize(1250, 720)
        self.resize(1250, 720)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        input_style = "\n".join(
            [
                f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )

        btn_style = "\n".join(
            [
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                "QPushButton::icon { margin-right: 10px; }",
                f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: #FFFFFF; }}",
            ]
        )

        top = QWidget(self)
        top_l = QHBoxLayout(top)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.setSpacing(8)

        self.input_excel_path = QLineEdit(self)
        self.input_excel_path.setFont(font_normal)
        self.input_excel_path.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_excel_path.setPlaceholderText("Nhập đường dẫn file Excel (*.xlsx)")
        self.input_excel_path.setStyleSheet(input_style)
        self.input_excel_path.setCursor(Qt.CursorShape.PointingHandCursor)
        self.input_excel_path.installEventFilter(self)

        self.btn_view_template = QPushButton("Xem mẫu", self)
        self.btn_view_template.setFont(font_button)
        self.btn_view_template.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.btn_view_template.setIcon(QIcon(resource_path("assets/images/excel.svg")))
        self.btn_view_template.setIconSize(QSize(18, 18))
        self.btn_view_template.setStyleSheet(btn_style)
        self.btn_view_template.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_view_info = QPushButton("Xem thông tin", self)
        self.btn_view_info.setFont(font_button)
        self.btn_view_info.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.btn_view_info.setIcon(QIcon(resource_path("assets/images/staff.svg")))
        self.btn_view_info.setIconSize(QSize(18, 18))
        self.btn_view_info.setStyleSheet(btn_style)
        self.btn_view_info.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_apply_db = QPushButton("Cập nhập vào CSDL", self)
        self.btn_apply_db.setFont(font_button)
        self.btn_apply_db.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.btn_apply_db.setIcon(QIcon(resource_path("assets/images/save.svg")))
        self.btn_apply_db.setIconSize(QSize(18, 18))
        self.btn_apply_db.setStyleSheet(btn_style)
        self.btn_apply_db.setCursor(Qt.CursorShape.PointingHandCursor)

        top_l.addWidget(self.input_excel_path, 1)
        top_l.addWidget(self.btn_view_template, 0)
        top_l.addWidget(self.btn_view_info, 0)
        top_l.addWidget(self.btn_apply_db, 0)

        self.table = QTableWidget(self)
        headers = [
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
            "Lịch NV",
        ]
        widths = [
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
            70,  # Trễ
            70,  # Sớm
            80,  # Giờ
            80,  # Công
            80,  # KH
            80,  # Giờ +
            80,  # Công +
            80,  # KH +
            70,  # TC1
            70,  # TC2
            70,  # TC3
            160,  # Lịch NV
        ]
        _setup_preview_table(self.table, headers, column_widths=widths)
        # Extra safety: ensure no focus rectangle on selection.
        try:
            self.table.setFocusPolicy(Qt.NoFocus)
        except Exception:
            pass
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Toggle emoji checkbox on click
        try:
            self.table.cellClicked.connect(self._on_cell_clicked)
        except Exception:
            pass

        # Apply UI settings (font/alignment) and keep in sync.
        self.apply_ui_settings()
        try:
            ui_settings_bus.changed.connect(self.apply_ui_settings)
        except Exception:
            pass

        bottom = QWidget(self)
        bottom_l = QHBoxLayout(bottom)
        bottom_l.setContentsMargins(0, 0, 0, 0)
        bottom_l.setSpacing(10)

        self.label_status = QLabel("", self)
        self.label_status.setFont(font_normal)
        self.label_status.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        bottom_l.addStretch(1)
        bottom_l.addWidget(self.label_status, 1)

        root.addWidget(top, 0)
        root.addWidget(self.table, 1)
        root.addWidget(bottom, 0)

        # Put one placeholder row so users see the full table structure.
        self._set_placeholder_rows()

    def apply_ui_settings(self) -> None:
        ui = get_shift_attendance_table_ui()

        def _to_qt_align(s: str) -> Qt.AlignmentFlag:
            v = str(s or "").strip().lower()
            if v == "right":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            if v == "center":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        body_font = QFont(UI_FONT, int(ui.font_size))
        if str(ui.font_weight or "normal").strip().lower() == "bold":
            body_font.setWeight(QFont.Weight.Bold)
        else:
            body_font.setWeight(QFont.Weight.Normal)

        header_font = QFont(UI_FONT, int(ui.header_font_size))
        if str(ui.header_font_weight or "bold").strip().lower() == "bold":
            header_font.setWeight(QFont.Weight.Bold)
        else:
            header_font.setWeight(QFont.Weight.Normal)

        # Columns for this preview table (include checkbox + stt in front).
        col_keys = [
            "check",
            "stt",
            "employee_code",
            "full_name",
            "date",
            "weekday",
            "in_1",
            "out_1",
            "in_2",
            "out_2",
            "in_3",
            "out_3",
            "late",
            "early",
            "hours",
            "work",
            "leave",
            "hours_plus",
            "work_plus",
            "leave_plus",
            "tc1",
            "tc2",
            "tc3",
            "schedule",
        ]

        # Header font: set both font and stylesheet to avoid QSS overriding.
        try:
            self.table.horizontalHeader().setFont(header_font)
            fw_num = 700 if header_font.weight() >= QFont.Weight.DemiBold else 400
            self.table.horizontalHeader().setStyleSheet(
                f"QHeaderView::section {{ font-size: {int(ui.header_font_size)}px; font-weight: {fw_num}; }}"
            )
        except Exception:
            pass
        try:
            for c in range(int(self.table.columnCount())):
                it_h = self.table.horizontalHeaderItem(int(c))
                if it_h is not None:
                    it_h.setFont(header_font)
        except Exception:
            pass

        # Body font + per-column overrides + alignment.
        try:
            self.table.setFont(body_font)
        except Exception:
            pass

        try:
            row_count = int(self.table.rowCount())
            col_count = int(self.table.columnCount())
            for r in range(row_count):
                for c in range(col_count):
                    it = self.table.item(int(r), int(c))
                    if it is None:
                        continue

                    # Checkbox + STT always centered.
                    if int(c) in (0, 1):
                        it.setTextAlignment(
                            int(
                                Qt.AlignmentFlag.AlignVCenter
                                | Qt.AlignmentFlag.AlignCenter
                            )
                        )
                        it.setFont(body_font)
                        continue

                    key = col_keys[int(c)] if int(c) < len(col_keys) else ""
                    align_s = (ui.column_align or {}).get(key, "center")
                    it.setTextAlignment(int(_to_qt_align(align_s)))

                    f = QFont(body_font)
                    if key in (ui.column_bold or {}):
                        f.setWeight(
                            QFont.Weight.Bold
                            if bool(ui.column_bold.get(key))
                            else QFont.Weight.Normal
                        )
                    it.setFont(f)
        except Exception:
            pass

    def _set_status(self, text: str, ok: bool) -> None:
        self.label_status.setText(str(text or ""))
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS};" if ok else f"color: {COLOR_ERROR};"
        )

    def set_status(self, text: str, ok: bool = True) -> None:
        self._set_status(text, ok=ok)

    def get_excel_path(self) -> str:
        return str(self.input_excel_path.text() or "").strip()

    def set_excel_path(self, path: str) -> None:
        self.input_excel_path.setText(str(path or "").strip())

    def get_preview_rows(self) -> list[dict]:
        return list(self._preview_rows or [])

    def get_checked_preview_rows(self) -> list[dict]:
        """Return checked rows. If none checked, returns []."""
        rows: list[dict] = []
        try:
            for r_idx in range(int(self.table.rowCount())):
                it = self.table.item(int(r_idx), 0)
                if it is None:
                    continue
                if str(it.text() or "").strip() != "✅":
                    continue
                if 0 <= int(r_idx) < len(self._preview_rows):
                    rows.append(self._preview_rows[int(r_idx)])
        except Exception:
            return []
        return rows

    def get_rows_for_import(self) -> list[dict]:
        """If any checkbox checked -> import only checked; else import all."""
        checked = self.get_checked_preview_rows()
        return checked if checked else self.get_preview_rows()

    def set_preview_rows(self, rows: list[dict]) -> None:
        """Fill preview table from parsed Excel rows.

        Expected keys follow MainContent2 naming:
        employee_code, full_name, work_date, weekday, in_1..out_3, late, early,
        hours, work, leave, hours_plus, work_plus, leave_plus, tc1..tc3, schedule.
        """

        self._preview_rows = list(rows or [])
        self.table.setRowCount(len(self._preview_rows))

        def _to_display(v) -> str:
            if v is None:
                return ""
            return str(v)

        def _fmt_date_ddmmyyyy(v) -> str:
            if v is None:
                return ""
            s = str(v).strip()
            if not s:
                return ""
            # If already dd/MM/yyyy then keep
            if "/" in s and len(s.split("/")) == 3:
                return s
            try:
                from datetime import date as _date

                d = _date.fromisoformat(s)
                return d.strftime("%d/%m/%Y")
            except Exception:
                return s

        for r_idx, r in enumerate(self._preview_rows):
            # checkbox + stt
            it_chk = QTableWidgetItem("❌")
            it_chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 0, it_chk)

            it_stt = QTableWidgetItem(str(r_idx + 1))
            it_stt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r_idx, 1, it_stt)

            # data cols start at col=2
            values = [
                _to_display(r.get("employee_code")),
                _to_display(r.get("full_name")),
                _fmt_date_ddmmyyyy(r.get("work_date")),
                _to_display(r.get("weekday")),
                _to_display(r.get("in_1")),
                _to_display(r.get("out_1")),
                _to_display(r.get("in_2")),
                _to_display(r.get("out_2")),
                _to_display(r.get("in_3")),
                _to_display(r.get("out_3")),
                _to_display(r.get("late")),
                _to_display(r.get("early")),
                _to_display(r.get("hours")),
                _to_display(r.get("work")),
                _to_display(r.get("leave")),
                _to_display(r.get("hours_plus")),
                _to_display(r.get("work_plus")),
                _to_display(r.get("leave_plus")),
                _to_display(r.get("tc1")),
                _to_display(r.get("tc2")),
                _to_display(r.get("tc3")),
                _to_display(r.get("schedule")),
            ]
            for c_off, txt in enumerate(values):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(r_idx, 2 + c_off, it)

        self.apply_ui_settings()

    def _set_placeholder_rows(self) -> None:
        try:
            self._preview_rows = []
            self.table.setRowCount(1)
            chk = QTableWidgetItem("❌")
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 0, chk)
            stt = QTableWidgetItem("1")
            stt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 1, stt)
            self.apply_ui_settings()
        except Exception:
            pass

    def _on_cell_clicked(self, row: int, col: int) -> None:
        if int(col) != 0:
            return
        try:
            item = self.table.item(int(row), 0)
            if item is None:
                return
            cur = str(item.text() or "").strip()
            item.setText("✅" if cur != "✅" else "❌")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

    def eventFilter(self, obj, event) -> bool:
        if (
            obj is getattr(self, "input_excel_path", None)
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            if event.button() == Qt.MouseButton.LeftButton:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Chọn file Excel chấm công",
                    str(get_last_save_dir() or ""),
                    "Excel (*.xlsx)",
                )
                if file_path:
                    try:
                        from pathlib import Path

                        set_last_save_dir(str(Path(file_path).parent))
                    except Exception:
                        pass
                    self.input_excel_path.setText(file_path)
                return True
        return super().eventFilter(obj, event)
