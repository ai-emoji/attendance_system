"""ui.controllers.header_controllers

Controller cho Header.

Trách nhiệm:
- Xử lý click 4 tab: Khai báo / Kết nối / Chấm công / Công cụ
- Cập nhật danh sách phím chức năng ở phần 2 (ribbon)
- Quản lý trạng thái hover/active cho tab
- Mặc định active "Khai báo" khi mở ứng dụng

Lưu ý:
- UI chỉ điều phối và hiển thị
- Controller ghi log INFO/DEBUG vào log/debug.log (đã cấu hình ở main.py)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.resource import ICON_SETTINGS


@dataclass(frozen=True)
class HeaderAction:
    """Định nghĩa 1 phím chức năng của ribbon."""

    text: str
    svg: str


class HeaderController:
    """Controller điều khiển Header.

    View (Header) cần cung cấp:
    - btn_khai_bao, btn_ket_noi, btn_cham_cong, btn_cong_cu (QPushButton)
    - set_actions(actions: list[tuple[str, str]]) -> None
    - set_active_tab(tab_key: str) -> None
    """

    TAB_KHAI_BAO = "khai_bao"
    TAB_KET_NOI = "ket_noi"
    TAB_CHAM_CONG = "cham_cong"
    TAB_CONG_CU = "cong_cu"

    def __init__(self, view) -> None:
        self._view = view
        self._logger = logging.getLogger(__name__)

    def bind(self) -> None:
        """Gắn sự kiện UI và set trạng thái mặc định."""
        self._view.btn_khai_bao.clicked.connect(
            lambda: self.activate_tab(self.TAB_KHAI_BAO)
        )
        self._view.btn_ket_noi.clicked.connect(
            lambda: self.activate_tab(self.TAB_KET_NOI)
        )
        self._view.btn_cham_cong.clicked.connect(
            lambda: self.activate_tab(self.TAB_CHAM_CONG)
        )
        self._view.btn_cong_cu.clicked.connect(
            lambda: self.activate_tab(self.TAB_CONG_CU)
        )

        self._logger.debug("HeaderController đã bind signal")

        # Mặc định active "Khai báo"
        self.activate_tab(self.TAB_KHAI_BAO)

    def activate_tab(self, tab_key: str) -> None:
        """Kích hoạt tab và render danh sách chức năng tương ứng."""
        actions = self._get_actions_for_tab(tab_key)
        self._logger.info("Chuyển tab header: %s", tab_key)
        self._logger.debug("Số nút ribbon: %d", len(actions))

        self._view.set_active_tab(tab_key)
        self._view.set_actions([(a.text, a.svg) for a in actions])

    def _get_actions_for_tab(self, tab_key: str) -> list[HeaderAction]:
        if tab_key == self.TAB_KHAI_BAO:
            return [
                HeaderAction("Thông tin\nCông ty", "company.svg"),
                HeaderAction("Khai báo\nChức danh", "job_title.svg"),
                HeaderAction("Khai báo\nPhòng ban", "department.svg"),
                HeaderAction("Khai báo\nNgày lễ", "holiday.svg"),
                HeaderAction("Thông tin\nNhân viên", "employee.svg"),
                HeaderAction("Đổi\nMật khẩu", "password.svg"),
                HeaderAction("Thoát\nỨng dụng", "exit.svg"),
            ]

        if tab_key == self.TAB_KET_NOI:
            return [
                HeaderAction("Thêm Máy \nchấm công", "device.svg"),
                HeaderAction("Tải dữ liệu\nMáy chấm công", "download_attendance.svg"),
                HeaderAction("Tải DS NV\nTừ máy", "download_staff.svg"),
                HeaderAction("Tải DS NV\nLên máy", "upload_staff.svg"),
            ]

        if tab_key == self.TAB_CHAM_CONG:
            return [
                HeaderAction("Khai báo\nCa làm việc", "declare_work_shift.svg"),
                HeaderAction("khai báo lịch\nLàm việc", "arrange_schedule.svg"),
                HeaderAction("Sắp xếp lịch\nLàm việc", "schedule_work.svg"),
                HeaderAction("Ký hiệu\nChấm công", "attendance_symbol.svg"),
                HeaderAction("Chấm công\nTheo ca", "shift_attendance.svg"),
            ]

        if tab_key == self.TAB_CONG_CU:
            return [
                HeaderAction("Kết nối\nCSDL SQL", "login.svg"),
                HeaderAction("Sao lưu\nDữ liệu", "backup.svg"),
                HeaderAction("Khôi phục\nDữ liệu", "absence_restore.svg"),
                HeaderAction("Cài đặt", ICON_SETTINGS),
            ]

        # Fallback: coi như "Khai báo"
        self._logger.warning("Tab không hợp lệ: %s. Fallback về 'khai_bao'", tab_key)
        return self._get_actions_for_tab(self.TAB_KHAI_BAO)
