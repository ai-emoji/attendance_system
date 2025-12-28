"""core.attendance_symbol_bus

A tiny event bus to notify open views when attendance_symbols configuration changes.

Used to refresh UI (e.g. Shift Attendance grid) after editing symbols in the
"Ký hiệu Chấm công" dialog.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AttendanceSymbolBus(QObject):
    changed = Signal()


attendance_symbol_bus = AttendanceSymbolBus()
