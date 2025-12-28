"""ui.controllers.shift_attendance_maincontent2_controllers

Controller phụ trách dữ liệu cho MainContent2 (Shift Attendance).

UI layer chỉ gọi controller/service; mọi nghiệp vụ sắp xếp giờ nằm ở Service.
"""

from __future__ import annotations

import logging
from typing import Any

from services.shift_attendance_maincontent2_services import (
    ShiftAttendanceMainContent2Service,
)


logger = logging.getLogger(__name__)


class ShiftAttendanceMainContent2Controller:
    def __init__(
        self, service: ShiftAttendanceMainContent2Service | None = None
    ) -> None:
        self._service = service or ShiftAttendanceMainContent2Service()

    def list_attendance_audit_arranged(
        self,
        *,
        from_date: str | None,
        to_date: str | None,
        employee_ids: list[int] | None,
        attendance_codes: list[str] | None,
        department_id: int | None,
        title_id: int | None,
        progress_cb: callable[[int, str], None] | None = None,
        progress_items_cb: callable[[int, int, str], None] | None = None,
        cancel_cb: callable[[], bool] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return self._service.list_attendance_audit_arranged(
                from_date=from_date,
                to_date=to_date,
                employee_ids=employee_ids,
                attendance_codes=attendance_codes,
                department_id=department_id,
                title_id=title_id,
                progress_cb=progress_cb,
                progress_items_cb=progress_items_cb,
                cancel_cb=cancel_cb,
            )
        except Exception:
            logger.exception("Không thể tải attendance_audit (MainContent2)")
            raise
