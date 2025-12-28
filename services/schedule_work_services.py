"""services.schedule_work_services

Service layer cho màn "Sắp xếp lịch Làm việc".

Hiện tại ưu tiên phục vụ UI:
- Load cây Phòng ban/Chức danh
- Tìm nhân viên theo bộ lọc (phục vụ TitleBar2: Mã NV/Tên nhân viên)
- Xóa lịch NV (xóa các assignment của NV)

Nghiệp vụ chi tiết (gán lịch theo ngày/đợt, render bảng bên phải) sẽ triển khai sau.
"""

from __future__ import annotations

import logging
from datetime import date
from dataclasses import dataclass

from repository.schedule_work_repository import ScheduleWorkRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleWorkEmployeeRow:
    id: int
    employee_code: str
    mcc_code: str
    full_name: str
    department_id: int | None
    title_id: int | None
    department_name: str
    title_name: str


class ScheduleWorkService:
    def __init__(self, repo: ScheduleWorkRepository | None = None) -> None:
        self._repo = repo or ScheduleWorkRepository()

    def list_departments_tree_rows(self) -> list[tuple[int, int | None, str, str]]:
        rows = self._repo.list_departments()
        result: list[tuple[int, int | None, str, str]] = []
        for r in rows:
            try:
                result.append(
                    (
                        int(r.get("id")),
                        (
                            int(r.get("parent_id"))
                            if r.get("parent_id") is not None
                            else None
                        ),
                        str(r.get("department_name") or ""),
                        str(r.get("department_note") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def list_titles_tree_rows(self) -> list[tuple[int, int | None, str]]:
        rows = self._repo.list_titles()
        result: list[tuple[int, int | None, str]] = []
        for r in rows:
            try:
                result.append(
                    (
                        int(r.get("id")),
                        (
                            int(r.get("department_id"))
                            if r.get("department_id") is not None
                            else None
                        ),
                        str(r.get("title_name") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def list_schedules(self) -> list[tuple[int, str]]:
        rows = self._repo.list_schedules()
        result: list[tuple[int, str]] = []
        for r in rows:
            try:
                result.append((int(r.get("id")), str(r.get("schedule_name") or "")))
            except Exception:
                continue
        return result

    def search_employees(self, filters: dict) -> list[ScheduleWorkEmployeeRow]:
        search_by = str(filters.get("search_by") or "").strip() or None
        search_text = str(filters.get("search_text") or "").strip() or None

        dept_id = filters.get("department_id")
        title_id = filters.get("title_id")

        try:
            department_id = int(dept_id) if dept_id is not None else None
        except Exception:
            department_id = None
        try:
            title_id_i = int(title_id) if title_id is not None else None
        except Exception:
            title_id_i = None

        rows = self._repo.list_employees(
            search_by=search_by,
            search_text=search_text,
            department_id=department_id,
            title_id=title_id_i,
        )

        result: list[ScheduleWorkEmployeeRow] = []
        for r in rows:
            try:
                result.append(
                    ScheduleWorkEmployeeRow(
                        id=int(r.get("id")),
                        employee_code=str(r.get("employee_code") or ""),
                        mcc_code=str(r.get("mcc_code") or ""),
                        full_name=str(r.get("full_name") or ""),
                        department_id=(
                            int(r.get("department_id"))
                            if r.get("department_id") is not None
                            else None
                        ),
                        title_id=(
                            int(r.get("title_id"))
                            if r.get("title_id") is not None
                            else None
                        ),
                        department_name=str(r.get("department_name") or ""),
                        title_name=str(r.get("title_name") or ""),
                    )
                )
            except Exception:
                continue
        return result

    def apply_schedule_to_employees(
        self,
        *,
        employee_ids: list[int],
        schedule_id: int,
        effective_from: str | None = None,
    ) -> int:
        if not employee_ids or not schedule_id:
            return 0

        eff = str(effective_from or date.today().isoformat())
        processed = 0
        for emp_id in employee_ids:
            try:
                self._repo.upsert_employee_schedule_assignment(
                    employee_id=int(emp_id),
                    schedule_id=int(schedule_id),
                    effective_from=eff,
                    effective_to=None,
                    note=None,
                )
                processed += 1
            except Exception:
                logger.exception(
                    "apply_schedule_to_employees thất bại (emp_id=%s)", emp_id
                )
                continue
        return processed

    def get_employee_schedule_name_map(self, employee_ids: list[int]) -> dict[int, str]:
        ids: list[int] = []
        for x in employee_ids or []:
            try:
                v = int(x)
            except Exception:
                continue
            if v > 0:
                ids.append(v)
        ids = list(dict.fromkeys(ids))
        if not ids:
            return {}

        return self._repo.get_employee_schedule_name_map(
            employee_ids=ids,
            on_date=date.today().isoformat(),
        )

    def delete_employee_schedule(self, employee_id: int) -> tuple[bool, str, int]:
        if not employee_id:
            return False, "Vui lòng chọn nhân viên.", 0

        try:
            affected = self._repo.delete_assignments_by_employee_id(int(employee_id))
            return True, "Đã xóa lịch của nhân viên.", int(affected)
        except Exception:
            logger.exception("delete_employee_schedule thất bại")
            return False, "Không thể xóa lịch. Vui lòng thử lại.", 0

    def list_employee_schedule_assignments(self, employee_id: int) -> list[dict]:
        if not employee_id:
            return []
        rows = self._repo.list_employee_schedule_assignments(int(employee_id))
        return list(rows or [])

    def list_temp_schedule_assignments(
        self, employee_ids: list[int] | None = None
    ) -> list[dict]:
        rows = self._repo.list_temp_schedule_assignments(employee_ids=employee_ids)
        return list(rows or [])

    def get_employee_active_schedule_assignment(
        self, *, employee_id: int, on_date: str | None = None
    ) -> dict | None:
        if not employee_id:
            return None
        d = str(on_date or date.today().isoformat())
        return self._repo.get_employee_active_schedule_assignment(
            employee_id=int(employee_id),
            on_date=d,
        )

    def upsert_employee_schedule_assignment_with_range(
        self,
        *,
        employee_id: int,
        schedule_id: int,
        effective_from: str,
        effective_to: str | None,
        note: str | None = None,
    ) -> tuple[bool, str, int | None]:
        """Create/update a schedule assignment with from/to range.

        Returns (ok, message, assignment_id)
        """

        if not employee_id:
            return False, "Vui lòng chọn nhân viên.", None
        if not schedule_id or int(schedule_id) <= 0:
            return False, "Vui lòng chọn Lịch làm việc.", None
        if not str(effective_from or "").strip():
            return False, "Vui lòng chọn Từ ngày.", None

        try:
            self._repo.upsert_employee_schedule_assignment(
                employee_id=int(employee_id),
                schedule_id=int(schedule_id),
                effective_from=str(effective_from),
                effective_to=(str(effective_to) if effective_to else None),
                note=note,
            )

            assignment_id = self._repo.get_assignment_id_by_employee_from(
                employee_id=int(employee_id),
                effective_from=str(effective_from),
            )
            return True, "Đã lưu lịch trình tạm.", assignment_id
        except Exception:
            logger.exception("Không thể lưu lịch trình tạm")
            return (
                False,
                "Không thể lưu lịch trình tạm. Vui lòng kiểm tra cấu hình DB và thử lại.",
                None,
            )

    def delete_assignment_by_id(self, assignment_id: int) -> tuple[bool, str, int]:
        if not assignment_id:
            return False, "Vui lòng chọn dòng cần xóa.", 0
        try:
            affected = self._repo.delete_assignment_by_id(int(assignment_id))
            return True, "Đã xóa lịch trình tạm.", int(affected)
        except Exception:
            logger.exception("Không thể xóa lịch trình tạm")
            return False, "Không thể xóa lịch trình tạm. Vui lòng thử lại.", 0
