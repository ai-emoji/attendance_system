    -- =============================================================
    -- MyApp - Database Schema (MySQL)
    -- Engine: InnoDB | Charset: utf8mb4
    -- Lưu ý: chạy trong database đã cấu hình (Database.CONFIG["database"]).
    -- =============================================================

    -- =========================
    -- Danh mục / Khai báo chung
    -- =========================

    CREATE TABLE IF NOT EXISTS company (
        id INT NOT NULL PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        company_address VARCHAR(255) NULL,
        company_phone VARCHAR(50) NULL,
        company_logo LONGBLOB NULL,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Chức danh
    CREATE TABLE IF NOT EXISTS job_titles (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        title_name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_job_titles_title_name (title_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Phòng ban
    -- Quy ước: tên phòng ban không được trùng ở mọi cấp (unique toàn hệ thống)
    CREATE TABLE IF NOT EXISTS departments (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        parent_id INT NULL,
        department_name VARCHAR(255) NOT NULL,
        department_note TEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_departments_department_name (department_name),
        KEY idx_departments_parent_id (parent_id),
        CONSTRAINT fk_departments_parent
            FOREIGN KEY (parent_id)
            REFERENCES departments (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Thông tin Nhân viên
    -- Quy ước:
    -- - employee_code: Mã NV (unique)
    -- - Liên kết phòng ban/chức danh bằng FK (SET NULL khi xóa)
    -- - Các cột ngày dùng kiểu DATE
    CREATE TABLE IF NOT EXISTS employees (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        sort_order INT NULL,
        employee_code VARCHAR(50) NOT NULL,
        mcc_code VARCHAR(50) NULL,
        full_name VARCHAR(255) NOT NULL,
        name_on_mcc VARCHAR(255) NULL,
        start_date DATE NULL,
        title_id INT NULL,
        department_id INT NULL,
        date_of_birth DATE NULL,
        gender VARCHAR(20) NULL,
        national_id VARCHAR(50) NULL,
        id_issue_date DATE NULL,
        id_issue_place VARCHAR(255) NULL,
        address VARCHAR(255) NULL,
        phone VARCHAR(50) NULL,
        insurance_no VARCHAR(50) NULL,
        tax_code VARCHAR(50) NULL,
        degree VARCHAR(255) NULL,
        major VARCHAR(255) NULL,
        contract1_signed TINYINT(1) NOT NULL DEFAULT 0,
        contract1_term VARCHAR(50) NULL,
        contract1_no VARCHAR(100) NULL,
        contract1_sign_date DATE NULL,
        contract1_expire_date DATE NULL,
        contract2_indefinite TINYINT(1) NOT NULL DEFAULT 0,
        contract2_no VARCHAR(100) NULL,
        contract2_sign_date DATE NULL,
        children_count INT NULL,
        child_dob_1 DATE NULL,
        child_dob_2 DATE NULL,
        child_dob_3 DATE NULL,
        child_dob_4 DATE NULL,
        employment_status VARCHAR(20) NULL,
        note TEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_employees_employee_code (employee_code),
        KEY idx_employees_department_id (department_id),
        KEY idx_employees_title_id (title_id),
        CONSTRAINT fk_employees_department
            FOREIGN KEY (department_id)
            REFERENCES departments (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_employees_title
            FOREIGN KEY (title_id)
            REFERENCES job_titles (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Ngày lễ
    -- Quy ước: cho phép trùng ngày nếu khác thông tin; chỉ chặn trùng hoàn toàn (date + info)
    CREATE TABLE IF NOT EXISTS holidays (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        holiday_date DATE NOT NULL,
        holiday_info VARCHAR(255) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Máy chấm công
    CREATE TABLE IF NOT EXISTS devices (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        device_no INT NOT NULL,
        device_name VARCHAR(255) NOT NULL,
        ip_address VARCHAR(50) NOT NULL,
        password VARCHAR(50) NULL,
        port INT NOT NULL DEFAULT 4370,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_devices_ip_address (ip_address),
        KEY idx_devices_device_no (device_no)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- =========================
    -- Nghiệp vụ Chấm công
    -- =========================


    -- =========================
    -- Tải dữ liệu chấm công (tạm) + lưu thô
    -- =========================

    -- attendance_raw: lưu dữ liệu chấm công thô (lưu lâu dài)
    -- Quy ước:
    -- - attendance_code: mã chấm công (user_id trên máy)
    -- - work_date: ngày chấm công
    -- - time_in/out_1..3: tối đa 3 cặp vào/ra trong ngày
    -- - device_no: snapshot số máy (để làm unique và tránh clone)
    -- - ON DUPLICATE KEY UPDATE sẽ ghi đè nếu trùng key
    CREATE TABLE IF NOT EXISTS attendance_raw (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        attendance_code VARCHAR(50) NOT NULL,
        work_date DATE NOT NULL,
        time_in_1 TIME NULL,
        time_out_1 TIME NULL,
        time_in_2 TIME NULL,
        time_out_2 TIME NULL,
        time_in_3 TIME NULL,
        time_out_3 TIME NULL,
        device_no INT NOT NULL,
        device_id INT NULL,
        device_name VARCHAR(255) NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_attendance_raw_code_date_device (attendance_code, work_date, device_no),
        KEY idx_attendance_raw_work_date (work_date),
        KEY idx_attendance_raw_device_no (device_no),
        CONSTRAINT fk_attendance_raw_device
            FOREIGN KEY (device_id)
            REFERENCES devices (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- download_attendance: bảng tạm cho lần tải hiện tại (sẽ xóa khi đóng phần mềm)
    -- Ghi chú:
    -- - Schema tương tự attendance_raw
    -- - Upsert để ghi đè nếu trùng
    CREATE TABLE IF NOT EXISTS download_attendance (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        attendance_code VARCHAR(50) NOT NULL,
        work_date DATE NOT NULL,
        time_in_1 TIME NULL,
        time_out_1 TIME NULL,
        time_in_2 TIME NULL,
        time_out_2 TIME NULL,
        time_in_3 TIME NULL,
        time_out_3 TIME NULL,
        device_no INT NOT NULL,
        device_id INT NULL,
        device_name VARCHAR(255) NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_download_attendance_code_date_device (attendance_code, work_date, device_no),
        KEY idx_download_attendance_work_date (work_date),
        KEY idx_download_attendance_device_no (device_no),
        CONSTRAINT fk_download_attendance_device
            FOREIGN KEY (device_id)
            REFERENCES devices (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Ca làm việc
    -- Quy ước:
    -- - shift_code: mã ca (unique)
    -- - Các cột giờ dùng kiểu TIME
    -- - total_minutes: tổng phút
    -- - work_count: số công (ví dụ 1.0, 0.5)
    CREATE TABLE IF NOT EXISTS work_shifts (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        shift_code VARCHAR(50) NOT NULL,
        time_in TIME NOT NULL,
        time_out TIME NOT NULL,
        lunch_start TIME NULL,
        lunch_end TIME NULL,
        total_minutes INT NULL,
        work_count DECIMAL(6,2) NULL,
        in_window_start TIME NULL,
        in_window_end TIME NULL,
        out_window_start TIME NULL,
        out_window_end TIME NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_work_shifts_shift_code (shift_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Ký hiệu Chấm công
    -- Quy ước:
    -- - Lưu theo dạng nhiều dòng (giống absence_symbols)
    -- - code cố định C01..C09
    -- - description: mô tả
    -- - symbol: ký hiệu
    -- - is_visible: checkbox "Hiện"
    CREATE TABLE IF NOT EXISTS attendance_symbols (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(3) NOT NULL,
        description VARCHAR(255) NULL,
        symbol VARCHAR(50) NULL,
        is_visible TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_attendance_symbols_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    -- Seed: C01..C09 (nếu chưa có)
    INSERT INTO attendance_symbols (code, description, symbol, is_visible) VALUES
    ('C01', 'Ký hiệu đi trễ', '', 1),
    ('C02', 'Ký hiệu về sớm', '', 1),
    ('C03', 'Ký hiệu đúng giờ', '', 1),
    ('C04', 'Ký hiệu tăng ca', '', 1),
    ('C05', 'Ký hiệu thiếu giờ ra', '', 1),
    ('C06', 'Ký hiệu thiếu giờ vào', '', 1),
    ('C07', 'Ký hiệu vắng (mặc định không chấm công)', '', 1),
    ('C08', 'Ký hiệu đúng giờ ca có qua đêm', '', 1),
    ('C09', 'Ký hiệu ngày không xếp ca', '', 1)
    ON DUPLICATE KEY UPDATE code = code;


    -- Ký hiệu Vắng
    -- Quy ước:
    -- - Hiển thị cố định A01..A15
    -- - description: mô tả
    -- - symbol: ký hiệu
    -- - is_used: sử dụng
    -- - is_paid: tính công
    CREATE TABLE IF NOT EXISTS absence_symbols (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(3) NOT NULL,
        description VARCHAR(255) NULL,
        symbol VARCHAR(50) NULL,
        is_used TINYINT(1) NOT NULL DEFAULT 0,
        is_paid TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_absence_symbols_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    -- Seed: A01..A15 (nếu chưa có)
    INSERT INTO absence_symbols (code, description, symbol, is_used, is_paid) VALUES
    ('A01', '', '', 0, 0),
    ('A02', '', '', 0, 0),
    ('A03', '', '', 0, 0),
    ('A04', '', '', 0, 0),
    ('A05', '', '', 0, 0),
    ('A06', '', '', 0, 0),
    ('A07', '', '', 0, 0),
    ('A08', '', '', 0, 0),
    ('A09', '', '', 0, 0),
    ('A10', '', '', 0, 0),
    ('A11', '', '', 0, 0),
    ('A12', '', '', 0, 0),
    ('A13', '', '', 0, 0),
    ('A14', '', '', 0, 0),
    ('A15', '', '', 0, 0)
    ON DUPLICATE KEY UPDATE code = code;


    -- Chọn ngày Cuối tuần
    -- Quy ước:
    -- - Hiển thị cố định Thứ 2..Chủ nhật
    -- - is_weekend: checkbox "Cuối tuần"
    CREATE TABLE IF NOT EXISTS weekend_settings (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        day_name VARCHAR(20) NOT NULL,
        is_weekend TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_weekend_settings_day_name (day_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    -- Seed: Thứ 2..Chủ nhật (nếu chưa có)
    INSERT INTO weekend_settings (day_name, is_weekend) VALUES
    ('Thứ 2', 0),
    ('Thứ 3', 0),
    ('Thứ 4', 0),
    ('Thứ 5', 0),
    ('Thứ 6', 0),
    ('Thứ 7', 1),
    ('Chủ nhật', 1)
    ON DUPLICATE KEY UPDATE day_name = day_name;

    -- =========================
    -- Ghi chú migrate thủ công
    -- =========================
    -- Nếu bạn đang dùng bản cũ (attendance_symbols dạng 1 dòng nhiều cột), cần migrate thủ công:
    -- 1) Đổi tên bảng cũ để backup: RENAME TABLE attendance_symbols TO attendance_symbols_old;
    -- 2) Chạy lại đoạn CREATE + INSERT attendance_symbols (mới) bên trên.
    -- 3) Nếu cần, copy dữ liệu từ bảng cũ sang bảng mới theo mapping code.
    -- Nếu bảng holidays đã tồn tại với unique theo holiday_date, chạy thủ công:
    -- ALTER TABLE holidays DROP INDEX uq_holidays_holiday_date;
    -- ALTER TABLE holidays ADD UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info);
