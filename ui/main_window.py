"""ui.main_window

Cửa sổ chính của ứng dụng.

Theo .copilot_instructions:
- UI chỉ dùng PySide6
- Layout mặc định margin=0, padding=0
- MainWindow tối thiểu 1366x768
- Tài nguyên (icon/ảnh/stylesheet) phải load qua resource_path()
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
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
from ui.controllers.company_controllers import CompanyController
from ui.controllers.device_controllers import DeviceController
from ui.controllers.department_controllers import DepartmentController
from ui.controllers.holiday_controllers import HolidayController
from ui.controllers.title_controllers import TitleController
from ui.common.footer import Footer as CommonFooter
from ui.common.header import Header as CommonHeader
from ui.widgets.department_widgets import MainContent as DepartmentContent
from ui.widgets.department_widgets import TitleBar1 as DepartmentTitleBar1
from ui.widgets.department_widgets import TitleBar2 as DepartmentTitleBar2
from ui.widgets.holiday_widgets import MainContent as HolidayContent
from ui.widgets.holiday_widgets import TitleBar1 as HolidayTitleBar1
from ui.widgets.holiday_widgets import TitleBar2 as HolidayTitleBar2
from ui.widgets.title_widgets import MainContent, TitleBar1, TitleBar2
from ui.widgets.device_widgets import (
    MainContent as DeviceContent,
    TitleBar1 as DeviceTitleBar1,
    TitleBar2 as DeviceTitleBar2,
)


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

    def show_job_title_view(self) -> None:
        """Hiển thị màn hình Khai báo Chức danh."""
        title1 = TitleBar1("Khai báo Chức danh", "assets/images/job_title.svg", self)
        title2 = TitleBar2("Tổng: 0", self)
        content = MainContent(self)
        self.set_container_widgets([title1, title2, content])

        # Controller CRUD
        self._title_controller = TitleController(self.window(), title2, content)
        self._title_controller.bind()

    def show_department_view(self) -> None:
        """Hiển thị màn hình Khai báo Phòng ban."""
        title1 = DepartmentTitleBar1(
            "Khai báo Phòng ban", "assets/images/department.svg", self
        )
        title2 = DepartmentTitleBar2("Tổng: 0", self)
        content = DepartmentContent(self)
        self.set_container_widgets([title1, title2, content])

        self._department_controller = DepartmentController(
            self.window(), title2, content
        )
        self._department_controller.bind()

    def show_holiday_view(self) -> None:
        """Hiển thị màn hình Khai báo Ngày lễ."""
        title1 = HolidayTitleBar1("Khai báo Ngày lễ", "assets/images/holiday.svg", self)
        title2 = HolidayTitleBar2("Tổng: 0", self)
        content = HolidayContent(self)
        self.set_container_widgets([title1, title2, content])

        self._holiday_controller = HolidayController(self.window(), title2, content)
        self._holiday_controller.bind()

    def show_device_view(self) -> None:
        """Hiển thị màn hình Thêm Máy chấm công."""
        title1 = DeviceTitleBar1("Thêm Máy chấm công", "assets/images/device.svg", self)
        title2 = DeviceTitleBar2("Tổng: 0", self)
        content = DeviceContent(self)
        self.set_container_widgets([title1, title2, content])

        self._device_controller = DeviceController(self.window(), title2, content)
        self._device_controller.bind()


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
        self._init_ui()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện người dùng."""
        # Set tiêu đề cửa sổ
        self.setWindowTitle("Ứng Dụng Desktop")

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

        # Controller cho dialog công ty
        self._company_controller = CompanyController(self)
        self.header.action_triggered.connect(self._on_header_action_triggered)

        main_layout.addWidget(self.header)
        main_layout.addWidget(self.container, 1)
        main_layout.addWidget(self.footer)

        # Căn giữa cửa sổ trên màn hình
        self._center_window()

    def _on_header_action_triggered(self, action_text: str) -> None:
        """Điều phối sự kiện click phím chức năng trên Header."""
        if action_text == "Thông tin\nCông ty" and self._company_controller is not None:
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

        # HeaderController currently has a space before newline in this label.
        if (
            action_text == "Thêm Máy \nchấm công"
            or action_text == "Thêm Máy\nchấm công"
        ):
            self.container.show_device_view()
            return

        if action_text == "Thoát\nỨng dụng":
            QApplication.quit()
            return

    def _center_window(self) -> None:
        """Căn giữa cửa sổ trên màn hình."""
        screen_geometry = self.screen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())
