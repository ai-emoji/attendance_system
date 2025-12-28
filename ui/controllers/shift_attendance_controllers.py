"""ui.controllers.shift_attendance_controllers

Controller cho màn "Chấm công Theo ca".

Hiện tại:
- Load phòng ban vào combobox
- Load danh sách nhân viên (lọc có mcc_code) vào bảng MainContent1
- Nút "Làm mới" reset toàn bộ field của MainContent1
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QDate,
    QElapsedTimer,
    QObject,
    QThread,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtWidgets import QFileDialog, QDialog
from PySide6.QtWidgets import QTableWidgetItem

from export.export_details import export_shift_attendance_details_xlsx
from export.export_grid_list import CompanyInfo, export_shift_attendance_grid_xlsx
from services.arrange_schedule_services import ArrangeScheduleService
from services.company_services import CompanyService
from services.employee_services import EmployeeService
from services.export_grid_list_services import (
    ExportGridListService,
    ExportGridListSettings,
)
from services.attendance_symbol_services import AttendanceSymbolService
from services.shift_attendance_services import ShiftAttendanceService
from ui.controllers.shift_attendance_maincontent2_controllers import (
    ShiftAttendanceMainContent2Controller,
)
from core.attendance_symbol_bus import attendance_symbol_bus
from core.threads import BackgroundTaskRunner
from core.ui_settings import get_last_save_dir, set_last_save_dir
from ui.dialog.export_grid_list_dialog import ExportGridListDialog, NoteStyle
from ui.dialog.title_dialog import MessageDialog
from ui.dialog.loading_dialog import LoadingDialog


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
        self._mc2_controller = ShiftAttendanceMainContent2Controller()
        self._audit_mode: str = (
            "default"  # 'default' (dept/title) | 'selected' (checked)
        )

        # Keep refs to background loader to avoid premature GC.
        self._audit_loader_thread: QThread | None = None
        self._audit_loader_worker: QObject | None = None
        self._audit_loader_bridge: QObject | None = None

        # Time-sliced render state for the audit table to avoid UI freeze.
        self._audit_render_timer: QTimer | None = None
        self._audit_render_state: dict[str, Any] | None = None
        self._audit_render_tick = None

        # Background loader for MainContent1 (employee list) to avoid blocking UI.
        self._employee_loader_thread: QThread | None = None
        self._employee_loader_worker: QObject | None = None
        self._employee_loader_bridge: QObject | None = None

        # Time-sliced render state for MainContent1 table.
        self._employee_render_timer: QTimer | None = None
        self._employee_render_state: dict[str, Any] | None = None
        self._employee_render_tick = None

        # Cache attendance symbols to avoid repeated DB calls during render.
        self._symbols_by_code_cache: dict[str, dict[str, Any]] | None = None

        # Background runner for export (do not touch Qt widgets in worker thread).
        self._export_runner = BackgroundTaskRunner(parent=self._parent_window, name="export")

        # Export snapshot state (UI-thread chunking) + loading dialog.
        self._export_snapshot_timer: QTimer | None = None
        self._export_snapshot_state: dict[str, Any] | None = None
        self._export_loading_dialog: LoadingDialog | None = None

    def _cancel_export_snapshot(self) -> None:
        try:
            if self._export_snapshot_timer is not None:
                try:
                    self._export_snapshot_timer.stop()
                except Exception:
                    pass
                try:
                    self._export_snapshot_timer.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass
        self._export_snapshot_timer = None
        self._export_snapshot_state = None

        try:
            if self._export_loading_dialog is not None:
                try:
                    self._export_loading_dialog.close()
                except Exception:
                    pass
        except Exception:
            pass
        self._export_loading_dialog = None

    def _export_table_background(
        self,
        *,
        title: str,
        table,
        rows_to_export: list[int] | None,
        do_export: "callable[[object], tuple[bool, str]]",
    ) -> None:
        """Show a loading dialog, snapshot table on UI thread in chunks, then export in background.

        Notes:
        - QTableWidget cannot be accessed from a worker thread.
        - We snapshot visible text into a lightweight pure-python table-like object.
        """

        # Cancel any in-flight snapshot/export.
        try:
            self._export_runner.cancel_current()
        except Exception:
            pass
        self._cancel_export_snapshot()

        loading = LoadingDialog(
            self._parent_window,
            title=str(title),
            message="Đang chuẩn bị dữ liệu...",
        )
        self._export_loading_dialog = loading

        try:
            loading.set_min_duration_ms(900)
        except Exception:
            pass

        # Show non-blocking (do not exec()) so the event loop keeps processing.
        try:
            loading.show()
            loading.raise_()
            loading.activateWindow()
        except Exception:
            pass

        # Build snapshot incrementally on the UI thread.
        try:
            col_count = int(table.columnCount())
        except Exception:
            col_count = 0

        headers: list[str] = []
        hidden_cols: set[int] = set()
        try:
            for c in range(int(col_count)):
                try:
                    hi = table.horizontalHeaderItem(int(c))
                    headers.append("" if hi is None else str(hi.text() or "").strip())
                except Exception:
                    headers.append("")
                try:
                    if bool(table.isColumnHidden(int(c))):
                        hidden_cols.add(int(c))
                except Exception:
                    pass
        except Exception:
            headers = [""] * int(col_count)
            hidden_cols = set()

        try:
            total_rows = int(table.rowCount())
        except Exception:
            total_rows = 0

        src_rows = list(range(int(total_rows)))
        if rows_to_export is not None:
            src_rows = [int(r) for r in (rows_to_export or []) if 0 <= int(r) < int(total_rows)]

        state: dict[str, Any] = {
            "i": 0,
            "src_rows": src_rows,
            "headers": headers,
            "hidden_cols": hidden_cols,
            "rows": [],
            "col_count": int(col_count),
        }
        self._export_snapshot_state = state

        timer = QTimer(loading)
        timer.setInterval(1)
        self._export_snapshot_timer = timer

        def _finish_with_message(msg: str) -> None:
            try:
                self._cancel_export_snapshot()
            except Exception:
                pass
            MessageDialog.info(self._parent_window, str(title), str(msg))

        def _tick() -> None:
            st = self._export_snapshot_state
            if st is None:
                return

            i = int(st.get("i", 0))
            src = st.get("src_rows", []) or []
            n = len(src)
            if n <= 0:
                # Empty export: still allow export function to decide.
                try:
                    loading.set_indeterminate(True, message="Đang xuất Excel, xin chờ...")
                except Exception:
                    pass

                snapshot = _make_snapshot(
                    headers=st.get("headers", []) or [],
                    hidden_cols=st.get("hidden_cols", set()) or set(),
                    rows=[],
                )
                self._start_export_worker(title=title, loading=loading, snapshot=snapshot, do_export=do_export)
                return

            # Process a chunk of rows per tick to keep UI responsive.
            chunk = 25
            end = min(n, i + chunk)
            coln = int(st.get("col_count", 0))
            out_rows: list[list[str]] = st.get("rows", [])

            for idx in range(i, end):
                rr = int(src[int(idx)])
                row_vals: list[str] = []
                for c in range(coln):
                    try:
                        it = table.item(int(rr), int(c))
                        row_vals.append("" if it is None else str(it.text() or ""))
                    except Exception:
                        row_vals.append("")
                out_rows.append(row_vals)

            st["i"] = int(end)
            st["rows"] = out_rows

            try:
                loading.set_count_target(int(end), int(n), message="Đang chuẩn bị dữ liệu...")
            except Exception:
                pass

            if int(end) >= int(n):
                try:
                    loading.set_indeterminate(True, message="Đang xuất Excel, xin chờ...")
                except Exception:
                    pass
                snapshot = _make_snapshot(
                    headers=st.get("headers", []) or [],
                    hidden_cols=st.get("hidden_cols", set()) or set(),
                    rows=st.get("rows", []) or [],
                )
                self._start_export_worker(title=title, loading=loading, snapshot=snapshot, do_export=do_export)

        def _make_snapshot(*, headers: list[str], hidden_cols: set[int], rows: list[list[str]]):
            class _SnapHeader:
                def __init__(self, txt: str) -> None:
                    self._txt = str(txt or "")

                def text(self) -> str:
                    return str(self._txt)

            class _SnapItem:
                def __init__(self, txt: str) -> None:
                    self._txt = str(txt or "")

                def text(self) -> str:
                    return str(self._txt)

            class _TableSnapshot:
                def __init__(
                    self,
                    *,
                    headers_in: list[str],
                    hidden_cols_in: set[int],
                    rows_in: list[list[str]],
                ) -> None:
                    self._headers = [str(x or "") for x in (headers_in or [])]
                    self._hidden = {int(x) for x in (hidden_cols_in or set())}
                    self._rows = rows_in or []

                def columnCount(self) -> int:
                    return int(len(self._headers))

                def rowCount(self) -> int:
                    return int(len(self._rows))

                def isColumnHidden(self, c: int) -> bool:
                    return int(c) in self._hidden

                def horizontalHeaderItem(self, c: int):
                    cc = int(c)
                    if cc < 0 or cc >= len(self._headers):
                        return None
                    t = str(self._headers[cc] or "")
                    if not t:
                        return None
                    return _SnapHeader(t)

                def item(self, r: int, c: int):
                    rr = int(r)
                    cc = int(c)
                    if rr < 0 or rr >= len(self._rows):
                        return None
                    row = self._rows[rr]
                    if cc < 0 or cc >= len(row):
                        return None
                    v = "" if row[cc] is None else str(row[cc])
                    if not v:
                        return None
                    return _SnapItem(v)

            return _TableSnapshot(headers_in=headers, hidden_cols_in=hidden_cols, rows_in=rows)

        try:
            timer.timeout.connect(_tick)
            timer.start()
        except Exception as e:
            _finish_with_message(f"Không thể bắt đầu xuất: {e}")

    def _start_export_worker(
        self,
        *,
        title: str,
        loading: LoadingDialog,
        snapshot: object,
        do_export: "callable[[object], tuple[bool, str]]",
    ) -> None:
        # Stop snapshot timer/state now that we have the snapshot.
        try:
            if self._export_snapshot_timer is not None:
                try:
                    self._export_snapshot_timer.stop()
                except Exception:
                    pass
                try:
                    self._export_snapshot_timer.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass
        self._export_snapshot_timer = None
        self._export_snapshot_state = None

        def _fn() -> object:
            return do_export(snapshot)

        def _on_success(result: object) -> None:
            try:
                if self._export_loading_dialog is loading:
                    self._export_loading_dialog = None
                try:
                    loading.close()
                except Exception:
                    pass
            except Exception:
                pass

            try:
                ok, msg = result  # type: ignore[misc]
            except Exception:
                ok, msg = (False, "Xuất Excel thất bại.")

            MessageDialog.info(self._parent_window, str(title), str(msg))

        def _on_error(msg: str) -> None:
            try:
                if self._export_loading_dialog is loading:
                    self._export_loading_dialog = None
                try:
                    loading.close()
                except Exception:
                    pass
            except Exception:
                pass
            MessageDialog.info(self._parent_window, str(title), str(msg))

        self._export_runner.run(fn=_fn, on_success=_on_success, on_error=_on_error, coalesce=True)

    def _get_symbols_by_code_cached(self) -> dict[str, dict[str, Any]]:
        if self._symbols_by_code_cache is not None:
            return self._symbols_by_code_cache
        try:
            self._symbols_by_code_cache = AttendanceSymbolService().list_rows_by_code() or {}
        except Exception:
            self._symbols_by_code_cache = {}
        return self._symbols_by_code_cache

    def _cancel_employee_render(self) -> None:
        try:
            if self._employee_render_timer is not None:
                try:
                    if self._employee_render_tick is not None:
                        self._employee_render_timer.timeout.disconnect(
                            self._employee_render_tick
                        )
                except Exception:
                    pass
                try:
                    self._employee_render_timer.stop()
                except Exception:
                    pass
                try:
                    self._employee_render_timer.deleteLater()
                except Exception:
                    pass
        finally:
            self._employee_render_timer = None
            self._employee_render_state = None
            self._employee_render_tick = None

    def _cancel_audit_render(self) -> None:
        try:
            if self._audit_render_timer is not None:
                try:
                    if self._audit_render_tick is not None:
                        self._audit_render_timer.timeout.disconnect(
                            self._audit_render_tick
                        )
                except Exception:
                    pass
                try:
                    self._audit_render_timer.stop()
                except Exception:
                    pass
                try:
                    self._audit_render_timer.deleteLater()
                except Exception:
                    pass
        finally:
            self._audit_render_timer = None
            self._audit_render_state = None
            self._audit_render_tick = None

    def bind(self) -> None:
        self._content1.refresh_clicked.connect(self.on_refresh_clicked)
        self._content1.department_changed.connect(self.refresh)
        try:
            self._content1.title_changed.connect(self.refresh)
        except Exception:
            pass
        self._content1.search_changed.connect(self.refresh)

        # Live-refresh audit grid when attendance_symbols are updated.
        try:
            attendance_symbol_bus.changed.connect(self._on_attendance_symbols_changed)
        except Exception:
            pass
        if self._content2 is not None:
            self._content1.view_clicked.connect(self.on_view_clicked)
            try:
                self._content2.export_grid_clicked.connect(self.on_export_grid_clicked)
            except Exception:
                pass
            try:
                self._content2.detail_clicked.connect(self.on_export_detail_clicked)
            except Exception:
                pass

        # Initial
        self._load_departments()
        self._load_titles()
        self._reset_fields(clear_table=False)
        # Defer heavy work to the event loop so the widget can paint first.
        try:
            QTimer.singleShot(0, self.refresh)
        except Exception:
            self.refresh()

        # Default: show ALL audit rows for current date range when opening.
        # Load in background (no modal dialog) to avoid blocking initial navigation.
        if self._content2 is not None:
            self._audit_mode = "default"
            try:
                QTimer.singleShot(
                    0,
                    lambda: self._load_audit_for_current_range_background(
                        employee_ids=None,
                        attendance_codes=None,
                        department_id=None,
                        title_id=None,
                    ),
                )
            except Exception:
                self._load_audit_for_current_range_background(
                    employee_ids=None,
                    attendance_codes=None,
                    department_id=None,
                    title_id=None,
                )

    def _on_attendance_symbols_changed(self) -> None:
        # Invalidate cached symbols.
        try:
            self._symbols_by_code_cache = None
        except Exception:
            pass
        # Only reload audit table; do not reset filters or main employee list.
        if self._content2 is None:
            return

        if str(self._audit_mode or "").strip() == "selected":
            try:
                checked_ids, checked_codes = self._content1.get_checked_employee_keys()
            except Exception:
                checked_ids, checked_codes = ([], [])
            self._load_audit_for_current_range(
                employee_ids=checked_ids or None,
                attendance_codes=checked_codes or None,
                department_id=None,
                title_id=None,
            )
            return

        self._load_audit_for_current_range(
            employee_ids=None,
            attendance_codes=None,
            department_id=self._selected_department_id(),
            title_id=self._selected_title_id(),
        )

    def on_export_grid_clicked(self) -> None:
        if self._content2 is None:
            return

        # If any row is checked (✅) in the table, export only checked rows.
        checked_rows: list[int] = []
        try:
            t = self._content2.table
            for r in range(int(t.rowCount())):
                it = t.item(int(r), 0)
                if it is None:
                    continue
                if str(it.text() or "").strip() == "✅":
                    checked_rows.append(int(r))
        except Exception:
            checked_rows = []

        # Load defaults: DB settings (if any) + company table fallback
        default_company = CompanyInfo()
        try:
            data = CompanyService().load_company()
            if data is not None:
                default_company = CompanyInfo(
                    name=str(data.company_name or "").strip(),
                    address=str(data.company_address or "").strip(),
                    phone=str(data.company_phone or "").strip(),
                )
        except Exception:
            default_company = CompanyInfo()

        export_service = ExportGridListService()
        saved = None
        try:
            saved = export_service.load()
        except Exception:
            saved = None

        dialog = ExportGridListDialog(
            self._parent_window, export_button_text="Xuất lưới"
        )
        dialog.set_values(
            company_name=(
                saved.company_name
                if saved and saved.company_name
                else default_company.name
            ),
            company_address=(
                saved.company_address
                if saved and saved.company_address
                else default_company.address
            ),
            company_phone=(
                saved.company_phone
                if saved and saved.company_phone
                else default_company.phone
            ),
            creator=(saved.creator if saved else ""),
            note_text=(saved.note_text if saved else ""),
            company_name_style=(
                NoteStyle(
                    font_size=(saved.company_name_font_size if saved else 13),
                    bold=(saved.company_name_bold if saved else False),
                    italic=(saved.company_name_italic if saved else False),
                    underline=(saved.company_name_underline if saved else False),
                    align=(saved.company_name_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            company_address_style=(
                NoteStyle(
                    font_size=(saved.company_address_font_size if saved else 13),
                    bold=(saved.company_address_bold if saved else False),
                    italic=(saved.company_address_italic if saved else False),
                    underline=(saved.company_address_underline if saved else False),
                    align=(saved.company_address_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            company_phone_style=(
                NoteStyle(
                    font_size=(saved.company_phone_font_size if saved else 13),
                    bold=(saved.company_phone_bold if saved else False),
                    italic=(saved.company_phone_italic if saved else False),
                    underline=(saved.company_phone_underline if saved else False),
                    align=(saved.company_phone_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            creator_style=(
                NoteStyle(
                    font_size=(saved.creator_font_size if saved else 13),
                    bold=(saved.creator_bold if saved else False),
                    italic=(saved.creator_italic if saved else False),
                    underline=(saved.creator_underline if saved else False),
                    align=(saved.creator_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            note_style=(
                NoteStyle(
                    font_size=(saved.note_font_size if saved else 13),
                    bold=(saved.note_bold if saved else False),
                    italic=(saved.note_italic if saved else False),
                    underline=(saved.note_underline if saved else False),
                    align=(saved.note_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            export_kind="grid",
            time_pairs=(saved.time_pairs if saved is not None else 4),
        )

        def _selected_time_pairs() -> int:
            try:
                return int(dialog.get_time_pairs())
            except Exception:
                return 4

        def _pair_excludes(tp: int) -> set[str]:
            if int(tp) == 2:
                return {"Vào 2", "Ra 2", "Vào 3", "Ra 3"}
            if int(tp) == 4:
                return {"Vào 3", "Ra 3"}
            return set()

        def _save_settings() -> tuple[bool, str]:
            vals = dialog.get_values()
            note_st = dialog.get_note_style()
            creator_st = dialog.get_creator_style()
            cn_st = dialog.get_company_name_style()
            ca_st = dialog.get_company_address_style()
            cp_st = dialog.get_company_phone_style()
            export_kind = "grid"
            time_pairs = _selected_time_pairs()
            settings = ExportGridListSettings(
                export_kind=export_kind,
                time_pairs=time_pairs,
                company_name=vals.get("company_name", ""),
                company_address=vals.get("company_address", ""),
                company_phone=vals.get("company_phone", ""),
                company_name_font_size=int(cn_st.font_size),
                company_name_bold=bool(cn_st.bold),
                company_name_italic=bool(cn_st.italic),
                company_name_underline=bool(cn_st.underline),
                company_name_align=str(cn_st.align or "left"),
                company_address_font_size=int(ca_st.font_size),
                company_address_bold=bool(ca_st.bold),
                company_address_italic=bool(ca_st.italic),
                company_address_underline=bool(ca_st.underline),
                company_address_align=str(ca_st.align or "left"),
                company_phone_font_size=int(cp_st.font_size),
                company_phone_bold=bool(cp_st.bold),
                company_phone_italic=bool(cp_st.italic),
                company_phone_underline=bool(cp_st.underline),
                company_phone_align=str(cp_st.align or "left"),
                creator=vals.get("creator", ""),
                creator_font_size=int(creator_st.font_size),
                creator_bold=bool(creator_st.bold),
                creator_italic=bool(creator_st.italic),
                creator_underline=bool(creator_st.underline),
                creator_align=str(creator_st.align or "left"),
                note_text=(
                    vals.get("note_text", "")
                    if export_kind == "grid"
                    else (saved.note_text if saved else "")
                ),
                note_font_size=(
                    int(note_st.font_size)
                    if export_kind == "grid"
                    else (int(saved.note_font_size) if saved else 13)
                ),
                note_bold=(
                    bool(note_st.bold)
                    if export_kind == "grid"
                    else (bool(saved.note_bold) if saved else False)
                ),
                note_italic=(
                    bool(note_st.italic)
                    if export_kind == "grid"
                    else (bool(saved.note_italic) if saved else False)
                ),
                note_underline=(
                    bool(note_st.underline)
                    if export_kind == "grid"
                    else (bool(saved.note_underline) if saved else False)
                ),
                note_align=(
                    str(note_st.align or "left")
                    if export_kind == "grid"
                    else (str(saved.note_align) if saved else "left")
                ),
                detail_note_text=(
                    vals.get("note_text", "")
                    if export_kind == "detail"
                    else (str(saved.detail_note_text or "") if saved else "")
                ),
                detail_note_font_size=(
                    int(note_st.font_size)
                    if export_kind == "detail"
                    else (int(saved.detail_note_font_size) if saved else 13)
                ),
                detail_note_bold=(
                    bool(note_st.bold)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_bold) if saved else False)
                ),
                detail_note_italic=(
                    bool(note_st.italic)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_italic) if saved else False)
                ),
                detail_note_underline=(
                    bool(note_st.underline)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_underline) if saved else False)
                ),
                detail_note_align=(
                    str(note_st.align or "left")
                    if export_kind == "detail"
                    else (str(saved.detail_note_align) if saved else "left")
                ),
            )
            ok, msg = export_service.save(settings, context="xuất lưới")
            dialog.set_status(msg, ok=ok)
            return ok, msg

        def _export_clicked() -> None:
            ok, _ = _save_settings()
            if not ok:
                return
            dialog.mark_export()
            dialog.accept()

        try:
            dialog.btn_save.clicked.connect(lambda: _save_settings())
            dialog.btn_export.clicked.connect(_export_clicked)
        except Exception:
            pass

        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.did_export():
            return

        vals = dialog.get_values()
        note_style = dialog.get_note_style()
        creator_style = dialog.get_creator_style()
        cn_style = dialog.get_company_name_style()
        ca_style = dialog.get_company_address_style()
        cp_style = dialog.get_company_phone_style()

        # Date range text
        try:
            from_qdate: QDate = self._content1.date_from.date()
            to_qdate: QDate = self._content1.date_to.date()
            from_txt = from_qdate.toString("dd/MM/yyyy")
            to_txt = to_qdate.toString("dd/MM/yyyy")
            from_file = from_qdate.toString("ddMMyyyy")
            to_file = to_qdate.toString("ddMMyyyy")
        except Exception:
            from_txt = ""
            to_txt = ""
            from_file = ""
            to_file = ""

        time_pairs = _selected_time_pairs()
        title = "Xuất lưới chấm công"
        default_name = (
            f"Xuất Lưới_{from_file}_{to_file}.xlsx"
            if from_file and to_file
            else "Xuất Lưới.xlsx"
        )

        initial = str(Path(get_last_save_dir()) / default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self._parent_window,
            title,
            initial,
            "Excel (*.xlsx)",
        )
        if not file_path:
            return
        try:
            set_last_save_dir(str(Path(file_path).parent))
        except Exception:
            pass

        company = CompanyInfo(
            name=str(vals.get("company_name", "") or "").strip(),
            address=str(vals.get("company_address", "") or "").strip(),
            phone=str(vals.get("company_phone", "") or "").strip(),
        )

        # Decide schedule-driven visibility (only force-hide for strict first_last),
        # then apply the user's selected time_pairs cap (2/4/6).
        force_exclude_headers: set[str] | None = None
        in_out_mode_by_employee_code: dict[str, str | None] = {}
        try:
            t = self._content2.table
            row_count = int(t.rowCount())
            rows_to_export = checked_rows if checked_rows else list(range(row_count))

            def _find_col(header_text: str) -> int | None:
                target = str(header_text or "").strip().lower()
                for c in range(int(t.columnCount())):
                    hi = t.horizontalHeaderItem(int(c))
                    ht = "" if hi is None else str(hi.text() or "")
                    if ht.strip().lower() == target:
                        return int(c)
                return None

            col_schedule = _find_col("Lịch làm việc")
            col_emp = _find_col("Mã nv")
            col_in2 = _find_col("Vào 2")
            col_out2 = _find_col("Ra 2")
            col_in3 = _find_col("Vào 3")
            col_out3 = _find_col("Ra 3")

            schedule_names: list[str] = []
            max_pair_used = 1
            emp_to_schedules: dict[str, set[str]] = {}

            for r in rows_to_export:
                rr = int(r)
                if rr < 0 or rr >= row_count:
                    continue

                if col_schedule is not None:
                    it = t.item(rr, int(col_schedule))
                    s = "" if it is None else str(it.text() or "").strip()
                    if s:
                        schedule_names.append(s)
                        if col_emp is not None:
                            it2 = t.item(rr, int(col_emp))
                            emp_code = (
                                "" if it2 is None else str(it2.text() or "").strip()
                            )
                            if emp_code:
                                emp_to_schedules.setdefault(emp_code, set()).add(s)

                def _has_text(col: int | None) -> bool:
                    if col is None:
                        return False
                    it2 = t.item(rr, int(col))
                    return bool(str("" if it2 is None else it2.text() or "").strip())

                if _has_text(col_in3) or _has_text(col_out3):
                    max_pair_used = max(max_pair_used, 3)
                if _has_text(col_in2) or _has_text(col_out2):
                    max_pair_used = max(max_pair_used, 2)

            schedule_names = list(dict.fromkeys([s for s in schedule_names if s]))

            if schedule_names:
                mode_map = ArrangeScheduleService().get_in_out_mode_map(schedule_names)
                modes = [mode_map.get(n) for n in schedule_names]

                has_unknown = any(m is None for m in modes)
                has_device = any(m == "device" for m in modes)
                has_auto = any(m == "auto" for m in modes)

                # IMPORTANT: Export columns are controlled by the user's 2/4/6 selection.
                # Do not force-hide pairs based on schedule mode here.

                for emp_code, ss in (emp_to_schedules or {}).items():
                    emp_modes = [mode_map.get(x) for x in (ss or set())]
                    if any(m is None for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "device"
                    elif any(m == "device" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "device"
                    elif any(m == "auto" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "auto"
                    elif any(m == "first_last" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "first_last"
                    else:
                        in_out_mode_by_employee_code[emp_code] = None
        except Exception:
            force_exclude_headers = None
            in_out_mode_by_employee_code = {}

        # Apply user's selected 2/4/6 time-pair cap.
        cap_ex = _pair_excludes(time_pairs)
        if cap_ex:
            force_exclude_headers = set(force_exclude_headers or set()) | cap_ex

        def _do_export(snapshot_table: object) -> tuple[bool, str]:
            return export_shift_attendance_grid_xlsx(
                file_path=file_path,
                company=company,
                from_date_text=from_txt,
                to_date_text=to_txt,
                table=snapshot_table,
                row_indexes=None,
                force_exclude_headers=force_exclude_headers,
                company_name_style={
                    "font_size": int(cn_style.font_size),
                    "bold": bool(cn_style.bold),
                    "italic": bool(cn_style.italic),
                    "underline": bool(cn_style.underline),
                    "align": str(cn_style.align or "left"),
                },
                company_address_style={
                    "font_size": int(ca_style.font_size),
                    "bold": bool(ca_style.bold),
                    "italic": bool(ca_style.italic),
                    "underline": bool(ca_style.underline),
                    "align": str(ca_style.align or "left"),
                },
                company_phone_style={
                    "font_size": int(cp_style.font_size),
                    "bold": bool(cp_style.bold),
                    "italic": bool(cp_style.italic),
                    "underline": bool(cp_style.underline),
                    "align": str(cp_style.align or "left"),
                },
                creator=str(vals.get("creator", "") or "").strip(),
                creator_style={
                    "font_size": int(creator_style.font_size),
                    "bold": bool(creator_style.bold),
                    "italic": bool(creator_style.italic),
                    "underline": bool(creator_style.underline),
                    "align": str(creator_style.align or "left"),
                },
                note_text=str(vals.get("note_text", "") or ""),
                note_style={
                    "font_size": int(note_style.font_size),
                    "bold": bool(note_style.bold),
                    "italic": bool(note_style.italic),
                    "underline": bool(note_style.underline),
                    "align": str(note_style.align or "left"),
                },
            )

        self._export_table_background(
            title=title,
            table=self._content2.table,
            rows_to_export=(checked_rows if checked_rows else None),
            do_export=_do_export,
        )

    def on_export_detail_clicked(self) -> None:
        if self._content2 is None:
            return

        # If any row is checked (✅) in the table, export only checked rows.
        checked_rows: list[int] = []
        try:
            t = self._content2.table
            for r in range(int(t.rowCount())):
                it = t.item(int(r), 0)
                if it is None:
                    continue
                if str(it.text() or "").strip() == "✅":
                    checked_rows.append(int(r))
        except Exception:
            checked_rows = []

        # Load defaults: DB settings (if any) + company table fallback
        default_company = CompanyInfo()
        try:
            data = CompanyService().load_company()
            if data is not None:
                default_company = CompanyInfo(
                    name=str(data.company_name or "").strip(),
                    address=str(data.company_address or "").strip(),
                    phone=str(data.company_phone or "").strip(),
                )
        except Exception:
            default_company = CompanyInfo()

        export_service = ExportGridListService()
        saved = None
        try:
            saved = export_service.load()
        except Exception:
            saved = None

        dialog = ExportGridListDialog(
            self._parent_window, export_button_text="Xuất chi tiết"
        )
        dialog.set_values(
            company_name=(
                saved.company_name
                if saved and saved.company_name
                else default_company.name
            ),
            company_address=(
                saved.company_address
                if saved and saved.company_address
                else default_company.address
            ),
            company_phone=(
                saved.company_phone
                if saved and saved.company_phone
                else default_company.phone
            ),
            creator=(saved.creator if saved else ""),
            note_text=(saved.detail_note_text if saved else ""),
            company_name_style=(
                NoteStyle(
                    font_size=(saved.company_name_font_size if saved else 13),
                    bold=(saved.company_name_bold if saved else False),
                    italic=(saved.company_name_italic if saved else False),
                    underline=(saved.company_name_underline if saved else False),
                    align=(saved.company_name_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            company_address_style=(
                NoteStyle(
                    font_size=(saved.company_address_font_size if saved else 13),
                    bold=(saved.company_address_bold if saved else False),
                    italic=(saved.company_address_italic if saved else False),
                    underline=(saved.company_address_underline if saved else False),
                    align=(saved.company_address_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            company_phone_style=(
                NoteStyle(
                    font_size=(saved.company_phone_font_size if saved else 13),
                    bold=(saved.company_phone_bold if saved else False),
                    italic=(saved.company_phone_italic if saved else False),
                    underline=(saved.company_phone_underline if saved else False),
                    align=(saved.company_phone_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            creator_style=(
                NoteStyle(
                    font_size=(saved.creator_font_size if saved else 13),
                    bold=(saved.creator_bold if saved else False),
                    italic=(saved.creator_italic if saved else False),
                    underline=(saved.creator_underline if saved else False),
                    align=(saved.creator_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            note_style=(
                NoteStyle(
                    font_size=(saved.detail_note_font_size if saved else 13),
                    bold=(saved.detail_note_bold if saved else False),
                    italic=(saved.detail_note_italic if saved else False),
                    underline=(saved.detail_note_underline if saved else False),
                    align=(saved.detail_note_align if saved else "left"),
                )
                if saved is not None
                else NoteStyle()
            ),
            export_kind="detail",
            time_pairs=(saved.time_pairs if saved is not None else 4),
        )

        def _selected_time_pairs() -> int:
            try:
                return int(dialog.get_time_pairs())
            except Exception:
                return 4

        def _pair_excludes(tp: int) -> set[str]:
            if int(tp) == 2:
                return {"Vào 2", "Ra 2", "Vào 3", "Ra 3"}
            if int(tp) == 4:
                return {"Vào 3", "Ra 3"}
            return set()

        def _save_settings() -> tuple[bool, str]:
            vals = dialog.get_values()
            note_st = dialog.get_note_style()
            creator_st = dialog.get_creator_style()
            cn_st = dialog.get_company_name_style()
            ca_st = dialog.get_company_address_style()
            cp_st = dialog.get_company_phone_style()
            export_kind = "detail"
            time_pairs = _selected_time_pairs()
            settings = ExportGridListSettings(
                export_kind=export_kind,
                time_pairs=time_pairs,
                company_name=vals.get("company_name", ""),
                company_address=vals.get("company_address", ""),
                company_phone=vals.get("company_phone", ""),
                company_name_font_size=int(cn_st.font_size),
                company_name_bold=bool(cn_st.bold),
                company_name_italic=bool(cn_st.italic),
                company_name_underline=bool(cn_st.underline),
                company_name_align=str(cn_st.align or "left"),
                company_address_font_size=int(ca_st.font_size),
                company_address_bold=bool(ca_st.bold),
                company_address_italic=bool(ca_st.italic),
                company_address_underline=bool(ca_st.underline),
                company_address_align=str(ca_st.align or "left"),
                company_phone_font_size=int(cp_st.font_size),
                company_phone_bold=bool(cp_st.bold),
                company_phone_italic=bool(cp_st.italic),
                company_phone_underline=bool(cp_st.underline),
                company_phone_align=str(cp_st.align or "left"),
                creator=vals.get("creator", ""),
                creator_font_size=int(creator_st.font_size),
                creator_bold=bool(creator_st.bold),
                creator_italic=bool(creator_st.italic),
                creator_underline=bool(creator_st.underline),
                creator_align=str(creator_st.align or "left"),
                note_text=(
                    vals.get("note_text", "")
                    if export_kind == "grid"
                    else (saved.note_text if saved else "")
                ),
                note_font_size=(
                    int(note_st.font_size)
                    if export_kind == "grid"
                    else (int(saved.note_font_size) if saved else 13)
                ),
                note_bold=(
                    bool(note_st.bold)
                    if export_kind == "grid"
                    else (bool(saved.note_bold) if saved else False)
                ),
                note_italic=(
                    bool(note_st.italic)
                    if export_kind == "grid"
                    else (bool(saved.note_italic) if saved else False)
                ),
                note_underline=(
                    bool(note_st.underline)
                    if export_kind == "grid"
                    else (bool(saved.note_underline) if saved else False)
                ),
                note_align=(
                    str(note_st.align or "left")
                    if export_kind == "grid"
                    else (str(saved.note_align) if saved else "left")
                ),
                detail_note_text=(
                    vals.get("note_text", "")
                    if export_kind == "detail"
                    else (str(saved.detail_note_text or "") if saved else "")
                ),
                detail_note_font_size=(
                    int(note_st.font_size)
                    if export_kind == "detail"
                    else (int(saved.detail_note_font_size) if saved else 13)
                ),
                detail_note_bold=(
                    bool(note_st.bold)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_bold) if saved else False)
                ),
                detail_note_italic=(
                    bool(note_st.italic)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_italic) if saved else False)
                ),
                detail_note_underline=(
                    bool(note_st.underline)
                    if export_kind == "detail"
                    else (bool(saved.detail_note_underline) if saved else False)
                ),
                detail_note_align=(
                    str(note_st.align or "left")
                    if export_kind == "detail"
                    else (str(saved.detail_note_align) if saved else "left")
                ),
            )
            ok, msg = export_service.save(settings, context="xuất chi tiết")
            dialog.set_status(msg, ok=ok)
            return ok, msg

        def _export_clicked() -> None:
            ok, _ = _save_settings()
            if not ok:
                return
            dialog.mark_export()
            dialog.accept()

        try:
            dialog.btn_save.clicked.connect(lambda: _save_settings())
            dialog.btn_export.clicked.connect(_export_clicked)
        except Exception:
            pass

        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.did_export():
            return

        vals = dialog.get_values()
        note_style = dialog.get_note_style()
        creator_style = dialog.get_creator_style()
        cn_style = dialog.get_company_name_style()
        ca_style = dialog.get_company_address_style()
        cp_style = dialog.get_company_phone_style()

        # Date range text
        try:
            from_qdate: QDate = self._content1.date_from.date()
            to_qdate: QDate = self._content1.date_to.date()
            from_txt = from_qdate.toString("dd/MM/yyyy")
            to_txt = to_qdate.toString("dd/MM/yyyy")
            from_file = from_qdate.toString("ddMMyyyy")
            to_file = to_qdate.toString("ddMMyyyy")
        except Exception:
            from_txt = ""
            to_txt = ""
            from_file = ""
            to_file = ""

        time_pairs = _selected_time_pairs()
        title = "Xuất chi tiết chấm công"
        default_name = (
            f"Xuất Chi Tiết_{from_file}_{to_file}.xlsx"
            if from_file and to_file
            else "Xuất Chi Tiết.xlsx"
        )

        initial = str(Path(get_last_save_dir()) / default_name)

        file_path, _ = QFileDialog.getSaveFileName(
            self._parent_window,
            title,
            initial,
            "Excel (*.xlsx)",
        )
        if not file_path:
            return
        try:
            set_last_save_dir(str(Path(file_path).parent))
        except Exception:
            pass

        company = CompanyInfo(
            name=str(vals.get("company_name", "") or "").strip(),
            address=str(vals.get("company_address", "") or "").strip(),
            phone=str(vals.get("company_phone", "") or "").strip(),
        )

        # Auto-hide unnecessary in/out columns based on Arrange Schedule in_out_mode.
        force_exclude_headers: set[str] | None = None
        in_out_mode_by_employee_code: dict[str, str | None] = {}
        try:
            t = self._content2.table
            row_count = int(t.rowCount())
            rows_to_export = checked_rows if checked_rows else list(range(row_count))

            def _find_col(header_text: str) -> int | None:
                target = str(header_text or "").strip().lower()
                for c in range(int(t.columnCount())):
                    hi = t.horizontalHeaderItem(int(c))
                    ht = "" if hi is None else str(hi.text() or "")
                    if ht.strip().lower() == target:
                        return int(c)
                return None

            col_schedule = _find_col("Lịch làm việc")
            col_emp = _find_col("Mã nv")
            col_in2 = _find_col("Vào 2")
            col_out2 = _find_col("Ra 2")
            col_in3 = _find_col("Vào 3")
            col_out3 = _find_col("Ra 3")

            schedule_names: list[str] = []
            max_pair_used = 1
            emp_to_schedules: dict[str, set[str]] = {}

            for r in rows_to_export:
                rr = int(r)
                if rr < 0 or rr >= row_count:
                    continue

                if col_schedule is not None:
                    it = t.item(rr, int(col_schedule))
                    s = "" if it is None else str(it.text() or "").strip()
                    if s:
                        schedule_names.append(s)
                        if col_emp is not None:
                            it2 = t.item(rr, int(col_emp))
                            emp_code = (
                                "" if it2 is None else str(it2.text() or "").strip()
                            )
                            if emp_code:
                                emp_to_schedules.setdefault(emp_code, set()).add(s)

                def _has_text(col: int | None) -> bool:
                    if col is None:
                        return False
                    it2 = t.item(rr, int(col))
                    return bool(str("" if it2 is None else it2.text() or "").strip())

                if _has_text(col_in3) or _has_text(col_out3):
                    max_pair_used = max(max_pair_used, 3)
                if _has_text(col_in2) or _has_text(col_out2):
                    max_pair_used = max(max_pair_used, 2)

            schedule_names = list(dict.fromkeys([s for s in schedule_names if s]))

            if schedule_names:
                mode_map = ArrangeScheduleService().get_in_out_mode_map(schedule_names)
                modes = [mode_map.get(n) for n in schedule_names]

                has_unknown = any(m is None for m in modes)
                has_device = any(m == "device" for m in modes)
                has_auto = any(m == "auto" for m in modes)

                # IMPORTANT: Export columns are controlled by the user's 2/4/6 selection.
                # Do not force-hide pairs based on schedule mode here.

                # Per-employee mode (used by details template to decide whether to render Vào2/Ra2 lines)
                for emp_code, ss in (emp_to_schedules or {}).items():
                    emp_modes = [mode_map.get(x) for x in (ss or set())]
                    if any(m is None for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "device"
                    elif any(m == "device" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "device"
                    elif any(m == "auto" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "auto"
                    elif any(m == "first_last" for m in emp_modes):
                        in_out_mode_by_employee_code[emp_code] = "first_last"
                    else:
                        in_out_mode_by_employee_code[emp_code] = None
        except Exception:
            force_exclude_headers = None
            in_out_mode_by_employee_code = {}

        # Apply user's selected 2/4/6 time-pair cap.
        cap_ex = _pair_excludes(time_pairs)
        if cap_ex:
            force_exclude_headers = set(force_exclude_headers or set()) | cap_ex

        def _do_export(snapshot_table: object) -> tuple[bool, str]:
            dept_txt = ""
            title_txt = ""

            # Fallback: if the audit table doesn't contain department/title columns,
            # fetch distinct values from DB by exported employee codes.
            try:
                # Find employee code column in the snapshot table.
                code_col = None
                try:
                    col_count = int(getattr(snapshot_table, "columnCount")())
                except Exception:
                    col_count = 0

                for c in range(int(col_count)):
                    try:
                        hi = getattr(snapshot_table, "horizontalHeaderItem")(int(c))
                        ht = "" if hi is None else str(getattr(hi, "text")() or "")
                        ht = ht.strip().lower()
                    except Exception:
                        ht = ""
                    if ht in {"mã nv", "mã nhân viên", "ma nv", "ma nhan vien"}:
                        code_col = int(c)
                        break

                codes: list[str] = []
                if code_col is not None:
                    try:
                        rc = int(getattr(snapshot_table, "rowCount")())
                    except Exception:
                        rc = 0

                    seen_codes: set[str] = set()
                    for r in range(int(rc)):
                        try:
                            it = getattr(snapshot_table, "item")(int(r), int(code_col))
                            code = "" if it is None else str(getattr(it, "text")() or "")
                            code = code.strip()
                        except Exception:
                            code = ""
                        if not code:
                            continue
                        if code in seen_codes:
                            continue
                        seen_codes.add(code)
                        codes.append(code)

                if codes:
                    dept_txt, title_txt = EmployeeService().get_department_title_text_by_employee_codes(codes)
            except Exception:
                dept_txt = ""
                title_txt = ""

            return export_shift_attendance_details_xlsx(
                file_path=file_path,
                company=company,
                from_date_text=from_txt,
                to_date_text=to_txt,
                table=snapshot_table,
                row_indexes=None,
                force_exclude_headers=force_exclude_headers,
                in_out_mode_by_employee_code=in_out_mode_by_employee_code,
                department_text=dept_txt,
                title_text=title_txt,
                company_name_style={
                    "font_size": int(cn_style.font_size),
                    "bold": bool(cn_style.bold),
                    "italic": bool(cn_style.italic),
                    "underline": bool(cn_style.underline),
                    "align": str(cn_style.align or "left"),
                },
                company_address_style={
                    "font_size": int(ca_style.font_size),
                    "bold": bool(ca_style.bold),
                    "italic": bool(ca_style.italic),
                    "underline": bool(ca_style.underline),
                    "align": str(ca_style.align or "left"),
                },
                company_phone_style={
                    "font_size": int(cp_style.font_size),
                    "bold": bool(cp_style.bold),
                    "italic": bool(cp_style.italic),
                    "underline": bool(cp_style.underline),
                    "align": str(cp_style.align or "left"),
                },
                creator=str(vals.get("creator", "") or "").strip(),
                creator_style={
                    "font_size": int(creator_style.font_size),
                    "bold": bool(creator_style.bold),
                    "italic": bool(creator_style.italic),
                    "underline": bool(creator_style.underline),
                    "align": str(creator_style.align or "left"),
                },
                note_text=str(vals.get("note_text", "") or ""),
                note_style={
                    "font_size": int(note_style.font_size),
                    "bold": bool(note_style.bold),
                    "italic": bool(note_style.italic),
                    "underline": bool(note_style.underline),
                    "align": str(note_style.align or "left"),
                },
            )

        self._export_table_background(
            title=title,
            table=self._content2.table,
            rows_to_export=(checked_rows if checked_rows else None),
            do_export=_do_export,
        )

    def _current_date_range(self) -> tuple[str | None, str | None]:
        try:
            from_qdate: QDate = self._content1.date_from.date()
            to_qdate: QDate = self._content1.date_to.date()
            return (
                from_qdate.toString("yyyy-MM-dd"),
                to_qdate.toString("yyyy-MM-dd"),
            )
        except Exception:
            return (None, None)

    def _load_audit_for_current_range(
        self,
        *,
        employee_ids: list[int] | None,
        attendance_codes: list[str] | None,
        department_id: int | None,
        title_id: int | None,
    ) -> None:
        if self._content2 is None:
            return

        from_date, to_date = self._current_date_range()
        try:
            rows = self._mc2_controller.list_attendance_audit_arranged(
                from_date=from_date,
                to_date=to_date,
                employee_ids=employee_ids,
                attendance_codes=attendance_codes,
                department_id=department_id,
                title_id=title_id,
            )
            self._render_audit_table(rows)
        except Exception:
            logger.exception("Không thể tải attendance_audit")
            try:
                self._content2.table.setRowCount(0)
            except Exception:
                pass

    def _load_audit_for_current_range_background(
        self,
        *,
        employee_ids: list[int] | None,
        attendance_codes: list[str] | None,
        department_id: int | None,
        title_id: int | None,
    ) -> None:
        """Load audit rows in background without blocking initial UI.

        Notes:
        - No modal LoadingDialog (only used for explicit 'Xem công').
        - Render is time-sliced so the table becomes visible progressively.
        """

        if self._content2 is None:
            return

        from_date, to_date = self._current_date_range()

        # Cancel any in-flight table rendering.
        self._cancel_audit_render()

        # Cancel any in-flight loader.
        try:
            if self._audit_loader_worker is not None:
                try:
                    getattr(self._audit_loader_worker, "cancel")()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._audit_loader_thread is not None:
                try:
                    self._audit_loader_thread.quit()
                except Exception:
                    pass
        except Exception:
            pass

        # Clear table quickly; keep table visible.
        try:
            self._content2.table.setRowCount(0)
        except Exception:
            pass
        try:
            if (
                hasattr(self._content2, "table_frame")
                and self._content2.table_frame is not None
            ):
                self._content2.table_frame.setVisible(True)
        except Exception:
            pass

        thread = QThread(self._parent_window)
        worker = self._AuditLoadWorker(
            self._mc2_controller,
            from_date=from_date,
            to_date=to_date,
            employee_ids=employee_ids,
            attendance_codes=attendance_codes,
            department_id=department_id,
            title_id=title_id,
            enable_progress=False,
        )
        worker.moveToThread(thread)

        class _UiBridge(QObject):
            def __init__(self) -> None:
                super().__init__()

            @Slot(list)
            def on_finished(self, rows: list) -> None:
                try:
                    self_parent._render_audit_table_chunked(rows, None)
                except Exception:
                    logger.exception("Không thể render attendance_audit")

            @Slot(str)
            def on_failed(self, msg: str) -> None:
                try:
                    self_parent._content2.table.setRowCount(0)  # type: ignore[name-defined]
                except Exception:
                    pass
                try:
                    logger.error("Không thể tải dữ liệu chấm công: %s", msg)
                except Exception:
                    pass

        self_parent = self
        bridge = _UiBridge()

        # Hold strong refs until thread finishes.
        self._audit_loader_thread = thread
        self._audit_loader_worker = worker
        self._audit_loader_bridge = bridge

        worker.finished.connect(bridge.on_finished)
        worker.failed.connect(bridge.on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        def _cleanup() -> None:
            try:
                thread.quit()
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                bridge.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass
            try:
                if self_parent._audit_loader_thread is thread:
                    self_parent._audit_loader_thread = None
                if self_parent._audit_loader_worker is worker:
                    self_parent._audit_loader_worker = None
                if self_parent._audit_loader_bridge is bridge:
                    self_parent._audit_loader_bridge = None
            except Exception:
                pass

        thread.finished.connect(_cleanup)
        thread.started.connect(worker.run)
        thread.start()

    class _AuditLoadWorker(QObject):
        progress = Signal(int, str)  # percent, message
        progress_items = Signal(int, int, str)  # done, total, message
        finished = Signal(list)  # rows
        failed = Signal(str)

        def __init__(
            self,
            controller: ShiftAttendanceMainContent2Controller,
            *,
            from_date: str | None,
            to_date: str | None,
            employee_ids: list[int] | None,
            attendance_codes: list[str] | None,
            department_id: int | None,
            title_id: int | None,
            enable_progress: bool = True,
        ) -> None:
            super().__init__()
            self._controller = controller
            self._from_date = from_date
            self._to_date = to_date
            self._employee_ids = employee_ids
            self._attendance_codes = attendance_codes
            self._department_id = department_id
            self._title_id = title_id
            self._enable_progress = bool(enable_progress)
            self._cancelled = False

        def cancel(self) -> None:
            self._cancelled = True

        def _is_cancelled(self) -> bool:
            return bool(self._cancelled)

        def run(self) -> None:
            try:
                t0 = time.perf_counter()
                progress_cb = None
                progress_items_cb = None
                if self._enable_progress:

                    def _on_progress(pct: int, msg: str) -> None:
                        try:
                            self.progress.emit(int(pct), str(msg))
                        except Exception:
                            pass

                    def _on_progress_items(done: int, total: int, msg: str) -> None:
                        try:
                            self.progress_items.emit(int(done), int(total), str(msg))
                        except Exception:
                            pass

                    progress_cb = _on_progress
                    progress_items_cb = _on_progress_items

                rows = self._controller.list_attendance_audit_arranged(
                    from_date=self._from_date,
                    to_date=self._to_date,
                    employee_ids=self._employee_ids,
                    attendance_codes=self._attendance_codes,
                    department_id=self._department_id,
                    title_id=self._title_id,
                    progress_cb=progress_cb,
                    progress_items_cb=progress_items_cb,
                    cancel_cb=self._is_cancelled,
                )
                try:
                    dt_ms = int((time.perf_counter() - t0) * 1000)
                    logger.info(
                        "Xem công: service rows=%s in %sms",
                        (len(rows) if isinstance(rows, list) else "?"),
                        dt_ms,
                    )
                except Exception:
                    pass
                if isinstance(rows, list):
                    self.finished.emit(rows)
                else:
                    self.finished.emit(list(rows or []))
            except Exception as e:
                self.failed.emit(str(e))

    def _load_audit_for_current_range_async(
        self,
        *,
        employee_ids: list[int] | None,
        attendance_codes: list[str] | None,
        department_id: int | None,
        title_id: int | None,
    ) -> None:
        if self._content2 is None:
            return

        from_date, to_date = self._current_date_range()

        # Cancel any in-flight table rendering to keep UI responsive.
        self._cancel_audit_render()

        # Cancel any in-flight loader.
        try:
            if self._audit_loader_worker is not None:
                try:
                    getattr(self._audit_loader_worker, "cancel")()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._audit_loader_thread is not None:
                try:
                    self._audit_loader_thread.quit()
                except Exception:
                    pass
        except Exception:
            pass

        dlg = LoadingDialog(
            self._parent_window,
            title="Đang xem công",
            message="Đang tính toán...",
        )

        # Busy-only UX: do not show percent/count progress for "xem công".
        try:
            dlg.set_indeterminate(True, "Đang tính toán...")
        except Exception:
            pass

        # Data-driven minimum duration so progress doesn't jump to 100% too fast.
        # Estimate work by employees * days in range.
        def _days_in_range(a: str | None, b: str | None) -> int:
            try:
                if not a or not b:
                    return 1
                from datetime import date

                d1 = date.fromisoformat(str(a))
                d2 = date.fromisoformat(str(b))
                delta = (d2 - d1).days
                return max(1, int(abs(delta)) + 1)
            except Exception:
                return 1

        est_days = _days_in_range(from_date, to_date)
        est_emps = max(
            1,
            int(len(employee_ids or [])) if employee_ids else 0,
            int(len(attendance_codes or [])) if attendance_codes else 0,
        )
        est_units = max(1, int(est_days) * max(1, int(est_emps)))
        # 1200ms base + 10ms/unit, clamp to 10s.
        min_ms = int(min(10000, 1200 + (est_units * 10)))
        try:
            dlg.set_min_duration_ms(min_ms)
        except Exception:
            pass

        thread = QThread(self._parent_window)
        worker = self._AuditLoadWorker(
            self._mc2_controller,
            from_date=from_date,
            to_date=to_date,
            employee_ids=employee_ids,
            attendance_codes=attendance_codes,
            department_id=department_id,
            title_id=title_id,
            enable_progress=False,
        )
        worker.moveToThread(thread)

        class _UiBridge(QObject):
            def __init__(self) -> None:
                super().__init__()

            @Slot(int, str)
            def on_progress(self, p: int, m: str) -> None:
                # Ignore worker progress; keep a stable "Đang tính toán..." message.
                try:
                    dlg.set_message("Đang tính toán...")
                except Exception:
                    pass

            @Slot(int, int, str)
            def on_progress_items(self, done: int, total: int, msg: str) -> None:
                # Ignore item progress; keep busy indicator.
                try:
                    dlg.set_message("Đang tính toán...")
                except Exception:
                    pass

            @Slot(list)
            def on_finished(self, rows: list) -> None:
                try:
                    self_parent._render_audit_table_chunked(rows, dlg)  # type: ignore[name-defined]
                except Exception:
                    logger.exception("Không thể render attendance_audit")
                    try:
                        if (
                            self_parent._content2 is not None
                            and hasattr(self_parent._content2, "table_frame")
                            and self_parent._content2.table_frame is not None
                        ):
                            self_parent._content2.table_frame.setVisible(True)
                    except Exception:
                        pass
                    try:
                        dlg.finish_and_close()
                    except Exception:
                        try:
                            dlg.close()
                        except Exception:
                            pass

            @Slot(str)
            def on_failed(self, msg: str) -> None:
                try:
                    self_parent._content2.table.setRowCount(0)  # type: ignore[name-defined]
                except Exception:
                    pass
                try:
                    MessageDialog.info(
                        self_parent._parent_window,  # type: ignore[name-defined]
                        "Thông báo",
                        f"Không thể tải dữ liệu chấm công.\n{msg}",
                    )
                except Exception:
                    pass
                try:
                    if (
                        self_parent._content2 is not None
                        and hasattr(self_parent._content2, "table_frame")
                        and self_parent._content2.table_frame is not None
                    ):
                        self_parent._content2.table_frame.setVisible(True)
                except Exception:
                    pass
                try:
                    dlg.close()
                except Exception:
                    pass

        # Ensure slots run on the UI thread.
        self_parent = self
        bridge = _UiBridge()

        # Hold strong refs until thread finishes.
        self._audit_loader_thread = thread
        self._audit_loader_worker = worker
        self._audit_loader_bridge = bridge

        worker.progress.connect(bridge.on_progress)
        worker.progress_items.connect(bridge.on_progress_items)
        worker.finished.connect(bridge.on_finished)
        worker.failed.connect(bridge.on_failed)

        # Always stop the thread when work ends.
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        # Cancel if user closes the dialog.
        def _on_dialog_finished(_r: int) -> None:
            try:
                worker.cancel()
            except Exception:
                pass
            try:
                thread.quit()
            except Exception:
                pass
            try:
                self_parent._cancel_audit_render()  # type: ignore[name-defined]
            except Exception:
                pass

        try:
            dlg.finished.connect(_on_dialog_finished)
        except Exception:
            pass

        # Cleanup without thread.wait() (avoids "wait on itself").
        def _cleanup() -> None:
            try:
                thread.quit()
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                bridge.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass

            # Release refs
            try:
                if self_parent._audit_loader_thread is thread:
                    self_parent._audit_loader_thread = None
                if self_parent._audit_loader_worker is worker:
                    self_parent._audit_loader_worker = None
                if self_parent._audit_loader_bridge is bridge:
                    self_parent._audit_loader_bridge = None
            except Exception:
                pass

        thread.finished.connect(_cleanup)

        thread.started.connect(worker.run)
        thread.start()

        # Modal dialog; UI stays responsive since work runs in QThread.
        dlg.exec()

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

    def _load_titles(self) -> None:
        cb = getattr(self._content1, "cbo_title", None)
        if cb is None:
            return

        try:
            items = self._service.list_titles_dropdown() or []
        except Exception:
            logger.exception("Không thể tải danh sách chức vụ")
            items = []

        old = cb.blockSignals(True)
        try:
            cb.clear()
            cb.addItem("Tất cả chức vụ", None)
            for title_id, title_name in items:
                cb.addItem(f"{title_id} - {title_name}", int(title_id))
        finally:
            cb.blockSignals(old)

    def _selected_department_id(self) -> int | None:
        try:
            dept_id = self._content1.cbo_department.currentData()
            return int(dept_id) if dept_id else None
        except Exception:
            return None

    def _selected_title_id(self) -> int | None:
        try:
            cb = getattr(self._content1, "cbo_title", None)
            if cb is None:
                return None
            title_id = cb.currentData()
            return int(title_id) if title_id else None
        except Exception:
            return None

    def _build_filters(self) -> dict[str, Any]:
        filters: dict[str, Any] = {}

        filters["department_id"] = self._selected_department_id()
        filters["title_id"] = self._selected_title_id()

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
        self._load_titles()
        self._reset_fields(clear_table=True)
        self.refresh()
        # Default: show ALL audit rows for current date range after refresh.
        if self._content2 is not None:
            self._audit_mode = "default"
            self._load_audit_for_current_range(
                employee_ids=None,
                attendance_codes=None,
                department_id=None,
                title_id=None,
            )

    def refresh(self) -> None:
        """Refresh employee list without freezing UI.

        This method is called on filter changes (textChanged, combobox, etc.).
        DB + QTableWidget rendering can be expensive; we move DB work to a QThread
        and render rows in time slices using QTimer.
        """

        # Defer actual work so the UI can process paint/events first.
        try:
            QTimer.singleShot(0, self._refresh_async)
        except Exception:
            self._refresh_async()

    class _EmployeeLoadWorker(QObject):
        # PySide6/Shiboken không hỗ trợ copy-convert dict trong typed Signal.
        finished = Signal(object, object)  # rows, schedule_map
        failed = Signal(str)

        def __init__(
            self,
            service: ShiftAttendanceService,
            *,
            filters: dict[str, Any],
            on_date: str | None,
        ) -> None:
            super().__init__()
            self._service = service
            self._filters = dict(filters or {})
            self._on_date = on_date
            self._cancelled = False

        def cancel(self) -> None:
            self._cancelled = True

        def _is_cancelled(self) -> bool:
            return bool(self._cancelled)

        def run(self) -> None:
            try:
                if self._is_cancelled():
                    self.finished.emit([], {})
                    return

                rows = self._service.list_employees(self._filters)

                schedule_map: dict[int, str] = {}
                if self._on_date and rows:
                    try:
                        emp_ids = [int(r.get("id")) for r in rows if r.get("id")]
                        if emp_ids and (not self._is_cancelled()):
                            schedule_map = self._service.get_employee_schedule_name_map(
                                employee_ids=emp_ids,
                                on_date=str(self._on_date),
                            )
                    except Exception:
                        logger.exception("Không thể tải lịch làm việc của nhân viên")
                        schedule_map = {}

                if self._is_cancelled():
                    self.finished.emit([], {})
                    return

                self.finished.emit(list(rows or []), dict(schedule_map or {}))
            except Exception as e:
                self.failed.emit(str(e))

    def _refresh_async(self) -> None:
        # Cancel any in-flight render.
        self._cancel_employee_render()

        # Cancel any in-flight loader.
        try:
            if self._employee_loader_worker is not None:
                try:
                    getattr(self._employee_loader_worker, "cancel")()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if self._employee_loader_thread is not None:
                try:
                    self._employee_loader_thread.quit()
                except Exception:
                    pass
        except Exception:
            pass

        from_date, _to_date = self._current_date_range()
        filters = self._build_filters()

        thread = QThread(self._parent_window)
        worker = self._EmployeeLoadWorker(
            self._service,
            filters=filters,
            on_date=from_date,
        )
        worker.moveToThread(thread)

        class _UiBridge(QObject):
            def __init__(self) -> None:
                super().__init__()

            @Slot(object, object)
            def on_finished(self, rows: object, schedule_map: object) -> None:
                try:
                    self_parent._render_main_table_chunked(
                        list(rows or []) if isinstance(rows, list) else [],
                        schedule_map=(
                            dict(schedule_map or {}) if isinstance(schedule_map, dict) else {}
                        ),
                    )
                except Exception:
                    logger.exception("Không thể render danh sách nhân viên")
                    try:
                        self_parent._content1.table.setRowCount(0)
                    except Exception:
                        pass
                    try:
                        self_parent._content1.set_total(0)
                    except Exception:
                        pass

            @Slot(str)
            def on_failed(self, msg: str) -> None:
                try:
                    logger.error("Không thể tải danh sách nhân viên: %s", msg)
                except Exception:
                    pass
                try:
                    self_parent._content1.table.setRowCount(0)
                except Exception:
                    pass
                try:
                    self_parent._content1.set_total(0)
                except Exception:
                    pass

        self_parent = self
        bridge = _UiBridge()

        # Hold strong refs.
        self._employee_loader_thread = thread
        self._employee_loader_worker = worker
        self._employee_loader_bridge = bridge

        worker.finished.connect(bridge.on_finished)
        worker.failed.connect(bridge.on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)

        def _cleanup() -> None:
            try:
                thread.quit()
            except Exception:
                pass
            try:
                worker.deleteLater()
            except Exception:
                pass
            try:
                bridge.deleteLater()
            except Exception:
                pass
            try:
                thread.deleteLater()
            except Exception:
                pass
            try:
                if self_parent._employee_loader_thread is thread:
                    self_parent._employee_loader_thread = None
                if self_parent._employee_loader_worker is worker:
                    self_parent._employee_loader_worker = None
                if self_parent._employee_loader_bridge is bridge:
                    self_parent._employee_loader_bridge = None
            except Exception:
                pass

        thread.finished.connect(_cleanup)
        thread.started.connect(worker.run)
        thread.start()

    def _render_main_table_chunked(
        self,
        rows: list[dict[str, Any]],
        *,
        schedule_map: dict[int, str] | None = None,
    ) -> None:
        """Render MainContent1 table in time slices to keep UI responsive."""

        table = self._content1.table

        # Reset quickly.
        try:
            table.setRowCount(0)
        except Exception:
            pass

        if not rows:
            try:
                self._content1.set_total(0)
            except Exception:
                pass
            return

        schedule_map = schedule_map or {}

        try:
            table.setRowCount(len(rows))
        except Exception:
            pass

        # Disable sorting to avoid expensive re-layout during item insertion.
        try:
            table.setSortingEnabled(False)
        except Exception:
            pass

        self._employee_render_state = {
            "rows": rows,
            "schedule_map": schedule_map,
            "idx": 0,
            "table": table,
        }

        if self._employee_render_timer is None:
            self._employee_render_timer = QTimer(self._parent_window)
            self._employee_render_timer.setSingleShot(True)

        def _tick() -> None:
            st = self._employee_render_state
            if not st:
                return

            _rows: list[dict[str, Any]] = st["rows"]
            _table = st["table"]
            _schedule_map: dict[int, str] = st.get("schedule_map") or {}
            try:
                idx = int(st.get("idx") or 0)
            except Exception:
                idx = 0

            budget = QElapsedTimer()
            budget.start()

            # Batch: avoid repaint per-cell; repaint once per slice.
            try:
                _table.setUpdatesEnabled(False)
            except Exception:
                pass

            while idx < len(_rows) and int(budget.elapsed()) < 12:
                r = _rows[idx]

                emp_id = r.get("id")
                dept_id = r.get("department_id")
                title_id = r.get("title_id")

                mcc_code = r.get("mcc_code")
                attendance_code = (
                    str(mcc_code or "").strip()
                    or str(r.get("employee_code") or "").strip()
                )

                chk = QTableWidgetItem("❌")
                chk.setFlags(chk.flags() & ~Qt.ItemFlag.ItemIsEditable)
                chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                chk.setData(Qt.ItemDataRole.UserRole, emp_id)
                chk.setData(Qt.ItemDataRole.UserRole + 1, attendance_code)
                chk.setData(Qt.ItemDataRole.UserRole + 2, dept_id)
                chk.setData(Qt.ItemDataRole.UserRole + 3, title_id)
                _table.setItem(idx, 0, chk)

                stt_val = r.get("stt")
                if stt_val is None or str(stt_val).strip() == "":
                    stt_val = idx + 1
                stt_item = QTableWidgetItem(str(stt_val))
                stt_item.setFlags(stt_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                _table.setItem(idx, 1, stt_item)

                values = [
                    r.get("employee_code"),
                    r.get("full_name"),
                    r.get("mcc_code"),
                    _schedule_map.get(int(emp_id), "") if emp_id is not None else "",
                    r.get("title_name"),
                    r.get("department_name"),
                    r.get("start_date"),
                ]

                for c_idx, v in enumerate(values, start=2):
                    item = QTableWidgetItem(str(v or ""))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if c_idx == 2:
                        item.setData(Qt.ItemDataRole.UserRole, emp_id)
                        item.setData(Qt.ItemDataRole.UserRole + 1, dept_id)
                        item.setData(Qt.ItemDataRole.UserRole + 2, title_id)
                    _table.setItem(idx, c_idx, item)

                idx += 1

            st["idx"] = idx

            try:
                _table.setUpdatesEnabled(True)
                _table.viewport().update()
            except Exception:
                pass

            if idx >= len(_rows):
                try:
                    self._content1.apply_ui_settings()
                except Exception:
                    pass
                try:
                    self._content1.set_total(len(_rows))
                except Exception:
                    pass
                self._cancel_employee_render()
                return

            try:
                self._employee_render_timer.start(0)
            except Exception:
                QTimer.singleShot(0, _tick)

        try:
            if self._employee_render_tick is not None:
                self._employee_render_timer.timeout.disconnect(
                    self._employee_render_tick
                )
        except Exception:
            pass
        self._employee_render_tick = _tick
        self._employee_render_timer.timeout.connect(_tick)
        self._employee_render_timer.start(0)

    def _render_main_table(
        self,
        rows: list[dict[str, Any]],
        *,
        schedule_map: dict[int, str] | None = None,
    ) -> None:
        table = self._content1.table
        table.setRowCount(0)
        if not rows:
            return

        schedule_map = schedule_map or {}

        # Columns: [✓] | STT | Mã NV | Tên nhân viên | Mã chấm công | Lịch trình | Chức vụ | Phòng Ban | Ngày vào làm
        table.setRowCount(len(rows))
        for r_idx, r in enumerate(rows):
            emp_id = r.get("id")
            dept_id = r.get("department_id")
            title_id = r.get("title_id")

            mcc_code = r.get("mcc_code")
            attendance_code = (
                str(mcc_code or "").strip() or str(r.get("employee_code") or "").strip()
            )

            chk = QTableWidgetItem("❌")
            chk.setFlags(chk.flags() & ~Qt.ItemFlag.ItemIsEditable)
            chk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            chk.setData(Qt.ItemDataRole.UserRole, emp_id)
            chk.setData(Qt.ItemDataRole.UserRole + 1, attendance_code)
            chk.setData(Qt.ItemDataRole.UserRole + 2, dept_id)
            chk.setData(Qt.ItemDataRole.UserRole + 3, title_id)
            table.setItem(r_idx, 0, chk)

            stt_val = r.get("stt")
            if stt_val is None or str(stt_val).strip() == "":
                stt_val = r_idx + 1
            stt_item = QTableWidgetItem(str(stt_val))
            stt_item.setFlags(stt_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r_idx, 1, stt_item)

            values = [
                r.get("employee_code"),
                r.get("full_name"),
                r.get("mcc_code"),
                schedule_map.get(int(emp_id), "") if emp_id is not None else "",
                r.get("title_name"),
                r.get("department_name"),
                r.get("start_date"),
            ]

            for c_idx, v in enumerate(values, start=2):
                item = QTableWidgetItem(str(v or ""))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c_idx == 2:
                    item.setData(Qt.ItemDataRole.UserRole, emp_id)
                    item.setData(Qt.ItemDataRole.UserRole + 1, dept_id)
                    item.setData(Qt.ItemDataRole.UserRole + 2, title_id)
                table.setItem(r_idx, c_idx, item)

        # Ensure per-column UI settings (align/bold/visible) apply to created items.
        try:
            self._content1.apply_ui_settings()
        except Exception:
            pass

    def _selected_employee_id(self) -> int | None:
        try:
            table = self._content1.table
            row = int(table.currentRow())
            if row < 0:
                return None
            item = table.item(row, 0)
            if item is None:
                return None
            emp_id = item.data(Qt.ItemDataRole.UserRole)
            return int(emp_id) if emp_id is not None else None
        except Exception:
            return None

    def _selected_attendance_code(self) -> str | None:
        """Returns selected employee attendance code (mcc_code) from MainContent1 table."""
        try:
            table = self._content1.table
            row = int(table.currentRow())
            if row < 0:
                return None
            # Column order in MainContent1: [✓], STT, employee_code, full_name, mcc_code, ...
            item = table.item(row, 4)
            if item is None:
                return None
            code = str(item.text() or "").strip()
            return code or None
        except Exception:
            return None

    def on_view_clicked(self) -> None:
        if self._content2 is None:
            return

        checked_ids: list[int] = []
        checked_codes: list[str] = []
        try:
            checked_ids, checked_codes = self._content1.get_checked_employee_keys()
        except Exception:
            checked_ids, checked_codes = ([], [])

        if checked_ids or checked_codes:
            self._audit_mode = "selected"
            self._load_audit_for_current_range_async(
                employee_ids=checked_ids,
                attendance_codes=checked_codes,
                department_id=None,
                title_id=None,
            )
            return

        # No checkbox selection: apply department/title filters.
        self._audit_mode = "default"
        self._load_audit_for_current_range_async(
            employee_ids=None,
            attendance_codes=None,
            department_id=self._selected_department_id(),
            title_id=self._selected_title_id(),
        )

    def _render_audit_table(self, rows: list[dict[str, Any]]) -> None:
        if self._content2 is None:
            return

        table = self._content2.table
        table.setRowCount(0)
        if not rows:
            return

        cols = [k for (k, _label) in getattr(self._content2, "_COLUMNS", [])]
        if not cols:
            return

        # Load symbols for displaying values like "2.63 +" or "1.0 X".
        overtime_symbol = "+"  # C04
        work_symbol = "X"  # C03
        late_symbol = "Tr"  # C01
        early_symbol = "Sm"  # C02
        holiday_symbol = "Le"  # C10
        absent_symbol = "V"  # C07
        off_symbol = "OFF"  # C09
        missing_out_symbol = "KR"  # C05
        missing_in_symbol = "KV"  # C06
        try:
            sym = AttendanceSymbolService().list_rows_by_code()

            def _sym(code: str, default: str) -> str:
                row_data = sym.get(code)
                if row_data is not None:
                    try:
                        if int(row_data.get("is_visible") or 0) != 1:
                            return ""
                    except Exception:
                        return ""
                    return (
                        str(row_data.get("symbol") or "").strip()
                        or str(default).strip()
                    )
                return str(default).strip()

            overtime_symbol = _sym("C04", "+")
            work_symbol = _sym("C03", "X")
            late_symbol = _sym("C01", "Tr")
            early_symbol = _sym("C02", "Sm")
            holiday_symbol = _sym("C10", "Le")
            absent_symbol = _sym("C07", "V")
            off_symbol = _sym("C09", "OFF")
            missing_out_symbol = _sym("C05", "KR")
            missing_in_symbol = _sym("C06", "KV")
        except Exception:
            overtime_symbol = "+"
            work_symbol = "X"
            late_symbol = "Tr"
            early_symbol = "Sm"
            holiday_symbol = "Le"
            absent_symbol = "V"
            off_symbol = "OFF"
            missing_out_symbol = "KR"
            missing_in_symbol = "KV"

        table.setRowCount(len(rows))
        for r_idx, r in enumerate(rows):
            # Fill KR/KV per in/out pair (only the missing one), based on configured
            # attendance symbols C05/C06.
            try:
                has_shift = bool(str(r.get("shift_code") or "").strip()) or bool(
                    str(r.get("schedule") or "").strip()
                )

                def _is_empty_time(v: object | None) -> bool:
                    s = "" if v is None else str(v)
                    s = s.strip()
                    if not s:
                        return True
                    # If it's not a time (e.g. 'Le', 'V', 'OFF'), don't treat it as a punch.
                    # This prevents showing KR/KV when in_1 is already filled by C10/C07/C09.
                    if ":" not in s:
                        return True
                    return s.lower() in {"none", "null"}

                def _pair_fill(key: str) -> str:
                    if not has_shift:
                        return ""
                    if key.startswith("in_"):
                        out_key = "out_" + key.split("_", 1)[1]
                        if _is_empty_time(r.get(key)) and (
                            not _is_empty_time(r.get(out_key))
                        ):
                            return str(missing_in_symbol or "").strip()
                        return ""
                    if key.startswith("out_"):
                        in_key = "in_" + key.split("_", 1)[1]
                        if _is_empty_time(r.get(key)) and (
                            not _is_empty_time(r.get(in_key))
                        ):
                            return str(missing_out_symbol or "").strip()
                        return ""
                    return ""

            except Exception:
                has_shift = False

                def _pair_fill(_key: str) -> str:  # type: ignore[no-redef]
                    return ""

            for c_idx, key in enumerate(cols):
                if key == "__check":
                    item = QTableWidgetItem("❌")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    try:
                        item.setData(Qt.ItemDataRole.UserRole, r.get("id"))
                    except Exception:
                        pass
                elif key == "stt":
                    stt_val = r.get("stt")
                    if stt_val is None or str(stt_val).strip() == "":
                        stt_val = r_idx + 1
                    item = QTableWidgetItem(str(stt_val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                else:
                    v = r.get(key)

                    if key in {"in_1", "out_1", "in_2", "out_2", "in_3", "out_3"}:
                        raw = "" if v is None else str(v).strip()
                        if (not raw) or (raw.lower() in {"none", "null"}):
                            fill_val = _pair_fill(str(key))
                            if fill_val:
                                raw = fill_val
                        try:
                            txt = self._content2._format_time_value(raw)  # type: ignore[attr-defined]
                        except Exception:
                            txt = raw
                        item = QTableWidgetItem(str(txt))
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw)
                        except Exception:
                            pass
                    elif key in {"hours_plus", "work_plus", "leave_plus"}:
                        raw_val = v
                        txt = "" if raw_val is None else str(raw_val)
                        txt = txt.strip()
                        item = QTableWidgetItem(txt)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw_val)
                        except Exception:
                            pass
                    elif key == "hours":
                        raw_val = v
                        txt0 = "" if raw_val is None else str(raw_val).strip()

                        def _is_full_hours(row0: dict[str, Any]) -> bool:
                            try:
                                late0 = int(float(str(row0.get("late") or 0).strip()))
                            except Exception:
                                late0 = 0
                            try:
                                early0 = int(float(str(row0.get("early") or 0).strip()))
                            except Exception:
                                early0 = 0
                            return late0 <= 0 and early0 <= 0

                        def _fmt_trunc_hours(val: object | None, places: int) -> str:
                            if val is None:
                                return ""
                            s = "" if val is None else str(val).strip()
                            if not s or s.lower() in {"none", "null"}:
                                return ""
                            try:
                                from decimal import Decimal, ROUND_DOWN

                                d = Decimal(str(val))
                                q = Decimal("1") if places <= 0 else Decimal("0.1")
                                return str(d.quantize(q, rounding=ROUND_DOWN))
                            except Exception:
                                try:
                                    f = float(s)
                                    if places <= 0:
                                        return str(int(f))
                                    return f"{f:.{places}f}"
                                except Exception:
                                    return s

                        if (not txt0) or (txt0.lower() in {"none", "null"}):
                            txt = ""
                        else:
                            full_h = _is_full_hours(r)
                            txt = _fmt_trunc_hours(raw_val, 0 if full_h else 1)
                        item = QTableWidgetItem(txt)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw_val)
                        except Exception:
                            pass
                    elif key == "work":
                        raw_val = v
                        txt0 = "" if raw_val is None else str(raw_val).strip()

                        def _work_amount(val: object | None):
                            s = "" if val is None else str(val).strip()
                            if not s or s.lower() in {"none", "null"}:
                                return None
                            try:
                                from decimal import Decimal

                                return Decimal(s)
                            except Exception:
                                try:
                                    from decimal import Decimal

                                    return Decimal(str(float(s)))
                                except Exception:
                                    return None

                        def _is_full_work(row0: dict[str, Any], val0: object | None) -> bool:
                            # UX rule: show work symbol (C03) only when work is a full integer day (>= 1).
                            d = _work_amount(val0)
                            if d is None:
                                return False
                            try:
                                from decimal import Decimal, ROUND_DOWN

                                int_part = d.quantize(Decimal("1"), rounding=ROUND_DOWN)
                                if d != int_part:
                                    return False
                                return d >= Decimal("1")
                            except Exception:
                                try:
                                    f = float(str(val0).strip())
                                except Exception:
                                    return False
                                if abs(f - round(f)) > 1e-9:
                                    return False
                                return f >= 1.0

                        def _fmt_trunc(val: object | None, places: int) -> str:
                            if val is None:
                                return ""
                            s = "" if val is None else str(val).strip()
                            if not s or s.lower() in {"none", "null"}:
                                return ""
                            try:
                                from decimal import Decimal, ROUND_DOWN

                                d = Decimal(str(val))
                                q = (
                                    Decimal("1")
                                    if places <= 0
                                    else Decimal("0." + ("0" * (places - 1)) + "1")
                                )
                                return str(d.quantize(q, rounding=ROUND_DOWN))
                            except Exception:
                                try:
                                    f = float(s)
                                    if places <= 0:
                                        return str(int(f))
                                    return f"{f:.{places}f}"
                                except Exception:
                                    return s

                        if (not txt0) or (txt0.lower() in {"none", "null"}):
                            txt = ""
                        else:
                            d0 = _work_amount(raw_val)
                            full = _is_full_work(r, raw_val)
                            # Keep integers compact (e.g. 0, 1, 2) and decimals like 0.5.
                            if d0 is not None:
                                try:
                                    from decimal import Decimal, ROUND_DOWN

                                    is_int = d0 == d0.quantize(Decimal("1"), rounding=ROUND_DOWN)
                                except Exception:
                                    try:
                                        f0 = float(str(raw_val).strip())
                                        is_int = abs(f0 - round(f0)) <= 1e-9
                                    except Exception:
                                        is_int = False
                            else:
                                is_int = False

                            txt = _fmt_trunc(raw_val, 0 if is_int else 1)
                            if full:
                                if txt and work_symbol and work_symbol not in txt:
                                    txt = f"{txt} {work_symbol}".strip()

                        item = QTableWidgetItem(txt)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw_val)
                        except Exception:
                            pass
                    elif key in {"late", "early"}:
                        raw_val = v
                        try:
                            in1 = str(r.get("in_1") or "").strip()
                        except Exception:
                            in1 = ""

                        if (
                            in1
                            and ":" not in in1
                            and in1
                            in {
                                str(absent_symbol or "").strip(),
                                str(off_symbol or "").strip(),
                                str(holiday_symbol or "").strip(),
                            }
                        ):
                            txt = ""
                        else:
                            try:
                                m = (
                                    int(float(str(raw_val).strip()))
                                    if raw_val is not None
                                    else 0
                                )
                            except Exception:
                                m = 0
                            txt = str(max(0, m))

                        if key == "late" and txt:
                            try:
                                if (
                                    txt != "0"
                                    and late_symbol
                                    and late_symbol not in txt
                                ):
                                    txt = f"{txt} {late_symbol}".strip()
                            except Exception:
                                pass
                        if key == "early" and txt:
                            try:
                                if (
                                    txt != "0"
                                    and early_symbol
                                    and early_symbol not in txt
                                ):
                                    txt = f"{txt} {early_symbol}".strip()
                            except Exception:
                                pass
                        item = QTableWidgetItem(txt)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw_val)
                        except Exception:
                            pass
                    elif key in {"tc1", "tc2", "tc3"}:
                        raw_val = v
                        txt = "" if raw_val is None else str(raw_val).strip()
                        if txt:
                            try:
                                if float(txt) != 0 and overtime_symbol and overtime_symbol not in txt:
                                    txt = f"{txt} {overtime_symbol}".strip()
                            except Exception:
                                if overtime_symbol and overtime_symbol not in txt:
                                    txt = f"{txt} {overtime_symbol}".strip()
                        item = QTableWidgetItem(txt)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, raw_val)
                        except Exception:
                            pass
                    else:
                        item = QTableWidgetItem("" if v is None else str(v))

                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(r_idx, c_idx, item)

        # Ensure per-column UI settings apply to created items.
        try:
            self._content2.apply_ui_settings()
        except Exception:
            pass

    def _render_audit_table_chunked(
        self, rows: list[dict[str, Any]], dlg: QDialog | None
    ) -> None:
        """Render audit table without freezing the UI.

        QTableWidget cell creation is expensive; rendering everything in one loop can
        make Windows show "Not Responding". We time-slice with QTimer.
        """

        if self._content2 is None:
            if dlg is not None:
                try:
                    dlg.finish_and_close()  # type: ignore[attr-defined]
                except Exception:
                    try:
                        dlg.close()
                    except Exception:
                        pass
            return

        table = self._content2.table

        # Reset table quickly.
        try:
            table.setRowCount(0)
        except Exception:
            pass

        # Show table once we start rendering (compute already finished).
        try:
            if hasattr(self._content2, "table_frame") and self._content2.table_frame is not None:
                self._content2.table_frame.setVisible(True)
        except Exception:
            pass
        if not rows:
            try:
                if hasattr(self._content2, "table_frame") and self._content2.table_frame is not None:
                    self._content2.table_frame.setVisible(True)
            except Exception:
                pass
            if dlg is not None:
                try:
                    dlg.finish_and_close()  # type: ignore[attr-defined]
                except Exception:
                    try:
                        dlg.close()
                    except Exception:
                        pass
            return

        cols = [k for (k, _label) in getattr(self._content2, "_COLUMNS", [])]
        if not cols:
            try:
                if hasattr(self._content2, "table_frame") and self._content2.table_frame is not None:
                    self._content2.table_frame.setVisible(True)
            except Exception:
                pass
            if dlg is not None:
                try:
                    dlg.finish_and_close()  # type: ignore[attr-defined]
                except Exception:
                    try:
                        dlg.close()
                    except Exception:
                        pass
            return

        # Load symbols (cached; avoid extra DB query on every view).
        overtime_symbol = "+"  # C04
        work_symbol = "X"  # C03
        late_symbol = "Tr"  # C01
        early_symbol = "Sm"  # C02
        holiday_symbol = "Le"  # C10
        absent_symbol = "V"  # C07
        off_symbol = "OFF"  # C09
        missing_out_symbol = "KR"  # C05
        missing_in_symbol = "KV"  # C06
        try:
            sym = self._get_symbols_by_code_cached()

            def _sym(code: str, default: str) -> str:
                row_data = sym.get(code)
                if row_data is not None:
                    try:
                        if int(row_data.get("is_visible") or 0) != 1:
                            return ""
                    except Exception:
                        return ""
                    return (
                        str(row_data.get("symbol") or "").strip()
                        or str(default).strip()
                    )
                return str(default).strip()

            overtime_symbol = _sym("C04", "+")
            work_symbol = _sym("C03", "X")
            late_symbol = _sym("C01", "Tr")
            early_symbol = _sym("C02", "Sm")
            holiday_symbol = _sym("C10", "Le")
            absent_symbol = _sym("C07", "V")
            off_symbol = _sym("C09", "OFF")
            missing_out_symbol = _sym("C05", "KR")
            missing_in_symbol = _sym("C06", "KV")
        except Exception:
            overtime_symbol = "+"
            work_symbol = "X"
            late_symbol = "Tr"
            early_symbol = "Sm"
            holiday_symbol = "Le"
            absent_symbol = "V"
            off_symbol = "OFF"
            missing_out_symbol = "KR"
            missing_in_symbol = "KV"

        # Prepare table for incremental append (avoid setRowCount(len) spike on large result).
        try:
            table.setRowCount(0)
        except Exception:
            pass
        # Keep table visible and repaint once per tick (avoid "tính xong mới hiện").
        try:
            table.setUpdatesEnabled(True)
        except Exception:
            pass
        try:
            table.setSortingEnabled(False)
        except Exception:
            pass

        # Store state so we can cancel/restart safely.
        self._audit_render_state = {
            "rows": rows,
            "cols": cols,
            "idx": 0,
            "t0": time.perf_counter(),
            "dlg": dlg,
            "table": table,
            "overtime_symbol": overtime_symbol,
            "work_symbol": work_symbol,
            "late_symbol": late_symbol,
            "early_symbol": early_symbol,
            "holiday_symbol": holiday_symbol,
            "missing_out_symbol": missing_out_symbol,
            "missing_in_symbol": missing_in_symbol,
        }

        if self._audit_render_timer is None:
            self._audit_render_timer = QTimer(self._parent_window)
            self._audit_render_timer.setSingleShot(True)

        def _tick() -> None:
            st = self._audit_render_state
            if not st:
                return

            _rows: list[dict[str, Any]] = st["rows"]
            _cols: list[str] = st["cols"]
            _table = st["table"]
            _dlg = st["dlg"]

            overtime_symbol2 = str(st.get("overtime_symbol") or "").strip()
            work_symbol2 = str(st.get("work_symbol") or "").strip()
            late_symbol2 = str(st.get("late_symbol") or "").strip()
            early_symbol2 = str(st.get("early_symbol") or "").strip()
            missing_out_symbol2 = str(st.get("missing_out_symbol") or "").strip()
            missing_in_symbol2 = str(st.get("missing_in_symbol") or "").strip()

            try:
                idx = int(st.get("idx") or 0)
            except Exception:
                idx = 0

            # Render for up to ~12ms per tick to keep Windows responsive.
            budget = QElapsedTimer()
            budget.start()

            def _norm(s: object | None) -> str:
                return str("" if s is None else s).strip()

            try:
                _table.blockSignals(True)
            except Exception:
                pass

            while idx < len(_rows) and int(budget.elapsed()) < 12:
                r = _rows[idx]

                # Ensure row exists before setItem.
                try:
                    if _table.rowCount() < (idx + 1):
                        _table.setRowCount(idx + 1)
                except Exception:
                    pass

                # Fill KR/KV per in/out pair (only the missing one).
                try:
                    has_shift = bool(_norm(r.get("shift_code"))) or bool(
                        _norm(r.get("schedule"))
                    )

                    def _is_empty_time(v: object | None) -> bool:
                        s = _norm(v)
                        if not s:
                            return True
                        # If it's not a time (e.g. 'Le', 'V', 'OFF'), don't treat it as a punch.
                        if ":" not in s:
                            return True
                        return s.lower() in {"none", "null"}

                    def _pair_fill(key: str) -> str:
                        if not has_shift:
                            return ""
                        if key.startswith("in_"):
                            out_key = "out_" + key.split("_", 1)[1]
                            if _is_empty_time(r.get(key)) and (
                                not _is_empty_time(r.get(out_key))
                            ):
                                return missing_in_symbol2
                            return ""
                        if key.startswith("out_"):
                            in_key = "in_" + key.split("_", 1)[1]
                            if _is_empty_time(r.get(key)) and (
                                not _is_empty_time(r.get(in_key))
                            ):
                                return missing_out_symbol2
                            return ""
                        return ""

                except Exception:

                    def _pair_fill(_key: str) -> str:  # type: ignore[no-redef]
                        return ""

                for c_idx, key in enumerate(_cols):
                    if key == "__check":
                        item = QTableWidgetItem("❌")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        try:
                            item.setData(Qt.ItemDataRole.UserRole, r.get("id"))
                        except Exception:
                            pass
                    elif key == "stt":
                        stt_val = r.get("stt")
                        if stt_val is None or str(stt_val).strip() == "":
                            stt_val = idx + 1
                        item = QTableWidgetItem(str(stt_val))
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    else:
                        v = r.get(key)

                        if key in {"in_1", "out_1", "in_2", "out_2", "in_3", "out_3"}:
                            raw = _norm(v)
                            if (not raw) or (raw.lower() in {"none", "null"}):
                                fill_val = _pair_fill(str(key))
                                if fill_val:
                                    raw = fill_val
                            try:
                                txt = self._content2._format_time_value(raw)  # type: ignore[attr-defined]
                            except Exception:
                                txt = raw
                            item = QTableWidgetItem(str(txt))
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw)
                            except Exception:
                                pass
                        elif key in {"hours_plus", "work_plus", "leave_plus"}:
                            raw_val = v
                            txt = _norm(raw_val)
                            item = QTableWidgetItem(txt)
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw_val)
                            except Exception:
                                pass
                        elif key == "hours":
                            raw_val = v
                            txt0 = _norm(raw_val)

                            def _is_full_hours2(row0: dict[str, Any]) -> bool:
                                try:
                                    late0 = int(
                                        float(str(row0.get("late") or 0).strip())
                                    )
                                except Exception:
                                    late0 = 0
                                try:
                                    early0 = int(
                                        float(str(row0.get("early") or 0).strip())
                                    )
                                except Exception:
                                    early0 = 0
                                return late0 <= 0 and early0 <= 0

                            def _fmt_trunc_hours2(
                                val: object | None, places: int
                            ) -> str:
                                if val is None:
                                    return ""
                                s = _norm(val)
                                if not s or s.lower() in {"none", "null"}:
                                    return ""
                                try:
                                    from decimal import Decimal, ROUND_DOWN

                                    d = Decimal(str(val))
                                    q = Decimal("1") if places <= 0 else Decimal("0.1")
                                    return str(d.quantize(q, rounding=ROUND_DOWN))
                                except Exception:
                                    try:
                                        f = float(s)
                                        if places <= 0:
                                            return str(int(f))
                                        return f"{f:.{places}f}"
                                    except Exception:
                                        return s

                            if (not txt0) or (txt0.lower() in {"none", "null"}):
                                txt = ""
                            else:
                                full_h = _is_full_hours2(r)
                                txt = _fmt_trunc_hours2(raw_val, 0 if full_h else 1)
                            item = QTableWidgetItem(txt)
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw_val)
                            except Exception:
                                pass
                        elif key == "work":
                            raw_val = v
                            txt = _norm(raw_val)

                            def _work_amount2(val: object | None):
                                s = _norm(val)
                                if not s or s.lower() in {"none", "null"}:
                                    return None
                                try:
                                    from decimal import Decimal

                                    return Decimal(s)
                                except Exception:
                                    try:
                                        from decimal import Decimal

                                        return Decimal(str(float(s)))
                                    except Exception:
                                        return None

                            def _is_full_work2(row0: dict[str, Any], val0: object | None) -> bool:
                                d = _work_amount2(val0)
                                if d is None:
                                    return False
                                try:
                                    from decimal import Decimal, ROUND_DOWN

                                    int_part = d.quantize(Decimal("1"), rounding=ROUND_DOWN)
                                    if d != int_part:
                                        return False
                                    return d >= Decimal("1")
                                except Exception:
                                    try:
                                        f = float(_norm(val0))
                                    except Exception:
                                        return False
                                    if abs(f - round(f)) > 1e-9:
                                        return False
                                    return f >= 1.0

                            def _fmt_trunc2(val: object | None, places: int) -> str:
                                if val is None:
                                    return ""
                                s = _norm(val)
                                if not s or s.lower() in {"none", "null"}:
                                    return ""
                                try:
                                    from decimal import Decimal, ROUND_DOWN

                                    d = Decimal(str(val))
                                    q = (
                                        Decimal("0." + ("0" * (places - 1)) + "1")
                                        if places > 0
                                        else Decimal("1")
                                    )
                                    return str(d.quantize(q, rounding=ROUND_DOWN))
                                except Exception:
                                    try:
                                        f = float(s)
                                        if places <= 0:
                                            return str(int(f))
                                        return f"{f:.{places}f}"
                                    except Exception:
                                        return s

                            full2 = _is_full_work2(r, raw_val)
                            if not txt or txt.lower() in {"none", "null"}:
                                txt2 = ""
                            else:
                                d02 = _work_amount2(raw_val)
                                if d02 is not None:
                                    try:
                                        from decimal import Decimal, ROUND_DOWN

                                        is_int2 = d02 == d02.quantize(
                                            Decimal("1"), rounding=ROUND_DOWN
                                        )
                                    except Exception:
                                        try:
                                            f02 = float(_norm(raw_val))
                                            is_int2 = abs(f02 - round(f02)) <= 1e-9
                                        except Exception:
                                            is_int2 = False
                                else:
                                    is_int2 = False

                                txt2 = _fmt_trunc2(raw_val, 0 if is_int2 else 1)
                                if full2:
                                    if (
                                        txt2
                                        and work_symbol2
                                        and work_symbol2 not in txt2
                                    ):
                                        txt2 = f"{txt2} {work_symbol2}".strip()

                            item = QTableWidgetItem(txt2)
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw_val)
                            except Exception:
                                pass
                        elif key in {"late", "early"}:
                            raw_val = v
                            try:
                                in1 = _norm(r.get("in_1"))
                            except Exception:
                                in1 = ""

                            if (
                                in1
                                and ":" not in in1
                                and in1
                                in {
                                    str(absent_symbol or "").strip(),
                                    str(off_symbol or "").strip(),
                                    str(holiday_symbol or "").strip(),
                                }
                            ):
                                txt = ""
                            else:
                                try:
                                    m = (
                                        int(float(str(raw_val).strip()))
                                        if raw_val is not None
                                        else 0
                                    )
                                except Exception:
                                    m = 0
                                txt = str(max(0, m))

                            if key == "late" and txt:
                                try:
                                    if (
                                        txt != "0"
                                        and late_symbol2
                                        and late_symbol2 not in txt
                                    ):
                                        txt = f"{txt} {late_symbol2}".strip()
                                except Exception:
                                    pass
                            if key == "early" and txt:
                                try:
                                    if (
                                        txt != "0"
                                        and early_symbol2
                                        and early_symbol2 not in txt
                                    ):
                                        txt = f"{txt} {early_symbol2}".strip()
                                except Exception:
                                    pass
                            item = QTableWidgetItem(txt)
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw_val)
                            except Exception:
                                pass
                        elif key in {"tc1", "tc2", "tc3"}:
                            raw_val = v
                            txt = _norm(raw_val)
                            if txt:
                                try:
                                    if float(txt) != 0 and overtime_symbol2 and overtime_symbol2 not in txt:
                                        txt = f"{txt} {overtime_symbol2}".strip()
                                except Exception:
                                    if overtime_symbol2 and overtime_symbol2 not in txt:
                                        txt = f"{txt} {overtime_symbol2}".strip()
                            item = QTableWidgetItem(txt)
                            try:
                                item.setData(Qt.ItemDataRole.UserRole, raw_val)
                            except Exception:
                                pass
                        else:
                            item = QTableWidgetItem("" if v is None else str(v))

                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    _table.setItem(idx, c_idx, item)

                idx += 1

            try:
                _table.blockSignals(False)
            except Exception:
                pass

            st["idx"] = idx

            # Repaint after each slice so user sees rows appear progressively.
            try:
                _table.viewport().update()
            except Exception:
                pass

            if idx >= len(_rows):
                try:
                    self._content2.apply_ui_settings()
                except Exception:
                    pass
                try:
                    t0 = float(st.get("t0") or 0)
                    dt_ms = int((time.perf_counter() - t0) * 1000) if t0 else 0
                    logger.info("Xem công: render rows=%s in %sms", len(_rows), dt_ms)
                except Exception:
                    pass
                if _dlg is not None:
                    try:
                        _dlg.finish_and_close()  # type: ignore[attr-defined]
                    except Exception:
                        try:
                            _dlg.close()
                        except Exception:
                            pass
                # Keep table visible; do not wait until end to show.
                self._cancel_audit_render()
                return

            # Continue next slice.
            try:
                self._audit_render_timer.start(0)
            except Exception:
                QTimer.singleShot(0, _tick)

        try:
            if self._audit_render_tick is not None:
                self._audit_render_timer.timeout.disconnect(self._audit_render_tick)
        except Exception:
            pass
        self._audit_render_tick = _tick
        self._audit_render_timer.timeout.connect(_tick)
        self._audit_render_timer.start(0)
