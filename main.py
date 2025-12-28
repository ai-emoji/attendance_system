"""
Điểm vào chính của ứng dụng Desktop GUI sử dụng PySide6.
Khởi tạo ứng dụng và cửa sổ chính.
"""

import sys
import logging
import faulthandler
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication

from core.resource import resource_path
from ui.main_window import MainWindow


def _user_data_dir() -> Path:
    """Return a writable per-user data directory (Windows-friendly)."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "attendance"

    # Fallback: best-effort path that works on Windows too
    return Path.home() / "AppData" / "Local" / "attendance"


def setup_logging() -> None:
    """
    Thiết lập hệ thống logging cho ứng dụng.
    Tạo file log/debug.log khi chạy ứng dụng.
    """
    # Tránh lỗi Unicode trên Windows console (cp1252/cp932...)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    log_path = _user_data_dir() / "log" / "debug.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Ghi đầy đủ DEBUG/INFO/... vào file
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Tránh nhân đôi handler khi gọi lại
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Không hiển thị log ra terminal


def main() -> None:
    """Hàm chính để khởi chạy ứng dụng."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Khởi động ứng dụng...")

    # Dump trace nếu gặp crash native/segfault (hữu ích khi app "out" không traceback)
    try:
        dump_path = _user_data_dir() / "log" / "faulthandler.log"
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with dump_path.open("a", encoding="utf-8") as f:
            faulthandler.enable(file=f, all_threads=True)
    except Exception:
        pass

    app = QApplication(sys.argv)

    # Tạo cửa sổ chính
    main_window = MainWindow()
    main_window.show()

    logger.info("Ứng dụng đã sẵn sàng.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
