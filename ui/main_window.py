"""ui.main_window

Cửa sổ chính của ứng dụng.

Theo .copilot_instructions:
- UI chỉ dùng PySide6
- Layout mặc định margin=0, padding=0
- MainWindow tối thiểu 1366x768
- Tài nguyên (icon/ảnh/stylesheet) phải load qua resource_path()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    CONTAINER_MIN_HEIGHT,
    MIN_MAINWINDOW_HEIGHT,
    MIN_MAINWINDOW_WIDTH,
    set_window_icon,
)
from core.ui_settings import update_shift_attendance_state
from ui.common.footer import Footer as CommonFooter
from ui.common.header import Header as CommonHeader


if TYPE_CHECKING:
    from ui.controllers.absence_restore_controllers import AbsenceRestoreController
    from ui.controllers.arrange_schedule_controllers import ArrangeScheduleController
    from ui.controllers.backup_controllers import BackupController
    from ui.controllers.company_controllers import CompanyController
    from ui.controllers.csdl_controllers import CSDLController
    from ui.controllers.declare_work_shift_controllers import DeclareWorkShiftController
    from ui.controllers.department_controllers import DepartmentController
    from ui.controllers.device_controllers import DeviceController
    from ui.controllers.download_attendance_controllers import (
        DownloadAttendanceController,
    )
    from ui.controllers.employee_controllers import EmployeeController
    from ui.controllers.holiday_controllers import HolidayController
    from ui.controllers.schedule_work_controllers import ScheduleWorkController
    from ui.controllers.shift_attendance_controllers import ShiftAttendanceController
    from ui.controllers.title_controllers import TitleController


class Header(CommonHeader):
    """Header của ứng dụng (kế thừa triển khai trong ui.common.header)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)


class Container(QWidget):
    """Khu vực nội dung chính của ứng dụng."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title_controller: TitleController | None = None
        self._department_controller: DepartmentController | None = None
        self._holiday_controller: HolidayController | None = None
        self._device_controller: DeviceController | None = None
        self._declare_work_shift_controller: DeclareWorkShiftController | None = None
        self._employee_controller: EmployeeController | None = None
        self._download_attendance_controller: DownloadAttendanceController | None = None
        self._shift_attendance_controller: ShiftAttendanceController | None = None
        self._arrange_schedule_controller: ArrangeScheduleController | None = None
        self._schedule_work_controller: ScheduleWorkController | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("Container")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(CONTAINER_MIN_HEIGHT)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._placeholder = QLabel("Nội dung")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._placeholder, 1)

    def set_container_widgets(self, widgets: list[QWidget]) -> None:
        """Clear container and show provided widgets top-to-bottom."""
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for w in widgets:
            self._layout.addWidget(w)
            self._layout.setStretchFactor(w, 0)

        # Widget cuối (content) chiếm phần còn lại
        if widgets:
            self._layout.setStretchFactor(widgets[-1], 1)

    @staticmethod
    def _defer_bind(controller: object) -> None:
        """Defer controller.bind() to next event-loop tick so UI can render first."""

        bind = getattr(controller, "bind", None)
        if callable(bind):
            QTimer.singleShot(0, bind)

    def show_job_title_view(self) -> None:
        """Hiển thị màn hình Khai báo Chức danh."""
        from ui.controllers.title_controllers import TitleController
        from ui.widgets.title_widgets import MainContent, TitleBar1, TitleBar2

        title1 = TitleBar1("Khai báo Chức danh", "assets/images/job_title.svg", self)
        title2 = TitleBar2("Tổng: 0", self)
        content = MainContent(self)
        self.set_container_widgets([title1, title2, content])

        # Controller CRUD
        ctrl = TitleController(self.window(), title2, content)
        self._title_controller = ctrl
        self._defer_bind(ctrl)

    def show_department_view(self) -> None:
        """Hiển thị màn hình Khai báo Phòng ban."""
        from ui.controllers.department_controllers import DepartmentController
        from ui.widgets.department_widgets import (
            MainContent as DepartmentContent,
            TitleBar1 as DepartmentTitleBar1,
            TitleBar2 as DepartmentTitleBar2,
        )

        title1 = DepartmentTitleBar1(
            "Khai báo Phòng ban", "assets/images/department.svg", self
        )
        title2 = DepartmentTitleBar2("Tổng: 0", self)
        content = DepartmentContent(self)
        self.set_container_widgets([title1, title2, content])

        ctrl = DepartmentController(self.window(), title2, content)
        self._department_controller = ctrl
        self._defer_bind(ctrl)

    def show_holiday_view(self) -> None:
        """Hiển thị màn hình Khai báo Ngày lễ."""
        from ui.controllers.holiday_controllers import HolidayController
        from ui.widgets.holiday_widgets import (
            MainContent as HolidayContent,
            TitleBar1 as HolidayTitleBar1,
            TitleBar2 as HolidayTitleBar2,
        )

        title1 = HolidayTitleBar1("Khai báo Ngày lễ", "assets/images/holiday.svg", self)
        title2 = HolidayTitleBar2("Tổng: 0", self)
        content = HolidayContent(self)
        self.set_container_widgets([title1, title2, content])

        ctrl = HolidayController(self.window(), title2, content)
        self._holiday_controller = ctrl
        self._defer_bind(ctrl)

    def show_device_view(self) -> None:
        """Hiển thị màn hình Thêm Máy chấm công."""
        from ui.controllers.device_controllers import DeviceController
        from ui.widgets.device_widgets import (
            MainContent as DeviceContent,
            TitleBar1 as DeviceTitleBar1,
            TitleBar2 as DeviceTitleBar2,
        )

        title1 = DeviceTitleBar1("Thêm Máy chấm công", "assets/images/device.svg", self)
        title2 = DeviceTitleBar2("Tổng: 0", self)
        content = DeviceContent(self)
        self.set_container_widgets([title1, title2, content])

        ctrl = DeviceController(self.window(), title2, content)
        self._device_controller = ctrl
        self._defer_bind(ctrl)

    def show_declare_work_shift_view(self) -> None:
        """Hiển thị màn hình Khai báo Ca làm việc."""
        from ui.controllers.declare_work_shift_controllers import (
            DeclareWorkShiftController,
        )
        from ui.widgets.declare_work_shift_widgets import (
            MainContent as DeclareWorkShiftContent,
            TitleBar1 as DeclareWorkShiftTitleBar1,
            TitleBar2 as DeclareWorkShiftTitleBar2,
        )

        title1 = DeclareWorkShiftTitleBar1(
            "Khai báo Ca làm việc", "assets/images/declare_work_shift.svg", self
        )
        title2 = DeclareWorkShiftTitleBar2("Tổng: 0", self)
        content = DeclareWorkShiftContent(self)
        self.set_container_widgets([title1, title2, content])

        ctrl = DeclareWorkShiftController(self.window(), title2, content)
        self._declare_work_shift_controller = ctrl
        self._defer_bind(ctrl)

    def show_employee_view(self) -> None:
        """Hiển thị màn hình Thông tin Nhân viên."""
        from ui.controllers.employee_controllers import EmployeeController
        from ui.widgets.employee_widgets import MainContent as EmployeeContent
        from ui.widgets.employee_widgets import TitleBar1 as EmployeeTitleBar1

        title1 = EmployeeTitleBar1(
            "Thông tin Nhân viên", "assets/images/employee.svg", self
        )
        content = EmployeeContent(self)
        self.set_container_widgets([title1, content])

        ctrl = EmployeeController(self.window(), content)
        self._employee_controller = ctrl
        self._defer_bind(ctrl)

    def show_download_attendance_view(self) -> None:
        """Hiển thị màn hình Tải dữ liệu Máy chấm công."""
        from ui.controllers.download_attendance_controllers import (
            DownloadAttendanceController,
        )
        from ui.widgets.download_attendance_widgets import (
            MainContent as DownloadAttendanceContent,
            TitleBar1 as DownloadAttendanceTitleBar1,
            TitleBar2 as DownloadAttendanceTitleBar2,
        )

        title1 = DownloadAttendanceTitleBar1(
            "Tải dữ liệu Máy chấm công", "assets/images/download_attendance.svg", self
        )
        title2 = DownloadAttendanceTitleBar2(self)
        content = DownloadAttendanceContent(self)
        self.set_container_widgets([title1, title2, content])

        ctrl = DownloadAttendanceController(self.window(), title2, content)
        self._download_attendance_controller = ctrl
        self._defer_bind(ctrl)

    def show_shift_attendance_view(self) -> None:
        """Hiển thị màn hình Chấm công Theo ca."""
        from ui.controllers.shift_attendance_controllers import (
            ShiftAttendanceController,
        )
        from ui.widgets.shift_attendance_widgets import (
            TitleBar1 as ShiftAttendanceTitleBar1,
            MainContent1 as ShiftAttendanceContent1,
            MainContent2 as ShiftAttendanceContent2,
        )

        title1 = ShiftAttendanceTitleBar1(
            "Chấm công Theo ca", "assets/images/shift_attendance.svg", self
        )

        # Gói 2 phần content vào một widget để Container chỉ stretch 1 vùng nội dung.
        content_root = QWidget(self)
        content_root.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        content_layout = QVBoxLayout(content_root)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical, content_root)
        splitter.setChildrenCollapsible(False)

        content1 = ShiftAttendanceContent1(splitter)
        content2 = ShiftAttendanceContent2(splitter)
        splitter.addWidget(content1)
        splitter.addWidget(content2)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        # Tỉ lệ mặc định: phần danh sách NV nhỏ hơn phần lưới chấm công.
        # Tránh setSizes([1,1]) (pixel) vì có thể làm pane bị co/"ẩn" khi layout cập nhật.
        def _init_splitter_sizes() -> None:
            try:
                h = int(splitter.size().height())
            except Exception:
                h = 0
            try:
                if h > 0:
                    top = max(220, int(h * 0.35))
                    bottom = max(220, h - top)
                    splitter.setSizes([top, bottom])
                else:
                    splitter.setSizes([280, 520])
            except Exception:
                pass

        try:
            QTimer.singleShot(0, _init_splitter_sizes)
        except Exception:
            try:
                _init_splitter_sizes()
            except Exception:
                pass

        content_layout.addWidget(splitter, 1)

        self.set_container_widgets([title1, content_root])

        # Controller: load phòng ban + danh sách nhân viên cho MainContent1
        ctrl = ShiftAttendanceController(self.window(), content1, content2)
        self._shift_attendance_controller = ctrl
        self._defer_bind(ctrl)

    def show_arrange_schedule_view(self) -> None:
        """Hiển thị màn hình Sắp xếp lịch Làm việc."""
        from ui.controllers.arrange_schedule_controllers import (
            ArrangeScheduleController,
        )
        from ui.widgets.arrange_schedule_widgets import ArrangeScheduleView

        view = ArrangeScheduleView(self)
        self.set_container_widgets([view])

        # Controller (hiện tại stub/no-op theo yêu cầu)
        ctrl = ArrangeScheduleController(self.window(), view.left, view.right)
        self._arrange_schedule_controller = ctrl
        self._defer_bind(ctrl)

    def show_schedule_work_view(self) -> None:
        """Hiển thị màn hình Sắp xếp lịch Làm việc."""
        from ui.controllers.schedule_work_controllers import ScheduleWorkController
        from ui.widgets.schedule_work_widgets import ScheduleWorkView

        view = ScheduleWorkView(self)
        self.set_container_widgets([view])

        ctrl = ScheduleWorkController(self.window(), view)
        self._schedule_work_controller = ctrl
        self._defer_bind(ctrl)


class Footer(CommonFooter):
    """Footer của ứng dụng (kế thừa triển khai trong ui.common.footer)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)


class MainWindow(QMainWindow):
    """
    Lớp cửa sổ chính của ứng dụng.

    Trách nhiệm:
    - Quản lý bố cục chính
    - Set kích thước cửa sổ tối thiểu
    - Điều phối các thành phần UI
    """

    def __init__(self) -> None:
        """Khởi tạo cửa sổ chính."""
        super().__init__()
        self._company_controller: CompanyController | None = None
        self._csdl_controller: CSDLController | None = None
        self._backup_controller: BackupController | None = None
        self._absence_restore_controller: AbsenceRestoreController | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện người dùng."""
        # Set tiêu đề cửa sổ
        self.setWindowTitle("Phần mềm chấm công Tam Niên")

        # Gán icon app (load qua resource_path)
        set_window_icon(self)

        # Set kích thước cửa sổ tối thiểu
        self.setMinimumWidth(MIN_MAINWINDOW_WIDTH)
        self.setMinimumHeight(MIN_MAINWINDOW_HEIGHT)

        # Set kích thước cửa sổ mặc định
        self.resize(MIN_MAINWINDOW_WIDTH, MIN_MAINWINDOW_HEIGHT)

        # Tạo widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Tạo layout chính
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 3 khu vực chính: Header - Container - Footer
        self.header = Header(central_widget)
        self.container = Container(central_widget)
        self.footer = Footer(central_widget)

        # Reset filter Shift Attendance khi thoát app (kể cả trường hợp bấm "Thoát\nỨng dụng"
        # gọi QApplication.quit() và không đi qua closeEvent như kỳ vọng).
        try:
            app = QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self._on_about_to_quit)
        except Exception:
            pass

        # Controller cho dialog công ty
        # Lazy-init controllers on demand to keep startup fast.
        self._company_controller = None
        self._csdl_controller = None
        self._backup_controller = None
        self._absence_restore_controller = None
        self.header.action_triggered.connect(self._on_header_action_triggered)

        main_layout.addWidget(self.header)
        main_layout.addWidget(self.container, 1)
        main_layout.addWidget(self.footer)

        # Căn giữa cửa sổ trên màn hình
        self._center_window()

    def _reset_shift_attendance_filters_on_exit(self) -> None:
        try:
            update_shift_attendance_state(
                content1={
                    "department_id": None,
                    "title_id": None,
                    "search_by_data": "auto",
                    "search_text": "",
                    "date_from": "",
                    "date_to": "",
                }
            )
        except Exception:
            # Best-effort
            pass

    def _on_about_to_quit(self) -> None:
        # Đảm bảo reset filter là thao tác cuối trước khi app thoát.
        self._reset_shift_attendance_filters_on_exit()

    def _on_header_action_triggered(self, action_text: str) -> None:
        """Điều phối sự kiện click phím chức năng trên Header."""
        action_text = str(action_text or "").strip()
        logging.getLogger(__name__).info("Header action clicked: %s", action_text)

        # Note: UX requirement changed - even without DB connection/config,
        # the app should still allow opening screens and show UI quickly.
        # Controllers handle DB errors and will show empty UI when offline.

        if action_text == "Thông tin\nCông ty" and self._company_controller is not None:
            self._company_controller.show_dialog()
            return

        if action_text == "Thông tin\nCông ty":
            if self._company_controller is None:
                from ui.controllers.company_controllers import CompanyController

                self._company_controller = CompanyController(self)
            self._company_controller.show_dialog()
            return

        if action_text == "Khai báo\nChức danh":
            self.container.show_job_title_view()
            return

        if action_text == "Khai báo\nPhòng ban":
            self.container.show_department_view()
            return

        if action_text == "Khai báo\nNgày lễ":
            self.container.show_holiday_view()
            return

        if action_text == "Thông tin\nNhân viên":
            self.container.show_employee_view()
            return

        if action_text == "Khai báo\nCa làm việc":
            self.container.show_declare_work_shift_view()
            return

        if action_text == "Ký hiệu\nChấm công":
            from ui.dialog.attendance_symbol_dialog import AttendanceSymbolDialog

            dlg = AttendanceSymbolDialog(self)
            dlg.exec()
            return

        # HeaderController currently has a space before newline in this label.
        if (
            action_text == "Thêm Máy \nchấm công"
            or action_text == "Thêm Máy\nchấm công"
        ):
            self.container.show_device_view()
            return

        if action_text == "Tải dữ liệu\nMáy chấm công":
            self.container.show_download_attendance_view()
            return

        if action_text == "Chấm công\nTheo ca":
            self.container.show_shift_attendance_view()
            return

        if action_text == "khai báo lịch\nLàm việc":
            self.container.show_arrange_schedule_view()
            return

        if action_text == "Sắp xếp lịch\nLàm việc":
            self.container.show_schedule_work_view()
            return

        if action_text == "Thoát\nỨng dụng":
            QApplication.quit()
            return

        if action_text == "Kết nối\nCSDL SQL" and self._csdl_controller is not None:
            self._csdl_controller.show_dialog()
            return

        if action_text == "Kết nối\nCSDL SQL":
            if self._csdl_controller is None:
                from ui.controllers.csdl_controllers import CSDLController

                self._csdl_controller = CSDLController(self)
            self._csdl_controller.show_dialog()
            return

        if action_text == "Sao lưu\nDữ liệu" and self._backup_controller is not None:
            self._backup_controller.show_dialog()
            return

        if action_text == "Sao lưu\nDữ liệu":
            if self._backup_controller is None:
                from ui.controllers.backup_controllers import BackupController

                self._backup_controller = BackupController(self)
            self._backup_controller.show_dialog()
            return

        if (
            action_text == "Khôi phục\nDữ liệu"
            and self._absence_restore_controller is not None
        ):
            self._absence_restore_controller.show_dialog()
            return

        if action_text == "Khôi phục\nDữ liệu":
            if self._absence_restore_controller is None:
                from ui.controllers.absence_restore_controllers import (
                    AbsenceRestoreController,
                )

                self._absence_restore_controller = AbsenceRestoreController(self)
            self._absence_restore_controller.show_dialog()
            return

        if action_text == "Cài đặt":
            from ui.dialog.settings_dialog import SettingsDialog

            dlg = SettingsDialog(self)
            dlg.exec()
            return

    def _center_window(self) -> None:
        """Căn giữa cửa sổ trên màn hình."""
        screen_geometry = self.screen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def closeEvent(self, event) -> None:
        """Khi đóng phần mềm.

        - Tự động xóa dữ liệu tải tạm trong download_attendance.
        - Reset filter tìm kiếm của màn Chấm công Theo ca cho lần mở sau.
        """

        try:
            from services.download_attendance_services import DownloadAttendanceService

            DownloadAttendanceService().clear_download_attendance()
        except Exception:
            # Best-effort: không chặn app đóng nếu xóa thất bại
            pass

        # Để tránh trường hợp các widget con (ShiftAttendance) persist state trong hideEvent
        # khi app đang đóng, reset state sau khi window đã close.
        try:
            super().closeEvent(event)
        finally:
            self._reset_shift_attendance_filters_on_exit()
