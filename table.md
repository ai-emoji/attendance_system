# Hướng dẫn tạo bảng (wxPython Grid)

Tài liệu này hướng dẫn cách chạy và cách tạo bảng trong dự án hiện tại (`main.py`).

## 1) Yêu cầu

- Windows
- Python 3.11+ (khuyên dùng)
- Virtual environment (venv)
- Thư viện: `wxPython`

## 2) Cài đặt môi trường

### Cách 1: Dùng venv trong workspace (khuyên dùng)

Mở PowerShell tại thư mục dự án và chạy:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install wxPython
```

> Lưu ý: `wxPython` có thể cài khá lâu tuỳ máy.

### Cách 2: Nếu bạn đã có sẵn venv

Chỉ cần đảm bảo bạn chạy bằng Python trong `.venv`:

```powershell
& ".\.venv\Scripts\python.exe" ".\main.py"
```

## 3) Cách chạy để hiện cửa sổ

### Chạy bằng venv (đúng nhất)

```powershell
& ".\.venv\Scripts\python.exe" ".\main.py"
```

### Chạy bằng `python main.py`

Trong `main.py` có cơ chế tự kiểm tra:

- Nếu `python` bạn đang dùng KHÔNG có `wxPython` nhưng trong project có `.venv`, chương trình sẽ tự chạy lại bằng `.venv`.

## 4) Bảng được tạo như thế nào

Trong `main.py`, bảng được dựng bằng **một widget duy nhất**: `wx.grid.Grid`.

### Các bước chính

1. Tạo app + frame

   - `app = wx.App()`
   - `frame = wx.Frame(None, title="Bảng thông tin")`
   - Set size cửa sổ = 50% màn hình và căn giữa.

2. Tạo grid

   - `grid = wx.grid.Grid(panel)`
   - `grid.CreateGrid(row_count, col_count)`

3. Cấu hình hiển thị

   - Tắt sửa dữ liệu: `grid.EnableEditing(False)`
   - Ẩn nhãn dòng (row label): `grid.SetRowLabelSize(0)`
   - Chọn theo dòng: `grid.SetSelectionMode(wx.grid.Grid.GridSelectRows)`

4. Căn giữa chữ (cells + header)

   - `grid.SetDefaultCellAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)`
   - `grid.SetColLabelAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)`

5. Set kích thước

   - Chiều cao dòng: `grid.SetDefaultRowSize(30, True)`
   - Chiều rộng cột: `grid.SetColSize(col, 140)`

6. Kẻ đường viền / ngăn cách row rõ ràng

   - Bật grid lines: `grid.EnableGridLines(True)`
   - Set màu đường kẻ: `grid.SetGridLineColour(...)`

7. Tô màu xen kẽ (zebra rows)

   - Dòng chẵn/lẻ có background khác nhau để dễ đọc.

8. Khóa (freeze) 3 cột đầu
   - Dùng `grid.FreezeTo(0, 3)` để cố định 3 cột đầu (cột 0–2).
   - Việc freeze được gọi sau khi cửa sổ `Show()` bằng `wx.CallAfter(...)` để đảm bảo ổn định.

## 5) Kiểm tra nhanh freeze có hoạt động

Khi chạy, chương trình sẽ in ra terminal:

- `Frozen cols: 3 | Frozen rows: 0`

Và trong UI:

- Kéo thanh cuộn ngang sang phải: 3 cột đầu phải đứng yên.

## 6) Troubleshooting

- Nếu chạy `python main.py` bị lỗi `No module named 'wx'`:
  - Hãy chạy bằng venv: `& ".\.venv\Scripts\python.exe" ".\main.py"`
- Nếu không thấy cửa sổ:
  - Chạy lại từ PowerShell (không dùng terminal bị giới hạn GUI), hoặc đảm bảo bạn đang ở desktop session bình thường.

## 7) Bảng mẫu đơn giản (Markdown)

Dưới đây là một bảng Markdown đơn giản để bạn copy dùng nhanh:

| STT | Họ và tên       | Phòng ban | Vai trò    | Trạng thái |
| --- | -------------- | -------- | ---------- | --------- |
| 1   | Nguyễn Văn A    | Kế toán   | Nhân viên  | Đang làm   |
| 2   | Trần Thị B      | Kinh doanh| Trưởng nhóm| Đang làm   |
| 3   | Lê Văn C        | IT       | Thực tập   | Tạm nghỉ   |

## 8) Hướng dẫn tạo Filter (giống Excel, KHÔNG dùng icon)

Trong `employee_widgets.py`, filter được làm theo hướng **giống Excel** nhưng giữ UI tối giản và **không phụ thuộc icon**.

### Cách dùng (trong UI)

1. Click vào **tiêu đề cột** (header) để mở cửa sổ filter.
2. Trong cửa sổ filter bạn có thể:
   - **Sắp xếp tăng dần / giảm dần** theo cột đang chọn.
   - **Tìm kiếm** để lọc danh sách giá trị.
   - Tick/bỏ tick nhiều giá trị (multi-select).
   - **(Chọn tất cả)** để bật/tắt nhanh.
   - **Xoá bộ lọc** để trả cột về trạng thái không lọc.
3. Bấm **Đồng ý** để áp dụng, **Hủy** để huỷ.

### Quy tắc hoạt động

- Filter áp dụng đồng thời nhiều cột theo kiểu **AND** (dòng phải thoả tất cả các cột đang lọc).
- Nếu chọn **tất cả giá trị** của một cột thì coi như **không lọc** cột đó.
- Nếu **bỏ chọn hết** giá trị của một cột thì kết quả sẽ **0 dòng** (giống Excel).

### Điểm chính trong code

- Sự kiện mở filter: click header cột qua `wx.grid.EVT_GRID_LABEL_LEFT_CLICK`.
- Filter được lưu theo từng cột và áp dụng lại để render bảng.
- Sắp xếp: thao tác trực tiếp trên dữ liệu nguồn rồi áp dụng lại filter.
