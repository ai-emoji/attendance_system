"""
Điểm vào chính của ứng dụng Desktop GUI sử dụng PySide6.
Khởi tạo ứng dụng và cửa sổ chính.
"""

import sys
import logging
import faulthandler
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from core.resource import resource_path, user_data_dir
from ui.main_window import MainWindow
from ui.dialog.start_dialog import StartDialog


def _install_dir() -> Path:
    try:
        p = Path(sys.argv[0]).resolve()
        if str(p):
            return p.parent
    except Exception:
        pass
    return Path.cwd()


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

    log_path = _install_dir() / "log" / "debug.log"
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

    app = QApplication(sys.argv)

    # Dump trace nếu gặp crash native/segfault (hữu ích khi app "out" không traceback)
    try:
        dump_path = _install_dir() / "log" / "faulthandler.log"
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with dump_path.open("a", encoding="utf-8") as f:
            faulthandler.enable(file=f, all_threads=True)
    except Exception:
        pass

    start = StartDialog(create_main_window=lambda: MainWindow())
    if start.exec() != start.DialogCode.Accepted:
        return

    main_window = start.get_main_window()
    if not isinstance(main_window, MainWindow):
        main_window = MainWindow()

    # Tạo cửa sổ chính
    main_window.show()

    def _apply_admin_title(username: str) -> None:
        u = str(username or "").strip()
        if not u:
            return
        try:
            main_window.setWindowTitle(f"Phần mềm chấm công Tam Niên - Admin : {u}")
        except Exception:
            pass

    # Show login once (first successful login persists in database/ui_login.json)
    try:
        from ui.dialog.login_dialog import (
            LoginDialog,
            get_last_username,
            is_login_required,
        )

        # If login was already completed before, still show username on title.
        if not is_login_required():
            _apply_admin_title(get_last_username())

        if is_login_required():

            def _show_login() -> None:
                dlg = LoginDialog(main_window)
                if dlg.exec() != dlg.DialogCode.Accepted:
                    app.quit()
                    return

                # Login OK -> set title "Admin : <username>"
                try:
                    _apply_admin_title(get_last_username())
                except Exception:
                    pass

            # Ensure MainWindow is visible before opening the login dialog.
            QTimer.singleShot(0, _show_login)
    except Exception:
        pass

    logger.info("Ứng dụng đã sẵn sàng.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
