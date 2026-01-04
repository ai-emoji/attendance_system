"""ui.dialog.employee_dialog

Dialog Thông tin Nhân viên:
- Thêm mới / Sửa đổi / Xóa
- Label + input trên 1 hàng
- Dropdown: Giới tính, Phòng ban, Chức danh, Nơi cấp (gợi ý)
- Date picker (calendar) cho các cột ngày
- Mã NV: 5 chữ số (ví dụ 00001)

Ghi chú:
- Không dùng QMessageBox (dùng status nội tuyến)
"""

from __future__ import annotations

from PySide6.QtCore import QDate, QEvent, QLocale, QObject, Qt, QRegularExpression
from PySide6.QtGui import QFont, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDateEdit,
)

from core.resource import (
    COLOR_TEXT_PRIMARY,
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
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    UI_FONT,
)


class EmployeeDialog(QDialog):
    def __init__(
        self,
        mode: str = "add",
        employee: dict | None = None,
        departments: list[tuple[int, str]] | None = None,
        titles: list[tuple[int, str]] | None = None,
        issue_places: list[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._employee: dict = employee or {}
        self._departments = departments or []
        self._titles = titles or []
        self._issue_places = issue_places or []
        self._init_ui()
        if self._mode != "delete":
            self._load_sources()
            self.set_data(self._employee)
        else:
            self._set_delete_message(self._employee)

    def _init_ui(self) -> None:
        self.setModal(True)
        if self._mode == "delete":
            self.setFixedSize(450, 150)
        else:
            self.setMinimumSize(820, 800)
            self.resize(820, 800)

        if self._mode == "add":
            self.setWindowTitle("Thêm nhân viên")
        elif self._mode == "delete":
            self.setWindowTitle("Xóa nhân viên")
        else:
            self.setWindowTitle("Sửa thông tin")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        if self._mode == "delete":
            self._build_delete_ui(root, font_normal, font_button)
            return

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        form_widget = QWidget(scroll)
        form_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout = QVBoxLayout(form_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        columns = QWidget(form_widget)
        columns_layout = QHBoxLayout(columns)
        columns_layout.setContentsMargins(0, 0, 0, 0)
        columns_layout.setSpacing(16)

        left_panel = QWidget(columns)
        left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        left_form = QFormLayout(left_panel)
        left_form.setContentsMargins(0, 0, 0, 0)
        left_form.setSpacing(10)
        left_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        left_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        right_panel = QWidget(columns)
        right_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_form = QFormLayout(right_panel)
        right_form.setContentsMargins(0, 0, 0, 0)
        right_form.setSpacing(10)
        right_form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        right_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        divider = QFrame(columns)
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet(f"color: {COLOR_BORDER};")

        columns_layout.addWidget(left_panel, 1)
        columns_layout.addWidget(divider)
        columns_layout.addWidget(right_panel, 1)
        content_layout.addWidget(columns, 1)

        scroll.setWidget(form_widget)

        input_style = "\n".join(
            [
                f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )

        combo_style = "\n".join(
            [
                f"QComboBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                f"QComboBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )

        date_style = "\n".join(
            [
                f"QDateEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                f"QDateEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
            ]
        )

        self.input_code = QLineEdit()
        self.input_code.setFont(font_normal)
        self.input_code.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_code.setMinimumWidth(220)
        self.input_code.setMaxLength(5)
        self.input_code.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,5}$"))
        )
        self.input_code.setPlaceholderText("00001")
        self.input_code.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_code.setStyleSheet(input_style)

        self.input_name = QLineEdit()
        self.input_name.setFont(font_normal)
        self.input_name.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.input_name.setMinimumWidth(220)
        self.input_name.setPlaceholderText("(ví dụ: Nguyễn Văn A)")
        self.input_name.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_name.setStyleSheet(input_style)

        self.input_mcc_code = self._make_line_edit(input_style, font_normal)
        self.input_name_on_mcc = self._make_line_edit(input_style, font_normal)

        self.input_start_date = self._make_date_edit(date_style, font_normal)

        self.cbo_department = QComboBox()
        self.cbo_department.setFont(font_normal)
        self.cbo_department.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_department.setStyleSheet(combo_style)

        self.cbo_title = QComboBox()
        self.cbo_title.setFont(font_normal)
        self.cbo_title.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_title.setStyleSheet(combo_style)

        self.input_dob = self._make_date_edit(date_style, font_normal)

        self.cbo_gender = QComboBox()
        self.cbo_gender.setFont(font_normal)
        self.cbo_gender.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_gender.setStyleSheet(combo_style)

        self.input_national_id = self._make_line_edit(input_style, font_normal)
        self.input_id_issue_date = self._make_date_edit(date_style, font_normal)

        self.cbo_id_issue_place = QComboBox()
        self.cbo_id_issue_place.setEditable(True)
        self.cbo_id_issue_place.setFont(font_normal)
        self.cbo_id_issue_place.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_id_issue_place.setStyleSheet(combo_style)

        self.cbo_employment_status = QComboBox()
        self.cbo_employment_status.setFont(font_normal)
        self.cbo_employment_status.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_employment_status.setStyleSheet(combo_style)

        self.input_address = self._make_line_edit(input_style, font_normal)
        self.input_phone = self._make_line_edit(input_style, font_normal)
        self.input_insurance = self._make_line_edit(input_style, font_normal)
        self.input_tax_code = self._make_line_edit(input_style, font_normal)
        self.input_degree = self._make_line_edit(input_style, font_normal)
        self.input_major = self._make_line_edit(input_style, font_normal)

        self.cbo_contract1_signed = QComboBox()
        self.cbo_contract1_signed.setFont(font_normal)
        self.cbo_contract1_signed.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_contract1_signed.setStyleSheet(combo_style)
        self.input_contract1_no = self._make_line_edit(input_style, font_normal)
        self.input_contract1_sign_date = self._make_date_edit(date_style, font_normal)
        self.input_contract1_expire_date = self._make_date_edit(date_style, font_normal)

        self.cbo_contract2_indefinite = QComboBox()
        self.cbo_contract2_indefinite.setFont(font_normal)
        self.cbo_contract2_indefinite.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.cbo_contract2_indefinite.setStyleSheet(combo_style)
        self.input_contract2_no = self._make_line_edit(input_style, font_normal)
        self.input_contract2_sign_date = self._make_date_edit(date_style, font_normal)

        self.spin_children = QSpinBox()
        self.spin_children.setFont(font_normal)
        self.spin_children.setRange(-1, 20)
        self.spin_children.setSpecialValueText("Chưa có")
        self.spin_children.setValue(-1)
        self.spin_children.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        self.spin_children.setStyleSheet(
            "\n".join(
                [
                    f"QSpinBox {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 0px; }}",
                    f"QSpinBox:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                ]
            )
        )

        self.input_child_dob_1 = self._make_date_edit(date_style, font_normal)
        self.input_child_dob_2 = self._make_date_edit(date_style, font_normal)
        self.input_child_dob_3 = self._make_date_edit(date_style, font_normal)
        self.input_child_dob_4 = self._make_date_edit(date_style, font_normal)

        self.input_note = self._make_line_edit(input_style, font_normal)

        # Left 50%
        left_form.addRow("Mã NV", self.input_code)
        left_form.addRow("Mã CC", self.input_mcc_code)
        left_form.addRow("Họ và tên", self.input_name)
        left_form.addRow("Tên trên MCC", self.input_name_on_mcc)
        left_form.addRow("Ngày vào làm", self.input_start_date)
        left_form.addRow("Phòng ban", self.cbo_department)
        left_form.addRow("Chức vụ", self.cbo_title)
        left_form.addRow("Giới tính", self.cbo_gender)
        left_form.addRow("Số điện thoại", self.input_phone)
        left_form.addRow("Địa chỉ", self.input_address)
        left_form.addRow("Ghi chú", self.input_note)
        left_form.addRow("HĐLĐ (ký lần 1)", self.cbo_contract1_signed)
        left_form.addRow("Số HĐLĐ (lần 1)", self.input_contract1_no)
        left_form.addRow("Ngày ký (lần 1)", self.input_contract1_sign_date)
        left_form.addRow("Ngày hết hạn (lần 1)", self.input_contract1_expire_date)
        left_form.addRow("HĐLĐ ký không thời hạn", self.cbo_contract2_indefinite)
        left_form.addRow("Số HĐLĐ (không thời hạn)", self.input_contract2_no)
        left_form.addRow("Ngày ký (không thời hạn)", self.input_contract2_sign_date)

        # Right 50%
        right_form.addRow("Ngày tháng năm sinh", self.input_dob)
        right_form.addRow("CCCD/CMT", self.input_national_id)
        right_form.addRow("Ngày Cấp", self.input_id_issue_date)
        right_form.addRow("Nơi Cấp", self.cbo_id_issue_place)
        right_form.addRow("Số Bảo Hiểm", self.input_insurance)
        right_form.addRow("Mã số Thuế TNCN", self.input_tax_code)
        right_form.addRow("Bằng cấp", self.input_degree)
        right_form.addRow("Chuyên ngành", self.input_major)
        right_form.addRow("Số con", self.spin_children)
        right_form.addRow("Ngày sinh con 1", self.input_child_dob_1)
        right_form.addRow("Ngày sinh con 2", self.input_child_dob_2)
        right_form.addRow("Ngày sinh con 3", self.input_child_dob_3)
        right_form.addRow("Ngày sinh con 4", self.input_child_dob_4)
        right_form.addRow("Hiện trạng", self.cbo_employment_status)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_save = QPushButton("Lưu" if self._mode != "delete" else "Xóa")
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(120)
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

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setFont(font_button)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setMinimumWidth(120)
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

        root.addWidget(scroll, 1)
        root.addWidget(self.label_status)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self.reject)
        self.input_code.returnPressed.connect(self.btn_save.click)
        self.input_name.returnPressed.connect(self.btn_save.click)
        self.input_code.setFocus()

    def _make_line_edit(self, style: str, font: QFont) -> QLineEdit:
        w = QLineEdit()
        w.setFont(font)
        w.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        w.setStyleSheet(style)
        w.setCursor(Qt.CursorShape.IBeamCursor)
        w.setPlaceholderText("Chưa có")
        return w

    def _build_delete_ui(
        self, root: QVBoxLayout, font_normal: QFont, font_button: QFont
    ) -> None:
        self.label_delete = QLabel("")
        self.label_delete.setFont(font_normal)
        self.label_delete.setWordWrap(True)
        self.label_delete.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        self.label_status.setMinimumHeight(18)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_save = QPushButton("Xóa")
        self.btn_save.setFont(font_button)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setFixedHeight(36)
        self.btn_save.setMinimumWidth(120)
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

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setFont(font_button)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setMinimumWidth(120)
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

        root.addWidget(self.label_delete)
        root.addStretch(1)
        root.addWidget(self.label_status)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self.reject)

    def _set_delete_message(self, employee: dict | None) -> None:
        if not hasattr(self, "label_delete"):
            return
        e = employee or {}
        code = str(e.get("employee_code") or "").strip()
        name = str(e.get("full_name") or "").strip()
        if code and name:
            self.label_delete.setText(
                f"Bạn có chắc chắn muốn xóa nhân viên {code} - {name} không?"
            )
        elif code or name:
            self.label_delete.setText(
                f"Bạn có chắc chắn muốn xóa nhân viên {code or name} không?"
            )
        else:
            self.label_delete.setText("Bạn có chắc chắn muốn xóa nhân viên này không?")

    def _make_date_edit(self, style: str, font: QFont) -> QDateEdit:
        w = QDateEdit()
        w.setFont(font)
        w.setFixedHeight(INPUT_HEIGHT_DEFAULT)
        w.setCalendarPopup(True)
        w.setDisplayFormat("dd/MM/yyyy")
        w.setStyleSheet(style)
        w.setSpecialValueText("Chưa chọn ngày")
        w.setDate(w.minimumDate())

        vi = QLocale("vi_VN")
        w.setLocale(vi)
        cal = w.calendarWidget()
        if cal is not None:
            cal.setLocale(vi)
            cal.installEventFilter(EmployeeDialog._CalendarPopupMonthFix(w, cal))
        return w

    class _CalendarPopupMonthFix(QObject):
        def __init__(self, date_edit: QDateEdit, calendar_widget: QWidget) -> None:
            super().__init__(calendar_widget)
            self._date_edit = date_edit

        def eventFilter(self, obj, event) -> bool:
            if event.type() == QEvent.Type.Show:
                try:
                    # If field is "not selected" (minimumDate), show current month.
                    if self._date_edit.date() == self._date_edit.minimumDate():
                        today = QDate.currentDate()
                        cal = self._date_edit.calendarWidget()
                        if cal is not None:
                            cal.setSelectedDate(self._date_edit.minimumDate())
                            cal.setCurrentPage(int(today.year()), int(today.month()))
                except Exception:
                    pass
            return super().eventFilter(obj, event)

    def _set_read_only(self, value: bool) -> None:
        for w in (
            self.input_code,
            self.input_name,
            self.input_address,
            self.input_phone,
            self.input_insurance,
            self.input_tax_code,
            self.input_degree,
            self.input_major,
            self.input_national_id,
            self.input_contract1_no,
            self.input_contract2_no,
            self.input_note,
        ):
            w.setReadOnly(bool(value))

        for w in (
            self.input_start_date,
            self.input_dob,
            self.input_id_issue_date,
            self.input_contract1_sign_date,
            self.input_contract1_expire_date,
            self.input_contract2_sign_date,
            self.input_child_dob_1,
            self.input_child_dob_2,
            self.input_child_dob_3,
            self.input_child_dob_4,
        ):
            w.setEnabled(not bool(value))

        for w in (
            self.cbo_department,
            self.cbo_title,
            self.cbo_gender,
            self.cbo_id_issue_place,
            self.cbo_employment_status,
            self.spin_children,
            self.cbo_contract1_signed,
            self.cbo_contract2_indefinite,
        ):
            w.setEnabled(not bool(value))

    def _load_sources(self) -> None:
        # Gender
        self.cbo_gender.clear()
        self.cbo_gender.addItem("Chưa chọn", None)
        for g in ("Nam", "Nữ", "Khác"):
            self.cbo_gender.addItem(g, g)

        # Departments
        self.cbo_department.clear()
        self.cbo_department.addItem("Nhân viên mới", None)
        for dept_id, dept_name in self._departments:
            self.cbo_department.addItem(str(dept_name), int(dept_id))
        self.cbo_department.setCurrentIndex(0)

        # Titles
        self.cbo_title.clear()
        self.cbo_title.addItem("Chưa sắp xếp", None)
        for title_id, title_name in self._titles:
            self.cbo_title.addItem(str(title_name), int(title_id))
        self.cbo_title.setCurrentIndex(0)

        # Issue place suggestions
        self.cbo_id_issue_place.clear()
        self.cbo_id_issue_place.addItem("")
        for p in self._issue_places:
            s = str(p or "").strip()
            if s:
                self.cbo_id_issue_place.addItem(s)

        # Employment status
        self.cbo_employment_status.clear()
        self.cbo_employment_status.addItem("Chưa chọn", "")
        # Store codes as strings to match DB storage (VARCHAR) and avoid type mismatch.
        self.cbo_employment_status.addItem("Đi làm", "1")
        self.cbo_employment_status.addItem("Nghỉ thai sản", "2")
        self.cbo_employment_status.addItem("Đã nghỉ việc", "3")
        self.cbo_employment_status.setCurrentIndex(0)

        # Contracts
        self.cbo_contract1_signed.clear()
        self.cbo_contract1_signed.addItem("Chưa ký", False)
        self.cbo_contract1_signed.addItem("Đã ký", True)
        self.cbo_contract1_signed.setCurrentIndex(0)

        self.cbo_contract2_indefinite.clear()
        self.cbo_contract2_indefinite.addItem("Không", False)
        self.cbo_contract2_indefinite.addItem("Có", True)
        self.cbo_contract2_indefinite.setCurrentIndex(0)

    def _set_combo_by_data(self, combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _parse_iso_date_to_qdate(self, value) -> QDate | None:
        s = str(value or "").strip()
        if not s:
            return None
        # accept YYYY-MM-DD
        parts = s.split("-")
        if len(parts) == 3:
            try:
                y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                qd = QDate(y, m, d)
                return qd if qd.isValid() else None
            except Exception:
                return None
        # accept DD/MM/YYYY
        parts2 = s.split("/")
        if len(parts2) == 3:
            try:
                d, m, y = int(parts2[0]), int(parts2[1]), int(parts2[2])
                qd = QDate(y, m, d)
                return qd if qd.isValid() else None
            except Exception:
                return None
        return None

    def _date_edit_to_iso(self, w: QDateEdit) -> str | None:
        qd = w.date()
        if qd == w.minimumDate():
            return None
        if not qd.isValid():
            return None
        return qd.toString("yyyy-MM-dd")

    def set_data(self, employee: dict | None) -> None:
        e = employee or {}

        self.set_employee_code(str(e.get("employee_code") or ""))
        self.set_full_name(str(e.get("full_name") or ""))
        try:
            self.input_mcc_code.setText(str(e.get("mcc_code") or ""))
        except Exception:
            pass
        try:
            self.input_name_on_mcc.setText(str(e.get("name_on_mcc") or ""))
        except Exception:
            pass

        # dates
        for key, widget in (
            ("start_date", self.input_start_date),
            ("date_of_birth", self.input_dob),
            ("id_issue_date", self.input_id_issue_date),
            ("contract1_sign_date", self.input_contract1_sign_date),
            ("contract1_expire_date", self.input_contract1_expire_date),
            ("contract2_sign_date", self.input_contract2_sign_date),
            ("child_dob_1", self.input_child_dob_1),
            ("child_dob_2", self.input_child_dob_2),
            ("child_dob_3", self.input_child_dob_3),
            ("child_dob_4", self.input_child_dob_4),
        ):
            qd = self._parse_iso_date_to_qdate(e.get(key))
            widget.setDate(qd if qd is not None else widget.minimumDate())

        # combos
        self._set_combo_by_data(self.cbo_department, e.get("department_id"))
        self._set_combo_by_data(self.cbo_title, e.get("title_id"))

        gender = str(e.get("gender") or "").strip() or None
        self._set_combo_by_data(self.cbo_gender, gender)

        self.input_national_id.setText(str(e.get("national_id") or ""))

        place = str(e.get("id_issue_place") or "").strip()
        if place:
            idx = self.cbo_id_issue_place.findText(place)
            if idx >= 0:
                self.cbo_id_issue_place.setCurrentIndex(idx)
            else:
                self.cbo_id_issue_place.setCurrentText(place)
        else:
            self.cbo_id_issue_place.setCurrentIndex(0)

        status_raw = e.get("employment_status")
        status_txt = str(status_raw or "").strip()
        status_code: str | None = None
        if status_txt:
            # Accept both numeric codes and legacy Vietnamese text.
            if status_txt in {"1", "2", "3"}:
                status_code = status_txt
            else:
                s = status_txt.strip().lower()
                if s in {"đi làm", "di lam", "đang làm", "dang lam", "working"}:
                    status_code = "1"
                elif s in {
                    "nghỉ thai sản",
                    "nghi thai san",
                    "thai sản",
                    "thai san",
                    "maternity",
                    "maternity leave",
                    "nghỉ thai sải",
                    "nghi thai sai",
                }:
                    status_code = "2"
                elif s in {
                    "đã nghỉ việc",
                    "da nghi viec",
                    "nghỉ việc",
                    "nghi viec",
                    "resigned",
                    "quit",
                }:
                    status_code = "3"

        if status_code in {"1", "2", "3"}:
            idx_s = self.cbo_employment_status.findData(status_code)
            self.cbo_employment_status.setCurrentIndex(idx_s if idx_s >= 0 else 0)
        else:
            self.cbo_employment_status.setCurrentIndex(0)

        self.input_address.setText(str(e.get("address") or ""))
        self.input_phone.setText(str(e.get("phone") or ""))
        self.input_insurance.setText(str(e.get("insurance_no") or ""))
        self.input_tax_code.setText(str(e.get("tax_code") or ""))
        self.input_degree.setText(str(e.get("degree") or ""))
        self.input_major.setText(str(e.get("major") or ""))

        self._set_combo_by_data(
            self.cbo_contract1_signed, bool(int(e.get("contract1_signed") or 0))
        )
        self.input_contract1_no.setText(str(e.get("contract1_no") or ""))
        self._set_combo_by_data(
            self.cbo_contract2_indefinite,
            bool(int(e.get("contract2_indefinite") or 0)),
        )
        self.input_contract2_no.setText(str(e.get("contract2_no") or ""))

        cc = e.get("children_count")
        if cc is None or str(cc).strip() == "":
            self.spin_children.setValue(-1)
        else:
            try:
                self.spin_children.setValue(int(cc))
            except Exception:
                self.spin_children.setValue(-1)

        self.input_note.setText(str(e.get("note") or ""))

    def get_data(self) -> dict:
        code = self.get_employee_code()
        name = self.get_full_name()

        dept_id = self.cbo_department.currentData()
        title_id = self.cbo_title.currentData()

        gender = self.cbo_gender.currentData()
        gender = str(gender).strip() if gender is not None else None
        issue_place = (self.cbo_id_issue_place.currentText() or "").strip() or None

        status = self.cbo_employment_status.currentData()
        status = str(status).strip() if status is not None else ""
        status = status or None

        return {
            "employee_code": code,
            "mcc_code": (self.input_mcc_code.text() or "").strip() or None,
            "full_name": name,
            "name_on_mcc": (self.input_name_on_mcc.text() or "").strip() or None,
            "start_date": self._date_edit_to_iso(self.input_start_date),
            "department_id": int(dept_id) if dept_id is not None else None,
            "title_id": int(title_id) if title_id is not None else None,
            "date_of_birth": self._date_edit_to_iso(self.input_dob),
            "gender": gender,
            "national_id": (self.input_national_id.text() or "").strip() or None,
            "id_issue_date": self._date_edit_to_iso(self.input_id_issue_date),
            "id_issue_place": issue_place,
            "employment_status": status,
            "address": (self.input_address.text() or "").strip() or None,
            "phone": (self.input_phone.text() or "").strip() or None,
            "insurance_no": (self.input_insurance.text() or "").strip() or None,
            "tax_code": (self.input_tax_code.text() or "").strip() or None,
            "degree": (self.input_degree.text() or "").strip() or None,
            "major": (self.input_major.text() or "").strip() or None,
            "contract1_signed": bool(self.cbo_contract1_signed.currentData()),
            "contract1_no": (self.input_contract1_no.text() or "").strip() or None,
            "contract1_sign_date": self._date_edit_to_iso(
                self.input_contract1_sign_date
            ),
            "contract1_expire_date": self._date_edit_to_iso(
                self.input_contract1_expire_date
            ),
            "contract2_indefinite": bool(self.cbo_contract2_indefinite.currentData()),
            "contract2_no": (self.input_contract2_no.text() or "").strip() or None,
            "contract2_sign_date": self._date_edit_to_iso(
                self.input_contract2_sign_date
            ),
            "children_count": (
                None
                if int(self.spin_children.value()) < 0
                else int(self.spin_children.value())
            ),
            "child_dob_1": self._date_edit_to_iso(self.input_child_dob_1),
            "child_dob_2": self._date_edit_to_iso(self.input_child_dob_2),
            "child_dob_3": self._date_edit_to_iso(self.input_child_dob_3),
            "child_dob_4": self._date_edit_to_iso(self.input_child_dob_4),
            "note": (self.input_note.text() or "").strip() or None,
        }

    def set_status(self, message: str, ok: bool = True) -> None:
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};"
        )
        self.label_status.setText(message or "")

    def get_employee_code(self) -> str:
        raw = (self.input_code.text() or "").strip()
        # inputMask can leave spaces; keep digits only
        digits = "".join([c for c in raw if c.isdigit()])
        if not digits:
            return ""
        return digits.zfill(5)[:5]

    def set_employee_code(self, value: str) -> None:
        s = str(value or "").strip()
        digits = "".join([c for c in s if c.isdigit()])
        if not digits:
            self.input_code.setText("")
            return
        self.input_code.setText(digits.zfill(5)[:5])

    def get_full_name(self) -> str:
        return (self.input_name.text() or "").strip()

    def set_full_name(self, value: str) -> None:
        self.input_name.setText(value or "")
