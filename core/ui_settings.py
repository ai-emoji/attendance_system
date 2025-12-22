"""core.ui_settings

Lưu/đọc cài đặt UI (hiện tại: bảng nhân viên).

Mục tiêu:
- Cho phép SettingsDialog ghi cấu hình
- EmployeeTable (ở employee_widgets / import_employee_dialog) tự đọc và tự apply
- Có signal để các bảng đang mở cập nhật ngay
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from core.resource import resource_path


def _settings_path() -> Path:
    # Keep under database/ so it ships alongside app data.
    return Path(resource_path("database/ui_settings.json"))


DEFAULT_UI_SETTINGS: dict[str, Any] = {
    "employee_table": {
        # Font settings apply to table body.
        "font_size": 11,
        # "normal" | "bold"
        "font_weight": "normal",
        # Per-column: "left" | "center" | "right"
        "column_align": {
            "stt": "center",
            "employee_code": "center",
        },
        # Per-column: true/false (overrides table font_weight)
        "column_bold": {},
    }
}


class UISettingsBus(QObject):
    changed = Signal()


ui_settings_bus = UISettingsBus()


def load_ui_settings() -> dict[str, Any]:
    p = _settings_path()
    try:
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            save_ui_settings(DEFAULT_UI_SETTINGS)
            return json.loads(json.dumps(DEFAULT_UI_SETTINGS))

        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return json.loads(json.dumps(DEFAULT_UI_SETTINGS))
        return data
    except Exception:
        return json.loads(json.dumps(DEFAULT_UI_SETTINGS))


def save_ui_settings(data: dict[str, Any]) -> None:
    p = _settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(data or {}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@dataclass
class EmployeeTableUI:
    font_size: int
    font_weight: str
    column_align: dict[str, str]
    column_bold: dict[str, bool]


def get_employee_table_ui() -> EmployeeTableUI:
    data = load_ui_settings()
    t = data.get("employee_table") if isinstance(data, dict) else None
    if not isinstance(t, dict):
        t = {}

    font_size = int(t.get("font_size") or DEFAULT_UI_SETTINGS["employee_table"]["font_size"])
    if font_size < 8:
        font_size = 8
    if font_size > 24:
        font_size = 24

    font_weight = str(t.get("font_weight") or "normal").strip().lower()
    if font_weight not in {"normal", "bold"}:
        font_weight = "normal"

    col_align = t.get("column_align")
    if not isinstance(col_align, dict):
        col_align = {}

    col_bold = t.get("column_bold")
    if not isinstance(col_bold, dict):
        col_bold = {}

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

    # Merge defaults for aligns
    defaults_align = DEFAULT_UI_SETTINGS["employee_table"]["column_align"]
    for k, v in defaults_align.items():
        if k not in column_align:
            column_align[k] = v

    return EmployeeTableUI(
        font_size=font_size,
        font_weight=font_weight,
        column_align=column_align,
        column_bold=column_bold,
    )


def update_employee_table_ui(
    *,
    font_size: int | None = None,
    font_weight: str | None = None,
    column_key: str | None = None,
    column_align: str | None = None,
    column_bold: str | None = None,
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

    data["employee_table"] = t
    save_ui_settings(data)
    ui_settings_bus.changed.emit()
