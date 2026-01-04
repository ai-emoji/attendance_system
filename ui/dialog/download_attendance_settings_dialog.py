"""ui.dialog.download_attendance_settings_dialog

Dialog cài đặt giao diện phần "Tải dữ liệu chấm công".

Yêu cầu:
- Chỉnh kích thước chữ trong bảng
- Chỉnh kích thước chữ combobox/input
- Chỉnh kích thước chữ lịch (calendar popup)
- Ẩn/hiện các cột trong bảng tải dữ liệu
- Click "Áp dụng" sẽ áp dụng ngay cho các màn đang mở

Ghi chú:
- Lưu/đọc từ core.ui_settings và phát signal để các bảng đang mở cập nhật ngay.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.resource import (
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    CONTENT_FONT,
    COLOR_TEXT_LIGHT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    UI_FONT,
)
from core.ui_settings import get_download_attendance_ui, update_download_attendance_ui


def _norm_text(s: str) -> str:
    return " ".join(str(s or "").strip().split())


class DownloadAttendanceSettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open DownloadAttendanceSettingsDialog")
        self.setModal(True)
        self.setWindowTitle("Cài đặt tải dữ liệu chấm công")
        self.setMinimumSize(640, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        group = QGroupBox("Cài đặt tải dữ liệu chấm công", self)
        group.setFont(font_normal)

        form = QFormLayout(group)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._ui = get_download_attendance_ui()

        self.spin_table_font_size = QSpinBox(group)
        self.spin_table_font_size.setRange(8, 24)
        self.spin_table_font_size.setValue(int(self._ui.table_font_size))
        self.spin_table_font_size.setFont(font_normal)

        self.spin_table_header_font_size = QSpinBox(group)
        self.spin_table_header_font_size.setRange(8, 24)
        self.spin_table_header_font_size.setValue(int(self._ui.table_header_font_size))
        self.spin_table_header_font_size.setFont(font_normal)

        self.cbo_table_header_weight = QComboBox(group)
        self.cbo_table_header_weight.setFont(font_normal)
        self.cbo_table_header_weight.addItem("Nhạt", "normal")
        self.cbo_table_header_weight.addItem("Đậm", "bold")
        self.cbo_table_header_weight.setCurrentIndex(
            max(
                0,
                self.cbo_table_header_weight.findData(
                    str(self._ui.table_header_font_weight)
                ),
            )
        )

        self.spin_combo_font_size = QSpinBox(group)
        self.spin_combo_font_size.setRange(8, 24)
        self.spin_combo_font_size.setValue(int(self._ui.combo_font_size))
        self.spin_combo_font_size.setFont(font_normal)

        self.spin_calendar_font_size = QSpinBox(group)
        self.spin_calendar_font_size.setRange(8, 24)
        self.spin_calendar_font_size.setValue(int(self._ui.calendar_font_size))
        self.spin_calendar_font_size.setFont(font_normal)

        # Sizing / layout
        self.spin_input_height = QSpinBox(group)
        self.spin_input_height.setRange(0, 99999)
        self.spin_input_height.setValue(int(self._ui.input_height))
        self.spin_input_height.setFont(font_normal)

        self.spin_button_height = QSpinBox(group)
        self.spin_button_height.setRange(0, 99999)
        self.spin_button_height.setValue(int(self._ui.button_height))
        self.spin_button_height.setFont(font_normal)

        self.spin_date_width = QSpinBox(group)
        self.spin_date_width.setRange(0, 99999)
        self.spin_date_width.setValue(int(self._ui.date_width))
        self.spin_date_width.setFont(font_normal)

        self.spin_device_width = QSpinBox(group)
        self.spin_device_width.setRange(0, 99999)
        self.spin_device_width.setValue(int(self._ui.device_width))
        self.spin_device_width.setFont(font_normal)

        self.spin_search_by_width = QSpinBox(group)
        self.spin_search_by_width.setRange(0, 99999)
        self.spin_search_by_width.setValue(int(self._ui.search_by_width))
        self.spin_search_by_width.setFont(font_normal)

        self.spin_search_text_min_width = QSpinBox(group)
        self.spin_search_text_min_width.setRange(0, 99999)
        self.spin_search_text_min_width.setValue(int(self._ui.search_text_min_width))
        self.spin_search_text_min_width.setFont(font_normal)

        self.spin_download_button_width = QSpinBox(group)
        self.spin_download_button_width.setRange(0, 99999)
        self.spin_download_button_width.setValue(int(self._ui.download_button_width))
        self.spin_download_button_width.setFont(font_normal)

        self.spin_time_button_width = QSpinBox(group)
        self.spin_time_button_width.setRange(0, 99999)
        self.spin_time_button_width.setValue(int(self._ui.time_button_width))
        self.spin_time_button_width.setFont(font_normal)

        self.spin_clock_icon_size = QSpinBox(group)
        self.spin_clock_icon_size.setRange(0, 99999)
        self.spin_clock_icon_size.setValue(int(self._ui.clock_icon_size))
        self.spin_clock_icon_size.setFont(font_normal)

        self.cbo_layout_mode = QComboBox(group)
        self.cbo_layout_mode.setFont(font_normal)
        self.cbo_layout_mode.addItem("Trái sang phải", "ltr")
        self.cbo_layout_mode.addItem("Phải sang trái", "rtl")
        self.cbo_layout_mode.addItem("Căn đều 2 bên", "space_between")
        self.cbo_layout_mode.setCurrentIndex(
            max(0, self.cbo_layout_mode.findData(str(self._ui.layout_mode)))
        )

        self.spin_layout_margin = QSpinBox(group)
        self.spin_layout_margin.setRange(0, 99999)
        self.spin_layout_margin.setValue(int(self._ui.layout_margin))
        self.spin_layout_margin.setFont(font_normal)

        self.spin_layout_spacing = QSpinBox(group)
        self.spin_layout_spacing.setRange(0, 99999)
        self.spin_layout_spacing.setValue(int(self._ui.layout_spacing))
        self.spin_layout_spacing.setFont(font_normal)

        self.cbo_column = QComboBox(group)
        self.cbo_column.setFont(font_normal)
        # Keep in sync with ui.widgets.download_attendance_widgets
        columns = [
            ("attendance_code", "Mã chấm công"),
            ("name_on_mcc", "Tên trên MCC"),
            ("work_date", "Ngày tháng năm"),
            ("in_1", "Giờ vào 1"),
            ("out_1", "Giờ ra 1"),
            ("in_2", "Giờ vào 2"),
            ("out_2", "Giờ ra 2"),
            ("in_3", "Giờ vào 3"),
            ("out_3", "Giờ ra 3"),
            ("device_name", "Tên máy"),
        ]
        for key, label in columns:
            self.cbo_column.addItem(label, key)

        # Visible toggle (emoji) - consistent with other screens
        self.btn_visible = QPushButton(group)
        self.btn_visible.setFont(font_normal)
        self.btn_visible.setCheckable(True)
        self.btn_visible.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_visible.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ border: 1px solid {COLOR_BORDER}; border-radius: 0px; padding: 6px 10px; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:hover {{ color: {COLOR_TEXT_LIGHT}; }}",
                    # Checked = show
                    f"QPushButton:checked {{ background: {COLOR_BUTTON_PRIMARY}; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:checked:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                    # Unchecked = hide
                    f"QPushButton:!checked {{ background: {COLOR_BUTTON_CANCEL}; color: {COLOR_TEXT_LIGHT}; }}",
                    f"QPushButton:!checked:hover {{ background: {COLOR_BUTTON_CANCEL_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                ]
            )
        )

        def _set_visible_button(is_visible: bool) -> None:
            self.btn_visible.blockSignals(True)
            try:
                self.btn_visible.setChecked(bool(is_visible))
                self.btn_visible.setText("✅ Hiển thị" if bool(is_visible) else "❌ Ẩn")
            finally:
                self.btn_visible.blockSignals(False)

        self.btn_visible.toggled.connect(lambda v: _set_visible_button(bool(v)))

        def _refresh_column_defaults() -> None:
            key = str(self.cbo_column.currentData() or "").strip()
            vis = bool((self._ui.column_visible or {}).get(key, True))
            _set_visible_button(bool(vis))

        self.cbo_column.currentIndexChanged.connect(
            lambda _i: _refresh_column_defaults()
        )
        _refresh_column_defaults()

        form.addRow("Kích thước chữ (bảng)", self.spin_table_font_size)
        form.addRow("Kích thước chữ (header)", self.spin_table_header_font_size)
        form.addRow("Chữ đậm/nhạt (header)", self.cbo_table_header_weight)
        form.addRow("Kích thước chữ (combobox/input)", self.spin_combo_font_size)
        form.addRow("Kích thước chữ (lịch)", self.spin_calendar_font_size)
        form.addRow("Chiều cao input", self.spin_input_height)
        form.addRow("Chiều cao button", self.spin_button_height)
        form.addRow("Rộng ô lịch (Từ/Đến)", self.spin_date_width)
        form.addRow("Rộng combobox Máy", self.spin_device_width)
        form.addRow("Rộng combobox Tìm theo", self.spin_search_by_width)
        form.addRow("Rộng tối thiểu ô tìm kiếm", self.spin_search_text_min_width)
        form.addRow("Rộng nút Tải dữ liệu", self.spin_download_button_width)
        form.addRow("Rộng nút HH:MM", self.spin_time_button_width)
        form.addRow("Kích thước icon đồng hồ", self.spin_clock_icon_size)
        form.addRow("Kiểu hiển thị hàng", self.cbo_layout_mode)
        form.addRow("Margin (trái/phải)", self.spin_layout_margin)
        form.addRow("Khoảng cách (spacing)", self.spin_layout_spacing)
        form.addRow("Chọn cột", self.cbo_column)
        form.addRow("Hiển thị cột", self.btn_visible)

        self.label_status = QLabel("", self)
        self.label_status.setFont(font_normal)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(10)

        self.btn_apply = QPushButton("Áp dụng", self)
        self.btn_apply.setFont(font_button)
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_close = QPushButton("Đóng", self)
        self.btn_close.setFont(font_button)
        self.btn_close.setFixedHeight(34)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(self.btn_apply, 1)
        btn_row.addWidget(self.btn_close, 1)

        root.addWidget(group, 0)
        root.addWidget(self.label_status, 0)
        root.addLayout(btn_row)
        root.addStretch(1)

        self.btn_close.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self._on_apply)

    def _on_apply(self) -> None:
        try:
            table_fs = int(self.spin_table_font_size.value())
            table_hfs = int(self.spin_table_header_font_size.value())
            table_hfw = str(
                self.cbo_table_header_weight.currentData() or "bold"
            ).strip()
            combo_fs = int(self.spin_combo_font_size.value())
            cal_fs = int(self.spin_calendar_font_size.value())

            input_h = int(self.spin_input_height.value())
            button_h = int(self.spin_button_height.value())
            date_w = int(self.spin_date_width.value())
            device_w = int(self.spin_device_width.value())
            search_by_w = int(self.spin_search_by_width.value())
            search_text_min_w = int(self.spin_search_text_min_width.value())
            download_w = int(self.spin_download_button_width.value())
            time_w = int(self.spin_time_button_width.value())
            clock_icon = int(self.spin_clock_icon_size.value())
            layout_mode = str(self.cbo_layout_mode.currentData() or "ltr").strip()
            layout_margin = int(self.spin_layout_margin.value())
            layout_spacing = int(self.spin_layout_spacing.value())

            col_key = str(self.cbo_column.currentData() or "").strip()
            visible = "show" if bool(self.btn_visible.isChecked()) else "hide"

            update_download_attendance_ui(
                table_font_size=table_fs,
                table_header_font_size=table_hfs,
                table_header_font_weight=table_hfw,
                combo_font_size=combo_fs,
                calendar_font_size=cal_fs,
                input_height=input_h,
                button_height=button_h,
                date_width=date_w,
                device_width=device_w,
                search_by_width=search_by_w,
                search_text_min_width=search_text_min_w,
                download_button_width=download_w,
                time_button_width=time_w,
                clock_icon_size=clock_icon,
                layout_mode=layout_mode,
                layout_margin=layout_margin,
                layout_spacing=layout_spacing,
                column_key=col_key,
                column_visible=visible,
            )
            self._ui = get_download_attendance_ui()
            self.label_status.setText("Đã áp dụng.")
        except Exception as exc:
            self.label_status.setText(_norm_text(str(exc)))
