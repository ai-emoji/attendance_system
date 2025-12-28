"""ui.widgets.device_widgets

Widget cho màn "Thêm Máy chấm công".

- Copy TitleBar1 / TitleBar2 theo pattern các module khác.
- TitleBar2 gồm 3 nút: Làm mới / Lưu / Xóa và hiển thị Tổng.
- MainContent chia 2 phần:
  - Trái: bảng danh sách thiết bị (ID, STT, Tên máy, Địa chỉ IP)
  - Phải: form nhập Số máy, Tên máy, IP (4 ô xxx.xxx.xxx.xxx), Mật mã, Cổng kết nối
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QFrame,
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
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    EVEN_ROW_BG_COLOR,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_BOLD,
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
    COLOR_TEXT_LIGHT,
    BUTTON_FONT,
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

        # Tổng (hiển thị bên phải)
        self.label_total = QLabel(text or "Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font.setWeight(QFont.Weight.Normal)
        self.label_total.setFont(font)

        layout.addStretch(1)
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

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -----------------
        # Left: table
        # -----------------
        left = QWidget(self)
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.table = QTableWidget(left)
        # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
        try:
            self.table.setFrameShape(QFrame.Shape.NoFrame)
            self.table.setLineWidth(0)
        except Exception:
            pass
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "STT", "Tên máy", "Địa chỉ IP"])
        self.table.setColumnHidden(0, True)

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

        self._last_selected_row: int = -1
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID (ẩn)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # STT
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # IP

        self._min_column_widths: dict[int, int] = {1: 120, 3: 200}
        self.table.setColumnWidth(1, self._min_column_widths[1])
        self.table.setColumnWidth(3, self._min_column_widths[3])

        def _enforce_min_width(logical_index: int, _old: int, new: int) -> None:
            min_w = self._min_column_widths.get(int(logical_index))
            if min_w is not None and int(new) < int(min_w):
                header.resizeSection(int(logical_index), int(min_w))

        header.sectionResized.connect(_enforce_min_width)
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

        self.table_frame = QFrame(left)
        try:
            self.table_frame.setObjectName("device_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#device_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        left_layout.addWidget(self.table_frame, 1)
        root.addWidget(left, 1)

        # -----------------
        # Right: form
        # -----------------
        right = QWidget(self)
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(10)

        label_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            label_font.setWeight(QFont.Weight.Normal)

        def _mk_label(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setFont(label_font)
            return lb

        def _mk_input(placeholder: str = "") -> QLineEdit:
            inp = QLineEdit()
            inp.setFont(self._font_normal)
            inp.setFixedHeight(INPUT_HEIGHT_DEFAULT)
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

        def _mk_combo() -> QComboBox:
            cb = QComboBox()
            cb.setFont(self._font_normal)
            cb.setFixedHeight(INPUT_HEIGHT_DEFAULT)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setStyleSheet(
                "\n".join(
                    [
                        f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                        f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    ]
                )
            )
            return cb

        # Số máy
        right_layout.addWidget(_mk_label("Số máy"))
        self.input_device_no = _mk_input("(ví dụ: 1)")
        self.input_device_no.setValidator(QIntValidator(0, 999999, self))
        right_layout.addWidget(self.input_device_no)

        # Tên máy
        right_layout.addWidget(_mk_label("Tên máy"))
        self.input_device_name = _mk_input("(ví dụ: Ronald Jack X629ID)")
        right_layout.addWidget(self.input_device_name)

        # Địa chỉ IP (4 ô)
        right_layout.addWidget(_mk_label("Địa chỉ IP"))
        ip_row = QWidget(right)
        ip_layout = QHBoxLayout(ip_row)
        ip_layout.setContentsMargins(0, 0, 0, 0)
        ip_layout.setSpacing(6)

        ip_validator = QIntValidator(0, 255, self)

        def _mk_ip_part() -> QLineEdit:
            part = _mk_input("xxx")
            part.setFixedWidth(60)
            part.setAlignment(Qt.AlignmentFlag.AlignCenter)
            part.setValidator(ip_validator)
            part.setMaxLength(3)
            return part

        self.ip_1 = _mk_ip_part()
        self.ip_2 = _mk_ip_part()
        self.ip_3 = _mk_ip_part()
        self.ip_4 = _mk_ip_part()

        # Combobox chọn dòng máy (đặt cùng hàng với IP)
        self.cbo_device_model = _mk_combo()
        self.cbo_device_model.setFixedWidth(250)
        self.cbo_device_model.addItem("ZKTeco SenseFace A4", "SENSEFACE_A4")
        self.cbo_device_model.addItem("Ronald Jack X629ID", "X629ID")

        dot = lambda: QLabel(".")
        for lb in (dot(), dot(), dot()):
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setFixedWidth(10)

        ip_layout.addWidget(self.ip_1)
        ip_layout.addWidget(dot())
        ip_layout.addWidget(self.ip_2)
        ip_layout.addWidget(dot())
        ip_layout.addWidget(self.ip_3)
        ip_layout.addWidget(dot())
        ip_layout.addWidget(self.ip_4)

        ip_layout.addSpacing(12)
        lb_model = _mk_label("Máy")
        lb_model.setFixedWidth(35)
        lb_model.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        ip_layout.addWidget(lb_model)
        ip_layout.addWidget(self.cbo_device_model)
        ip_layout.addStretch(1)

        right_layout.addWidget(ip_row)

        def _norm(s: str) -> str:
            return "".join(ch.lower() for ch in (s or "") if ch.isalnum())

        def _on_model_changed(text: str) -> None:
            current = (self.input_device_name.text() or "").strip()
            # Chỉ auto-fill khi ô Tên máy đang trống hoặc đang đúng 1 trong 2 mẫu
            if not current or _norm(current) in (
                _norm("ZKTeco SenseFace A4"),
                _norm("Ronald Jack X629ID"),
            ):
                self.input_device_name.setText(text or "")

        self.cbo_device_model.currentTextChanged.connect(_on_model_changed)

        # Mật mã
        right_layout.addWidget(_mk_label("Mật mã"))
        self.input_password = _mk_input("(ví dụ: 0)")
        right_layout.addWidget(self.input_password)

        # Cổng kết nối
        right_layout.addWidget(_mk_label("Cổng kết nối"))
        self.input_port = _mk_input("(ví dụ: 4370)")
        self.input_port.setValidator(QIntValidator(0, 65535, self))
        right_layout.addWidget(self.input_port)

        # Button kết nối
        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setFixedHeight(40)
        self.btn_connect.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: {COLOR_BUTTON_PRIMARY}; font-weight: {FONT_WEIGHT_BOLD}; color: {COLOR_TEXT_LIGHT}; font-size: {BUTTON_FONT}px; padding: 10px; border-radius: 6px; }}",
                    f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: #FFFFFF; }}",
                ]
            )
        )
        right_layout.addWidget(self.btn_connect)

        # Trạng thái kết nối
        right_layout.addWidget(_mk_label("Trạng thái kết nối"))
        self.label_connection_status = QLabel("Chưa kết nối")
        self.label_connection_status.setFont(self._font_normal)
        self.label_connection_status.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self.label_connection_status.setMinimumHeight(18)
        right_layout.addWidget(self.label_connection_status)

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
            self.table.setCurrentCell(needed - 1, 2)

    def set_devices(self, rows: list[tuple[int, str, str]]) -> None:
        """rows: [(id, device_name, ip_address)]"""
        self._rows_data_count = len(rows or [])

        viewport_h = self.table.viewport().height()
        desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
        needed = max(desired, self._rows_data_count, 1)
        self._ensure_row_count(needed)

        for r in range(self.table.rowCount()):
            if r < self._rows_data_count:
                device_id, name, ip_addr = rows[r]
                self._set_row_data(r, device_id, r + 1, name, ip_addr)
            else:
                self._set_row_data(r, None, None, "", "")

    def get_selected_device(self) -> tuple[int, str, str] | None:
        row = self.table.currentRow()
        if row < 0:
            return None

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 2)
        ip_item = self.table.item(row, 3)
        if id_item is None:
            return None

        raw_id = (id_item.text() or "").strip()
        if not raw_id:
            return None

        try:
            device_id = int(raw_id)
        except Exception:
            return None

        return (
            device_id,
            (name_item.text() if name_item is not None else ""),
            (ip_item.text() if ip_item is not None else ""),
        )

    def clear_form(self) -> None:
        self.input_device_no.setText("")
        self.input_device_name.setText("")
        self.ip_1.setText("")
        self.ip_2.setText("")
        self.ip_3.setText("")
        self.ip_4.setText("")
        self.input_password.setText("")
        self.input_port.setText("")
        if hasattr(self, "cbo_device_model"):
            try:
                self.cbo_device_model.setCurrentIndex(0)
            except Exception:
                pass
        self.set_connection_status("Chưa kết nối")

    def set_connection_status(self, status: str, ok: bool | None = None) -> None:
        """ok: None=neutral, True=success, False=error"""

        self.label_connection_status.setText(status or "")
        if ok is True:
            self.label_connection_status.setStyleSheet(f"color: {COLOR_SUCCESS};")
        elif ok is False:
            self.label_connection_status.setStyleSheet(f"color: {COLOR_ERROR};")
        else:
            self.label_connection_status.setStyleSheet(
                f"color: {COLOR_TEXT_SECONDARY};"
            )

    def select_device_by_id(self, device_id: int) -> None:
        """Chọn dòng theo id (nếu có)."""

        try:
            target = str(int(device_id))
        except Exception:
            return

        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            if id_item is None:
                continue
            if (id_item.text() or "").strip() == target:
                self.table.setCurrentCell(row, 2)
                self.table.selectRow(row)
                return

    def set_form(
        self,
        device_no: int | None,
        name: str,
        device_type: str | None,
        ip_address: str,
        password: str,
        port: int | None,
    ) -> None:
        self.input_device_no.setText("" if device_no is None else str(int(device_no)))
        self.input_device_name.setText(name or "")

        # Set loại máy theo device_type từ DB (ưu tiên); fallback theo tên nếu thiếu
        if hasattr(self, "cbo_device_model"):
            dt = (device_type or "").strip().upper()
            try:
                if dt in ("SENSEFACE_A4", "X629ID"):
                    self.cbo_device_model.setCurrentIndex(
                        0 if dt == "SENSEFACE_A4" else 1
                    )
                else:
                    n = "".join(ch.lower() for ch in (name or "") if ch.isalnum())
                    if any(k in n for k in ("senseface", "a4", "zkteco")):
                        self.cbo_device_model.setCurrentIndex(0)
                    elif any(
                        k in n
                        for k in ("ronaldjack", "ronald", "jack", "x629", "x629id")
                    ):
                        self.cbo_device_model.setCurrentIndex(1)
            except Exception:
                pass

        parts = [p.strip() for p in (ip_address or "").split(".")]
        parts += [""] * (4 - len(parts))
        self.ip_1.setText(parts[0])
        self.ip_2.setText(parts[1])
        self.ip_3.setText(parts[2])
        self.ip_4.setText(parts[3])

        self.input_password.setText(password or "")
        self.input_port.setText("" if port is None else str(int(port)))

    def get_form_data(self) -> dict[str, str]:
        device_no = (self.input_device_no.text() or "").strip()
        name = (self.input_device_name.text() or "").strip()
        device_type = ""
        if hasattr(self, "cbo_device_model"):
            try:
                device_type = str(self.cbo_device_model.currentData() or "").strip()
            except Exception:
                device_type = ""
        ip_address = ".".join(
            [
                (self.ip_1.text() or "").strip(),
                (self.ip_2.text() or "").strip(),
                (self.ip_3.text() or "").strip(),
                (self.ip_4.text() or "").strip(),
            ]
        )
        password = (self.input_password.text() or "").strip()
        port = (self.input_port.text() or "").strip()

        return {
            "device_no": device_no,
            "device_name": name,
            "device_type": device_type,
            "ip_address": ip_address,
            "password": password,
            "port": port,
        }

    def _set_row_data(
        self,
        row: int,
        device_id: int | None,
        stt: int | None,
        device_name: str,
        ip_address: str,
    ) -> None:
        if self.table.item(row, 0) is None:
            self._init_row_items(row)

        self.table.item(row, 0).setText(
            "" if device_id is None else str(int(device_id))
        )
        self.table.item(row, 1).setText("" if stt is None else str(int(stt)))
        self.table.item(row, 2).setText(device_name or "")
        self.table.item(row, 3).setText(ip_address or "")

    def _init_row_items(self, row: int) -> None:
        # ID (ẩn)
        id_item = QTableWidgetItem("")
        id_item.setFont(self._font_normal)
        self.table.setItem(row, 0, id_item)

        stt_item = QTableWidgetItem("")
        stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        stt_item.setFont(self._font_normal)
        self.table.setItem(row, 1, stt_item)

        name_item = QTableWidgetItem("")
        name_item.setFont(self._font_normal)
        self.table.setItem(row, 2, name_item)

        ip_item = QTableWidgetItem("")
        ip_item.setFont(self._font_normal)
        self.table.setItem(row, 3, ip_item)

        self.table.setRowHeight(row, ROW_HEIGHT)
