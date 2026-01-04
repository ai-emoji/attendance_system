# Recipe – Cách “tính/chuẩn hoá hiển thị” trong `ui/widgets/shift_attendance_widgets.py`

> Ghi chú quan trọng: `shift_attendance_widgets.py` là file dựng UI (widget + signal) và **không tính nghiệp vụ chấm công** (ví dụ: Trễ/Sớm/Giờ/Công/TC1-3/Tổng). File này chủ yếu **chuẩn hoá định dạng** (ngày/giờ), hiển thị tổng số dòng, và áp dụng UI settings (ẩn/hiện cột, canh lề, in đậm…).

---

## 1) Chuẩn hoá hiển thị ngày `dd/MM/yyyy`

### Hàm: `_fmt_date_ddmmyyyy(value)`

**Mục tiêu**: mọi giá trị ngày đưa lên bảng hiển thị theo định dạng `dd/MM/yyyy`.

**Input có thể gặp**:
- `None`
- `QDate`
- `datetime.date` / `datetime.datetime`
- chuỗi: `dd/MM/yyyy`, `yyyy-mm-dd`, `dd-mm-yyyy`, hoặc chuỗi có kèm thời gian (`2026-01-04 08:00:00`)

**Luồng xử lý**:
1. Nếu `value is None` → trả về chuỗi rỗng.
2. Nếu là `QDate` → `toString("dd/MM/yyyy")`.
3. Nếu là `date/datetime` → `strftime("%d/%m/%Y")`.
4. Nếu là chuỗi:
   - Nếu đã giống `dd/MM/yyyy` → lấy 10 ký tự đầu.
   - Tách token trước dấu cách (bỏ phần giờ), chuẩn hoá `/` thành `-`.
   - Nếu token là `yyyy-mm-dd` → parse thành `date(yyyy, mm, dd)` rồi format lại.
   - Nếu token là `dd-mm-yyyy` → parse thành `date(yyyy, mm, dd)` rồi format lại.
   - Nếu không parse được → trả về chuỗi gốc.

**Nơi được áp dụng**:
- Cột `start_date` (MainContent1) và cột `date` (MainContent2) khi áp UI settings/refresh item.
- Ưu tiên lấy dữ liệu gốc từ `Qt.ItemDataRole.UserRole`; nếu không có thì lấy `item.text()`.

---

## 2) Hiển thị checkbox dạng emoji ✅ / ❌

### Hàm: `_apply_check_item_style(item, checked)`

**Mục tiêu**: cột chọn dòng hiển thị rõ ràng và nhất quán.

**Luồng xử lý**:
- Canh giữa text.
- Nếu `checked=True`:
  - chữ màu sáng (trắng)
  - nền màu primary.
- Nếu `checked=False`:
  - chữ màu sáng (trắng)
  - nền màu save.

### Toggle khi click

Trong `MainContent2._on_cell_clicked(row, col)`:
- Chỉ xử lý khi click đúng cột `0`.
- Đọc text hiện tại:
  - nếu khác `✅` → set `✅`
  - nếu đang `✅` → set `❌`
- Sau đó gọi `_apply_check_item_style` để đổi màu.

---

## 3) Chuẩn hoá hiển thị giờ `HH:MM` hoặc `HH:MM:SS`

### Trạng thái: `MainContent2._show_seconds`

- Mặc định `True` (hiển thị `HH:MM:SS`).
- Người dùng chuyển chế độ bằng 2 nút:
  - `HH:MM`
  - `HH:MM:SS`

Khi đổi chế độ:
- Đồng bộ nút check (blockSignals để tránh phát sự kiện vòng lặp).
- Gọi `set_time_show_seconds(show_seconds)`.
- Lưu state (debounce 200ms) vào UI state: `content2.show_seconds`.

### Hàm: `MainContent2._format_time_value(value)`

**Mục tiêu**: đưa các giá trị giờ về dạng chuẩn `HH:MM` hoặc `HH:MM:SS`.

**Input có thể gặp**:
- `None` / rỗng
- chuỗi giờ: `8:3`, `08:03`, `08:03:02`, `08:03:02.000000`
- chuỗi datetime có khoảng trắng: `2026-01-04 08:03:02`
- nhãn không phải giờ: `Nghỉ Lễ`, `OFF`, `V`…

**Luồng xử lý**:
1. `None` hoặc rỗng → trả `""`.
2. Nếu chuỗi **không chứa `:`** → coi là nhãn, trả về nguyên văn.
3. Nếu có `:` và có khoảng trắng → lấy token cuối (thường là phần `HH:MM:SS`).
4. Bỏ các dấu `:` thừa ở cuối (ví dụ `08:00:` → `08:00`).
5. Tách theo `:` và parse số:
   - ưu tiên `int(p)`
   - fallback `int(float(p))` để xử lý kiểu `"00.000000"`.
6. Format:
   - nếu `_show_seconds=True` → `HH:MM:SS`.
   - nếu `_show_seconds=False` → `HH:MM`.

### Công thức chuẩn hoá giờ ra/vào (chi tiết)

Áp dụng cho các cột giờ: `in_1/out_1/in_2/out_2/in_3/out_3` thông qua `set_time_show_seconds()`.

**Quy tắc nhận diện**
- Nếu giá trị không có dấu `:` → **không coi là giờ**, hiển thị nguyên văn (VD: `OFF`, `Nghỉ Lễ`, `V`).
- Nếu có dấu `:` → coi là dữ liệu giờ, tiến hành chuẩn hoá.

**Ưu tiên nguồn dữ liệu (để không mất dữ liệu gốc)**
- Lấy `raw = item.data(Qt.ItemDataRole.UserRole)`.
- Nếu `raw` rỗng → fallback `raw = item.text()`.

**Pseudo-code (theo đúng logic trong UI)**

```text
normalize_time(raw, show_seconds):
  s = str(raw).strip()      # raw None -> ""
  if s == "": return ""

  if ":" not in s:
    return s                # label không phải giờ

  if " " in s:
    s = last_token(s)       # ví dụ: "2026-01-04 08:03:02" -> "08:03:02"

  while s endswith ":":
    s = s without last char # ví dụ: "08:00:" -> "08:00"

  parts = split(s, ":") and remove empty parts
  if len(parts) < 2: return s

  hh = to_int(parts[0])
  mm = to_int(parts[1])
  ss = to_int(first_2_chars(parts[2])) if len(parts) >= 3 else 0

  if show_seconds:
    return format("%02d:%02d:%02d", hh, mm, ss)
  else:
    return format("%02d:%02d", hh, mm)

to_int(p):
  try int(p)
  else try int(float(p))    # xử lý "00.000000"
  else 0
```

**Ví dụ chuẩn hoá**

- Input `None` → Output `""`
- Input `""` → Output `""`
- Input `"OFF"` → Output `"OFF"` (không có `:`)
- Input `"8:3"` →
  - mode `HH:MM` → `"08:03"`
  - mode `HH:MM:SS` → `"08:03:00"`
- Input `"08:03:02"` →
  - mode `HH:MM` → `"08:03"`
  - mode `HH:MM:SS` → `"08:03:02"`
- Input `"2026-01-04 08:03:02"` →
  - mode `HH:MM` → `"08:03"`
  - mode `HH:MM:SS` → `"08:03:02"`
- Input `"08:03:02.000000"` →
  - mode `HH:MM` → `"08:03"`
  - mode `HH:MM:SS` → `"08:03:02"`
- Input `"08:00:"` →
  - mode `HH:MM` → `"08:00"`
  - mode `HH:MM:SS` → `"08:00:00"`

### Hàm: `MainContent2.set_time_show_seconds(show_seconds)`

**Mục tiêu**: cập nhật toàn bộ các ô giờ đang hiển thị theo mode mới.

**Các cột giờ bị ảnh hưởng**:
- `in_1`, `out_1`, `in_2`, `out_2`, `in_3`, `out_3`

**Luồng xử lý**:
- Set `_show_seconds`.
- Dò index cột theo key bằng `_col_index(key)`.
- Với từng item trong các cột trên:
  - ưu tiên lấy raw từ `Qt.ItemDataRole.UserRole`
  - nếu không có thì lấy `item.text()`
  - set lại text = `_format_time_value(raw)`.

---

## 4) “Tổng” ở MainContent1 chỉ là hiển thị

### Hàm: `MainContent1.set_total(total)`

- Không tính toán.
- Chỉ set label: `"Tổng: {total}"`.

**Nghĩa là** controller/service phải tự đếm tổng rồi gọi hàm này.

---

## 5) Áp UI settings ảnh hưởng “cách hiển thị”

### Hàm: `MainContent2.apply_ui_settings()` (và tương tự ở MainContent1)

Các bước chính:
- Set font body/header theo `ui.font_size`, `ui.font_weight`, `ui.header_font_size`, `ui.header_font_weight`.
- Ẩn/hiện cột theo `ui.column_visible`.
  - Cột cố định (`__check`, `stt`) luôn visible.
  - Cơ chế safety: không cho phép ẩn tất cả cột.
- Canh lề theo `ui.column_align` (left/center/right).
- In đậm theo `ui.column_bold` (override theo từng cột) hoặc theo font_weight mặc định.
- Chuẩn hoá hiển thị:
  - Cột ngày (`date`/`start_date`) → `_fmt_date_ddmmyyyy(raw)`
  - Cột check (`__check`) → `_apply_check_item_style(...)`

---

## 6) Cột “Giờ/Công/TC/Tổng” (nghiệp vụ) được tính ở đâu?

Trong `shift_attendance_widgets.py` chỉ có **key cột** và **hiển thị**, ví dụ:
- `late`, `early`, `hours`, `work`, `tc1`, `tc2`, `tc3`, `total`

Công thức nghiệp vụ (ví dụ: cách tính Trễ/Sớm, quy đổi Giờ → Công, cộng TC, làm tròn…) **không nằm trong file UI này**.

Gợi ý chỗ thường nằm:
- lớp controller của màn Shift Attendance
- `services/shift_attendance_services.py` hoặc các service/repository liên quan (tuỳ kiến trúc hiện tại).
