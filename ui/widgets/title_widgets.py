"""ui.widgets.title_widgets

Các widget dùng cho layout phần tiêu đề và nội dung trong Container.

Spec:
- TITLE_HEIGHT = 40
- COLOR_BUTTON_PRIMARY_HOVER = "#E6E6E6"  (tên biến theo yêu cầu; thực chất là màu nền)
- TITLE_2_HEIGHT = 40
- BG_TITLE_2_HEIGHT = "#F4F4F4"  (tên biến theo yêu cầu; thực chất là màu nền)
- MAIN_CONTENT_MIN_HEIGHT = 588
- MAIN_CONTENT_BG_COLOR = "#FFFFFF"

Tạo 3 class tương ứng 3 phần.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
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
    COLOR_TEXT_PRIMARY,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    GRID_LINES_COLOR,
    HOVER_ROW_BG_COLOR,
    ICON_ADD,
    ICON_DELETE,
    ICON_EDIT,
    ICON_TOTAL,
    UI_FONT,
    COLOR_BUTTON_PRIMARY_HOVER,
    TITLE_HEIGHT,
    TITLE_2_HEIGHT,
    BG_TITLE_2_HEIGHT,
    MAIN_CONTENT_MIN_HEIGHT,
    MAIN_CONTENT_BG_COLOR,
    ODD_ROW_BG_COLOR,
    EVEN_ROW_BG_COLOR,
    ROW_HEIGHT,
    BG_TITLE_1_HEIGHT,
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
    add_clicked = Signal()
    edit_clicked = Signal()
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

        # 3 nút: Thêm mới / Sửa đổi / Xóa
        self.btn_add = QPushButton("Thêm mới")
        self.btn_edit = QPushButton("Sửa đổi")
        self.btn_delete = QPushButton("Xóa")

        for btn, icon_path in (
            (self.btn_add, ICON_ADD),
            (self.btn_edit, ICON_EDIT),
            (self.btn_delete, ICON_DELETE),
        ):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(QIcon(resource_path(icon_path)))
            btn.setIconSize(QSize(18, 18))
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "\n".join(
                    [
                        f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; padding: 0 10px; border-radius: 6px; }}",
                        # Tăng khoảng cách giữa icon và nội dung
                        "QPushButton::icon { margin-right: 10px; }",
                        f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER};color: #FFFFFF; }}",
                    ]
                )
            )

        self.btn_add.clicked.connect(self.add_clicked.emit)
        self.btn_edit.clicked.connect(self.edit_clicked.emit)
        self.btn_delete.clicked.connect(self.delete_clicked.emit)

        # Label tổng (bên phải)
        self.total_icon = QLabel("")
        self.total_icon.setFixedSize(18, 18)
        self.total_icon.setPixmap(
            QIcon(resource_path(ICON_TOTAL)).pixmap(QSize(18, 18))
        )

        self.label_total = QLabel(text or "Tổng: 0")
        self.label_total.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font.setWeight(QFont.Weight.Normal)
        self.label_total.setFont(font)

        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)
        layout.addSpacing(12)
        layout.addWidget(self.total_icon)
        layout.addWidget(self.label_total)
        layout.addStretch(1)

    def set_total(self, total: int | str) -> None:
        self.label_total.setText(f"Tổng: {total}")


class MainContent(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(MAIN_CONTENT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        self.table = QTableWidget(self)
        # table.mb: QFrame vẽ viền ngoài, QTableWidget chỉ vẽ grid bên trong
        try:
            self.table.setFrameShape(QFrame.Shape.NoFrame)
            self.table.setLineWidth(0)
        except Exception:
            pass
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "STT", "Tên Chức Danh / Chức Vụ"])
        self.table.setColumnHidden(0, True)  # Ẩn cột ID

        # Hành vi bảng
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

        # Header
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(40)
        header.setSectionsMovable(False)

        # Font header: SEMIBOLD
        header_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            header_font.setWeight(QFont.Weight.DemiBold)
        header.setFont(header_font)

        # Fonts cho nội dung
        self._font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            self._font_normal.setWeight(QFont.Weight.Normal)

        self._font_semibold = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            self._font_semibold.setWeight(QFont.Weight.DemiBold)

        self._last_selected_row: int = -1
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        # Kích thước cột
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID (ẩn)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # STT
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )  # Chức danh chiếm phần còn lại
        self._min_column_widths: dict[int, int] = {1: 120}
        self.table.setColumnWidth(1, self._min_column_widths[1])  # STT = 120

        def _enforce_min_width(logical_index: int, _old: int, new: int) -> None:
            min_w = self._min_column_widths.get(int(logical_index))
            if min_w is not None and int(new) < int(min_w):
                header.resizeSection(int(logical_index), int(min_w))

        header.sectionResized.connect(_enforce_min_width)

        # Không cho người dùng resize cột bằng tay
        header.setSectionsClickable(False)

        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        # Style theo resource
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
                    # Selected row: đổi màu phủ 100% chiều ngang, không bo góc, không viền focus
                    f"QTableWidget::item:selected {{ background-color: {HOVER_ROW_BG_COLOR}; color: {COLOR_TEXT_PRIMARY}; border-radius: 0px; border: 0px; }}",
                    "QTableWidget::item:focus { outline: none; }",
                    "QTableWidget:focus { outline: none; }",
                ]
            )
        )

        self._rows_data_count = 0

        # Tạo bảng trống ban đầu, sau đó tự canh theo kích thước thực tế
        self.table.setRowCount(1)
        self._init_row_items(0)
        self.table_frame = QFrame(self)
        try:
            self.table_frame.setObjectName("title_table_frame")
        except Exception:
            pass
        try:
            self.table_frame.setFrameShape(QFrame.Shape.Box)
            self.table_frame.setFrameShadow(QFrame.Shadow.Plain)
            self.table_frame.setLineWidth(1)
        except Exception:
            pass
        self.table_frame.setStyleSheet(
            f"QFrame#title_table_frame {{ border: 1px solid {COLOR_BORDER}; background-color: {MAIN_CONTENT_BG_COLOR}; }}"
        )
        frame_root = QVBoxLayout(self.table_frame)
        frame_root.setContentsMargins(0, 0, 0, 0)
        frame_root.setSpacing(0)
        frame_root.addWidget(self.table)

        layout.addWidget(self.table_frame, 1)

        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def _on_current_cell_changed(
        self, current_row: int, _current_col: int, previous_row: int, _previous_col: int
    ) -> None:
        # Reset font cho row trước đó
        if previous_row is not None and previous_row >= 0:
            self._apply_row_font(previous_row, self._font_normal)

        # Set semibold cho row hiện tại
        if current_row is not None and current_row >= 0:
            self._apply_row_font(current_row, self._font_semibold)

        self._last_selected_row = current_row

    def _apply_row_font(self, row: int, font: QFont) -> None:
        # Cột 0 ẩn, nhưng vẫn set để đồng nhất nếu có item
        for col in (0, 1, 2):
            item = self.table.item(row, col)
            if item is not None:
                item.setFont(font)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Khi mở rộng vùng bảng, tự thêm dòng để đủ chiều cao
        QTimer.singleShot(0, self._ensure_rows_fit_viewport)

    def _ensure_rows_fit_viewport(self) -> None:
        """Tự động tạo thêm dòng trống để đủ kích thước hiển thị.

        - Không tạo STT trước (để trống).
        - Chỉ thêm khi bảng được mở rộng; không xóa dòng khi thu nhỏ.
        - Tính theo viewport để tránh dòng cuối bị cắt/ẩn.
        """

        viewport_h = self.table.viewport().height()
        if viewport_h <= 0:
            return

        desired = max(1, int(viewport_h // ROW_HEIGHT))
        data_count = max(0, int(getattr(self, "_rows_data_count", 0) or 0))
        needed = max(desired, data_count, 1)
        self._ensure_row_count(needed)

    def _ensure_row_count(self, needed: int) -> None:
        """Đảm bảo số dòng đúng nhu cầu.

        - Phóng to: thêm dòng trống.
        - Thu nhỏ: cắt bớt dòng trống (không xóa dữ liệu).
        """

        needed = max(1, int(needed))
        current = self.table.rowCount()
        if current == needed:
            return

        # Nếu đang shrink, lưu row đang chọn để tránh currentRow out-of-range
        selected_row = self.table.currentRow()

        if current < needed:
            self.table.setRowCount(needed)
            for row in range(current, needed):
                self._init_row_items(row)
        else:
            # Chỉ cắt bớt phần trống ở cuối.
            self.table.setRowCount(needed)

        # Điều chỉnh selection nếu bị vượt phạm vi sau khi shrink
        if selected_row >= needed:
            self.table.clearSelection()
            self.table.setCurrentCell(needed - 1, 2)

    def set_titles(self, rows: list[tuple[int, str]]) -> None:
        """Nạp dữ liệu chức danh vào bảng.

        - Giữ phần rows trống để fill chiều cao.
        - STT chỉ hiện với dòng có dữ liệu.
        """

        self._rows_data_count = len(rows or [])

        # Đảm bảo đủ số dòng cho cả dữ liệu và viewport
        viewport_h = self.table.viewport().height()
        desired = max(1, int(viewport_h // ROW_HEIGHT)) if viewport_h > 0 else 1
        needed = max(desired, self._rows_data_count, 1)

        self._ensure_row_count(needed)

        # Fill data + clear the rest
        for r in range(self.table.rowCount()):
            if r < self._rows_data_count:
                title_id, title_name = rows[r]
                self._set_row_data(r, title_id, r + 1, title_name)
            else:
                self._set_row_data(r, None, None, "")

        # Default state: do not auto-select any row
        prev_row = self.table.currentRow()
        try:
            self.table.blockSignals(True)
            self.table.clearSelection()
            self.table.setCurrentItem(None)
        finally:
            self.table.blockSignals(False)

        if prev_row is not None and int(prev_row) >= 0:
            try:
                self._apply_row_font(int(prev_row), self._font_normal)
            except Exception:
                pass
        self._last_selected_row = -1

    def get_selected_title(self) -> tuple[int, str] | None:
        """Trả về (id, title_name) của dòng đang chọn."""

        row = self.table.currentRow()
        if row < 0:
            return None

        id_item = self.table.item(row, 0)
        name_item = self.table.item(row, 2)
        if id_item is None:
            return None

        raw_id = (id_item.text() or "").strip()
        if not raw_id:
            return None

        try:
            title_id = int(raw_id)
        except Exception:
            return None

        return title_id, (name_item.text() if name_item is not None else "")

    def _set_row_data(
        self,
        row: int,
        title_id: int | None,
        stt: int | None,
        title_name: str,
    ) -> None:
        if self.table.item(row, 0) is None:
            self._init_row_items(row)

        self.table.item(row, 0).setText("" if title_id is None else str(int(title_id)))
        self.table.item(row, 1).setText("" if stt is None else str(int(stt)))
        self.table.item(row, 2).setText(title_name or "")

    def _init_row_items(self, row: int) -> None:
        normal_font = getattr(self, "_font_normal", None)
        if normal_font is None:
            normal_font = QFont(UI_FONT, CONTENT_FONT)
            if FONT_WEIGHT_NORMAL >= 400:
                normal_font.setWeight(QFont.Weight.Normal)

        # ID (ẩn)
        id_item = QTableWidgetItem("")
        id_item.setFont(normal_font)
        self.table.setItem(row, 0, id_item)

        # STT (không tạo sẵn)
        stt_item = QTableWidgetItem("")
        stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        stt_item.setFont(normal_font)
        self.table.setItem(row, 1, stt_item)

        # Tên chức danh (trống)
        name_item = QTableWidgetItem("")
        name_item.setFont(normal_font)
        self.table.setItem(row, 2, name_item)

        self.table.setRowHeight(row, ROW_HEIGHT)
