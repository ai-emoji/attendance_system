"""services.shift_attendance_services

Services cho màn Shift Attendance.

Hiện tại dùng lại dữ liệu từ EmployeeService:
- Danh sách phòng ban cho combobox
- Danh sách nhân viên cho bảng (lọc các nhân viên có Mã chấm công / mcc_code)
"""

from __future__ import annotations

from typing import Any

from services.employee_services import EmployeeService


class ShiftAttendanceService:
	def __init__(self, employee_service: EmployeeService | None = None) -> None:
		self._employee_service = employee_service or EmployeeService()

	def list_departments_dropdown(self) -> list[tuple[int, str]]:
		return self._employee_service.list_departments_dropdown()

	def list_employees(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
		return self._employee_service.list_employees(filters or {})
