"""ui.controllers.shift_attendance_controllers

Controller cho màn "Chấm công Theo ca".

Hiện tại:
- Load phòng ban vào combobox
- Load danh sách nhân viên (lọc có mcc_code) vào bảng MainContent1
- Nút "Làm mới" reset toàn bộ field của MainContent1
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QTableWidgetItem

from services.shift_attendance_services import ShiftAttendanceService


logger = logging.getLogger(__name__)


class ShiftAttendanceController:
	def __init__(
		self,
		parent_window,
		content1,
		content2=None,
		service: ShiftAttendanceService | None = None,
	) -> None:
		self._parent_window = parent_window
		self._content1 = content1
		self._content2 = content2
		self._service = service or ShiftAttendanceService()

	def bind(self) -> None:
		self._content1.refresh_clicked.connect(self.on_refresh_clicked)
		self._content1.department_changed.connect(self.refresh)
		self._content1.search_changed.connect(self.refresh)

		# Initial
		self._load_departments()
		self._reset_fields(clear_table=False)
		self.refresh()

	def _load_departments(self) -> None:
		try:
			items = self._service.list_departments_dropdown() or []
		except Exception:
			logger.exception("Không thể tải danh sách phòng ban")
			items = []

		cb = self._content1.cbo_department
		old = cb.blockSignals(True)
		try:
			cb.clear()
			cb.addItem("Tất cả phòng ban", None)
			for dept_id, dept_name in items:
				# Hiển thị kèm ID để dễ đối soát
				cb.addItem(f"{dept_id} - {dept_name}", int(dept_id))
		finally:
			cb.blockSignals(old)

	def _build_filters(self) -> dict[str, Any]:
		filters: dict[str, Any] = {}

		dept_id = self._content1.cbo_department.currentData()
		filters["department_id"] = int(dept_id) if dept_id else None
		filters["title_id"] = None

		search_by = self._content1.cbo_search_by.currentData()
		search_text = str(self._content1.inp_search_text.text() or "").strip()

		if search_by and search_text:
			filters["search_by"] = str(search_by)
			filters["search_text"] = search_text
		else:
			filters["search_by"] = None
			filters["search_text"] = None

		return filters

	def _reset_fields(self, *, clear_table: bool) -> None:
		# Reset inputs
		try:
			self._content1.cbo_department.setCurrentIndex(0)
		except Exception:
			pass
		try:
			self._content1.cbo_search_by.setCurrentIndex(0)
		except Exception:
			pass
		try:
			self._content1.inp_search_text.setText("")
		except Exception:
			pass

		# Reset dates
		today = QDate.currentDate()
		try:
			self._content1.date_from.setDate(today)
			self._content1.date_to.setDate(today)
		except Exception:
			pass

		# Reset counter/total + table
		try:
			self._content1.set_total(0)
		except Exception:
			pass
		if clear_table:
			try:
				self._content1.table.setRowCount(0)
			except Exception:
				pass

	def on_refresh_clicked(self) -> None:
		self._load_departments()
		self._reset_fields(clear_table=True)
		self.refresh()

	def refresh(self) -> None:
		try:
			rows = self._service.list_employees(self._build_filters())
			self._render_main_table(rows)
			self._content1.set_total(len(rows))
		except Exception:
			logger.exception("Không thể tải danh sách nhân viên")
			try:
				self._content1.table.setRowCount(0)
			except Exception:
				pass
			try:
				self._content1.set_total(0)
			except Exception:
				pass

	def _render_main_table(self, rows: list[dict[str, Any]]) -> None:
		table = self._content1.table
		table.setRowCount(0)
		if not rows:
			return

		# Columns: Mã NV | Tên nhân viên | Mã chấm công | Lịch trình | Chức vụ | Phòng Ban | Ngày vào làm
		table.setRowCount(len(rows))
		for r_idx, r in enumerate(rows):
			emp_id = r.get("id")
			dept_id = r.get("department_id")
			title_id = r.get("title_id")

			values = [
				r.get("employee_code"),
				r.get("full_name"),
				r.get("mcc_code"),
				"",  # Lịch trình: xử lý sau
				r.get("title_name"),
				r.get("department_name"),
				r.get("start_date"),
			]

			for c_idx, v in enumerate(values):
				item = QTableWidgetItem(str(v or ""))
				item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
				if c_idx == 0:
					# Gắn đầy đủ id phục vụ xử lý về sau
					item.setData(Qt.ItemDataRole.UserRole, emp_id)
					item.setData(Qt.ItemDataRole.UserRole + 1, dept_id)
					item.setData(Qt.ItemDataRole.UserRole + 2, title_id)
				table.setItem(r_idx, c_idx, item)

		# Ensure per-column UI settings (align/bold/visible) apply to created items.
		try:
			self._content1.apply_ui_settings()
		except Exception:
			pass
