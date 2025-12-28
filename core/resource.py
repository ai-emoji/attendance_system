"""
Module quản lý tài nguyên ứng dụng.

Bao gồm:
- Hằng số UI (font, màu sắc, kích thước)
- Hàm resource_path() để load icon, ảnh, stylesheet
- Các constants khác
"""

import sys
import os
import logging
from pathlib import Path


_APP_ICON = None


# ============================================================================
# 1️⃣ KÍCH THƯỚC CỬA SỔ CHÍNH
# ============================================================================
MIN_MAINWINDOW_WIDTH = 1600
MIN_MAINWINDOW_HEIGHT = 900

# Dialog Thông tin công ty
COMPANY_DIALOG_WIDTH = 500
COMPANY_DIALOG_HEIGHT = 350

# Dialog Khai báo Chức danh
TITLE_DIALOG_WIDTH = 520
TITLE_DIALOG_HEIGHT = 200
TITLE_NAME_MAX_LENGTH = 255

# Dialog Khai báo Ngày lễ
HOLIDAY_DIALOG_WIDTH = 520
HOLIDAY_DIALOG_HEIGHT = 200
HOLIDAY_INFO_MAX_LENGTH = 255

# Dialog Khai báo Phòng ban
DEPARTMENT_DIALOG_WIDTH = 520
DEPARTMENT_DIALOG_HEIGHT = 250
DEPARTMENT_NAME_MAX_LENGTH = 255
DEPARTMENT_NOTE_MAX_LENGTH = 2000

# Dialog dùng chung (thông báo/xác nhận) - không dùng QMessageBox
MESSAGE_DIALOG_WIDTH = 520
MESSAGE_DIALOG_HEIGHT = 150

# cấu trúc Container
CONTAINER_MIN_HEIGHT = 588
CONTAINER_SHIFT_ATTENDANCE = 274
MAIN_CONTENT_MIN_HEIGHT = 508
TITLE_HEIGHT = 40
BG_TITLE_1_HEIGHT = "#E6E6E6"
TITLE_2_HEIGHT = 40
BG_TITLE_2_HEIGHT = "#FFFFFF"
MAIN_CONTENT_BG_COLOR = "#FFFFFF"
ROW_HEIGHT = 40
EVEN_ROW_BG_COLOR = "#FFFFFF"
ODD_ROW_BG_COLOR = "#E2E1E1"
HOVER_ROW_BG_COLOR = "#AEDEFC"
GRID_LINES_COLOR = "#000000"


# ============================================================================
# 2️⃣ FONT & TYPOGRAPHY
# ============================================================================
UI_FONT = "Roboto"
TITLE_FONT = 18
CONTENT_FONT = 13
BUTTON_FONT = 14
TABLE_FONT = 14


# ============================================================================
# 2️⃣1️⃣ THÔNG TIN ỨNG DỤNG
# ============================================================================
APP_INFO = "Thông tin"
APP_VERSION = "1.0.2"

# Font weight
FONT_WEIGHT_NORMAL = 400
FONT_WEIGHT_SEMIBOLD = 500
FONT_WEIGHT_BOLD = 600


# ============================================================================
# 3️⃣ LAYOUT & SPACING
# ============================================================================
MARGIN_DEFAULT = 0
PADDING_DEFAULT = 0
ROW_SPACING = 6


# ============================================================================
# 4️⃣ MÀU SẮC (Hex)
# ============================================================================
# Màu nền
COLOR_BG_HEADER = "#FFFFFF"
COLOR_BG_CONTAINER = "#F5F5F5"
COLOR_BG_FOOTER = "#8CA9FF"

# Màu chữ
COLOR_TEXT_PRIMARY = "#000000"
COLOR_TEXT_SECONDARY = "#666666"
COLOR_TEXT_LIGHT = "#FFFFFF"


# Gợi ý màu cho các button chức năng phụ (Save, Cancel, v.v.)
COLOR_BUTTON_SAVE = "#6C757D"  # Xám trung tính (Save)
COLOR_BUTTON_SAVE_HOVER = "#5A6268"  # Xám đậm hơn khi hover
COLOR_BUTTON_CANCEL = "#D9534F"  # Đỏ nhạt (Cancel)
COLOR_BUTTON_CANCEL_HOVER = "#C9302C"  # Đỏ đậm khi hover
COLOR_BUTTON_ACTIVE = "#0056b3"  # Xanh dương đậm (Active)
COLOR_BUTTON_ACTIVE_HOVER = "#0069D9"  # Xanh dương sáng hơn khi hover
COLOR_BUTTON_DISABLED = "#CCCCCC"  # Xám nhạt (Disabled)
COLOR_BUTTON_DISABLED_HOVER = "#CCCCCC"  # Không đổi khi hover
COLOR_BUTTON_WARNING = "#FFC107"  # Vàng cảnh báo
COLOR_BUTTON_WARNING_HOVER = "#E0A800"  # Vàng đậm khi hover
COLOR_BUTTON_PRIMARY = "#007BFF"
COLOR_BUTTON_PRIMARY_HOVER = "#0056b3"

# Màu border
COLOR_BORDER = "#000000"
COLOR_BORDER_FOCUS = "#007BFF"

# Màu trạng thái
COLOR_SUCCESS = "#28A745"
COLOR_ERROR = "#DC3545"
COLOR_WARNING = "#FFC107"
COLOR_INFO = "#17A2B8"


# INPUT
INPUT_WIDTH_DEFAULT = 50
INPUT_HEIGHT_DEFAULT = 35
INPUT_COLOR_BG = "#FFFFFF"
INPUT_COLOR_BORDER = "#000000"
INPUT_COLOR_BORDER_FOCUS = "#007BFF"
COLOR_TEXT_INPUT = "#000000"

# ============================================================================
# 5️⃣ CURSOR
# ============================================================================
CURSOR_POINTING_HAND = "PointingHandCursor"
CURSOR_IBEAM = "IBeamCursor"
CURSOR_FORBIDDEN = "ForbiddenCursor"
CURSOR_DEFAULT = "ArrowCursor"


# ============================================================================
# 6️⃣ ICON SIZE
# ============================================================================
ICON_SIZE_SMALL = 16
ICON_SIZE_MEDIUM = 24
ICON_SIZE_LARGE = 32


# ============================================================================
# 7️⃣ HÀM RESOURCE_PATH - LOAD TÀI NGUYÊN
# ============================================================================


def resource_path(relative_path: str) -> str:
    """
    Trả về đường dẫn tuyệt đối tới tài nguyên.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        # Không dùng __file__. Ưu tiên thư mục chứa entrypoint (main.py) khi chạy source.
        try:
            entry_point = Path(sys.argv[0]).resolve()
            base_path = entry_point.parent if str(entry_point) else Path.cwd()
        except Exception:
            base_path = Path.cwd()

    full_path = (Path(base_path) / relative_path).resolve()
    return str(full_path)


def get_icon_path(icon_name: str) -> str:
    """
    Lấy đường dẫn icon từ folder assets/icons.
    """
    return resource_path(f"assets/icons/{icon_name}")


def get_image_path(image_name: str) -> str:
    """
    Lấy đường dẫn ảnh từ folder assets/images.
    """
    return resource_path(f"assets/images/{image_name}")


def get_stylesheet_path(style_file: str) -> str:
    """
    Lấy đường dẫn stylesheet từ folder assets.
    """
    return resource_path(f"assets/{style_file}")


def get_database_path(db_file: str = "app.mysql") -> str:
    """
    Lấy đường dẫn database từ folder database.
    """
    return resource_path(f"database/{db_file}")


def get_log_path(log_file: str = "debug.log") -> str:
    """
    Lấy đường dẫn log file từ folder log.
    """
    return resource_path(f"log/{log_file}")


def read_stylesheet(style_file: str) -> str:
    """
    Đọc nội dung stylesheet (QSS).
    """
    stylesheet_path = get_stylesheet_path(style_file)
    try:
        with open(stylesheet_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Stylesheet không tìm thấy: {stylesheet_path}")
        return ""


# ============================================================================
# 8️⃣ ICON SVG PATHS
# ============================================================================

# Icon Algin text
ICON_ALGIN_LEFT = "assets/images/align_left.svg"
ICON_ALGIN_CENTER = "assets/images/align_center.svg"
ICON_ALGIN_RIGHT = "assets/images/align_right.svg"
ICON_BOLD = "assets/images/bold.svg"
ICON_ITALIC = "assets/images/italic.svg"
ICON_UNDERLINE = "assets/images/under_line.svg"

# Icon App (Main window)
ICON_APP = "assets/icons/app.ico"
APP_ICO = ICON_APP

# Icon Dashboard/Home
ICON_HOME = "assets/images/home.svg"
ICON_DASHBOARD = "assets/images/dashboard.svg"

# Icon CRUD
ICON_ADD = "assets/images/add.svg"
ICON_EDIT = "assets/images/edit.svg"
ICON_DELETE = "assets/images/delete.svg"
ICON_VIEW = "assets/images/view.svg"
ICON_TOTAL = "assets/images/total.svg"

# Icon Search/Filter
ICON_SEARCH = "assets/images/search.svg"
ICON_FILTER = "assets/images/filter.svg"
ICON_CLEAR = "assets/images/clear.svg"

# Icon Chấm công
ICON_CHECKIN = "assets/images/checkin.svg"
ICON_CHECKOUT = "assets/images/checkout.svg"
ICON_CLOCK = "assets/images/clock.svg"
ICON_CALENDAR = "assets/images/calendar.svg"
ICON_DECLARE_TIME = "assets/images/declare_time.svg"

# Icon User/Profile
ICON_PROFILE = "assets/images/profile.svg"
ICON_USER = "assets/images/user.svg"
ICON_USERS = "assets/images/users.svg"
ICON_LOGOUT = "assets/images/logout.svg"
ICON_LOGIN = "assets/images/login.svg"

# Icon Status
ICON_CHECK = "assets/images/check.svg"
ICON_CLOSE = "assets/images/close.svg"
ICON_CANCEL = "assets/images/cancel.svg"
ICON_WARNING = "assets/images/warning.svg"
ICON_ERROR = "assets/images/error.svg"
ICON_SUCCESS = "assets/images/success.svg"
ICON_INFO = "assets/images/info.svg"

# Icon File/Export
ICON_SAVE = "assets/images/save.svg"
ICON_DOWNLOAD = "assets/images/download.svg"
ICON_UPLOAD = "assets/images/upload.svg"
ICON_EXPORT = "assets/images/export.svg"
ICON_PRINT = "assets/images/print.svg"
ICON_EXCEL = "assets/images/excel.svg"
ICON_IMPORT = "assets/images/import.svg"

# Icon Settings/Configuration
ICON_SETTINGS = "assets/images/settings.svg"
ICON_CONFIG = "assets/images/config.svg"
ICON_HELP = "assets/images/help.svg"
ICON_ABOUT = "assets/images/about.svg"

# Icon Navigation
ICON_BACK = "assets/images/back.svg"
ICON_NEXT = "assets/images/next.svg"
ICON_MENU = "assets/images/menu.svg"
ICON_CLOSE_MENU = "assets/images/close_menu.svg"
ICON_DROPDOWN = "assets/images/dropdown.svg"
ICON_LIST = "assets/images/list.svg"
ICON_ARRANGE_SCHEDULE = "assets/images/arrange_schedule.svg"
ICON_SCHEDULE_WORK = "assets/images/schedule_work.svg"

# Icon Refresh/Reload
ICON_REFRESH = "assets/images/refresh.svg"
ICON_RELOAD = "assets/images/reload.svg"
ICON_LOADING = "assets/images/loading.svg"

# Icon Report/Statistics
ICON_REPORT = "assets/images/report.svg"
ICON_CHART = "assets/images/chart.svg"
ICON_STATISTICS = "assets/images/statistics.svg"
ICON_SUMMARY = "assets/images/summary.svg"

# Icon Notification
ICON_BELL = "assets/images/bell.svg"
ICON_NOTIFICATION = "assets/images/notification.svg"


# ============================================================================
# 8️⃣ CONSTANTS KHÁC
# ============================================================================

# Timeout
DB_CONNECTION_TIMEOUT = 5  # giây
DB_QUERY_TIMEOUT = 30  # giây

# Số lượng hàng mặc định
DEFAULT_PAGE_SIZE = 20

# Định dạng ngày/giờ
DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"


# ============================================================================
# 9️⃣ VALIDATION & ICON MANAGEMENT
# ============================================================================


def validate_resource_exists(resource_path_str: str) -> bool:
    """
    Kiểm tra file tài nguyên có tồn tại không.
    """
    return os.path.exists(resource_path_str)


def set_window_icon(window, icon_path: str = None) -> None:
    """Set icon cho 1 cửa sổ.

    - Nếu không truyền `icon_path`, dùng icon hiện tại của ứng dụng (QApplication.windowIcon).
    - Nếu truyền `icon_path`, cập nhật cả icon toàn ứng dụng để các cửa sổ khác đồng bộ.
    """

    from PySide6.QtGui import QIcon

    logger = logging.getLogger(__name__)

    try:
        if icon_path is None:
            icon = get_app_icon()
        else:
            resolved = (
                resource_path(icon_path) if not os.path.isabs(icon_path) else icon_path
            )
            if not validate_resource_exists(resolved):
                logger.warning("Icon không tìm thấy: %s", resolved)
                return
            icon = QIcon(resolved)
            set_app_icon(icon)

        window.setWindowIcon(icon)
    except Exception:
        logger.exception("Lỗi set window icon")


def set_all_windows_icon(windows_list: list, icon_path: str = None) -> None:
    for window in windows_list:
        if window is not None:
            set_window_icon(window, icon_path)


def get_app_icon():
    """Lấy icon hiện tại của ứng dụng (ưu tiên icon đã set runtime)."""

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    global _APP_ICON

    if _APP_ICON is not None:
        return _APP_ICON

    app = QApplication.instance()
    if app is not None:
        current = app.windowIcon()
        if isinstance(current, QIcon) and not current.isNull():
            _APP_ICON = current
            return _APP_ICON

    default_path = resource_path(ICON_APP)
    _APP_ICON = (
        QIcon(default_path) if validate_resource_exists(default_path) else QIcon()
    )
    if app is not None and not _APP_ICON.isNull():
        app.setWindowIcon(_APP_ICON)
    return _APP_ICON


def set_app_icon(icon) -> None:
    """Set icon toàn ứng dụng và đồng bộ real-time tới mọi top-level window."""

    from PySide6.QtWidgets import QApplication

    global _APP_ICON
    _APP_ICON = icon

    app = QApplication.instance()
    if app is None:
        return

    app.setWindowIcon(icon)
    for w in app.topLevelWidgets():
        try:
            w.setWindowIcon(icon)
        except Exception:
            # Tránh làm crash vì 1 widget lạ
            pass


def set_app_icon_from_bytes(data: bytes | None) -> bool:
    """Tạo icon từ bytes (png/jpg/ico/svg) và đồng bộ toàn app.

    Returns:
        bool: True nếu tạo và set icon thành công.
    """

    if not data:
        return False

    from PySide6.QtGui import QIcon, QPixmap

    # Nhận diện SVG đơn giản để tránh QPixmap.loadFromData fail
    head = data[:512].lower()
    is_svg = b"<svg" in head or head.strip().startswith(b"<?xml")

    if is_svg:
        from PySide6.QtCore import QByteArray, QSize
        from PySide6.QtGui import QImage, QPainter
        from PySide6.QtSvg import QSvgRenderer

        painter = None
        try:
            renderer = QSvgRenderer(QByteArray(data))
            size = renderer.defaultSize()
            if not size.isValid():
                size = QSize(256, 256)

            image = QImage(size, QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = QPainter(image)
            renderer.render(painter)
            pixmap = QPixmap.fromImage(image)
        except Exception:
            return False
        finally:
            try:
                if painter is not None:
                    painter.end()
            except Exception:
                pass
    else:
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return False

    icon = QIcon(pixmap)
    set_app_icon(icon)
    return True


if __name__ == "__main__":
    # Test resource paths
    print("📋 Testing Resource Paths:")
    print(f"Base: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    print(f"Icon: {get_icon_path(ICON_APP)}")
    print(f"Image: {get_image_path(ICON_APP)}")
    print(f"Database: {get_database_path()}")
    print(f"Log: {get_log_path()}")
