"""ui.dialog.arrange_schedule_dialog

Dialog "Sắp xếp ca cho lịch trình".

Yêu cầu:
- Set kích thước cửa sổ trước
- Để trống (chưa triển khai nội dung)
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWidgets import QTableWidgetItem

from core.resource import (
    COLOR_BORDER,
    COLOR_BUTTON_PRIMARY_HOVER,
    HOVER_ROW_BG_COLOR,
    COLOR_TEXT_PRIMARY,
    CONTENT_FONT,
    FONT_WEIGHT_SEMIBOLD,
    UI_FONT,
    COLOR_TEXT_LIGHT,
)

from core.database import Database
from ui.dialog.title_dialog import MessageDialog


class ArrangeScheduleDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        logging.getLogger(__name__).info("Open ArrangeScheduleDialog")
        self.setModal(True)
        self.setWindowTitle("Sắp xếp ca cho lịch trình")

        DAY_NAMES: tuple[str, ...] = (
            "Thứ 2",
            "Thứ 3",
            "Thứ 4",
            "Thứ 5",
            "Thứ 6",
            "Thứ 7",
            "Chủ nhật",
            "Ngày Lễ",
        )

        # Set size first (placeholder)
        self.setMinimumSize(900, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QWidget(self)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        def _mk_list() -> QListWidget:
            lw = QListWidget(self)
            lw.setSelectionMode(QListWidget.SelectionMode.NoSelection)
            lw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            lw.setStyleSheet(
                "\n".join(
                    [
                        f"QListWidget {{ border: 1px solid {COLOR_BORDER}; border-radius: 0px; padding: 6px; color: {COLOR_TEXT_PRIMARY}; }}",
                        "QListWidget::item { padding: 8px; }",
                        f"QListWidget::item:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                        "QListWidget::item:focus { outline: none; }",
                        "QListWidget:focus { outline: none; }",
                    ]
                )
            )
            return lw

        def _set_checked(item: QListWidgetItem, checked: bool) -> None:
            base = str(item.data(Qt.ItemDataRole.UserRole) or "")
            item.setText(f"✅ {base}" if checked else f"❌ {base}")
            item.setData(Qt.ItemDataRole.UserRole + 1, bool(checked))

        def _is_checked(item: QListWidgetItem) -> bool:
            return bool(item.data(Qt.ItemDataRole.UserRole + 1))

        def _toggle_item(item: QListWidgetItem) -> None:
            _set_checked(item, not _is_checked(item))

        def _get_checked_values(lw: QListWidget) -> list[str]:
            result: list[str] = []
            for i in range(lw.count()):
                it = lw.item(i)
                if it is None:
                    continue
                if _is_checked(it):
                    base = str(it.data(Qt.ItemDataRole.UserRole) or "").strip()
                    if base:
                        result.append(base)
            return result

        def _mk_group(title: str) -> QGroupBox:
            gb = QGroupBox(title, self)
            gb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            font = QFont(UI_FONT, CONTENT_FONT)
            if FONT_WEIGHT_SEMIBOLD >= 500:
                font.setWeight(QFont.Weight.DemiBold)
            gb.setFont(font)
            gb.setStyleSheet(
                "\n".join(
                    [
                        f"QGroupBox {{ border: 1px solid {COLOR_BORDER}; border-radius: 8px; margin-top: 10px; color: {COLOR_TEXT_PRIMARY}; }}",
                        "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }",
                    ]
                )
            )
            return gb

        def _list_shift_codes_from_db() -> list[str]:
            """Lấy danh sách mã ca từ module 'Khai báo Ca làm việc' (bảng work_shifts)."""
            cursor = None
            try:
                with Database.connect() as conn:
                    cursor = Database.get_cursor(conn, dictionary=True)
                    cursor.execute("SELECT shift_code FROM work_shifts ORDER BY id ASC")
                    rows = list(cursor.fetchall() or [])
                result: list[str] = []
                for r in rows:
                    code = str(r.get("shift_code") or "").strip()
                    if code:
                        result.append(code)
                # de-dup while keeping order
                seen: set[str] = set()
                ordered: list[str] = []
                for c in result:
                    if c in seen:
                        continue
                    seen.add(c)
                    ordered.append(c)
                return ordered
            except Exception:
                logging.getLogger(__name__).exception(
                    "Không thể tải danh sách ca từ work_shifts"
                )
                return []
            finally:
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception:
                        pass

        def _populate_shift_list(codes: list[str]) -> None:
            self.list_shifts.clear()
            for name in codes or []:
                it = QListWidgetItem(name, self.list_shifts)
                it.setData(Qt.ItemDataRole.UserRole, name)
                _set_checked(it, False)

        # Group 1 (bên trái): danh sách ca
        self.group_shift_types = _mk_group("Danh sách ca")
        g1 = QVBoxLayout(self.group_shift_types)
        g1.setContentsMargins(10, 14, 10, 10)
        g1.setSpacing(6)

        self.list_shifts = _mk_list()
        db_shift_codes = _list_shift_codes_from_db()
        if not db_shift_codes:
            db_shift_codes = ["HC", "SA", "CH", "Ca1", "Ca2"]
        _populate_shift_list(db_shift_codes)

        g1.addWidget(self.list_shifts, 1)

        # Group 2: danh sách ngày
        self.group_days_select = _mk_group("Danh sách ngày")
        g2 = QVBoxLayout(self.group_days_select)
        g2.setContentsMargins(10, 14, 10, 10)
        g2.setSpacing(6)

        self.list_days = _mk_list()
        for name in DAY_NAMES:
            it = QListWidgetItem(name, self.list_days)
            it.setData(Qt.ItemDataRole.UserRole, name)
            _set_checked(it, False)

        g2.addWidget(self.list_days, 1)

        # Group 3: danh sách ca chọn (phân cấp) + 4 button
        self.group_apply = _mk_group("Danh sách ca chọn")
        g3 = QVBoxLayout(self.group_apply)
        g3.setContentsMargins(10, 14, 10, 10)
        g3.setSpacing(10)

        self.tree_selected = QTreeWidget(self.group_apply)
        self.tree_selected.setHeaderHidden(True)
        self.tree_selected.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree_selected.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree_selected.setStyleSheet(
            "\n".join(
                [
                    f"QTreeWidget {{ border: 1px solid {COLOR_BORDER}; border-radius: 0px; padding: 6px; color: {COLOR_TEXT_PRIMARY}; }}",
                    "QTreeWidget::item { padding: 6px; }",
                    f"QTreeWidget::item:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; }}",
                    "QTreeWidget::item:focus { outline: none; }",
                    "QTreeWidget:focus { outline: none; }",
                ]
            )
        )

        buttons_row = QWidget(self.group_apply)
        btns = QHBoxLayout(buttons_row)
        btns.setContentsMargins(0, 0, 0, 0)
        btns.setSpacing(8)

        self.btn_apply_selected = QPushButton("Thực hiện chọn")
        self.btn_delete_selected = QPushButton("Xóa ca chọn")
        self.btn_delete_all = QPushButton("Xóa tất cả ca")
        self.btn_apply = QPushButton("Áp dụng")

        btn_style = "\n".join(
            [
                f"QPushButton {{ border: 1px solid {COLOR_BORDER}; background: transparent; color: {COLOR_TEXT_PRIMARY}; padding: 0 10px; border-radius: 0px; }}",
                f"QPushButton:hover {{ background: {COLOR_BUTTON_PRIMARY_HOVER}; color: {COLOR_TEXT_LIGHT}; border: 1px solid {COLOR_BORDER}; }}",
            ]
        )

        for b in (
            self.btn_apply_selected,
            self.btn_delete_selected,
            self.btn_delete_all,
            self.btn_apply,
        ):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(34)
            b.setStyleSheet(btn_style)
            btns.addWidget(b)

        g3.addWidget(self.tree_selected, 1)
        g3.addWidget(buttons_row, 0)

        top_layout.addWidget(self.group_shift_types, 1)
        top_layout.addWidget(self.group_days_select, 1)
        top_layout.addWidget(self.group_apply, 2)

        root.addWidget(top, 1)

        # Toggle behavior with emoji ✅
        def _on_list_item_clicked(lw: QListWidget, item: QListWidgetItem) -> None:
            _toggle_item(item)
            try:
                lw.setCurrentRow(-1)
            except Exception:
                pass

        self.list_shifts.itemClicked.connect(
            lambda item: _on_list_item_clicked(self.list_shifts, item)
        )
        self.list_days.itemClicked.connect(
            lambda item: _on_list_item_clicked(self.list_days, item)
        )

        def _tree_set_checked(item: QTreeWidgetItem, checked: bool) -> None:
            meta = item.data(0, Qt.ItemDataRole.UserRole) or {}
            kind = str(meta.get("kind") or "")
            base = str(meta.get("text") or "")
            is_child = kind == "shift"
            prefix = "└── " if is_child else ""
            item.setText(0, f"✅ {prefix}{base}" if checked else f"❌ {prefix}{base}")
            item.setData(0, Qt.ItemDataRole.UserRole + 1, bool(checked))

        def _tree_is_checked(item: QTreeWidgetItem) -> bool:
            return bool(item.data(0, Qt.ItemDataRole.UserRole + 1))

        def _tree_update_day_state(day_node: QTreeWidgetItem) -> None:
            any_checked = False
            for i in range(day_node.childCount()):
                ch = day_node.child(i)
                if ch is not None and _tree_is_checked(ch):
                    any_checked = True
                    break
            _tree_set_checked(day_node, any_checked)

        def _tree_toggle_item(item: QTreeWidgetItem) -> None:
            meta = item.data(0, Qt.ItemDataRole.UserRole) or {}
            kind = str(meta.get("kind") or "")
            new_state = not _tree_is_checked(item)

            _tree_set_checked(item, new_state)
            if kind == "day":
                for i in range(item.childCount()):
                    ch = item.child(i)
                    if ch is not None:
                        _tree_set_checked(ch, new_state)
            else:
                parent = item.parent()
                if parent is not None:
                    _tree_update_day_state(parent)

        def _init_selected_tree_days() -> None:
            self.tree_selected.clear()
            for day_name in DAY_NAMES:
                node = QTreeWidgetItem([""])
                node.setData(
                    0, Qt.ItemDataRole.UserRole, {"kind": "day", "text": day_name}
                )
                self.tree_selected.addTopLevelItem(node)
                node.setExpanded(True)
                _tree_set_checked(node, False)

        def _get_day_node(day_name: str) -> QTreeWidgetItem | None:
            def _norm_day(s: str) -> str:
                return str(s or "").strip().casefold()

            for i in range(self.tree_selected.topLevelItemCount()):
                node = self.tree_selected.topLevelItem(i)
                if node is None:
                    continue
                meta = node.data(0, Qt.ItemDataRole.UserRole) or {}
                if str(meta.get("kind") or "") == "day" and _norm_day(
                    str(meta.get("text") or "")
                ) == _norm_day(day_name):
                    return node
            return None

        def _find_child_shift(
            day_node: QTreeWidgetItem, shift_code: str
        ) -> QTreeWidgetItem | None:
            def _norm_code(s: str) -> str:
                return str(s or "").strip().casefold()

            for i in range(day_node.childCount()):
                ch = day_node.child(i)
                if ch is None:
                    continue
                meta = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                if str(meta.get("kind") or "") == "shift" and _norm_code(
                    str(meta.get("text") or "")
                ) == _norm_code(shift_code):
                    return ch
            return None

        def _on_apply_selected() -> None:
            shift_codes = _get_checked_values(self.list_shifts)
            day_names = _get_checked_values(self.list_days)
            if not shift_codes:
                MessageDialog.info(
                    self, "Thông báo", "Vui lòng tích chọn ít nhất 1 ca."
                )
                return
            if not day_names:
                MessageDialog.info(
                    self, "Thông báo", "Vui lòng tích chọn ít nhất 1 ngày."
                )
                return

            for day_name in day_names:
                day_node = _get_day_node(day_name)
                if day_node is None:
                    continue
                for code in shift_codes:
                    child = _find_child_shift(day_node, code)
                    if child is None:
                        child = QTreeWidgetItem([""])
                        child.setData(
                            0,
                            Qt.ItemDataRole.UserRole,
                            {"kind": "shift", "text": code},
                        )
                        day_node.addChild(child)
                    _tree_set_checked(child, True)
                _tree_update_day_state(day_node)

        def _on_delete_selected() -> None:
            item = self.tree_selected.currentItem()
            if item is None:
                return
            meta = item.data(0, Qt.ItemDataRole.UserRole) or {}
            kind = str(meta.get("kind") or "")

            # Không xóa node ngày (vẫn phải hiển thị đủ 8 ngày). Nếu chọn ngày thì chỉ xóa toàn bộ ca con.
            if kind == "day":
                while item.childCount() > 0:
                    item.takeChild(0)
                _tree_set_checked(item, False)
                return

            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
                _tree_update_day_state(parent)

        def _on_delete_all() -> None:
            for i in range(self.tree_selected.topLevelItemCount()):
                day_node = self.tree_selected.topLevelItem(i)
                if day_node is None:
                    continue
                while day_node.childCount() > 0:
                    day_node.takeChild(0)
                _tree_set_checked(day_node, False)

        def _build_mapping_from_tree() -> dict[str, list[str]]:
            result: dict[str, list[str]] = {}
            for i in range(self.tree_selected.topLevelItemCount()):
                day_node = self.tree_selected.topLevelItem(i)
                if day_node is None:
                    continue
                meta = day_node.data(0, Qt.ItemDataRole.UserRole) or {}
                day_name = str(meta.get("text") or "").strip()
                if not day_name:
                    continue
                shifts: list[str] = []
                for j in range(day_node.childCount()):
                    ch = day_node.child(j)
                    if ch is None:
                        continue
                    if not _tree_is_checked(ch):
                        continue
                    ch_meta = ch.data(0, Qt.ItemDataRole.UserRole) or {}
                    code = str(ch_meta.get("text") or "").strip()
                    if code:
                        shifts.append(code)
                if shifts:
                    result[day_name] = shifts
            return result

        def _fetch_shift_ids(codes: list[str]) -> dict[str, int]:
            def _norm_code(s: str) -> str:
                return str(s or "").strip().casefold()

            codes_norm = [_norm_code(c) for c in (codes or []) if _norm_code(c)]
            codes_norm = sorted(set(codes_norm))
            if not codes_norm:
                return {}
            placeholders = ",".join(["%s"] * len(codes_norm))
            query = (
                "SELECT id, shift_code FROM hr_attendance.work_shifts "
                f"WHERE LOWER(TRIM(shift_code)) IN ({placeholders})"
            )
            cursor = None
            try:
                with Database.connect() as conn:
                    cursor = Database.get_cursor(conn, dictionary=True)
                    cursor.execute(query, tuple(codes_norm))
                    rows = list(cursor.fetchall() or [])
                result: dict[str, int] = {}
                for r in rows:
                    try:
                        key = _norm_code(str(r.get("shift_code") or ""))
                        if key:
                            result[key] = int(r.get("id"))
                    except Exception:
                        continue
                return result
            finally:
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception:
                        pass

        def _seed_default_work_shifts(codes_to_seed: list[str]) -> bool:
            """Tạo nhanh ca mặc định để tránh lỗi thiếu ca khi DB chưa có dữ liệu.

            Chỉ insert nếu chưa tồn tại (theo UNIQUE shift_code).
            """

            def _norm_code(s: str) -> str:
                return str(s or "").strip().casefold()

            # Default templates (có thể chỉnh lại sau trong module Ca làm việc)
            templates: dict[str, dict[str, object]] = {
                "hc": {
                    "shift_code": "HC",
                    "time_in": "08:00:00",
                    "time_out": "17:00:00",
                    "work_count": 1.0,
                },
                "sa": {
                    "shift_code": "SA",
                    "time_in": "08:00:00",
                    "time_out": "12:00:00",
                    "work_count": 0.5,
                },
                "ch": {
                    "shift_code": "CH",
                    "time_in": "13:00:00",
                    "time_out": "17:00:00",
                    "work_count": 0.5,
                },
                "ca1": {
                    "shift_code": "Ca1",
                    "time_in": "06:00:00",
                    "time_out": "14:00:00",
                    "work_count": 1.0,
                },
                "ca2": {
                    "shift_code": "Ca2",
                    "time_in": "14:00:00",
                    "time_out": "22:00:00",
                    "work_count": 1.0,
                },
            }

            payload: list[dict[str, object]] = []
            for c in codes_to_seed or []:
                key = _norm_code(c)
                tpl = templates.get(key)
                if tpl:
                    payload.append(tpl)
            if not payload:
                return False

            query = (
                "INSERT INTO hr_attendance.work_shifts "
                "(shift_code, time_in, time_out, work_count) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE shift_code = shift_code"
            )

            cursor = None
            try:
                with Database.connect() as conn:
                    cursor = Database.get_cursor(conn, dictionary=False)
                    for row in payload:
                        cursor.execute(
                            query,
                            (
                                str(row.get("shift_code")),
                                str(row.get("time_in")),
                                str(row.get("time_out")),
                                row.get("work_count"),
                            ),
                        )
                    conn.commit()
                return True
            except Exception:
                logging.getLogger(__name__).exception(
                    "Không thể seed work_shifts mặc định"
                )
                return False
            finally:
                if cursor is not None:
                    try:
                        cursor.close()
                    except Exception:
                        pass

        def _on_apply() -> None:
            mapping = _build_mapping_from_tree()
            if not mapping:
                MessageDialog.info(
                    self, "Thông báo", "Chưa có dữ liệu trong 'Danh sách ca chọn'."
                )
                return

            def _norm_day(s: str) -> str:
                return str(s or "").strip().casefold()

            mapping_norm = {_norm_day(k): v for k, v in mapping.items()}

            # Determine how many "Tên ca" columns to show (max shifts per day)
            max_shift_count = 0
            for v in mapping_norm.values():
                try:
                    max_shift_count = max(max_shift_count, len(list(v or [])))
                except Exception:
                    continue

            all_codes: list[str] = []
            for shifts in mapping.values():
                all_codes.extend(shifts)
            code_to_id = _fetch_shift_ids(all_codes)

            def _norm_code(s: str) -> str:
                return str(s or "").strip().casefold()

            unique_codes = sorted(
                set([_norm_code(c) for c in all_codes if _norm_code(c)])
            )
            missing = [c for c in unique_codes if c not in code_to_id]

            def _apply_to_parent_table(_code_to_id: dict[str, int]) -> None:
                # Push to parent table (ArrangeScheduleWidgets.MainRight)
                parent = self.parent()
                table = getattr(parent, "table", None)
                if table is None:
                    MessageDialog.info(self, "Lỗi", "Không tìm thấy bảng để áp dụng.")
                    return

                # Update visible shift columns on parent
                if hasattr(parent, "build_table"):
                    try:
                        parent.build_table(max_shift_count)
                    except Exception:
                        pass

                # columns: 1=Ngày, 2..(2+n-1)=Tên ca
                for r in range(table.rowCount()):
                    day_item = table.item(r, 1)
                    day_name = str(day_item.text() if day_item else "").strip()
                    if not day_name:
                        continue

                    shifts = mapping_norm.get(_norm_day(day_name), [])
                    # store ids in UserRole, display codes in text
                    shift_pairs: list[tuple[int | None, str]] = []
                    for c in shifts:
                        sid = _code_to_id.get(_norm_code(c))
                        shift_pairs.append(
                            (int(sid) if sid is not None else None, str(c))
                        )
                    # pad to table columns
                    needed = max(0, table.columnCount() - 2)
                    while len(shift_pairs) < needed:
                        shift_pairs.append((None, ""))

                    shift_cols = list(range(2, table.columnCount()))
                    for idx, col in enumerate(shift_cols):
                        it = table.item(r, col)
                        if it is None:
                            it = QTableWidgetItem("")
                            it.setTextAlignment(int(Qt.AlignmentFlag.AlignCenter))
                            table.setItem(r, col, it)
                        sid, code_text = (
                            shift_pairs[idx] if idx < len(shift_pairs) else (None, "")
                        )
                        it.setData(Qt.ItemDataRole.UserRole, sid)
                        it.setText(code_text)

                # Ensure day colors remain
                if hasattr(parent, "_apply_day_row_colors"):
                    try:
                        parent._apply_day_row_colors()
                    except Exception:
                        pass

                # Trigger save (persist) and refresh list
                if hasattr(parent, "save_clicked"):
                    try:
                        parent.save_clicked.emit()
                    except Exception:
                        pass

                self.accept()

            if missing:
                if not MessageDialog.confirm(
                    self,
                    "Thiếu ca",
                    "Chưa có ca trong bảng 'Ca làm việc' cho các mã: "
                    + ", ".join(missing)
                    + "\n\nBạn có muốn tạo nhanh các ca mặc định để tiếp tục Áp dụng không?",
                    ok_text="Tạo ca",
                    cancel_text="Hủy",
                    destructive=False,
                ):
                    return

                seeded = _seed_default_work_shifts(missing)
                if seeded:
                    code_to_id = _fetch_shift_ids(all_codes)
                    missing = [c for c in unique_codes if c not in code_to_id]
                if missing:
                    MessageDialog.info(
                        self,
                        "Thiếu ca",
                        "Vẫn thiếu ca cho các mã: " + ", ".join(missing),
                    )
                    return

            _apply_to_parent_table(code_to_id)

        self.btn_apply_selected.clicked.connect(_on_apply_selected)
        self.btn_delete_selected.clicked.connect(_on_delete_selected)
        self.btn_delete_all.clicked.connect(_on_delete_all)
        self.btn_apply.clicked.connect(_on_apply)

        self.tree_selected.itemClicked.connect(
            lambda item, _col: _tree_toggle_item(item)
        )

        _init_selected_tree_days()

        def _load_selected_from_parent_table() -> None:
            parent = self.parent()
            table = getattr(parent, "table", None)
            if table is None:
                return

            for r in range(table.rowCount()):
                day_item = table.item(r, 1)
                day_name = str(day_item.text() if day_item else "").strip()
                if not day_name:
                    continue

                day_node = _get_day_node(day_name)
                if day_node is None:
                    continue

                # Clear existing children for this day, then rebuild from current table values
                while day_node.childCount() > 0:
                    day_node.takeChild(0)

                any_added = False
                for c in (2, 3, 4, 5, 6):
                    it = table.item(r, c)
                    code = str(it.text() if it else "").strip()
                    if not code:
                        continue

                    child = QTreeWidgetItem([""])
                    child.setData(
                        0, Qt.ItemDataRole.UserRole, {"kind": "shift", "text": code}
                    )
                    day_node.addChild(child)
                    _tree_set_checked(child, True)
                    any_added = True

                if any_added:
                    _tree_update_day_state(day_node)
                else:
                    _tree_set_checked(day_node, False)

        _load_selected_from_parent_table()

        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass
