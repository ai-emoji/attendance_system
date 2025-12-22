"""ui.dialog.import_employee_dialog

Dialog Nhập nhân viên từ Excel.

Cấu trúc UI:
- Input: đường dẫn file Excel
- Buttons: Xem mẫu, Xem thông tin, Cập nhập vào CSDL
- Bảng preview (giống EmployeeTable ở employee_widgets)
- Checkbox: Thêm mới nhân viên khi chưa có dữ liệu

Luồng:
- Xem mẫu: lưu file mẫu Excel
- Xem thông tin: đọc Excel và đổ vào bảng preview
- Cập nhập vào CSDL: import vào DB theo trạng thái checkbox
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from core.resource import (
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    MAIN_CONTENT_BG_COLOR,
    UI_FONT,
    resource_path,
)

from services.employee_services import EmployeeService
from ui.widgets.employee_widgets import EmployeeTable
from ui.dialog.title_dialog import MessageDialog


class ImportEmployeeDialog(QDialog):
    def __init__(
        self,
        service: EmployeeService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service or EmployeeService()
        self._preview_rows: list[dict] = []

        self._init_ui()

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle("Nhập nhân viên")
        self.setMinimumSize(1100, 720)
        self.resize(1100, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.setStyleSheet(f"background-color: {MAIN_CONTENT_BG_COLOR};")

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

        self.table = EmployeeTable(self)
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        bottom = QWidget(self)
        bottom_l = QHBoxLayout(bottom)
        bottom_l.setContentsMargins(0, 0, 0, 0)
        bottom_l.setSpacing(10)

        self.chk_only_new = QCheckBox("Thêm mới nhân viên khi chưa có dữ liệu", self)
        self.chk_only_new.setFont(font_normal)
        # Default ON: most users import into an empty DB and expect data to be inserted.
        self.chk_only_new.setChecked(True)
        self.chk_only_new.setStyleSheet(
            "\n".join(
                [
                    f"QCheckBox {{ color: {COLOR_TEXT_PRIMARY}; }}",
                    "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; }",
                    f"QCheckBox::indicator:unchecked {{ border: 1px solid {COLOR_BORDER}; background: {INPUT_COLOR_BG}; }}",
                    f"QCheckBox::indicator:checked {{ border: 1px solid {COLOR_BUTTON_PRIMARY}; background: {COLOR_BUTTON_PRIMARY}; }}",
                ]
            )
        )

        self.label_status = QLabel("", self)
        self.label_status.setFont(font_normal)
        self.label_status.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        bottom_l.addWidget(self.chk_only_new, 0)
        bottom_l.addStretch(1)
        bottom_l.addWidget(self.label_status, 1)

        root.addWidget(top, 0)
        root.addWidget(self.table, 1)
        root.addWidget(bottom, 0)

        self.btn_view_template.clicked.connect(self._on_view_template)
        self.btn_view_info.clicked.connect(self._on_view_info)
        self.btn_apply_db.clicked.connect(self._on_apply_db)

    def eventFilter(self, obj, event) -> bool:
        if (
            obj is getattr(self, "input_excel_path", None)
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            if event.button() == Qt.MouseButton.LeftButton:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Chọn file Excel nhân viên",
                    "",
                    "Excel (*.xlsx)",
                )
                if file_path:
                    self.input_excel_path.setText(file_path)
                return True
        return super().eventFilter(obj, event)

    def _set_status(self, text: str, ok: bool) -> None:
        self.label_status.setText(str(text or ""))
        self.label_status.setStyleSheet(
            f"color: {COLOR_SUCCESS};" if ok else f"color: {COLOR_ERROR};"
        )

    def _on_view_template(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Tải file mẫu nhân viên",
            "employees_template.xlsx",
            "Excel (*.xlsx)",
        )
        if not file_path:
            return

        ok, msg = self._service.export_employee_template_xlsx(file_path)
        self._set_status(msg, ok=ok)

    def _on_view_info(self) -> None:
        path = str(self.input_excel_path.text() or "").strip()
        ok, msg, rows = self._service.read_employees_from_xlsx(path)
        self._set_status(msg, ok=ok)
        if not ok:
            return
        self._preview_rows = rows
        self.table.set_rows(rows)

    def _on_apply_db(self) -> None:
        if not self._preview_rows:
            # Try reading from file path if user hasn't previewed
            path = str(self.input_excel_path.text() or "").strip()
            ok, msg, rows = self._service.read_employees_from_xlsx(path)
            if not ok:
                self._set_status(msg, ok=False)
                return
            self._preview_rows = rows
            self.table.set_rows(rows)

        only_new = bool(self.chk_only_new.isChecked())

        total = len(self._preview_rows)
        progress = QProgressDialog("Đang cập nhập vào CSDL...", "Hủy", 0, total, self)
        progress.setWindowTitle("Nhập nhân viên")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def on_progress(i: int, ok_row: bool, code: str, message: str) -> None:
            progress.setValue(i)
            progress.setLabelText(
                f"{i}/{total} - {code or '(không mã)'} - {'OK' if ok_row else 'FAIL'}"
            )
            if progress.wasCanceled():
                raise RuntimeError("Đã hủy.")

        try:
            ok, msg = self._service.import_employees_rows(
                self._preview_rows,
                only_new=only_new,
                progress_cb=on_progress,
            )
        except Exception as exc:
            progress.close()
            self._set_status(str(exc), ok=False)
            try:
                MessageDialog.info(self, "Nhập nhân viên", str(exc))
            except Exception:
                pass
            return
        finally:
            try:
                progress.setValue(total)
            except Exception:
                pass

        self._set_status(msg, ok=ok)

        # Always show 1 dialog summarizing counts.
        try:
            MessageDialog.info(self, "Nhập nhân viên", msg)
        except Exception:
            pass

        if ok:
            self.accept()
