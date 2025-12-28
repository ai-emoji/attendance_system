"""services.shift_attendance_services

Services cho màn Shift Attendance.

Hiện tại dùng lại dữ liệu từ EmployeeService:
- Danh sách phòng ban cho combobox
- Danh sách nhân viên cho bảng (lọc các nhân viên có Mã chấm công / mcc_code)
"""

from __future__ import annotations

from typing import Any

from services.employee_services import EmployeeService
from repository.attendance_audit_repository import AttendanceAuditRepository
from repository.schedule_work_repository import ScheduleWorkRepository


class ShiftAttendanceService:
    def __init__(self, employee_service: EmployeeService | None = None) -> None:
        self._employee_service = employee_service or EmployeeService()
        self._attendance_audit_repo = AttendanceAuditRepository()
        self._schedule_work_repo = ScheduleWorkRepository()

    def list_departments_dropdown(self) -> list[tuple[int, str]]:
        return self._employee_service.list_departments_dropdown()

    def list_titles_dropdown(self) -> list[tuple[int, str]]:
        return self._employee_service.list_titles_dropdown()

    def list_employees(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        return self._employee_service.list_employees(filters or {})

    def list_attendance_audit(
        self,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        employee_id: int | None = None,
        attendance_code: str | None = None,
        employee_ids: list[int] | None = None,
        attendance_codes: list[str] | None = None,
        department_id: int | None = None,
        title_id: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._attendance_audit_repo.list_rows(
            from_date=from_date,
            to_date=to_date,
            employee_id=employee_id,
            attendance_code=attendance_code,
            employee_ids=employee_ids,
            attendance_codes=attendance_codes,
            department_id=department_id,
            title_id=title_id,
        )

    def get_employee_schedule_name_map(
        self,
        *,
        employee_ids: list[int],
        on_date: str,
    ) -> dict[int, str]:
        return self._schedule_work_repo.get_employee_schedule_name_map(
            employee_ids=employee_ids,
            on_date=str(on_date),
        )
