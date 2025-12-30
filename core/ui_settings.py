"""core.ui_settings

Lưu/đọc cài đặt UI (hiện tại: bảng nhân viên).

Mục tiêu:
- Cho phép SettingsDialog ghi cấu hình
- EmployeeTable (ở employee_widgets / import_employee_dialog) tự đọc và tự apply
- Có signal để các bảng đang mở cập nhật ngay
"""

from __future__ import annotations

import json
import logging
from os import environ
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.resource import resource_path


_LOGGER = logging.getLogger(__name__)


def _packaged_settings_path() -> Path:
    """Path to the default settings that ship with the application."""

    # In PyInstaller, this points to the extracted/bundled app directory.
    # This location can be read-only when the app is installed under Program Files.
    return Path(resource_path("database/ui_settings.json"))


def _user_settings_path() -> Path:
    """Writable per-user settings path.

    We must not write into the installation folder (e.g. Program Files) because it
    is typically read-only for standard users.
    """

    app_name = "attendance"
    base = environ.get("APPDATA") or environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / app_name / "ui_settings.json"
    # Fallback (should rarely be needed on Windows)
    return Path.home() / "." / app_name / "ui_settings.json"


def _settings_path() -> Path:
    """Compatibility wrapper: always return the writable settings path."""

    return _user_settings_path()


DEFAULT_UI_SETTINGS: dict[str, Any] = {
    "file_dialog": {
        # Last directory used in Save dialogs (export/backup/template).
        # When empty, default to user's Desktop.
        "last_save_dir": "",
    },
    "employee_table": {
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Header font settings.
        "header_font_size": 11,
        # "normal" | "bold"
        "header_font_weight": "bold",
        # Per-column: "left" | "center" | "right"
        "column_align": {
            "stt": "center",
            "employee_code": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
        # Per-column visible: true/false (defaults to true when missing)
        "column_visible": {},
    },
    "shift_attendance_table": {
        # UI controls (Shift Attendance screen)
        # Show/hide the "Import dữ liệu chấm công" button.
        "show_import_button": True,
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Header font settings.
        "header_font_size": 11,
        # "normal" | "bold"
        "header_font_weight": "bold",
        # Per-column: "left" | "center" | "right"
        "column_align": {
            "employee_code": "center",
            "date": "center",
            "weekday": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
        # Per-column visible: true/false (defaults to true when missing)
        "column_visible": {},
    },
    "shift_attendance_state": {
        # Persist basic view state for Shift Attendance (filters + UI toggles).
        # Kept small and JSON-serializable (dates stored as yyyy-MM-dd strings).
        "content1": {
            "department_id": None,
            "title_id": None,
            "search_by_data": "auto",
            "search_text": "",
            "date_from": "",
            "date_to": "",
        },
        "content2": {
            "show_seconds": True,
        },
    },
    "schedule_work_table": {
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Header font settings.
        "header_font_size": 11,
        # "normal" | "bold"
        "header_font_weight": "bold",
        # Per-column: "left" | "center" | "right"
        # Keys are shared across both tables in Schedule Work.
        "column_align": {
            "check": "center",
            "employee_code": "center",
            "mcc_code": "center",
            "from_date": "center",
            "to_date": "center",
            "full_name": "center",
            "department_name": "center",
            "title_name": "center",
            "schedule_name": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
    },
    "declare_work_shift_table": {
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Header font settings.
        "header_font_size": 11,
        # "normal" | "bold"
        "header_font_weight": "bold",
        # Per-column: "left" | "center" | "right"
        "column_align": {
            "shift_code": "center",
            "time_in": "center",
            "time_out": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
    },
    "arrange_schedule_table": {
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Header font settings.
        "header_font_size": 11,
        # "normal" | "bold"
        "header_font_weight": "bold",
        # Per-column: "left" | "center" | "right"
        "column_align": {
            "list_schedule_name": "center",
            "detail_day": "center",
            "detail_shift_1": "center",
            "detail_shift_2": "center",
            "detail_shift_3": "center",
            "detail_shift_4": "center",
            "detail_shift_5": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
    },
    "download_attendance": {
        # Font size for the attendance table body.
        "table_font_size": 11,
        # Font size/weight for the attendance table header.
        "table_header_font_size": 11,
        "table_header_font_weight": "bold",
        # Font size for comboboxes / inputs in TitleBar2.
        "combo_font_size": 11,
        # Font size for calendar popup.
        "calendar_font_size": 10,
        # Sizing for inputs/buttons in TitleBar2.
        "input_height": 28,
        "button_height": 28,
        # Width of date edits (0 = keep auto width)
        "date_width": 0,
        "device_width": 220,
        "search_by_width": 150,
        # Minimum width for search text input.
        "search_text_min_width": 240,
        "download_button_width": 220,
        "time_button_width": 90,
        # Icon size for time format buttons.
        "clock_icon_size": 18,
        # Layout mode for TitleBar2: ltr | rtl | space_between
        "layout_mode": "ltr",
        # Horizontal margins and spacing for TitleBar2 row.
        "layout_margin": 0,
        "layout_spacing": 6,
        # Per-column visible: true/false (defaults to true when missing)
        "column_visible": {},
    },
}


class UISettingsBus(QObject):
    changed = Signal()


ui_settings_bus = UISettingsBus()


def load_ui_settings() -> dict[str, Any]:
    p = _user_settings_path()
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return json.loads(json.dumps(DEFAULT_UI_SETTINGS))

        # First run: initialize user settings.
        p.parent.mkdir(parents=True, exist_ok=True)

        packaged = _packaged_settings_path()
        if packaged.exists():
            try:
                p.write_text(packaged.read_text(encoding="utf-8"), encoding="utf-8")
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception as ex:
                _LOGGER.warning(
                    "Failed to initialize user ui_settings.json from packaged default: %s",
                    ex,
                )

        # Fallback to defaults.
        save_ui_settings(DEFAULT_UI_SETTINGS)
        return json.loads(json.dumps(DEFAULT_UI_SETTINGS))
    except Exception as ex:
        _LOGGER.warning("Failed to load UI settings: %s", ex)
        return json.loads(json.dumps(DEFAULT_UI_SETTINGS))


def save_ui_settings(data: dict[str, Any]) -> None:
    p = _user_settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(data or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as ex:
        # Never crash the UI for a settings write failure.
        _LOGGER.warning("Failed to save UI settings to %s: %s", p, ex)


def _default_desktop_dir() -> str:
    # Prefer OneDrive Desktop when present (common on Windows).
    try:
        home = Path(str(environ.get("USERPROFILE") or Path.home()))
    except Exception:
        home = Path.home()

    try:
        onedrive = home / "OneDrive" / "Desktop"
        if onedrive.exists():
            return str(onedrive)
    except Exception:
        pass

    try:
        desktop = home / "Desktop"
        if desktop.exists():
            return str(desktop)
    except Exception:
        pass

    return str(home)


def get_last_save_dir() -> str:
    data = load_ui_settings()
    try:
        d = str((data.get("file_dialog") or {}).get("last_save_dir") or "").strip()
    except Exception:
        d = ""
    if d:
        try:
            if Path(d).exists():
                return d
        except Exception:
            pass
    return _default_desktop_dir()


def set_last_save_dir(path: str) -> None:
    p = Path(str(path or "").strip())
    if not str(p):
        return
    try:
        if p.suffix:
            p = p.parent
    except Exception:
        p = p.parent

    data = load_ui_settings()
    fd = data.setdefault("file_dialog", {})
    fd["last_save_dir"] = str(p)
    save_ui_settings(data)


@dataclass
class EmployeeTableUI:
    font_size: int
    font_weight: str
    header_font_size: int
    header_font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]
    column_visible: dict[str, bool]


@dataclass
class ShiftAttendanceTableUI:
    show_import_button: bool
    font_size: int
    font_weight: str
    header_font_size: int
    header_font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]
    column_visible: dict[str, bool]


@dataclass
class ScheduleWorkTableUI:
    font_size: int
    font_weight: str
    header_font_size: int
    header_font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]


@dataclass
class DeclareWorkShiftTableUI:
    font_size: int
    font_weight: str
    header_font_size: int
    header_font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]


@dataclass
class ArrangeScheduleTableUI:
    font_size: int
    font_weight: str
    header_font_size: int
    header_font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]


@dataclass
class DownloadAttendanceUI:
    table_font_size: int
    table_header_font_size: int
    table_header_font_weight: str
    combo_font_size: int
    calendar_font_size: int
    input_height: int
    button_height: int
    date_width: int
    device_width: int
    search_by_width: int
    search_text_min_width: int
    download_button_width: int
    time_button_width: int
    clock_icon_size: int
    layout_mode: str
    layout_margin: int
    layout_spacing: int
    column_visible: dict[str, bool]


def get_employee_table_ui() -> EmployeeTableUI:
    data = load_ui_settings()
    t = data.get("employee_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    font_size = int(
        t.get("font_size") or DEFAULT_UI_SETTINGS["employee_table"]["font_size"]
    )
    if font_size < 8:
        font_size = 8
    if font_size > 24:
        font_size = 24

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    header_font_size = int(
        t.get("header_font_size")
        or DEFAULT_UI_SETTINGS["employee_table"]["header_font_size"]
    )
    header_font_size = max(8, min(24, header_font_size))

    header_font_weight = str(t.get("header_font_weight") or "bold").strip().lower()
    if header_font_weight not in {"normal", "bold"}:
        header_font_weight = "bold"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

    col_visible = t.get("column_visible")
    if not isinstance(col_visible, dict):
        col_visible = {}

    # Normalize
    column_align: dict[str, str] = {}
    for k, v in col_align.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip().lower()
        if not ks:
            continue
        if vs not in {"left", "center", "right"}:
            continue
        column_align[ks] = vs

    column_bold: dict[str, bool] = {}
    for k, v in col_bold.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_bold[ks] = bool(v)

    column_visible: dict[str, bool] = {}
    for k, v in col_visible.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_visible[ks] = bool(v)

    # Merge defaults for aligns
    defaults_align = DEFAULT_UI_SETTINGS["employee_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return EmployeeTableUI(
        font_size=font_size,
        font_weight=font_weight,
        header_font_size=header_font_size,
        header_font_weight=header_font_weight,
        column_align=column_align,
        column_bold=column_bold,
        column_visible=column_visible,
    )


def update_employee_table_ui(
    *,
    font_size: int | None = None,
    font_weight: str | None = None,
    header_font_size: int | None = None,
    header_font_weight: str | None = None,
    column_key: str | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
    column_visible: bool | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("employee_table")
    if not isinstance(t, dict):
        t = {}

    if font_size is not None:
        try:
            fs = int(font_size)
            fs = max(8, min(24, fs))
            t["font_size"] = fs
        except Exception:
            pass

    if font_weight is not None:
        fw = str(font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["font_weight"] = fw

    if header_font_size is not None:
        try:
            hfs = int(header_font_size)
            hfs = max(8, min(24, hfs))
            t["header_font_size"] = hfs
        except Exception:
            pass

    if header_font_weight is not None:
        hfw = str(header_font_weight).strip().lower()
        if hfw in {"normal", "bold"}:
            t["header_font_weight"] = hfw

    if column_key:
        ck = str(column_key).strip()
        if ck:
            if column_align is not None:
                ca = str(column_align).strip().lower()
                if ca in {"left", "center", "right"}:
                    m = t.get("column_align")
                    if not isinstance(m, dict):
                        m = {}
                    m[ck] = ca
                    t["column_align"] = m

            if column_bold is not None:
                cb = str(column_bold).strip().lower()
                m2 = t.get("column_bold")
                if not isinstance(m2, dict):
                    m2 = {}
                if cb in {"inherit", "theo bảng", "theo bang"}:
                    # remove override
                    if ck in m2:
                        m2.pop(ck, None)
                elif cb in {"bold", "đậm", "dam"}:
                    m2[ck] = True
                elif cb in {"normal", "nhạt", "nhat"}:
                    m2[ck] = False
                t["column_bold"] = m2

            if column_visible is not None:
                m3 = t.get("column_visible")
                if not isinstance(m3, dict):
                    m3 = {}
                m3[ck] = bool(column_visible)
                t["column_visible"] = m3

    data["employee_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()


def get_shift_attendance_table_ui() -> ShiftAttendanceTableUI:
    data = load_ui_settings()
    t = data.get("shift_attendance_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    show_import_button = bool(
        t.get("show_import_button")
        if "show_import_button" in t
        else DEFAULT_UI_SETTINGS["shift_attendance_table"].get(
            "show_import_button", True
        )
    )

    font_size = int(
        t.get("font_size") or DEFAULT_UI_SETTINGS["shift_attendance_table"]["font_size"]
    )
    if font_size < 8:
        font_size = 8
    if font_size > 24:
        font_size = 24

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    header_font_size = int(
        t.get("header_font_size")
        or DEFAULT_UI_SETTINGS["shift_attendance_table"]["header_font_size"]
    )
    header_font_size = max(8, min(24, header_font_size))

    header_font_weight = str(t.get("header_font_weight") or "bold").strip().lower()
    if header_font_weight not in {"normal", "bold"}:
        header_font_weight = "bold"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

    col_visible = t.get("column_visible")
    if not isinstance(col_visible, dict):
        col_visible = {}

    # Normalize
    column_align: dict[str, str] = {}
    for k, v in col_align.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip().lower()
        if not ks:
            continue
        if vs not in {"left", "center", "right"}:
            continue
        column_align[ks] = vs

    column_bold: dict[str, bool] = {}
    for k, v in col_bold.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_bold[ks] = bool(v)

    column_visible: dict[str, bool] = {}
    for k, v in col_visible.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_visible[ks] = bool(v)

    # Backward-compat: MainContent2 renamed column key from 'total' -> 'schedule'.
    # If a user has settings saved for 'total', carry them over.
    if "schedule" not in column_visible and "total" in column_visible:
        column_visible["schedule"] = bool(column_visible.get("total"))
    if "schedule" not in column_align and "total" in column_align:
        column_align["schedule"] = str(column_align.get("total"))
    if "schedule" not in column_bold and "total" in column_bold:
        column_bold["schedule"] = bool(column_bold.get("total"))

    # Merge defaults for aligns
    defaults_align = DEFAULT_UI_SETTINGS["shift_attendance_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return ShiftAttendanceTableUI(
        show_import_button=show_import_button,
        font_size=font_size,
        font_weight=font_weight,
        header_font_size=header_font_size,
        header_font_weight=header_font_weight,
        column_align=column_align,
        column_bold=column_bold,
        column_visible=column_visible,
    )


def get_shift_attendance_state() -> dict[str, Any]:
    """Read persisted Shift Attendance view state.

    Returns a dict with keys: content1, content2.
    Values are JSON-serializable primitives (dates are yyyy-MM-dd strings).
    """

    data = load_ui_settings()
    st = data.get("shift_attendance_state") if isinstance(data, dict) else None
    if not isinstance(st, dict):
        st = {}

    defaults = DEFAULT_UI_SETTINGS.get("shift_attendance_state")
    if not isinstance(defaults, dict):
        defaults = {}

    # Merge with defaults defensively.
    c1 = st.get("content1")
    if not isinstance(c1, dict):
        c1 = {}
    d1 = defaults.get("content1") if isinstance(defaults.get("content1"), dict) else {}
    merged_c1: dict[str, Any] = dict(d1)
    merged_c1.update(
        {
            k: v
            for k, v in c1.items()
            if k in d1
            or k
            in {
                "department_id",
                "title_id",
                "search_by_data",
                "search_text",
                "date_from",
                "date_to",
            }
        }
    )

    c2 = st.get("content2")
    if not isinstance(c2, dict):
        c2 = {}
    d2 = defaults.get("content2") if isinstance(defaults.get("content2"), dict) else {}
    merged_c2: dict[str, Any] = dict(d2)
    merged_c2.update({k: v for k, v in c2.items() if k in d2 or k in {"show_seconds"}})

    return {"content1": merged_c1, "content2": merged_c2}


def update_shift_attendance_state(
    *,
    content1: dict[str, Any] | None = None,
    content2: dict[str, Any] | None = None,
) -> None:
    """Persist Shift Attendance view state into ui_settings.json."""

    data = load_ui_settings()
    st = data.get("shift_attendance_state")
    if not isinstance(st, dict):
        st = {}

    if content1 is not None:
        c1 = st.get("content1")
        if not isinstance(c1, dict):
            c1 = {}
        for k, v in dict(content1).items():
            c1[str(k)] = v
        st["content1"] = c1

    if content2 is not None:
        c2 = st.get("content2")
        if not isinstance(c2, dict):
            c2 = {}
        for k, v in dict(content2).items():
            c2[str(k)] = v
        st["content2"] = c2

    data["shift_attendance_state"] = st
    save_ui_settings(data)


def get_schedule_work_table_ui() -> ScheduleWorkTableUI:
    data = load_ui_settings()
    t = data.get("schedule_work_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    font_size = int(
        t.get("font_size") or DEFAULT_UI_SETTINGS["schedule_work_table"]["font_size"]
    )
    font_size = max(8, min(24, font_size))

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    header_font_size = int(
        t.get("header_font_size")
        or DEFAULT_UI_SETTINGS["schedule_work_table"]["header_font_size"]
    )
    header_font_size = max(8, min(24, header_font_size))

    header_font_weight = str(t.get("header_font_weight") or "bold").strip().lower()
    if header_font_weight not in {"normal", "bold"}:
        header_font_weight = "bold"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

    column_align: dict[str, str] = {}
    for k, v in col_align.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip().lower()
        if not ks:
            continue
        if vs not in {"left", "center", "right"}:
            continue
        column_align[ks] = vs

    column_bold: dict[str, bool] = {}
    for k, v in col_bold.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_bold[ks] = bool(v)

    defaults_align = DEFAULT_UI_SETTINGS["schedule_work_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return ScheduleWorkTableUI(
        font_size=font_size,
        font_weight=font_weight,
        header_font_size=header_font_size,
        header_font_weight=header_font_weight,
        column_align=column_align,
        column_bold=column_bold,
    )


def update_schedule_work_table_ui(
    *,
    font_size: int | None = None,
    font_weight: str | None = None,
    header_font_size: int | None = None,
    header_font_weight: str | None = None,
    column_key: str | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("schedule_work_table")
    if not isinstance(t, dict):
        t = {}

    if font_size is not None:
        try:
            fs = int(font_size)
            fs = max(8, min(24, fs))
            t["font_size"] = fs
        except Exception:
            pass

    if font_weight is not None:
        fw = str(font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["font_weight"] = fw

    if header_font_size is not None:
        try:
            hfs = int(header_font_size)
            hfs = max(8, min(24, hfs))
            t["header_font_size"] = hfs
        except Exception:
            pass

    if header_font_weight is not None:
        hfw = str(header_font_weight).strip().lower()
        if hfw in {"normal", "bold"}:
            t["header_font_weight"] = hfw

    if column_key:
        ck = str(column_key).strip()
        if ck:
            if column_align is not None:
                ca = str(column_align).strip().lower()
                if ca in {"left", "center", "right"}:
                    m = t.get("column_align")
                    if not isinstance(m, dict):
                        m = {}
                    m[ck] = ca
                    t["column_align"] = m

            if column_bold is not None:
                cb = str(column_bold).strip().lower()
                m2 = t.get("column_bold")
                if not isinstance(m2, dict):
                    m2 = {}
                if cb in {"inherit", "theo bảng", "theo bang"}:
                    if ck in m2:
                        m2.pop(ck, None)
                elif cb in {"bold", "đậm", "dam"}:
                    m2[ck] = True
                elif cb in {"normal", "nhạt", "nhat"}:
                    m2[ck] = False
                t["column_bold"] = m2

    data["schedule_work_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()


def get_declare_work_shift_table_ui() -> DeclareWorkShiftTableUI:
    data = load_ui_settings()
    t = data.get("declare_work_shift_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    font_size = int(
        t.get("font_size")
        or DEFAULT_UI_SETTINGS["declare_work_shift_table"]["font_size"]
    )
    font_size = max(8, min(24, font_size))

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    header_font_size = int(
        t.get("header_font_size")
        or DEFAULT_UI_SETTINGS["declare_work_shift_table"]["header_font_size"]
    )
    header_font_size = max(8, min(24, header_font_size))

    header_font_weight = str(t.get("header_font_weight") or "bold").strip().lower()
    if header_font_weight not in {"normal", "bold"}:
        header_font_weight = "bold"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

    column_align: dict[str, str] = {}
    for k, v in col_align.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip().lower()
        if not ks:
            continue
        if vs not in {"left", "center", "right"}:
            continue
        column_align[ks] = vs

    column_bold: dict[str, bool] = {}
    for k, v in col_bold.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_bold[ks] = bool(v)

    defaults_align = DEFAULT_UI_SETTINGS["declare_work_shift_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return DeclareWorkShiftTableUI(
        font_size=font_size,
        font_weight=font_weight,
        header_font_size=header_font_size,
        header_font_weight=header_font_weight,
        column_align=column_align,
        column_bold=column_bold,
    )


def update_declare_work_shift_table_ui(
    *,
    font_size: int | None = None,
    font_weight: str | None = None,
    header_font_size: int | None = None,
    header_font_weight: str | None = None,
    column_key: str | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("declare_work_shift_table")
    if not isinstance(t, dict):
        t = {}

    if font_size is not None:
        try:
            fs = int(font_size)
            fs = max(8, min(24, fs))
            t["font_size"] = fs
        except Exception:
            pass

    if font_weight is not None:
        fw = str(font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["font_weight"] = fw

    if header_font_size is not None:
        try:
            hfs = int(header_font_size)
            hfs = max(8, min(24, hfs))
            t["header_font_size"] = hfs
        except Exception:
            pass

    if header_font_weight is not None:
        hfw = str(header_font_weight).strip().lower()
        if hfw in {"normal", "bold"}:
            t["header_font_weight"] = hfw

    if column_key:
        ck = str(column_key).strip()
        if ck:
            if column_align is not None:
                ca = str(column_align).strip().lower()
                if ca in {"left", "center", "right"}:
                    m = t.get("column_align")
                    if not isinstance(m, dict):
                        m = {}
                    m[ck] = ca
                    t["column_align"] = m

            if column_bold is not None:
                cb = str(column_bold).strip().lower()
                m2 = t.get("column_bold")
                if not isinstance(m2, dict):
                    m2 = {}
                if cb in {"inherit", "theo bảng", "theo bang"}:
                    if ck in m2:
                        m2.pop(ck, None)
                elif cb in {"bold", "đậm", "dam"}:
                    m2[ck] = True
                elif cb in {"normal", "nhạt", "nhat"}:
                    m2[ck] = False
                t["column_bold"] = m2

    data["declare_work_shift_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()


def get_arrange_schedule_table_ui() -> ArrangeScheduleTableUI:
    data = load_ui_settings()
    t = data.get("arrange_schedule_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    font_size = int(
        t.get("font_size") or DEFAULT_UI_SETTINGS["arrange_schedule_table"]["font_size"]
    )
    font_size = max(8, min(24, font_size))

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    header_font_size = int(
        t.get("header_font_size")
        or DEFAULT_UI_SETTINGS["arrange_schedule_table"]["header_font_size"]
    )
    header_font_size = max(8, min(24, header_font_size))

    header_font_weight = str(t.get("header_font_weight") or "bold").strip().lower()
    if header_font_weight not in {"normal", "bold"}:
        header_font_weight = "bold"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

    column_align: dict[str, str] = {}
    for k, v in col_align.items():
        ks = str(k or "").strip()
        vs = str(v or "").strip().lower()
        if not ks:
            continue
        if vs not in {"left", "center", "right"}:
            continue
        column_align[ks] = vs

    column_bold: dict[str, bool] = {}
    for k, v in col_bold.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_bold[ks] = bool(v)

    defaults_align = DEFAULT_UI_SETTINGS["arrange_schedule_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return ArrangeScheduleTableUI(
        font_size=font_size,
        font_weight=font_weight,
        header_font_size=header_font_size,
        header_font_weight=header_font_weight,
        column_align=column_align,
        column_bold=column_bold,
    )


def update_arrange_schedule_table_ui(
    *,
    font_size: int | None = None,
    font_weight: str | None = None,
    header_font_size: int | None = None,
    header_font_weight: str | None = None,
    column_key: str | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("arrange_schedule_table")
    if not isinstance(t, dict):
        t = {}

    if font_size is not None:
        try:
            fs = int(font_size)
            fs = max(8, min(24, fs))
            t["font_size"] = fs
        except Exception:
            pass

    if font_weight is not None:
        fw = str(font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["font_weight"] = fw

    if header_font_size is not None:
        try:
            hfs = int(header_font_size)
            hfs = max(8, min(24, hfs))
            t["header_font_size"] = hfs
        except Exception:
            pass

    if header_font_weight is not None:
        hfw = str(header_font_weight).strip().lower()
        if hfw in {"normal", "bold"}:
            t["header_font_weight"] = hfw

    if column_key:
        ck = str(column_key).strip()
        if ck:
            if column_align is not None:
                ca = str(column_align).strip().lower()
                if ca in {"left", "center", "right"}:
                    m = t.get("column_align")
                    if not isinstance(m, dict):
                        m = {}
                    m[ck] = ca
                    t["column_align"] = m

            if column_bold is not None:
                cb = str(column_bold).strip().lower()
                m2 = t.get("column_bold")
                if not isinstance(m2, dict):
                    m2 = {}
                if cb in {"inherit", "theo bảng", "theo bang"}:
                    if ck in m2:
                        m2.pop(ck, None)
                elif cb in {"bold", "đậm", "dam"}:
                    m2[ck] = True
                elif cb in {"normal", "nhạt", "nhat"}:
                    m2[ck] = False
                t["column_bold"] = m2

    data["arrange_schedule_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()


def get_download_attendance_ui() -> DownloadAttendanceUI:
    data = load_ui_settings()
    t = data.get("download_attendance") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    table_font_size = int(
        t.get("table_font_size")
        or DEFAULT_UI_SETTINGS["download_attendance"]["table_font_size"]
    )
    table_font_size = max(8, min(24, table_font_size))

    table_header_font_size = int(
        t.get("table_header_font_size")
        or DEFAULT_UI_SETTINGS["download_attendance"]["table_header_font_size"]
    )
    table_header_font_size = max(8, min(24, table_header_font_size))

    table_header_font_weight = (
        str(
            t.get("table_header_font_weight")
            or DEFAULT_UI_SETTINGS["download_attendance"]["table_header_font_weight"]
        )
        .strip()
        .lower()
    )
    if table_header_font_weight not in {"normal", "bold"}:
        table_header_font_weight = "bold"

    combo_font_size = int(
        t.get("combo_font_size")
        or DEFAULT_UI_SETTINGS["download_attendance"]["combo_font_size"]
    )
    combo_font_size = max(8, min(24, combo_font_size))

    calendar_font_size = int(
        t.get("calendar_font_size")
        or DEFAULT_UI_SETTINGS["download_attendance"]["calendar_font_size"]
    )
    calendar_font_size = max(8, min(24, calendar_font_size))

    input_height = int(
        t.get("input_height")
        or DEFAULT_UI_SETTINGS["download_attendance"]["input_height"]
    )
    if input_height < 0:
        input_height = 0

    button_height = int(
        t.get("button_height")
        or DEFAULT_UI_SETTINGS["download_attendance"]["button_height"]
    )
    if button_height < 0:
        button_height = 0

    date_width = int(
        t.get("date_width") or DEFAULT_UI_SETTINGS["download_attendance"]["date_width"]
    )
    if date_width < 0:
        date_width = 0

    device_width = int(
        t.get("device_width")
        or DEFAULT_UI_SETTINGS["download_attendance"]["device_width"]
    )
    if device_width < 0:
        device_width = 0

    search_by_width = int(
        t.get("search_by_width")
        or DEFAULT_UI_SETTINGS["download_attendance"]["search_by_width"]
    )
    if search_by_width < 0:
        search_by_width = 0

    search_text_min_width = int(
        t.get("search_text_min_width")
        or DEFAULT_UI_SETTINGS["download_attendance"]["search_text_min_width"]
    )
    if search_text_min_width < 0:
        search_text_min_width = 0

    download_button_width = int(
        t.get("download_button_width")
        or DEFAULT_UI_SETTINGS["download_attendance"]["download_button_width"]
    )
    if download_button_width < 0:
        download_button_width = 0

    time_button_width = int(
        t.get("time_button_width")
        or DEFAULT_UI_SETTINGS["download_attendance"]["time_button_width"]
    )
    if time_button_width < 0:
        time_button_width = 0

    clock_icon_size = int(
        t.get("clock_icon_size")
        or DEFAULT_UI_SETTINGS["download_attendance"]["clock_icon_size"]
    )
    if clock_icon_size < 0:
        clock_icon_size = 0

    layout_mode = (
        str(
            t.get("layout_mode")
            or DEFAULT_UI_SETTINGS["download_attendance"]["layout_mode"]
        )
        .strip()
        .lower()
    )
    if layout_mode not in {"ltr", "rtl", "space_between"}:
        layout_mode = "ltr"

    layout_margin = int(
        t.get("layout_margin")
        or DEFAULT_UI_SETTINGS["download_attendance"]["layout_margin"]
    )
    if layout_margin < 0:
        layout_margin = 0

    layout_spacing = int(
        t.get("layout_spacing")
        or DEFAULT_UI_SETTINGS["download_attendance"]["layout_spacing"]
    )
    if layout_spacing < 0:
        layout_spacing = 0

    col_visible = t.get("column_visible")
    if not isinstance(col_visible, dict):
        col_visible = {}

    column_visible: dict[str, bool] = {}
    for k, v in col_visible.items():
        ks = str(k or "").strip()
        if not ks:
            continue
        column_visible[ks] = bool(v)

    return DownloadAttendanceUI(
        table_font_size=table_font_size,
        table_header_font_size=table_header_font_size,
        table_header_font_weight=table_header_font_weight,
        combo_font_size=combo_font_size,
        calendar_font_size=calendar_font_size,
        input_height=input_height,
        button_height=button_height,
        date_width=date_width,
        device_width=device_width,
        search_by_width=search_by_width,
        search_text_min_width=search_text_min_width,
        download_button_width=download_button_width,
        time_button_width=time_button_width,
        clock_icon_size=clock_icon_size,
        layout_mode=layout_mode,
        layout_margin=layout_margin,
        layout_spacing=layout_spacing,
        column_visible=column_visible,
    )


def update_download_attendance_ui(
    *,
    table_font_size: int | None = None,
    table_header_font_size: int | None = None,
    table_header_font_weight: str | None = None,
    combo_font_size: int | None = None,
    calendar_font_size: int | None = None,
    input_height: int | None = None,
    button_height: int | None = None,
    date_width: int | None = None,
    device_width: int | None = None,
    search_by_width: int | None = None,
    search_text_min_width: int | None = None,
    download_button_width: int | None = None,
    time_button_width: int | None = None,
    clock_icon_size: int | None = None,
    layout_mode: str | None = None,
    layout_margin: int | None = None,
    layout_spacing: int | None = None,
    column_key: str | None = None,
    column_visible: str | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("download_attendance")
    if not isinstance(t, dict):
        t = {}

    if table_font_size is not None:
        try:
            fs = int(table_font_size)
            fs = max(8, min(24, fs))
            t["table_font_size"] = fs
        except Exception:
            pass

    if table_header_font_size is not None:
        try:
            fs = int(table_header_font_size)
            fs = max(8, min(24, fs))
            t["table_header_font_size"] = fs
        except Exception:
            pass

    if table_header_font_weight is not None:
        fw = str(table_header_font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["table_header_font_weight"] = fw

    if combo_font_size is not None:
        try:
            fs = int(combo_font_size)
            fs = max(8, min(24, fs))
            t["combo_font_size"] = fs
        except Exception:
            pass

    if calendar_font_size is not None:
        try:
            fs = int(calendar_font_size)
            fs = max(8, min(24, fs))
            t["calendar_font_size"] = fs
        except Exception:
            pass

    if input_height is not None:
        try:
            v = int(input_height)
            if v < 0:
                v = 0
            t["input_height"] = v
        except Exception:
            pass

    if button_height is not None:
        try:
            v = int(button_height)
            if v < 0:
                v = 0
            t["button_height"] = v
        except Exception:
            pass

    if date_width is not None:
        try:
            v = int(date_width)
            if v < 0:
                v = 0
            t["date_width"] = v
        except Exception:
            pass

    if device_width is not None:
        try:
            v = int(device_width)
            if v < 0:
                v = 0
            t["device_width"] = v
        except Exception:
            pass

    if search_by_width is not None:
        try:
            v = int(search_by_width)
            if v < 0:
                v = 0
            t["search_by_width"] = v
        except Exception:
            pass

    if search_text_min_width is not None:
        try:
            v = int(search_text_min_width)
            if v < 0:
                v = 0
            t["search_text_min_width"] = v
        except Exception:
            pass

    if download_button_width is not None:
        try:
            v = int(download_button_width)
            if v < 0:
                v = 0
            t["download_button_width"] = v
        except Exception:
            pass

    if time_button_width is not None:
        try:
            v = int(time_button_width)
            if v < 0:
                v = 0
            t["time_button_width"] = v
        except Exception:
            pass

    if clock_icon_size is not None:
        try:
            v = int(clock_icon_size)
            if v < 0:
                v = 0
            t["clock_icon_size"] = v
        except Exception:
            pass

    if layout_mode is not None:
        lm = str(layout_mode or "").strip().lower()
        if lm in {"ltr", "rtl", "space_between"}:
            t["layout_mode"] = lm

    if layout_margin is not None:
        try:
            v = int(layout_margin)
            if v < 0:
                v = 0
            t["layout_margin"] = v
        except Exception:
            pass

    if layout_spacing is not None:
        try:
            v = int(layout_spacing)
            if v < 0:
                v = 0
            t["layout_spacing"] = v
        except Exception:
            pass

    if column_key:
        ck = str(column_key).strip()
        if ck and column_visible is not None:
            vis = str(column_visible).strip().lower()
            m = t.get("column_visible")
            if not isinstance(m, dict):
                m = {}
            if vis in {"show", "hiển thị", "hien thi"}:
                m[ck] = True
            elif vis in {"hide", "ẩn", "an"}:
                m[ck] = False
            t["column_visible"] = m

    data["download_attendance"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()


def update_shift_attendance_table_ui(
    *,
    show_import_button: bool | None = None,
    font_size: int | None = None,
    font_weight: str | None = None,
    header_font_size: int | None = None,
    header_font_weight: str | None = None,
    column_key: str | None = None,
    column_visible: str | bool | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
) -> None:
    data = load_ui_settings()
    if not isinstance(data, dict):
        data = {}
    t = data.get("shift_attendance_table")
    if not isinstance(t, dict):
        t = {}

    if show_import_button is not None:
        t["show_import_button"] = bool(show_import_button)

    if font_size is not None:
        try:
            fs = int(font_size)
            fs = max(8, min(24, fs))
            t["font_size"] = fs
        except Exception:
            pass

    if font_weight is not None:
        fw = str(font_weight).strip().lower()
        if fw in {"normal", "bold"}:
            t["font_weight"] = fw

    if header_font_size is not None:
        try:
            hfs = int(header_font_size)
            hfs = max(8, min(24, hfs))
            t["header_font_size"] = hfs
        except Exception:
            pass

    if header_font_weight is not None:
        hfw = str(header_font_weight).strip().lower()
        if hfw in {"normal", "bold"}:
            t["header_font_weight"] = hfw

    if column_key:
        ck = str(column_key).strip()
        if ck:
            if column_visible is not None:
                m_vis = t.get("column_visible")
                if not isinstance(m_vis, dict):
                    m_vis = {}

                if isinstance(column_visible, bool):
                    m_vis[ck] = bool(column_visible)
                else:
                    cv = str(column_visible).strip().lower()
                    if cv in {"show", "visible", "hiển thị", "hien thi"}:
                        m_vis[ck] = True
                    elif cv in {"hide", "hidden", "ẩn", "an"}:
                        m_vis[ck] = False

                t["column_visible"] = m_vis

            if column_align is not None:
                ca = str(column_align).strip().lower()
                if ca in {"left", "center", "right"}:
                    m = t.get("column_align")
                    if not isinstance(m, dict):
                        m = {}
                    m[ck] = ca
                    t["column_align"] = m

            if column_bold is not None:
                cb = str(column_bold).strip().lower()
                m2 = t.get("column_bold")
                if not isinstance(m2, dict):
                    m2 = {}
                if cb in {"inherit", "theo bảng", "theo bang"}:
                    if ck in m2:
                        m2.pop(ck, None)
                elif cb in {"bold", "đậm", "dam"}:
                    m2[ck] = True
                elif cb in {"normal", "nhạt", "nhat"}:
                    m2[ck] = False
                t["column_bold"] = m2

    data["shift_attendance_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()
