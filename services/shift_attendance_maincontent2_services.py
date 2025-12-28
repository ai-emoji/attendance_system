"""services.shift_attendance_maincontent2_services

Service cho MainContent2 (Shift Attendance).

Nghiệp vụ:
- Lấy dữ liệu attendance_audit.
- Tra cứu in_out_mode từ arrange_schedules theo schedule_name.
- Chuẩn hoá/sắp xếp các cột giờ vào/ra theo mode:
    - auto: sắp xếp giờ tăng dần rồi ghép (in_1/out_1/in_2/out_2/in_3/out_3).
  - device: giữ nguyên dữ liệu như audit (theo máy chấm công).
  - first_last: lấy giờ đầu tiên trong ngày làm in_1 và giờ cuối cùng làm out_1, xoá các cặp còn lại.
"""

from __future__ import annotations

import datetime as _dt
import logging
import unicodedata
from decimal import Decimal
from typing import Any

from repository.arrange_schedule_repository import ArrangeScheduleRepository
from repository.shift_attendance_maincontent2_repository import (
    ShiftAttendanceMainContent2Repository,
)
from services.attendance_symbol_services import AttendanceSymbolService


logger = logging.getLogger(__name__)


class ShiftAttendanceMainContent2Service:
    def __init__(
        self,
        repo: ShiftAttendanceMainContent2Repository | None = None,
        arrange_repo: ArrangeScheduleRepository | None = None,
    ) -> None:
        self._repo = repo or ShiftAttendanceMainContent2Repository()
        self._arrange_repo = arrange_repo or ArrangeScheduleRepository()

    @staticmethod
    def _time_to_seconds(value: object | None) -> int | None:
        if value is None:
            return None

        if isinstance(value, _dt.time):
            return int(value.hour) * 3600 + int(value.minute) * 60 + int(value.second)

        if isinstance(value, _dt.timedelta):
            try:
                sec = int(value.total_seconds())
                return sec % 86400
            except Exception:
                return None

        # Some drivers may return datetime or string
        if isinstance(value, _dt.datetime):
            t = value.time()
            return int(t.hour) * 3600 + int(t.minute) * 60 + int(t.second)

        s = str(value).strip()
        if not s:
            return None

        # datetime-like: keep last token
        if " " in s and ":" in s:
            s = s.split()[-1].strip()

        # Accept HH:MM or HH:MM:SS
        parts = [p for p in s.split(":") if p != ""]
        if len(parts) < 2:
            return None
        try:
            hh = int(float(parts[0]))
            mm = int(float(parts[1]))
            ss = int(float(parts[2])) if len(parts) >= 3 else 0
            if hh < 0 or mm < 0 or ss < 0:
                return None
            return hh * 3600 + mm * 60 + ss
        except Exception:
            return None

    @staticmethod
    def _norm_text_no_diacritics(value: object | None) -> str:
        s = str(value or "").strip()
        if not s:
            return ""
        try:
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
        except Exception:
            pass
        return s.casefold().replace(" ", "")

    @classmethod
    def _is_overnight_shift_def(cls, sh: dict[str, Any]) -> bool:
        """Detect if a shift crosses midnight based on time_in/time_out or windows."""

        try:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True
        except Exception:
            pass

        try:
            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def _norm_schedule_name(value: object | None) -> str:
        s = str(value or "").strip()
        if not s:
            return ""
        try:
            # Normalize to NFC to avoid mismatches between precomposed/decomposed Vietnamese.
            s = unicodedata.normalize("NFC", s)
        except Exception:
            pass
        # Collapse internal whitespace
        try:
            s = " ".join(s.split())
        except Exception:
            pass
        return s

    @classmethod
    def _calc_late_minutes_for_shift(
        cls,
        *,
        in_value: object | None,
        shift: dict[str, Any],
    ) -> int | None:
        """Compute late minutes (floor) for a single shift.

        Rule:
        - late if in_i > time_in
        - minutes = floor((in_i - time_in)/60)
        - cap by total_minutes (max cannot exceed)
        - supports overnight shift: if shift crosses midnight and in_i is after 00:00,
          treat in_i as next day by adding 86400 when needed.
        """

        if in_value is None:
            return None

        time_in_sec = cls._time_to_seconds(shift.get("time_in"))
        time_out_sec = cls._time_to_seconds(shift.get("time_out"))
        in_sec = cls._time_to_seconds(in_value)
        if time_in_sec is None or time_out_sec is None or in_sec is None:
            return None

        # Normalize against shift time_in/time_out.
        # Overnight shift means time_out belongs to next day.
        start_sec = int(time_in_sec)
        end_sec = int(time_out_sec)
        is_overnight = int(time_out_sec) < int(time_in_sec)
        if is_overnight:
            end_sec = int(time_out_sec) + 86400

        eff_in_sec = int(in_sec)
        if is_overnight and int(in_sec) < int(time_in_sec):
            # Only treat as next-day IN when the punch is in the morning part
            # (<= original time_out). Early arrivals like 21:58 for a 22:00 shift
            # must stay on the same day.
            if int(in_sec) <= int(time_out_sec):
                eff_in_sec = int(in_sec) + 86400

        delta = int(eff_in_sec) - int(start_sec)
        if delta <= 0:
            return 0

        late_raw = int(delta) // 60  # floor minutes, no rounding

        try:
            total_minutes = int(shift.get("total_minutes") or 0)
        except Exception:
            total_minutes = 0
        if total_minutes > 0:
            return min(int(late_raw), int(total_minutes))

        return int(late_raw)

    @classmethod
    def _calc_early_minutes_for_shift(
        cls,
        *,
        out_value: object | None,
        shift: dict[str, Any],
    ) -> int | None:
        """Compute early minutes (floor) for a single shift.

        Rule (theo yêu cầu):
        - Nếu out_i >= time_out -> không sớm
        - Nếu out_i < time_out -> sớm
        - minutes = floor((time_out - out_i)/60)
        - cap bởi total_minutes (không vượt quá tổng phút ca)
        - Hỗ trợ ca qua ngày: time_out có thể thuộc ngày kế tiếp.
        """

        if out_value is None:
            return None

        time_in_sec = cls._time_to_seconds(shift.get("time_in"))
        time_out_sec = cls._time_to_seconds(shift.get("time_out"))
        out_sec = cls._time_to_seconds(out_value)
        if time_in_sec is None or time_out_sec is None or out_sec is None:
            return None

        # Normalize against shift time_in/time_out.
        start_sec = int(time_in_sec)
        sched_out_eff = int(time_out_sec)
        out_eff = int(out_sec)

        is_overnight = int(time_out_sec) < int(time_in_sec)
        if is_overnight:
            sched_out_eff = int(time_out_sec) + 86400
            if int(out_sec) < int(time_in_sec):
                out_eff = int(out_sec) + 86400

        delta = int(sched_out_eff) - int(out_eff)
        if delta <= 0:
            return 0

        early_raw = int(delta) // 60  # floor minutes, no rounding

        try:
            total_minutes = int(shift.get("total_minutes") or 0)
        except Exception:
            total_minutes = 0
        if total_minutes > 0:
            return min(int(early_raw), int(total_minutes))

        return int(early_raw)

    @classmethod
    def _recompute_early_from_displayed_out_values(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> None:
        """Recompute row['early'] from displayed out_i + schedule work_shifts.

        Priority:
        1) Nếu row.shift_code match work_shifts.shift_code -> dùng index ca -> out_{idx+1}.
        2) Nếu không match được -> cộng sớm theo thứ tự cho tối đa 3 ca.
        """

        if not shifts:
            return

        shifts_by_code: dict[str, dict[str, Any]] = {}
        for sh in shifts:
            code = str(sh.get("shift_code") or "").strip()
            if not code:
                continue
            shifts_by_code.setdefault(code.casefold(), sh)

        # 0) If auto-by-shifts attached a slot->shift mapping, use it.
        total = 0
        used_any = False
        for slot in (1, 2, 3):
            slot_code = str(row.get(f"_slot_shift_code_{slot}") or "").strip()
            if not slot_code:
                continue
            sh = shifts_by_code.get(slot_code.casefold())
            if sh is None:
                continue
            early_val = cls._calc_early_minutes_for_shift(
                out_value=row.get(f"out_{slot}"),
                shift=sh,
            )
            if early_val is None:
                continue
            used_any = True
            total += int(early_val)

        if used_any:
            row["early"] = int(total)
            return

        row_shift_code = str(row.get("shift_code") or "").strip()

        if row_shift_code:
            row_code_cf = row_shift_code.casefold()
            for idx, sh in enumerate(shifts):
                if str(sh.get("shift_code") or "").strip().casefold() == row_code_cf:
                    if idx >= 3:
                        return
                    early_val = cls._calc_early_minutes_for_shift(
                        out_value=row.get(f"out_{idx + 1}"),
                        shift=sh,
                    )
                    if early_val is not None:
                        row["early"] = int(early_val)
                    return

        total = 0
        used_any = False
        for idx, sh in enumerate(shifts[:3]):
            early_val = cls._calc_early_minutes_for_shift(
                out_value=row.get(f"out_{idx + 1}"),
                shift=sh,
            )
            if early_val is None:
                continue
            used_any = True
            total += int(early_val)

        if used_any:
            row["early"] = int(total)

    @classmethod
    def _recompute_late_from_displayed_in_values(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> None:
        """Recompute row['late'] from displayed in_i + schedule work_shifts.

        Priority:
        1) If row.shift_code matches a shift_code in shifts, use that shift index -> in_{idx+1}.
        2) Otherwise, compute total late across first 3 shifts/in slots.
        """

        if not shifts:
            return

        shifts_by_code: dict[str, dict[str, Any]] = {}
        for sh in shifts:
            code = str(sh.get("shift_code") or "").strip()
            if not code:
                continue
            shifts_by_code.setdefault(code.casefold(), sh)

        # 0) If auto-by-shifts attached a slot->shift mapping, use it.
        total = 0
        used_any = False
        for slot in (1, 2, 3):
            slot_code = str(row.get(f"_slot_shift_code_{slot}") or "").strip()
            if not slot_code:
                continue
            sh = shifts_by_code.get(slot_code.casefold())
            if sh is None:
                continue
            late_val = cls._calc_late_minutes_for_shift(
                in_value=row.get(f"in_{slot}"),
                shift=sh,
            )
            if late_val is None:
                continue
            used_any = True
            total += int(late_val)

        if used_any:
            row["late"] = int(total)
            return

        row_shift_code = str(row.get("shift_code") or "").strip()

        # 1) Match by shift_code -> use its order index
        if row_shift_code:
            row_code_cf = row_shift_code.casefold()
            for idx, sh in enumerate(shifts):
                if str(sh.get("shift_code") or "").strip().casefold() == row_code_cf:
                    if idx >= 3:
                        return
                    late_val = cls._calc_late_minutes_for_shift(
                        in_value=row.get(f"in_{idx + 1}"),
                        shift=sh,
                    )
                    if late_val is not None:
                        row["late"] = int(late_val)
                    return

        # 2) Fallback: sum across first 3 shifts
        total = 0
        used_any = False
        for idx, sh in enumerate(shifts[:3]):
            late_val = cls._calc_late_minutes_for_shift(
                in_value=row.get(f"in_{idx + 1}"),
                shift=sh,
            )
            if late_val is None:
                continue
            used_any = True
            total += int(late_val)

        if used_any:
            row["late"] = int(total)

    @classmethod
    def _collect_sorted_times(cls, row: dict[str, Any]) -> list[object]:
        keys = ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3")
        items: list[tuple[int, int, object]] = []
        for idx, k in enumerate(keys):
            v = row.get(k)
            sec = cls._time_to_seconds(v)
            if sec is None:
                continue
            items.append((int(sec), int(idx), v))
        items.sort(key=lambda t: (t[0], t[1]))
        return [v for _sec, _idx, v in items]

    @classmethod
    def _dedupe_close_times(
        cls,
        values: list[object],
        *,
        within_seconds: int = 120,
        keep: str = "first",
    ) -> list[object]:
        """Gộp các lần chấm quá gần nhau (nhiễu), để tránh sinh thêm cặp vào/ra rác."""

        if not values:
            return []

        try:
            window = max(0, int(within_seconds))
        except Exception:
            window = 90

        items: list[tuple[int, object]] = []
        for v in values:
            s = cls._time_to_seconds(v)
            if s is None:
                continue
            items.append((int(s), v))
        if not items:
            return []

        items.sort(key=lambda t: t[0])
        keep_last = str(keep or "").strip().lower() != "first"

        out: list[tuple[int, object]] = [items[0]]
        for sec, v in items[1:]:
            prev_sec, _prev_v = out[-1]
            if int(sec) - int(prev_sec) <= int(window):
                if keep_last:
                    out[-1] = (int(sec), v)
            else:
                out.append((int(sec), v))
        return [v for _sec, v in out]

    @classmethod
    def _ensure_slot_shift_mapping(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> None:
        """Infer slot->shift_code mapping from displayed in_i/out_i.

        This keeps late/early recompute correct even when shifts are skipped during
        matching (e.g., when only night shift exists and it ends up in slot1).
        """

        if not shifts:
            return

        def _is_overnight_shift(sh: dict[str, Any]) -> bool:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True
            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True
            return False

        def _sec(v: object | None) -> int | None:
            return cls._time_to_seconds(v)

        def _in_window(v: object | None, sh: dict[str, Any]) -> bool:
            if v is None:
                return False
            in_start = sh.get("in_window_start") or sh.get("time_in")
            in_end = sh.get("in_window_end") or sh.get("time_in")
            in_start_sec = _sec(in_start)
            in_end_sec = _sec(in_end)
            if in_start_sec is None and in_end_sec is None:
                return False
            return (
                cls._pick_time_in_range(
                    [v],
                    start_sec=in_start_sec,
                    end_sec=in_end_sec,
                    pick="first",
                )
                is not None
            )

        def _out_window(v: object | None, sh: dict[str, Any]) -> bool:
            if v is None:
                return False
            out_start = sh.get("out_window_start") or sh.get("time_out")
            out_end = sh.get("out_window_end") or sh.get("time_out")
            out_start_sec = _sec(out_start)
            out_end_sec = _sec(out_end)
            if out_start_sec is None and out_end_sec is None:
                return False
            return (
                cls._pick_time_in_range(
                    [v],
                    start_sec=out_start_sec,
                    end_sec=out_end_sec,
                    pick="first",
                )
                is not None
            )

        def _total_minutes(sh: dict[str, Any]) -> int:
            try:
                v = int(sh.get("total_minutes") or 0)
                return v if v > 0 else 10**9
            except Exception:
                return 10**9

        def _is_sang_or_chieu(sh: dict[str, Any]) -> bool:
            code = str(sh.get("shift_code") or "").strip().casefold()
            if not code:
                return False
            return code in {"sáng", "sang", "chiều", "chieu"}

        for slot in (1, 2, 3):
            key_code = f"_slot_shift_code_{slot}"
            key_complete = f"_slot_complete_{slot}"

            # Don't override if already computed.
            if str(row.get(key_code) or "").strip():
                continue

            in_v = row.get(f"in_{slot}")
            out_v = row.get(f"out_{slot}")

            candidates: list[tuple[int, int, int, dict[str, Any]]] = []
            for sh in shifts:
                in_ok = _in_window(in_v, sh)
                out_ok = _out_window(out_v, sh)
                if not in_ok and not out_ok:
                    continue

                complete = 2 if (in_ok and out_ok) else 1

                # Rule: only treat as SÁNG/CHIỀU when BOTH IN+OUT are within windows.
                if _is_sang_or_chieu(sh) and complete < 2:
                    continue

                tm = _total_minutes(sh)
                night = 1 if _is_overnight_shift(sh) else 0
                candidates.append(
                    (
                        -int(complete),
                        int(tm),
                        int(night),
                        sh,
                    )
                )

            if not candidates:
                continue

            candidates.sort(key=lambda t: (t[0], t[1], t[2]))
            chosen = candidates[0][3]
            code = str(chosen.get("shift_code") or "").strip() or None
            row[key_code] = code
            # strict complete: both IN+OUT within window
            try:
                in_ok = _in_window(in_v, chosen)
                out_ok = _out_window(out_v, chosen)
                row[key_complete] = bool(in_ok and out_ok)
            except Exception:
                row[key_complete] = False

    @staticmethod
    def _date_to_day_key(value: object | None) -> str:
        """Map date -> day_key used by arrange_schedule_details."""

        if value is None:
            return ""

        if isinstance(value, _dt.date) and not isinstance(value, _dt.datetime):
            w = int(value.weekday())
        else:
            # Accept 'YYYY-MM-DD' or datetime
            try:
                if isinstance(value, _dt.datetime):
                    w = int(value.date().weekday())
                else:
                    w = int(_dt.date.fromisoformat(str(value)).weekday())
            except Exception:
                return ""

        return (
            "mon"
            if w == 0
            else (
                "tue"
                if w == 1
                else (
                    "wed"
                    if w == 2
                    else (
                        "thu"
                        if w == 3
                        else ("fri" if w == 4 else ("sat" if w == 5 else "sun"))
                    )
                )
            )
        )

    @staticmethod
    def _sum_shift_minutes_and_work(
        shifts: list[dict[str, Any]],
    ) -> tuple[int, float | None]:
        """Return expected total_minutes and work_count for a schedule day.

        If there are multiple shifts in a day (e.g. SA + CH), sum them.
        Missing/NULL values are ignored.
        """

        total_minutes = 0
        work_total: float | None = None

        for sh in shifts or []:
            try:
                tm = int(sh.get("total_minutes") or 0)
            except Exception:
                tm = 0
            if tm > 0:
                total_minutes += int(tm)

            raw_wc = sh.get("work_count")
            if raw_wc is None or str(raw_wc).strip() == "":
                continue
            try:
                wc = float(raw_wc)
            except Exception:
                continue
            if work_total is None:
                work_total = 0.0
            work_total += float(wc)

        return int(total_minutes), work_total

    @classmethod
    def _pick_time_in_range(
        cls,
        values: list[object],
        *,
        start_sec: int | None,
        end_sec: int | None,
        pick: str,
    ) -> object | None:
        if not values:
            return None

        def _sec_in_range(s: int, start: int | None, end: int | None) -> bool:
            if start is None and end is None:
                return True
            if start is None:
                return s <= int(end)
            if end is None:
                return s >= int(start)

            # Support range that crosses midnight: e.g. 22:00 -> 02:00
            if int(start) <= int(end):
                return int(start) <= s <= int(end)
            return s >= int(start) or s <= int(end)

        def _in_range(v: object) -> bool:
            s = cls._time_to_seconds(v)
            if s is None:
                return False
            return _sec_in_range(int(s), start_sec, end_sec)

        candidates = [v for v in values if _in_range(v)]
        if not candidates:
            return None

        candidates_sorted = sorted(
            candidates,
            key=lambda v: (int(cls._time_to_seconds(v) or 0),),
        )
        return candidates_sorted[0] if pick == "first" else candidates_sorted[-1]

    @classmethod
    def _remove_first_occurrence(cls, values: list[object], target: object) -> None:
        try:
            values.remove(target)
        except Exception:
            # fallback by seconds compare
            t_sec = cls._time_to_seconds(target)
            if t_sec is None:
                return
            for i, v in enumerate(list(values)):
                if cls._time_to_seconds(v) == t_sec:
                    try:
                        values.pop(i)
                    except Exception:
                        pass
                    return

    @classmethod
    def _apply_mode_auto_by_shifts(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> None:
        """Auto mode dựa trên danh sách ca (work_shifts) theo thứ tự."""

        punches = cls._dedupe_close_times(
            cls._collect_sorted_times(row),
            within_seconds=120,
            keep="first",
        )
        keys = ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3")
        for k in keys:
            row[k] = None

        # Track which shift was matched into each displayed slot (1..3)
        for slot in (1, 2, 3):
            row[f"_slot_shift_code_{slot}"] = None

        used_any = False

        def _is_overnight_shift(sh: dict[str, Any]) -> bool:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True

            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True

            return False

        def _pick_out_relaxed(
            values: list[object],
            *,
            shift: dict[str, Any],
            out_start_sec: int | None,
            out_end_sec: int | None,
        ) -> object | None:
            """Chọn giờ ra để HIỂN THỊ (cho phép ngoài out_window_end => tăng ca).

            Quy tắc:
            - Ca ngày: lấy lần chấm MUỘN NHẤT từ out_window_start trở đi.
            - Ca đêm: chỉ lấy giờ buổi sáng (mặc định tới 15:00) để không ăn nhầm punch buổi tối.
            """

            if not values:
                return None

            start = int(out_start_sec) if out_start_sec is not None else None

            is_night = _is_overnight_shift(shift)
            if not is_night:
                # Day shift: allow any time >= start
                candidates: list[object] = []
                for v in values:
                    s = cls._time_to_seconds(v)
                    if s is None:
                        continue
                    if start is not None and int(s) < int(start):
                        continue
                    candidates.append(v)
                if not candidates:
                    return None
                return max(candidates, key=lambda v: int(cls._time_to_seconds(v) or 0))

            # Night shift: out should be morning; allow overtime but cap by 15:00
            upper = 15 * 3600
            if out_end_sec is not None:
                try:
                    upper = max(int(upper), int(out_end_sec))
                except Exception:
                    pass
            if start is None:
                start = 0

            candidates2: list[object] = []
            for v in values:
                s = cls._time_to_seconds(v)
                if s is None:
                    continue
                if int(s) < int(start):
                    continue
                if int(s) > int(upper):
                    continue
                candidates2.append(v)
            if not candidates2:
                return None
            return max(candidates2, key=lambda v: int(cls._time_to_seconds(v) or 0))

        def _sec(v: object | None) -> int | None:
            return cls._time_to_seconds(v)

        def _total_minutes(sh: dict[str, Any]) -> int:
            try:
                v = int(sh.get("total_minutes") or 0)
                return v if v > 0 else 10**9
            except Exception:
                return 10**9

        def _is_sang_or_chieu(sh: dict[str, Any]) -> bool:
            code = str(sh.get("shift_code") or "").strip().casefold()
            if not code:
                return False
            return code in {"sáng", "sang", "chiều", "chieu"}

        # Pre-score shifts by strict window hit so we can prioritize
        # "complete" shifts (has both IN+OUT within declared windows).
        scored: list[tuple[int, int, int, int, dict[str, Any]]] = []
        for idx, sh in enumerate(shifts):
            in_start = sh.get("in_window_start") or sh.get("time_in")
            in_end = sh.get("in_window_end") or sh.get("time_in")
            out_start = sh.get("out_window_start") or sh.get("time_out")
            out_end = sh.get("out_window_end") or sh.get("time_out")

            in_start_sec = _sec(in_start)
            in_end_sec = _sec(in_end)
            out_start_sec = _sec(out_start)
            out_end_sec = _sec(out_end)

            in_hit = None
            if in_start_sec is not None or in_end_sec is not None:
                in_hit = cls._pick_time_in_range(
                    punches,
                    start_sec=in_start_sec,
                    end_sec=in_end_sec,
                    pick="first",
                )
            out_hit = None
            if out_start_sec is not None or out_end_sec is not None:
                out_hit = cls._pick_time_in_range(
                    punches,
                    start_sec=out_start_sec,
                    end_sec=out_end_sec,
                    pick="last",
                )

            if in_hit is None and out_hit is None:
                continue

            complete = 2 if (in_hit is not None and out_hit is not None) else 1

            # Rule: only treat as SÁNG/CHIỀU when BOTH IN+OUT are within windows.
            if _is_sang_or_chieu(sh) and complete < 2:
                continue

            tm = _total_minutes(sh)
            night = 1 if _is_overnight_shift(sh) else 0
            # sort: complete first, then shorter shifts (SÁNG/CHIỀU), then day before night
            scored.append((-int(complete), int(tm), int(night), int(idx), sh))

        scored.sort(key=lambda t: (t[0], t[1], t[2], t[3]))

        pair_idx = 0
        for _score, _tm, _night, _idx, sh in scored:
            if pair_idx >= 3:
                break

            in_start = sh.get("in_window_start") or sh.get("time_in")
            in_end = sh.get("in_window_end") or sh.get("time_in")
            out_start = sh.get("out_window_start") or sh.get("time_out")
            out_end = sh.get("out_window_end") or sh.get("time_out")

            in_start_sec = _sec(in_start)
            in_end_sec = _sec(in_end)
            out_start_sec = _sec(out_start)
            out_end_sec = _sec(out_end)

            # Strict match để XÁC ĐỊNH ca
            in_strict = None
            if in_start_sec is not None or in_end_sec is not None:
                in_strict = cls._pick_time_in_range(
                    punches,
                    start_sec=in_start_sec,
                    end_sec=in_end_sec,
                    pick="first",
                )

            out_strict = None
            if out_start_sec is not None or out_end_sec is not None:
                out_strict = cls._pick_time_in_range(
                    punches,
                    start_sec=out_start_sec,
                    end_sec=out_end_sec,
                    pick="last",
                )

            # Nếu không match được gì trong window thì KHÔNG coi là ca này
            if in_strict is None and out_strict is None:
                continue

            in_val = in_strict
            if in_val is not None:
                cls._remove_first_occurrence(punches, in_val)

            # Out hiển thị: ưu tiên out_strict, nếu không có thì lấy overtime (relaxed)
            out_val = out_strict
            if out_val is None:
                out_val = _pick_out_relaxed(
                    punches,
                    shift=sh,
                    out_start_sec=out_start_sec,
                    out_end_sec=out_end_sec,
                )
            if out_val is not None:
                cls._remove_first_occurrence(punches, out_val)

            row[f"in_{pair_idx + 1}"] = in_val
            row[f"out_{pair_idx + 1}"] = out_val
            row[f"_slot_shift_code_{pair_idx + 1}"] = sh.get("shift_code")
            row[f"_slot_complete_{pair_idx + 1}"] = bool(
                in_strict is not None and out_strict is not None
            )

            if in_val is not None or out_val is not None:
                used_any = True

            pair_idx += 1

        # Không tự động nhồi các punch còn dư vào các cột trống,
        # vì dễ tạo ra cặp giờ rác (ví dụ: 17:00:24 + 17:00:25).
        # Nếu không match được ca nào, fallback về auto đơn giản (đã dedupe).
        if not used_any:
            # IMPORTANT: do NOT call _apply_mode_auto(row) here because we've already
            # cleared row in/out fields above; _apply_mode_auto() would see no punches.
            # Instead, refill directly from the already-collected `punches` list.
            sorted_vals = list(punches)

            # If only 1 punch and it's in the afternoon, treat it as OUT (missing IN => UI shows KV).
            try:
                if len(sorted_vals) == 1:
                    s0 = cls._time_to_seconds(sorted_vals[0])
                    if s0 is not None and int(s0) >= 13 * 3600:
                        row["in_1"] = None
                        row["out_1"] = sorted_vals[0]
                        return
            except Exception:
                pass

            keys = ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3")
            for i, k in enumerate(keys):
                row[k] = sorted_vals[i] if i < len(sorted_vals) else None
            return

        if used_any:
            # Prefer complete shifts (IN+OUT strict within windows) for labeling.
            codes_all: list[str] = []
            codes_complete: list[str] = []
            for slot in (1, 2, 3):
                code = str(row.get(f"_slot_shift_code_{slot}") or "").strip()
                if not code:
                    continue
                if code not in codes_all:
                    codes_all.append(code)
                if (
                    bool(row.get(f"_slot_complete_{slot}"))
                    and code not in codes_complete
                ):
                    codes_complete.append(code)

            label = "+".join(codes_complete or codes_all)
            row["shift_code"] = label if label else None

    @classmethod
    def _apply_mode_first_last_by_shifts(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> None:
        punches = cls._dedupe_close_times(
            cls._collect_sorted_times(row),
            within_seconds=120,
            keep="first",
        )
        for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
            row[k] = None
        if not punches:
            return

        def _is_overnight_shift(sh: dict[str, Any]) -> bool:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True
            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True
            return False

        def _sec(v: object | None) -> int | None:
            return cls._time_to_seconds(v)

        def _total_minutes(sh: dict[str, Any]) -> int:
            try:
                v = int(sh.get("total_minutes") or 0)
                return v if v > 0 else 10**9
            except Exception:
                return 10**9

        def _match_shift_for_in(
            punch: object,
            *,
            out_sec_hint: int | None,
        ) -> dict[str, Any] | None:
            ps = cls._time_to_seconds(punch)
            if ps is None:
                return None

            pref = cls._norm_text_no_diacritics(row.get("_preferred_shift_code"))

            def _is_partial_shift_code(code_norm: str) -> bool:
                return code_norm in {"sa", "ch", "sang", "chieu"}

            def _sec_in_range(s: int, start: int | None, end: int | None) -> bool:
                if start is None and end is None:
                    return True
                if start is None:
                    return s <= int(end)
                if end is None:
                    return s >= int(start)
                if int(start) <= int(end):
                    return int(start) <= s <= int(end)
                return s >= int(start) or s <= int(end)

            best: dict[str, Any] | None = None
            best_key: tuple[int, int, int] | None = None
            for sh in shifts or []:
                # Special rule: don't infer THAI SẢN from IN-only when OUT is too early.
                # THAI SẢN should generally be selected only when:
                # - user clocks out within/after its out window, OR
                # - it is explicitly matched by OUT.
                try:
                    sh_code_norm = cls._norm_text_no_diacritics(sh.get("shift_code"))
                except Exception:
                    sh_code_norm = ""
                if sh_code_norm == "thaisan":
                    try:
                        out_start = sh.get("out_window_start") or sh.get("time_out")
                        out_start_sec = _sec(out_start)
                    except Exception:
                        out_start_sec = None
                    # If we have an OUT hint and it is before THAI SẢN out start, skip.
                    if (
                        out_sec_hint is not None
                        and out_start_sec is not None
                        and int(out_sec_hint) < int(out_start_sec)
                    ):
                        continue

                # Partial shifts (SA/CH implying half-day) must have an OUT hint that
                # falls inside their OUT window; otherwise default to full-day shifts.
                if _is_partial_shift_code(sh_code_norm):
                    if out_sec_hint is None:
                        continue
                    try:
                        out_start = sh.get("out_window_start") or sh.get("time_out")
                        out_end = sh.get("out_window_end") or sh.get("time_out")
                        out_start_sec = _sec(out_start)
                        out_end_sec = _sec(out_end)
                    except Exception:
                        out_start_sec = None
                        out_end_sec = None
                    if not _sec_in_range(int(out_sec_hint), out_start_sec, out_end_sec):
                        continue

                in_start = sh.get("in_window_start") or sh.get("time_in")
                in_end = sh.get("in_window_end") or sh.get("time_in")

                in_start_sec = _sec(in_start)
                in_end_sec = _sec(in_end)
                # Không cho match nếu window/time không có (tránh match nhầm mọi punch)
                if in_start_sec is None and in_end_sec is None:
                    continue
                if (
                    cls._pick_time_in_range(
                        [punch],
                        start_sec=in_start_sec,
                        end_sec=in_end_sec,
                        pick="first",
                    )
                    is None
                ):
                    continue

                base = cls._time_to_seconds(sh.get("time_in"))
                if base is None:
                    score = 0
                else:
                    score = abs(int(ps) - int(base))

                # When OUT doesn't match any window, use OUT proximity to shift end
                # to disambiguate between shifts sharing the same start window (e.g. SA vs HÀNH CHÍNH).
                out_score = 0
                if out_sec_hint is not None:
                    out_base = cls._time_to_seconds(sh.get("time_out"))
                    in_base = cls._time_to_seconds(sh.get("time_in"))
                    if out_base is not None:
                        try:
                            out_eff = int(out_sec_hint)
                            out_base_eff = int(out_base)
                            # Overnight shift: end belongs to next day
                            if in_base is not None and int(out_base) < int(in_base):
                                out_base_eff = int(out_base) + 86400
                                if int(out_sec_hint) < int(in_base):
                                    out_eff = int(out_sec_hint) + 86400
                            out_score = abs(int(out_eff) - int(out_base_eff))
                        except Exception:
                            out_score = 0

                pref_hit = 0
                if pref:
                    try:
                        pref_hit = 0 if cls._norm_text_no_diacritics(sh.get("shift_code")) == pref else 1
                    except Exception:
                        pref_hit = 1
                else:
                    pref_hit = 1

                # Prefer preferred shift, then closest OUT-to-end, then closest IN-to-start,
                # then shorter shift.
                key = (int(pref_hit), int(out_score), int(score), int(_total_minutes(sh)))
                if best_key is None or key < best_key:
                    best = sh
                    best_key = key

            return best

        def _match_shift_for_out(
            punch: object,
            *,
            in_punch: object | None,
        ) -> dict[str, Any] | None:
            ps = cls._time_to_seconds(punch)
            if ps is None:
                return None

            pref = cls._norm_text_no_diacritics(row.get("_preferred_shift_code"))

            # OUT grace is a small fixed window to tolerate a few minutes late clock-out
            # when selecting the shift. IMPORTANT: do NOT use overtime_round_minutes here;
            # overtime_round_minutes is reserved for TC1/TC2/TC3 rounding only.
            OUT_MATCH_GRACE_SEC = 5 * 60

            def _in_window_hit(sh: dict[str, Any]) -> bool:
                if in_punch is None:
                    return False
                in_start = sh.get("in_window_start") or sh.get("time_in")
                in_end = sh.get("in_window_end") or sh.get("time_in")
                in_start_sec = _sec(in_start)
                in_end_sec = _sec(in_end)
                if in_start_sec is None and in_end_sec is None:
                    return False
                return (
                    cls._pick_time_in_range(
                        [in_punch],
                        start_sec=in_start_sec,
                        end_sec=in_end_sec,
                        pick="first",
                    )
                    is not None
                )

            best: dict[str, Any] | None = None
            best_key: tuple[int, int, int, int] | None = None
            for sh in shifts or []:
                out_start = sh.get("out_window_start") or sh.get("time_out")
                out_end = sh.get("out_window_end") or sh.get("time_out")

                out_start_sec = _sec(out_start)
                out_end_sec = _sec(out_end)

                # Allow small grace when matching OUT for day shifts.
                if not _is_overnight_shift(sh) and out_end_sec is not None:
                    try:
                        out_end_sec = int(out_end_sec) + int(OUT_MATCH_GRACE_SEC)
                    except Exception:
                        pass
                # Không cho match nếu window/time không có (tránh match nhầm mọi punch)
                if out_start_sec is None and out_end_sec is None:
                    continue
                if (
                    cls._pick_time_in_range(
                        [punch],
                        start_sec=out_start_sec,
                        end_sec=out_end_sec,
                        pick="first",
                    )
                    is None
                ):
                    continue

                # Prefer shifts that match BOTH the chosen IN and this OUT.
                # This prevents full-day punches (07:46-17:15) from being labeled as CH
                # just because CH is shorter while sharing the same time_out as HÀNH CHÍNH.
                complete_penalty = 0
                try:
                    complete_penalty = 0 if _in_window_hit(sh) else 1
                except Exception:
                    complete_penalty = 1

                base = cls._time_to_seconds(sh.get("time_out"))
                if base is None:
                    score = 0
                else:
                    score = abs(int(ps) - int(base))

                pref_hit = 0
                if pref:
                    try:
                        pref_hit = 0 if cls._norm_text_no_diacritics(sh.get("shift_code")) == pref else 1
                    except Exception:
                        pref_hit = 1
                else:
                    pref_hit = 1

                key = (
                    int(pref_hit),
                    int(complete_penalty),
                    int(score),
                    int(_total_minutes(sh)),
                )
                if best_key is None or key < best_key:
                    best = sh
                    best_key = key

            return best

        def _pick_out_relaxed(
            values: list[object],
            *,
            shift: dict[str, Any],
        ) -> object | None:
            if not values:
                return None

            out_start = shift.get("out_window_start") or shift.get("time_out")
            out_end = shift.get("out_window_end") or shift.get("time_out")
            out_start_sec = cls._time_to_seconds(out_start)
            out_end_sec = cls._time_to_seconds(out_end)

            start = int(out_start_sec) if out_start_sec is not None else None
            is_night = _is_overnight_shift(shift)
            if not is_night:
                candidates: list[object] = []
                for v in values:
                    s = cls._time_to_seconds(v)
                    if s is None:
                        continue
                    if start is not None and int(s) < int(start):
                        continue
                    candidates.append(v)
                if not candidates:
                    return None
                return max(candidates, key=lambda v: int(cls._time_to_seconds(v) or 0))

            upper = 15 * 3600
            if out_end_sec is not None:
                try:
                    upper = max(int(upper), int(out_end_sec))
                except Exception:
                    pass
            if start is None:
                start = 0

            candidates2: list[object] = []
            for v in values:
                s = cls._time_to_seconds(v)
                if s is None:
                    continue
                if int(s) < int(start):
                    continue
                if int(s) > int(upper):
                    continue
                candidates2.append(v)
            if not candidates2:
                return None
            return max(candidates2, key=lambda v: int(cls._time_to_seconds(v) or 0))

        # Pick IN: earliest punch that matches ANY shift in-window
        punches_sorted = sorted(
            punches, key=lambda v: int(cls._time_to_seconds(v) or 0)
        )

        # Special case: only 1 punch in the day.
        # If it is an afternoon punch (>= 13:00), treat it as OUT (missing IN => UI shows KV).
        try:
            if len(punches_sorted) == 1:
                only = punches_sorted[0]
                only_sec = cls._time_to_seconds(only)
                if only_sec is not None and int(only_sec) >= 13 * 3600:
                    row["in_1"] = None
                    row["out_1"] = only
                    # Best-effort label for downstream logic; later KV/KR handling may clear it.
                    try:
                        out_sh = _match_shift_for_out(only, in_punch=None)
                        if out_sh is not None:
                            code = str((out_sh or {}).get("shift_code") or "").strip()
                            if code:
                                row["shift_code"] = code
                                row["_slot_shift_code_1"] = code
                    except Exception:
                        pass
                    return
        except Exception:
            pass

        # OUT hint: latest punch in the day (even if it won't match any out-window)
        out_sec_hint: int | None = None
        try:
            out_sec_hint = max(
                [int(cls._time_to_seconds(v) or 0) for v in punches_sorted if cls._time_to_seconds(v) is not None],
                default=None,
            )
        except Exception:
            out_sec_hint = None

        in_val = None
        in_shift: dict[str, Any] | None = None
        for p in punches_sorted:
            sh = _match_shift_for_in(p, out_sec_hint=out_sec_hint)
            if sh is not None:
                in_val = p
                in_shift = sh
                break
        # Fallback: always show an IN time even when no punch matches any in-window.
        if in_val is None and punches_sorted:
            in_val = punches_sorted[0]
        if in_val is not None:
            cls._remove_first_occurrence(punches, in_val)

        # Pick OUT strict: latest punch that matches ANY shift out-window
        punches_sorted2 = sorted(
            punches,
            key=lambda v: int(cls._time_to_seconds(v) or 0),
            reverse=True,
        )
        out_strict = None
        out_shift: dict[str, Any] | None = None
        for p in punches_sorted2:
            sh = _match_shift_for_out(p, in_punch=in_val)
            if sh is not None:
                out_strict = p
                out_shift = sh
                break

        out_val = out_strict
        if out_val is not None:
            cls._remove_first_occurrence(punches, out_val)
        else:
            # Relax overtime display: dựa trên shift đã match IN, nếu không có thì dùng shift match OUT (hiếm)
            base_shift = in_shift or out_shift
            if base_shift is not None:
                out_val = _pick_out_relaxed(punches, shift=base_shift)
                if out_val is not None:
                    cls._remove_first_occurrence(punches, out_val)

        # Fallback: always show an OUT time even when no punch matches any out-window.
        if out_val is None and punches:
            try:
                out_val = max(punches, key=lambda v: int(cls._time_to_seconds(v) or 0))
            except Exception:
                out_val = punches[-1]
            if out_val is not None:
                cls._remove_first_occurrence(punches, out_val)

        row["in_1"] = in_val
        row["out_1"] = out_val

        def _is_overnight_shift(sh: dict[str, Any]) -> bool:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True
            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True
            return False

        # Chỉ set ca khi có match trong window
        if shifts and (in_shift is not None or out_shift is not None):
            # Prefer OUT match when available (OUT is more discriminative)
            base = out_shift or in_shift
            code = str((base or {}).get("shift_code") or "").strip()
            row["shift_code"] = code if code else None
            row["_slot_shift_code_1"] = code if code else None

            # Tăng ca 1 (TC1): nếu OUT vượt time_out của ca (day shift) và tc1 đang trống.
            try:
                if (row.get("tc1") is None) or (str(row.get("tc1") or "").strip() == ""):
                    if base is not None and out_val is not None and not _is_overnight_shift(base):
                        # Không tính tăng ca cho THAI SẢN
                        try:
                            base_code_norm = cls._norm_text_no_diacritics(
                                (base or {}).get("shift_code")
                            )
                            if base_code_norm == "thaisan":
                                raise ValueError("skip")
                        except ValueError:
                            raise
                        except Exception:
                            pass
                        out_sec = cls._time_to_seconds(out_val)
                        base_out_sec = cls._time_to_seconds(base.get("time_out"))
                        if out_sec is not None and base_out_sec is not None:
                            ot_min_raw = max(
                                0, (int(out_sec) - int(base_out_sec)) // 60
                            )

                            # Apply overtime rounding by shift config.
                            # Rule: round DOWN to nearest step (avoid over-counting).
                            try:
                                round_step = int(base.get("overtime_round_minutes") or 0)
                            except Exception:
                                round_step = 0
                            if round_step > 0:
                                ot_min = (int(ot_min_raw) // int(round_step)) * int(
                                    round_step
                                )
                            else:
                                ot_min = int(ot_min_raw)

                            # Chỉ hiển thị khi >= 1 giờ (sau khi làm tròn)
                            if ot_min >= 60:
                                ot_hours = float(ot_min) / 60.0
                                if int(ot_min) % 60 == 0:
                                    row["tc1"] = str(int(ot_hours))
                                else:
                                    row["tc1"] = (
                                        f"{ot_hours:.2f}".rstrip("0").rstrip(".")
                                    )
            except Exception:
                pass

            try:
                same = False
                if in_shift is not None and out_shift is not None:
                    ci = str((in_shift or {}).get("shift_code") or "").strip()
                    co = str((out_shift or {}).get("shift_code") or "").strip()
                    same = bool(ci and co and ci == co)
                row["_slot_complete_1"] = bool(same)
            except Exception:
                row["_slot_complete_1"] = False

    @classmethod
    def _compute_shift_label_from_punches(
        cls,
        row: dict[str, Any],
        *,
        shifts: list[dict[str, Any]],
    ) -> str | None:
        punches = cls._collect_sorted_times(row)
        if not punches or not shifts:
            return None

        def _is_overnight_shift(sh: dict[str, Any]) -> bool:
            tin = cls._time_to_seconds(sh.get("time_in"))
            tout = cls._time_to_seconds(sh.get("time_out"))
            if tin is not None and tout is not None and int(tout) < int(tin):
                return True
            win_in = cls._time_to_seconds(sh.get("in_window_start"))
            win_out = cls._time_to_seconds(sh.get("out_window_end"))
            if (
                win_in is not None
                and win_out is not None
                and int(win_out) < int(win_in)
            ):
                return True
            return False

        def _sec(v: object | None) -> int | None:
            return cls._time_to_seconds(v)

        def _total_minutes(sh: dict[str, Any]) -> int:
            try:
                v = int(sh.get("total_minutes") or 0)
                return v if v > 0 else 10**9
            except Exception:
                return 10**9

        def _is_sang_or_chieu(sh: dict[str, Any]) -> bool:
            code = str(sh.get("shift_code") or "").strip().casefold()
            if not code:
                return False
            return code in {"sáng", "sang", "chiều", "chieu"}

        hits: list[tuple[int, int, int, dict[str, Any], bool]] = []

        for sh in shifts:
            in_start = sh.get("in_window_start") or sh.get("time_in")
            in_end = sh.get("in_window_end") or sh.get("time_in")
            out_start = sh.get("out_window_start") or sh.get("time_out")
            out_end = sh.get("out_window_end") or sh.get("time_out")

            in_start_sec = _sec(in_start)
            in_end_sec = _sec(in_end)
            out_start_sec = _sec(out_start)
            out_end_sec = _sec(out_end)

            in_hit = None
            if in_start_sec is not None or in_end_sec is not None:
                in_hit = cls._pick_time_in_range(
                    punches,
                    start_sec=in_start_sec,
                    end_sec=in_end_sec,
                    pick="first",
                )

            out_hit = None
            if out_start_sec is not None or out_end_sec is not None:
                out_hit = cls._pick_time_in_range(
                    punches,
                    start_sec=out_start_sec,
                    end_sec=out_end_sec,
                    pick="first",
                )

            if in_hit is None and out_hit is None:
                continue

            complete = bool(in_hit is not None and out_hit is not None)

            # Rule: only label as SÁNG/CHIỀU when BOTH IN+OUT are within windows.
            if _is_sang_or_chieu(sh) and not complete:
                continue

            tm = _total_minutes(sh)
            night = 1 if _is_overnight_shift(sh) else 0
            # prefer complete, then shorter shifts (SÁNG/CHIỀU), then day before night
            hits.append((0 if complete else 1, int(tm), int(night), sh, complete))

        if not hits:
            return None

        hits.sort(key=lambda t: (t[0], t[1], t[2]))
        complete_codes: list[str] = []
        any_codes: list[str] = []
        for _c, _tm, _n, sh, is_complete in hits:
            code = str(sh.get("shift_code") or "").strip()
            if not code:
                continue
            if code not in any_codes:
                any_codes.append(code)
            if is_complete and code not in complete_codes:
                complete_codes.append(code)

        label = "+".join(complete_codes or any_codes)
        return label if label else None

    @classmethod
    def _apply_mode_auto(cls, row: dict[str, Any]) -> None:
        sorted_vals = cls._dedupe_close_times(
            cls._collect_sorted_times(row),
            within_seconds=120,
            keep="first",
        )

        if len(sorted_vals) == 1:
            s0 = cls._time_to_seconds(sorted_vals[0])
            if s0 is not None and int(s0) >= 13 * 3600:
                # Reset all
                for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                    row[k] = None
                row["out_1"] = sorted_vals[0]
                return

        keys = ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3")
        for i, k in enumerate(keys):
            row[k] = sorted_vals[i] if i < len(sorted_vals) else None

    @classmethod
    def _apply_mode_first_last(cls, row: dict[str, Any]) -> None:
        sorted_vals = cls._dedupe_close_times(
            cls._collect_sorted_times(row),
            within_seconds=120,
            keep="first",
        )
        # Reset all
        for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
            row[k] = None
        if not sorted_vals:
            return
        # If only 1 punch and it's in the afternoon, treat it as OUT.
        if len(sorted_vals) == 1:
            s0 = cls._time_to_seconds(sorted_vals[0])
            if s0 is not None and int(s0) >= 13 * 3600:
                row["out_1"] = sorted_vals[0]
                return

        row["in_1"] = sorted_vals[0]
        if len(sorted_vals) >= 2:
            row["out_1"] = sorted_vals[-1]

    def list_attendance_audit_arranged(
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
        progress_cb: callable[[int, str], None] | None = None,
        progress_items_cb: callable[[int, int, str], None] | None = None,
        cancel_cb: callable[[], bool] | None = None,
        recompute_import_locked: bool = False,
        overwrite_import_locked_computed: bool = False,
    ) -> list[dict[str, Any]]:
        def _cancelled() -> bool:
            try:
                return bool(cancel_cb()) if cancel_cb is not None else False
            except Exception:
                return False

        def _progress(pct: int, msg: str) -> None:
            if progress_cb is None:
                return
            try:
                progress_cb(max(0, min(100, int(pct))), str(msg))
            except Exception:
                pass

        def _progress_items(done: int, total: int, msg: str) -> None:
            if progress_items_cb is None:
                return
            try:
                progress_items_cb(int(done), int(total), str(msg))
            except Exception:
                pass

        _progress(0, "Đang chuẩn bị...")
        if _cancelled():
            return []

        _progress(3, "Đang tải dữ liệu chấm công...")
        rows = self._repo.list_rows(
            from_date=from_date,
            to_date=to_date,
            employee_id=employee_id,
            attendance_code=attendance_code,
            employee_ids=employee_ids,
            attendance_codes=attendance_codes,
            department_id=department_id,
            title_id=title_id,
        )

        _progress(12, "Đang tổng hợp dữ liệu...")
        if _cancelled():
            return []

        # Holidays map (for day_key = 'holiday')
        holidays: set[str] = set()
        try:
            holidays = self._repo.list_holiday_dates(
                from_date=from_date, to_date=to_date
            )
        except Exception:
            holidays = set()

        _progress(18, "Đang tải thiết lập lịch/ca...")
        if _cancelled():
            return rows

        # Map schedule_name -> {schedule_id, in_out_mode}
        schedule_names: list[str] = []
        for r in rows:
            name = self._norm_schedule_name(r.get("schedule"))
            if name:
                schedule_names.append(name)
        schedule_names = list(dict.fromkeys(schedule_names))

        schedule_map: dict[str, dict[str, Any]] = {}
        try:
            if schedule_names:
                schedule_map = self._repo.get_schedule_id_mode_by_names(schedule_names)
        except Exception:
            logger.exception("Không thể tải schedule_id/in_out_mode theo schedule_name")
            schedule_map = {}

        # Also allow lookup by normalized schedule key.
        schedule_map_norm: dict[str, dict[str, Any]] = {}
        try:
            for k, v in (schedule_map or {}).items():
                nk = self._norm_schedule_name(k)
                if nk:
                    schedule_map_norm[nk] = v
        except Exception:
            schedule_map_norm = {}

        _progress(28, "Đang tải chi tiết lịch...")
        if _cancelled():
            return rows

        schedule_ids: list[int] = []
        for v in schedule_map.values():
            sid = v.get("schedule_id")
            if sid is None:
                continue
            try:
                schedule_ids.append(int(sid))
            except Exception:
                continue
        schedule_ids = list(dict.fromkeys(schedule_ids))

        details_map: dict[tuple[int, str], dict[str, Any]] = {}
        try:
            if schedule_ids:
                details_map = self._repo.get_schedule_details_by_schedule_ids(
                    schedule_ids
                )
        except Exception:
            logger.exception("Không thể tải arrange_schedule_details")
            details_map = {}

        _progress(38, "Đang tải danh sách ca làm...")
        if _cancelled():
            return rows

        all_shift_ids: list[int] = []
        for d in details_map.values():
            for k in ("shift1_id", "shift2_id", "shift3_id", "shift4_id", "shift5_id"):
                sid = d.get(k)
                if sid is None:
                    continue
                try:
                    all_shift_ids.append(int(sid))
                except Exception:
                    continue
        all_shift_ids = list(dict.fromkeys(all_shift_ids))

        shift_map: dict[int, dict[str, Any]] = {}
        try:
            if all_shift_ids:
                shift_map = self._repo.get_work_shifts_by_ids(all_shift_ids)
        except Exception:
            logger.exception("Không thể tải work_shifts")
            shift_map = {}

        # Load attendance symbols for displaying OFF/V/Lễ when no punches.
        # Respect is_visible: 1 show, 0 hide.
        symbols_by_code: dict[str, str] = {}
        try:
            raw_syms = AttendanceSymbolService().list_rows_by_code()
            for code in ("C07", "C09", "C10"):
                row_sym = raw_syms.get(code)
                if row_sym is None:
                    continue
                try:
                    if int(row_sym.get("is_visible") or 0) != 1:
                        symbols_by_code[code] = ""
                        continue
                except Exception:
                    symbols_by_code[code] = ""
                    continue
                symbols_by_code[code] = str(row_sym.get("symbol") or "").strip()
        except Exception:
            symbols_by_code = {}

        # Main per-row processing: 40..80
        total_rows = max(1, int(len(rows)))
        _progress(40, f"Đang xử lý {len(rows)} dòng...")

        # Start item progress (done/total)
        _progress_items(0, int(total_rows), "Đang xử lý dữ liệu...")

        # Persist shift_code after all post-processing.
        stored_code_by_audit_id: dict[int, str | None] = {}

        step = max(1, int(total_rows // 100))
        for i, r in enumerate(rows):
            # Item progress: emit every row so UI can animate 1-by-1 without skipping.
            _progress_items(i + 1, int(total_rows), "Đang xử lý dữ liệu...")

            if i % step == 0:
                pct = 40 + int((i / total_rows) * 40)
                _progress(
                    pct, f"Đang xử lý dữ liệu... ({min(i, len(rows))}/{len(rows)})"
                )
                if _cancelled():
                    return rows

            def _norm_code(v: object | None) -> str | None:
                s = str(v or "").strip()
                return s if s else None

            stored_code = _norm_code(r.get("shift_code_db"))
            # Mặc định: hiển thị giá trị DB (device mode), auto/first_last sẽ recompute.
            r["shift_code"] = stored_code
            # Hint: nếu DB đã xác định THAI SẢN thì ưu tiên ca này khi lịch là CA GỘP
            # (giảm nhầm sang SA/HC khi thiếu OUT hoặc window chồng lấn).
            try:
                if self._norm_text_no_diacritics(stored_code) == "thaisan":
                    r["_preferred_shift_code"] = stored_code
                else:
                    r["_preferred_shift_code"] = None
            except Exception:
                r["_preferred_shift_code"] = None
            try:
                if r.get("id") is not None:
                    stored_code_by_audit_id[int(r.get("id"))] = stored_code
            except Exception:
                pass

            # IMPORTANT: import_locked=1 means "chốt công".
            # When viewing data, do not apply any recalculation or schedule/shift changes.
            try:
                is_locked = int(r.get("import_locked") or 0) == 1
            except Exception:
                is_locked = False

            if is_locked and (not bool(recompute_import_locked)):
                # Keep exactly what DB stores.
                r["in_out_mode"] = "device"
                continue

            schedule_name = self._norm_schedule_name(r.get("schedule"))
            meta = schedule_map.get(schedule_name) or schedule_map_norm.get(schedule_name) or {}
            mode = meta.get("in_out_mode")
            mode_norm = str(mode).strip().lower() if mode is not None else ""
            if mode_norm not in {"auto", "device", "first_last"}:
                mode_norm = "device"
            r["in_out_mode"] = mode_norm

            # Normalize noisy punches (double-tap within a short window).
            # This is applied defensively for all modes; especially important for
            # device mode (where we otherwise keep DB values as-is).
            try:
                orig_vals = self._collect_sorted_times(r)
                cleaned_vals = self._dedupe_close_times(
                    orig_vals,
                    within_seconds=120,
                    keep="first",
                )
                if mode_norm == "device" and len(cleaned_vals) != len(orig_vals):
                    keys0 = ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3")
                    for i0, k0 in enumerate(keys0):
                        r[k0] = cleaned_vals[i0] if i0 < len(cleaned_vals) else None
            except Exception:
                pass

            # Schedule flags
            try:
                ignore_absent_sat = int(meta.get("ignore_absent_sat") or 0)
            except Exception:
                ignore_absent_sat = 0
            try:
                ignore_absent_sun = int(meta.get("ignore_absent_sun") or 0)
            except Exception:
                ignore_absent_sun = 0
            try:
                ignore_absent_holiday = int(meta.get("ignore_absent_holiday") or 0)
            except Exception:
                ignore_absent_holiday = 0
            try:
                holiday_count_as_work = int(meta.get("holiday_count_as_work") or 0)
            except Exception:
                holiday_count_as_work = 0
            try:
                day_is_out_time = int(meta.get("day_is_out_time") or 0)
            except Exception:
                day_is_out_time = 0

            # Determine day_key for fetching schedule details
            day_key = self._date_to_day_key(r.get("date"))
            is_holiday = False
            try:
                if r.get("date") is not None and str(r.get("date")) in holidays:
                    day_key = "holiday"
                    is_holiday = True
            except Exception:
                pass
            r["day_key"] = day_key

            # Keep flags for post-processing (single-day carryover).
            try:
                r["_ignore_absent_sat"] = int(ignore_absent_sat)
            except Exception:
                r["_ignore_absent_sat"] = 0
            try:
                r["_ignore_absent_sun"] = int(ignore_absent_sun)
            except Exception:
                r["_ignore_absent_sun"] = 0
            try:
                r["_ignore_absent_holiday"] = int(ignore_absent_holiday)
            except Exception:
                r["_ignore_absent_holiday"] = 0
            try:
                r["_is_holiday"] = bool(is_holiday)
            except Exception:
                r["_is_holiday"] = False

            schedule_id = meta.get("schedule_id")
            try:
                r["schedule_id"] = int(schedule_id) if schedule_id is not None else None
            except Exception:
                r["schedule_id"] = None

            # Build ordered shifts (shift1..shift5)
            shifts: list[dict[str, Any]] = []
            detail_for_day: dict[str, Any] | None = None
            if r.get("schedule_id") is not None and day_key:
                detail_for_day = details_map.get(
                    (int(r.get("schedule_id")), str(day_key))
                )
            # Fallback by day_name (weekday string) when day_key lookup fails.
            if detail_for_day is None and r.get("schedule_id") is not None:
                wd = str(r.get("weekday") or "").strip()
                if wd:
                    wd_norm = wd.casefold().replace(" ", "")
                    sid0 = int(r.get("schedule_id"))
                    for (sid_k, _day_key_k), d in (details_map or {}).items():
                        if int(sid_k) != int(sid0):
                            continue
                        day_name = str((d or {}).get("day_name") or "").strip()
                        if not day_name:
                            continue
                        if day_name.casefold().replace(" ", "") == wd_norm:
                            detail_for_day = d
                            break

            if detail_for_day is not None:
                for k in (
                    "shift1_id",
                    "shift2_id",
                    "shift3_id",
                    "shift4_id",
                    "shift5_id",
                ):
                    sid = detail_for_day.get(k)
                    if sid is None:
                        continue
                    try:
                        sh = shift_map.get(int(sid))
                        if sh is not None:
                            shifts.append(sh)
                    except Exception:
                        continue

            try:
                r["_has_shift1"] = bool(
                    detail_for_day is not None and detail_for_day.get("shift1_id") is not None
                )
            except Exception:
                r["_has_shift1"] = False

            # Flags used for post-processing (e.g. overnight carryover).
            try:
                r["_has_overnight_shift"] = bool(
                    [sh for sh in (shifts or []) if self._is_overnight_shift_def(sh)]
                )
            except Exception:
                r["_has_overnight_shift"] = False

            expected_minutes, expected_work = self._sum_shift_minutes_and_work(shifts)

            def _expected_for_row_from_matched_shifts(
                row0: dict[str, Any],
                *,
                day_shifts: list[dict[str, Any]],
            ) -> tuple[int, float | None]:
                """Compute expected minutes/work for the row's matched shift(s).

                We must NOT sum all schedule-day shifts; otherwise HC/ĐÊM rows can
                show inflated values like 24h and 3.5 công.

                Preference order:
                1) slot mapping (_slot_shift_code_1..3)
                2) row['shift_code'] labels (may be joined by '+')
                3) fallback to single shift if only one exists
                """

                if not day_shifts:
                    return 0, None

                shifts_by_code: dict[str, dict[str, Any]] = {}
                for sh in day_shifts:
                    code = str(sh.get("shift_code") or "").strip()
                    if not code:
                        continue
                    shifts_by_code.setdefault(code.casefold(), sh)

                used_codes: list[str] = []

                # 1) slot mapping
                for slot in (1, 2, 3):
                    c = str(row0.get(f"_slot_shift_code_{slot}") or "").strip()
                    if c and c not in used_codes:
                        used_codes.append(c)

                # 2) shift_code label
                if not used_codes:
                    lbl = str(row0.get("shift_code") or "").strip()
                    if lbl:
                        parts = [p.strip() for p in lbl.split("+") if p.strip()]
                        for p in parts:
                            if p not in used_codes:
                                used_codes.append(p)

                matched: list[dict[str, Any]] = []
                for c in used_codes:
                    sh = shifts_by_code.get(c.casefold())
                    if sh is not None:
                        matched.append(sh)

                # 3) fallback: if schedule day defines only one shift, use it.
                if not matched and len(day_shifts) == 1:
                    matched = [day_shifts[0]]

                return self._sum_shift_minutes_and_work(matched)

            def _has_any_punch(row0: dict[str, Any]) -> bool:
                for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                    if self._time_to_seconds(row0.get(k)) is not None:
                        return True
                return False

            # Requested rules when there is no attendance data (no punch times):
            # - If work_date is a holiday => fill symbol C10 into in_1
            # - Else if schedule day has shift1_id => fill symbol C07 into in_1 (vắng)
            # - Else (no shift1_id) => fill symbol C09 into in_1 (OFF)
            # Respect is_visible: hidden symbols => leave blank.
            if not _has_any_punch(r):
                # Exception: THAI SẢN vẫn tính công như ca bình thường
                # khi lịch ngày đó chỉ có đúng 1 ca THAI SẢN.
                try:
                    if len(shifts) == 1:
                        only_code = str((shifts[0] or {}).get("shift_code") or "").strip()
                        if self._norm_text_no_diacritics(only_code) == "thaisan":
                            for k in (
                                "in_1",
                                "out_1",
                                "in_2",
                                "out_2",
                                "in_3",
                                "out_3",
                            ):
                                r[k] = None

                            r["shift_code"] = only_code
                            exp_m, exp_w = _expected_for_row_from_matched_shifts(
                                r, day_shifts=shifts
                            )
                            if exp_m > 0:
                                r["hours"] = round(float(exp_m) / 60.0, 2)
                            else:
                                r["hours"] = None
                            r["work"] = exp_w if exp_w is not None else 1.0
                            r["_work_full"] = True
                            r["late"] = None
                            r["early"] = None
                            continue
                except Exception:
                    # nếu có lỗi thì rơi về rule mặc định (V/OFF/Lễ)
                    pass

                sym_code: str | None = None
                if bool(is_holiday):
                    # Holiday behavior depends on ignore_absent_holiday.
                    # - 1: show Holiday symbol (C10)
                    # - 0: treat as a normal working day (can become V/OFF)
                    if int(ignore_absent_holiday) == 1:
                        sym_code = "C10"
                    else:
                        sym_code = None

                # Weekend ignore: if enabled, do NOT mark absent even if the day has shifts.
                if sym_code is None:
                    if day_key == "sat" and int(ignore_absent_sat) == 1:
                        sym_code = "C09"
                    elif day_key == "sun" and int(ignore_absent_sun) == 1:
                        sym_code = "C09"

                if sym_code is None:
                    has_shift1 = False
                    try:
                        has_shift1 = (
                            detail_for_day is not None
                            and detail_for_day.get("shift1_id") is not None
                        )
                    except Exception:
                        has_shift1 = False
                    sym_code = "C07" if has_shift1 else "C09"

                sym_text = str(symbols_by_code.get(sym_code or "") or "").strip()
                for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                    r[k] = None
                if sym_text:
                    r["in_1"] = sym_text

                # Khi vắng (V/C07) thì mặc định cộng Giờ+/Công+ để hiển thị.
                # Không ghi đè nếu DB đã có giá trị hours_plus/work_plus.
                if (sym_code or "").strip() == "C07":
                    if r.get("hours_plus") is None:
                        r["hours_plus"] = 8
                    if r.get("work_plus") is None:
                        r["work_plus"] = 1.0
                    if r.get("leave_plus") is None:
                        # KH+ mặc định lấy ký hiệu V (UI sẽ hiển thị thêm '+')
                        r["leave_plus"] = sym_text or "V"

                # hours/work rules:
                # - Holiday (C10): only count work when holiday_count_as_work=1
                # - V/OFF: do not count
                if (sym_code or "").strip() == "C10" and int(holiday_count_as_work) == 1:
                    if expected_minutes > 0:
                        r["hours"] = round(float(expected_minutes) / 60.0, 2)
                    else:
                        r["hours"] = 8
                    r["work"] = expected_work if expected_work is not None else 1.0
                    r["_work_full"] = True
                else:
                    r["hours"] = None
                    r["work"] = None
                    r["_work_full"] = False

                r["late"] = None
                r["early"] = None
                # Skip further shift matching/recompute for this row.
                continue

            # Nếu ngày lễ được khai báo mà có dữ liệu chấm công:
            # - Giữ giờ vào/ra như bình thường
            # - Hiển thị ký hiệu Lễ (C10) ở cột leave (chỉ để hiển thị)
            # - Không ghi đè nếu leave đã có giá trị (ví dụ đã import KH)
            try:
                if bool(is_holiday):
                    holiday_sym2 = str(symbols_by_code.get("C10") or "").strip()
                    if holiday_sym2:
                        cur_leave = r.get("leave")
                        cur_leave_s = (
                            "" if cur_leave is None else str(cur_leave).strip()
                        )
                        if (cur_leave is None) or (cur_leave_s == ""):
                            r["leave"] = holiday_sym2
            except Exception:
                pass

            if mode_norm == "auto":
                if shifts:
                    # Không dùng lại giá trị DB cũ vì có thể đã bị lưu sai.
                    r["shift_code"] = None
                    self._apply_mode_auto_by_shifts(r, shifts=shifts)
                else:
                    self._apply_mode_auto(r)
            elif mode_norm == "first_last":
                if shifts:
                    # Không dùng lại giá trị DB cũ vì có thể đã bị lưu sai.
                    r["shift_code"] = None
                    self._apply_mode_first_last_by_shifts(r, shifts=shifts)
                else:
                    self._apply_mode_first_last(r)
            else:
                # device: giữ nguyên giờ nhưng vẫn tính Ca (HC/Đêm) theo work_shifts nếu có
                if shifts:
                    r["shift_code"] = self._compute_shift_label_from_punches(
                        r, shifts=shifts
                    )

            # Recompute late from displayed in_i + schedule shifts (supports overnight, capped by total_minutes)
            try:
                if shifts:
                    # Ensure slot->shift mapping exists for accurate recompute in all modes.
                    self._ensure_slot_shift_mapping(r, shifts=shifts)
                    # Clear potentially stale DB values; recompute will repopulate when possible.
                    r["late"] = None
                    self._recompute_late_from_displayed_in_values(r, shifts=shifts)
            except Exception:
                logger.exception("Không thể tính lại thời gian trễ (late)")

            # Recompute early from displayed out_i + schedule shifts (supports overnight, capped by total_minutes)
            try:
                if shifts:
                    # Ensure slot->shift mapping exists for accurate recompute in all modes.
                    self._ensure_slot_shift_mapping(r, shifts=shifts)
                    # Clear potentially stale DB values; recompute will repopulate when possible.
                    r["early"] = None
                    self._recompute_early_from_displayed_out_values(r, shifts=shifts)
            except Exception:
                logger.exception("Không thể tính lại thời gian sớm (early)")

            # Nếu thiếu giờ vào/ra (KV/KR) thì không tính giờ/công và không xác định ca.
            # UI sẽ tự hiển thị ký hiệu KV/KR cho ô bị thiếu, nhưng nghiệp vụ không tính công.
            try:
                incomplete_pair = False
                for slot in (1, 2, 3):
                    in_sec = self._time_to_seconds(r.get(f"in_{slot}"))
                    out_sec = self._time_to_seconds(r.get(f"out_{slot}"))

                    # day_is_out_time: cho phép thiếu IN nhưng có OUT.
                    if int(day_is_out_time) == 1:
                        # Nếu có IN mà thiếu OUT => vẫn là lỗi (thiếu giờ ra)
                        if (in_sec is not None) and (out_sec is None):
                            incomplete_pair = True
                            break
                        # Nếu thiếu IN nhưng có OUT => hợp lệ
                        continue

                    # Default: XOR => thiếu cặp
                    if (in_sec is None) != (out_sec is None):
                        incomplete_pair = True
                        break

                if incomplete_pair:
                    r["hours"] = None
                    r["work"] = None
                    r["_work_full"] = False
                    r["late"] = None
                    r["early"] = None
                    r["shift_code"] = None
                    continue
            except Exception:
                # Nếu check lỗi thì không chặn tính công (giữ hành vi cũ)
                pass

            # Compute hours/work (per yêu cầu):
            # - Nếu in_1 là V hoặc OFF -> bỏ qua
            # - Nếu in_1 là Lễ -> hours=total_minutes/60, work=work_count
            # - Còn lại: hours=(total_minutes - late - early)/60,
            #   work = work_count * (actual_minutes / total_minutes) (tỉ lệ, không làm tròn)
            # - Không ghi đè nếu import_locked=1 và đã có hours/work (để tôn trọng dữ liệu import)
            try:
                in1_raw = str(r.get("in_1") or "").strip()
                absent_sym = str(symbols_by_code.get("C07") or "").strip()
                off_sym = str(symbols_by_code.get("C09") or "").strip()
                holiday_sym = str(symbols_by_code.get("C10") or "").strip()

                def _to_minutes(v: object | None) -> int:
                    if v is None:
                        return 0
                    try:
                        # service recompute stores ints, but accept numeric strings
                        return max(0, int(float(str(v).strip())))
                    except Exception:
                        return 0

                if in1_raw and ":" not in in1_raw and in1_raw in {absent_sym, off_sym}:
                    r["hours"] = None
                    r["work"] = None
                    r["_work_full"] = False

                    # Khi in_1 là V (C07) thì mặc định hours_plus/work_plus.
                    if absent_sym and in1_raw == absent_sym:
                        if r.get("hours_plus") is None:
                            r["hours_plus"] = 8
                        if r.get("work_plus") is None:
                            r["work_plus"] = 1.0
                        if r.get("leave_plus") is None:
                            r["leave_plus"] = absent_sym
                elif (
                    in1_raw
                    and ":" not in in1_raw
                    and holiday_sym
                    and in1_raw == holiday_sym
                ):
                    # Holiday symbol explicitly present in in_1: show FULL hours/work.
                    m_minutes, _m_work = _expected_for_row_from_matched_shifts(
                        r, day_shifts=shifts
                    )
                    if int(m_minutes) > 0:
                        r["hours"] = round(float(m_minutes) / 60.0, 2)
                    else:
                        # Holiday with no matched shift: default full-day hours.
                        r["hours"] = 8
                    r["work"] = _m_work if _m_work is not None else 1.0
                    r["_work_full"] = True
                else:
                    try:
                        import_locked = int(r.get("import_locked") or 0)
                    except Exception:
                        import_locked = 0

                    def _worked_minutes_from_pairs(row0: dict[str, Any]) -> int:
                        total_sec = 0
                        for slot in (1, 2, 3):
                            in_sec0 = self._time_to_seconds(row0.get(f"in_{slot}"))
                            out_sec0 = self._time_to_seconds(row0.get(f"out_{slot}"))
                            if in_sec0 is None or out_sec0 is None:
                                continue
                            try:
                                in_eff = int(in_sec0)
                                out_eff = int(out_sec0)
                                if out_eff < in_eff:
                                    out_eff += 86400
                                total_sec += max(0, int(out_eff) - int(in_eff))
                            except Exception:
                                continue
                        return max(0, int(total_sec) // 60)

                    def _use_expected_minus_late_early(row0: dict[str, Any]) -> bool:
                        """Return True when business wants actual = expected - late - early.

                        Applied for:
                        - HÀNH CHÍNH (HC)
                        - THAI SẢN (TS)
                        """

                        try:
                            code_norm = self._norm_text_no_diacritics(row0.get("shift_code"))
                        except Exception:
                            code_norm = ""
                        code_norm = str(code_norm or "").strip().replace("_", "")
                        return code_norm in {"hc", "hanhchinh", "thaisan"}

                    def _out_after_13(row0: dict[str, Any]) -> bool:
                        out_sec0 = self._time_to_seconds(row0.get("out_1"))
                        if out_sec0 is None:
                            return False
                        try:
                            return int(out_sec0) >= 13 * 3600
                        except Exception:
                            return False

                    def _calc_actual_minutes(
                        row0: dict[str, Any],
                        *,
                        expected_minutes0: int,
                        late_minutes0: int,
                        early_minutes0: int,
                    ) -> int:
                        """Business rule:
                        - For HC/THAI SẢN with OUT>=13: actual = expected - late - early
                        - Otherwise: actual = worked minutes from punch pairs (cap by expected)
                        """

                        expected_m = max(0, int(expected_minutes0 or 0))
                        if _use_expected_minus_late_early(row0) and _out_after_13(row0):
                            return max(0, expected_m - int(late_minutes0) - int(early_minutes0))

                        worked_m = _worked_minutes_from_pairs(row0)
                        if expected_m > 0:
                            return min(int(worked_m), int(expected_m))
                        return int(worked_m)

                    if (
                        import_locked == 1
                        and (not bool(overwrite_import_locked_computed))
                        and (r.get("hours") is not None or r.get("work") is not None)
                    ):
                        # Do not override imported values, but still compute the
                        # "full work" flag for UI symbol X.
                        m_minutes, _m_work = _expected_for_row_from_matched_shifts(
                            r, day_shifts=shifts
                        )
                        if int(m_minutes) > 0:
                            late_m = _to_minutes(r.get("late"))
                            early_m = _to_minutes(r.get("early"))
                            actual_minutes = _calc_actual_minutes(
                                r,
                                expected_minutes0=int(m_minutes),
                                late_minutes0=int(late_m),
                                early_minutes0=int(early_m),
                            )
                            r["_work_full"] = bool(
                                int(actual_minutes) >= int(m_minutes)
                            )
                        else:
                            r["_work_full"] = False
                    else:
                        m_minutes, m_work = _expected_for_row_from_matched_shifts(
                            r, day_shifts=shifts
                        )
                        # If cannot determine matched shift(s), don't fall back to
                        # summing all day shifts (can produce 24h/3.5 công).
                        actual_minutes = 0
                        if int(m_minutes) > 0:
                            late_m = _to_minutes(r.get("late"))
                            early_m = _to_minutes(r.get("early"))
                            actual_minutes = _calc_actual_minutes(
                                r,
                                expected_minutes0=int(m_minutes),
                                late_minutes0=int(late_m),
                                early_minutes0=int(early_m),
                            )
                            r["hours"] = round(float(actual_minutes) / 60.0, 2)
                        if m_work is not None and int(m_minutes) > 0:
                            # Proportional work by actual minutes.
                            # Keep full precision (no rounding) for display.
                            try:
                                w = Decimal(str(m_work))
                                ratio = Decimal(int(actual_minutes)) / Decimal(
                                    int(m_minutes)
                                )
                                r["work"] = w * ratio
                            except Exception:
                                try:
                                    r["work"] = float(m_work) * (
                                        float(actual_minutes) / float(m_minutes)
                                    )
                                except Exception:
                                    r["work"] = None
                        r["_work_full"] = bool(
                            int(m_minutes) > 0 and int(actual_minutes) >= int(m_minutes)
                        )

                        # Holiday fallback: if the date is a declared holiday but there is
                        # no schedule/shift defined (shifts empty), still count as full
                        # work = 1 and hours = 8.
                        if bool(is_holiday) and (not shifts):
                            if r.get("work") is None:
                                r["work"] = 1.0
                            if r.get("hours") is None:
                                r["hours"] = 8
                            r["_work_full"] = True
            except Exception:
                logger.exception("Không thể tính hours/work")

        # Post-process: ca Đêm thường có giờ ra nằm ở ngày kế tiếp (buổi sáng).
        # Nếu ngày kế tiếp chỉ có punch buổi sáng (không có punch trong ngày), coi đó là phần dư của ca Đêm hôm trước
        # và không hiển thị ở ngày kế tiếp.
        try:
            _progress(82, "Đang hậu xử lý ca Đêm...")
            merge_count = 0
            by_emp: dict[str, list[dict[str, Any]]] = {}
            for r in rows:
                key = str(
                    r.get("employee_code")
                    or r.get("attendance_code")
                    or r.get("employee_id")
                    or ""
                ).strip()
                if not key:
                    continue
                by_emp.setdefault(key, []).append(r)

            emp_total = max(1, int(len(by_emp)))
            emp_idx = 0

            def _row_date_key(v: object | None) -> str:
                if v is None:
                    return ""
                try:
                    return str(v)
                except Exception:
                    return ""

            def _parse_date(v: object | None) -> _dt.date | None:
                if v is None:
                    return None
                s = str(v).strip()
                if not s:
                    return None
                # Accept 'YYYY-MM-DD' (and datetime-like)
                try:
                    token = s.split()[0].strip()
                except Exception:
                    token = s
                try:
                    if "-" in token:
                        return _dt.date.fromisoformat(token)
                except Exception:
                    pass
                # Accept 'DD/MM/YYYY'
                try:
                    if "/" in token:
                        return _dt.datetime.strptime(token, "%d/%m/%Y").date()
                except Exception:
                    pass
                return None

            def _is_next_day(prev_row: dict[str, Any], cur_row: dict[str, Any]) -> bool:
                d1 = _parse_date(prev_row.get("date") or prev_row.get("work_date"))
                d2 = _parse_date(cur_row.get("date") or cur_row.get("work_date"))
                if d1 is None or d2 is None:
                    return False
                try:
                    return d2 == (d1 + _dt.timedelta(days=1))
                except Exception:
                    return False

            def _row_time_values(row: dict[str, Any]) -> list[object]:
                out: list[object] = []
                for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                    v = row.get(k)
                    if self._time_to_seconds(v) is None:
                        continue
                    out.append(v)
                return out

            MORNING_CUTOFF_SEC = 12 * 3600
            EVENING_CUTOFF_SEC = 18 * 3600
            MERGE_MAX_GAP_SEC = 10 * 60
            # When viewing exactly 1 day, suppress early-morning-only orphan rows (carryover from previous night).
            SINGLE_DAY_ORPHAN_MAX_SEC = 7 * 3600

            def _is_single_day_view() -> bool:
                try:
                    return bool(from_date and to_date and str(from_date) == str(to_date))
                except Exception:
                    return False

            for emp_key, items in by_emp.items():
                emp_idx += 1
                if emp_idx % 5 == 0:
                    pct = 80 + int((emp_idx / emp_total) * 15)
                    _progress(pct, f"Đang hậu xử lý... ({emp_idx}/{len(by_emp)})")
                    if _cancelled():
                        return rows
                items.sort(
                    key=lambda r: (
                        _row_date_key(r.get("date")),
                        int(r.get("id") or 0),
                    )
                )

                # Special case: user filters exactly 1 day.
                # If the day only has early-morning punches, this is very often the OUT of an overnight shift
                # that started the previous day. When filtering one day, we don't have the previous-day row
                # to merge into, so we look back 1 day in DB to confirm and then hide this orphan row.
                try:
                    if _is_single_day_view() and items:
                        first = items[0]
                        first_times = _row_time_values(first)
                        secs_first = [self._time_to_seconds(v) for v in first_times]
                        secs_first2 = [int(s) for s in secs_first if s is not None]
                        if secs_first2:
                            is_morning_only = (
                                max(secs_first2) < int(MORNING_CUTOFF_SEC)
                                and max(secs_first2) <= int(SINGLE_DAY_ORPHAN_MAX_SEC)
                                and (not [s for s in secs_first2 if int(s) >= int(EVENING_CUTOFF_SEC)])
                            )
                            if is_morning_only:
                                # Confirm by checking previous day's punches in DB.
                                prev_day = _parse_date(first.get("date") or first.get("work_date"))
                                if prev_day is None:
                                    try:
                                        prev_day = _dt.date.fromisoformat(str(from_date))
                                    except Exception:
                                        prev_day = None
                                prev_has_evening_db = False
                                if prev_day is not None:
                                    try:
                                        prev_date_str = (prev_day - _dt.timedelta(days=1)).isoformat()
                                        emp_id = first.get("employee_id")
                                        att_code = (
                                            first.get("attendance_code")
                                            or first.get("employee_code")
                                            or ""
                                        )
                                        emp_id_int = int(emp_id) if emp_id is not None else None
                                        att_code_str = str(att_code).strip() or None
                                        prev_rows_db = self._repo.list_rows(
                                            from_date=prev_date_str,
                                            to_date=prev_date_str,
                                            employee_id=emp_id_int,
                                            attendance_code=att_code_str,
                                            employee_ids=None,
                                            attendance_codes=None,
                                            department_id=None,
                                            title_id=None,
                                        )

                                        for pr in prev_rows_db or []:
                                            pr_times = _row_time_values(pr)
                                            pr_secs = [self._time_to_seconds(v) for v in pr_times]
                                            pr_secs2 = [int(s) for s in pr_secs if s is not None]
                                            if [s for s in pr_secs2 if int(s) >= int(EVENING_CUTOFF_SEC)]:
                                                prev_has_evening_db = True
                                                break
                                    except Exception:
                                        prev_has_evening_db = False

                                # Hide when confirmed carryover OR schedule says there is an overnight shift.
                                if prev_has_evening_db or bool(first.get("_has_overnight_shift")):
                                    for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                                        first[k] = None

                                    # Show OFF/V/Lễ like the normal "no-punch" rules.
                                    sym_code: str | None = None
                                    try:
                                        if bool(first.get("_is_holiday")) and int(first.get("_ignore_absent_holiday") or 0) == 1:
                                            sym_code = "C10"
                                    except Exception:
                                        sym_code = None

                                    try:
                                        dk = str(first.get("day_key") or "").strip()
                                    except Exception:
                                        dk = ""

                                    if sym_code is None:
                                        try:
                                            if dk == "sat" and int(first.get("_ignore_absent_sat") or 0) == 1:
                                                sym_code = "C09"
                                            elif dk == "sun" and int(first.get("_ignore_absent_sun") or 0) == 1:
                                                sym_code = "C09"
                                        except Exception:
                                            pass

                                    if sym_code is None:
                                        try:
                                            sym_code = "C07" if bool(first.get("_has_shift1")) else "C09"
                                        except Exception:
                                            sym_code = "C09"

                                    try:
                                        sym_text = str(symbols_by_code.get(sym_code or "") or "").strip()
                                    except Exception:
                                        sym_text = ""
                                    if sym_text:
                                        first["in_1"] = sym_text

                                    first["shift_code"] = None
                                    first["hours"] = None
                                    first["work"] = None
                                    first["late"] = None
                                    first["early"] = None
                                    first["_work_full"] = False
                                    try:
                                        logger.info(
                                            "POST_NIGHT_ORPHAN_HIDE emp=%s date=%s max_sec=%s prev_evening=%s overnight_flag=%s",
                                            str(emp_key),
                                            str(first.get("date") or first.get("work_date") or ""),
                                            int(max(secs_first2)),
                                            bool(prev_has_evening_db),
                                            bool(first.get("_has_overnight_shift")),
                                        )
                                    except Exception:
                                        pass
                except Exception:
                    pass

                for i in range(1, len(items)):
                    prev = items[i - 1]
                    cur = items[i]

                    # Nhận diện ca đêm qua ngày:
                    # - Ưu tiên theo nhãn shift_code (Đêm/Đ),
                    # - Hoặc suy luận theo punch: ngày trước có punch buổi tối (>= 18:00),
                    #   ngày sau chỉ có punch buổi sáng (< 12:00).
                    prev_code_raw = str(prev.get("shift_code") or "").strip()
                    prev_code_norm = self._norm_text_no_diacritics(prev_code_raw)
                    prev_times_all = _row_time_values(prev)
                    prev_secs_all = [self._time_to_seconds(v) for v in prev_times_all]
                    prev_secs2 = [int(s) for s in prev_secs_all if s is not None]
                    prev_has_evening = bool(
                        [s for s in prev_secs2 if int(s) >= int(EVENING_CUTOFF_SEC)]
                    )
                    is_label_night = ("đ" in prev_code_raw.casefold()) or ("dem" in prev_code_norm)

                    if not is_label_night:
                        # Chỉ merge khi thực sự là hai ngày liên tiếp.
                        if not _is_next_day(prev, cur):
                            continue

                    cur_times = _row_time_values(cur)
                    if not cur_times:
                        continue

                    secs = [self._time_to_seconds(v) for v in cur_times]
                    secs2 = [int(s) for s in secs if s is not None]
                    if not secs2:
                        continue

                    # Chỉ xử lý khi toàn bộ punch của ngày kế tiếp đều là buổi sáng.
                    if max(secs2) >= MORNING_CUTOFF_SEC:
                        continue

                    if (not is_label_night) and (not prev_has_evening):
                        continue

                    # Lấy punch buổi sáng muộn nhất để bổ sung cho giờ ra ca Đêm hôm trước (nếu cần).
                    best_time = max(
                        cur_times, key=lambda v: int(self._time_to_seconds(v) or 0)
                    )
                    prev_out = prev.get("out_1")
                    prev_out_sec = self._time_to_seconds(prev_out)
                    best_sec = self._time_to_seconds(best_time)

                    merged = False
                    if best_sec is not None:
                        # Only merge when:
                        # - explicit night label, OR
                        # - previous out exists and the next-day morning punch is very close (noise/duplicate).
                        gap_ok = False
                        try:
                            if prev_out_sec is not None and int(best_sec) >= int(prev_out_sec):
                                gap_ok = (int(best_sec) - int(prev_out_sec)) <= int(MERGE_MAX_GAP_SEC)
                        except Exception:
                            gap_ok = False

                        if is_label_night or gap_ok:
                            if prev_out_sec is None or int(best_sec) > int(prev_out_sec):
                                prev["out_1"] = best_time
                            merged = True

                    if merged:
                        merge_count += 1
                        try:
                            logger.info(
                                "POST_NIGHT_MERGE emp=%s prev_date=%s prev_out=%s best=%s gap_ok=%s label_night=%s",
                                str(emp_key),
                                str(prev.get("date") or prev.get("work_date") or ""),
                                str(prev_out or ""),
                                str(best_time or ""),
                                bool(gap_ok),
                                bool(is_label_night),
                            )
                        except Exception:
                            pass
                        # Clear toàn bộ punch của ngày kế tiếp để tránh hiển thị sai (vd Chủ nhật có 06:xx).
                        for k in ("in_1", "out_1", "in_2", "out_2", "in_3", "out_3"):
                            cur[k] = None
                        cur["shift_code"] = None
            try:
                if merge_count:
                    logger.info("POST_NIGHT_MERGE total=%s", int(merge_count))
            except Exception:
                pass

        except Exception:
            logger.exception("Lỗi post-process ca Đêm qua ngày")

        _progress(96, "Đang cập nhật ca xuống CSDL...")
        if _cancelled():
            return rows

        pending_shift_code_updates: list[tuple[int, str | None, str | None]] = []
        for r in rows:

            def _norm_code2(v: object | None) -> str | None:
                s = str(v or "").strip()
                return s if s else None

            try:
                audit_id = r.get("id")
                if audit_id is None:
                    continue
                aid = int(audit_id)
                stored_code = stored_code_by_audit_id.get(aid)
                computed_code = _norm_code2(r.get("shift_code"))
                if computed_code != stored_code:
                    pending_shift_code_updates.append(
                        (aid, str(r.get("date") or r.get("work_date") or ""), computed_code)
                    )
            except Exception:
                pass

        # Batch write shift_code xuống DB (không throw để tránh crash UI)
        if pending_shift_code_updates:
            try:
                self._repo.update_shift_codes(pending_shift_code_updates)
            except Exception:
                logger.exception("Không thể cập nhật shift_code vào attendance_audit")
        _progress(100, "Hoàn tất")
        return rows
