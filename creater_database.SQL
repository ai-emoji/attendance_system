    -- =============================================================
    -- MyApp - Database Schema (MySQL)
    -- Engine: InnoDB | Charset: utf8mb4
    -- Lưu ý: chạy trong database đã cấu hình (Database.CONFIG["database"]).
    -- =============================================================

     /* =========================
         Khởi tạo database (cài mới)
         - Nếu user MySQL không có quyền CREATE/DROP DATABASE, hãy tạo DB thủ công trong phpMyAdmin.
         - Khối DROP TABLE bên dưới sẽ xóa dữ liệu hiện có trong database hr_attendance.
         ========================= */

     CREATE DATABASE IF NOT EXISTS hr_attendance
     CHARACTER SET utf8mb4
     COLLATE utf8mb4_unicode_ci;

     USE hr_attendance;

     -- Đảm bảo import tiếng Việt đúng encoding (phpMyAdmin/MySQL client)
     SET NAMES utf8mb4;

     -- Dọn sạch các lần import dở trước đó
     SET FOREIGN_KEY_CHECKS = 0;

     DROP TABLE IF EXISTS hr_attendance.download_attendance;
     DROP TABLE IF EXISTS hr_attendance.attendance_raw;
     DROP TABLE IF EXISTS hr_attendance.employees;
     DROP TABLE IF EXISTS hr_attendance.departments;
     DROP TABLE IF EXISTS hr_attendance.job_titles;
     DROP TABLE IF EXISTS hr_attendance.devices;
     DROP TABLE IF EXISTS hr_attendance.holidays;
     DROP TABLE IF EXISTS hr_attendance.work_shifts;
     DROP TABLE IF EXISTS hr_attendance.company;

     DROP TABLE IF EXISTS hr_attendance.attendance_symbols;
     DROP TABLE IF EXISTS hr_attendance.absence_symbols;
     DROP TABLE IF EXISTS hr_attendance.weekend_settings;

     SET FOREIGN_KEY_CHECKS = 1;


    -- =========================
    -- Danh mục / Khai báo chung
    -- =========================

    CREATE TABLE IF NOT EXISTS hr_attendance.company (
        id INT NOT NULL PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        company_address VARCHAR(255) NULL,
        company_phone VARCHAR(50) NULL,
        company_logo LONGBLOB NULL,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Chức danh
    CREATE TABLE IF NOT EXISTS hr_attendance.job_titles (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        title_name VARCHAR(255) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_job_titles_title_name (title_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Phòng ban
    -- Quy ước: tên phòng ban không được trùng ở mọi cấp (unique toàn hệ thống)
    CREATE TABLE IF NOT EXISTS hr_attendance.departments (
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
            REFERENCES hr_attendance.departments (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Thông tin Nhân viên
    -- Quy ước:
    -- - employee_code: Mã NV (unique)
    -- - Liên kết phòng ban/chức danh bằng FK (SET NULL khi xóa)
    -- - Các cột ngày dùng kiểu DATE
    CREATE TABLE IF NOT EXISTS hr_attendance.employees (
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
            REFERENCES hr_attendance.departments (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_employees_title
            FOREIGN KEY (title_id)
            REFERENCES hr_attendance.job_titles (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Ngày lễ
    -- Quy ước: cho phép trùng ngày nếu khác thông tin; chỉ chặn trùng hoàn toàn (date + info)
    CREATE TABLE IF NOT EXISTS hr_attendance.holidays (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        holiday_date DATE NOT NULL,
        holiday_info VARCHAR(255) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Máy chấm công
    CREATE TABLE IF NOT EXISTS hr_attendance.devices (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        device_no INT NOT NULL,
        device_name VARCHAR(255) NOT NULL,
        -- Loại máy để chọn đúng module/driver (không phụ thuộc tên)
        -- Giá trị khuyến nghị: 'SENSEFACE_A4' hoặc 'X629ID'
        device_type VARCHAR(30) NULL,
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
    CREATE TABLE IF NOT EXISTS hr_attendance.attendance_raw (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        attendance_code VARCHAR(50) NOT NULL COMMENT 'Employee attendance code',
        work_date DATE NOT NULL,

        time_in_1 TIME NULL,
        time_out_1 TIME NULL,
        time_in_2 TIME NULL,
        time_out_2 TIME NULL,
        time_in_3 TIME NULL,
        time_out_3 TIME NULL,

        device_no INT NOT NULL COMMENT 'Device number from machine',
        device_id INT NULL COMMENT 'FK to devices table',

        device_name VARCHAR(255) NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_attendance_raw_code_date_device (attendance_code, work_date, device_no),
        KEY idx_attendance_raw_code_date (attendance_code, work_date),
        KEY idx_attendance_raw_work_date (work_date),
        KEY idx_attendance_raw_device_no (device_no),

        CONSTRAINT fk_attendance_raw_device
            FOREIGN KEY (device_id)
            REFERENCES hr_attendance.devices (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- download_attendance: bảng tạm cho lần tải hiện tại (sẽ xóa khi đóng phần mềm)
    -- Ghi chú:
    -- - Schema tương tự attendance_raw
    -- - Upsert để ghi đè nếu trùng
    CREATE TABLE IF NOT EXISTS hr_attendance.download_attendance (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        attendance_code VARCHAR(50) NOT NULL COMMENT 'Employee attendance code',
        work_date DATE NOT NULL,

        time_in_1 TIME NULL,
        time_out_1 TIME NULL,
        time_in_2 TIME NULL,
        time_out_2 TIME NULL,
        time_in_3 TIME NULL,
        time_out_3 TIME NULL,

        device_no INT NOT NULL COMMENT 'Device number from machine',
        device_id INT NULL COMMENT 'FK to devices table',

        device_name VARCHAR(255) NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_download_attendance_code_date_device (attendance_code, work_date, device_no),
        KEY idx_download_attendance_code_date (attendance_code, work_date),
        KEY idx_download_attendance_work_date (work_date),
        KEY idx_download_attendance_device_no (device_no),

        CONSTRAINT fk_download_attendance_device
            FOREIGN KEY (device_id)
            REFERENCES hr_attendance.devices (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Khai báo Ca làm việc
    -- Quy ước:
    -- - shift_code: mã ca (unique)
    -- - Các cột giờ dùng kiểu TIME
    -- - total_minutes: tổng phút
    -- - work_count: số công (ví dụ 1.0, 0.5)
    CREATE TABLE IF NOT EXISTS hr_attendance.work_shifts (
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
    -- Lưu ý: các dòng DROP TABLE bên dưới chỉ nên dùng khi cài mới
    -- hoặc khi gặp lỗi #1932 (table doesn't exist in engine). Nếu DB đang có dữ liệu,
    -- hãy xóa/disable các dòng DROP TABLE.
    DROP TABLE IF EXISTS hr_attendance.attendance_symbols;

    CREATE TABLE hr_attendance.attendance_symbols (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(3) NOT NULL,
        description VARCHAR(255) NULL,
        symbol VARCHAR(50) NULL,
        is_visible TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_attendance_symbols_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    /* Seed: C01..C09 (nếu chưa có) */
    INSERT INTO hr_attendance.attendance_symbols (code, description, symbol, is_visible)
    SELECT v.code, v.description, v.symbol, v.is_visible
    FROM (
        SELECT 'C01' AS code, 'Ký hiệu đi trễ' AS description, '' AS symbol, 1 AS is_visible
        UNION ALL SELECT 'C02', 'Ký hiệu về sớm', '', 1
        UNION ALL SELECT 'C03', 'Ký hiệu đúng giờ', '', 1
        UNION ALL SELECT 'C04', 'Ký hiệu tăng ca', '', 1
        UNION ALL SELECT 'C05', 'Ký hiệu thiếu giờ ra', '', 1
        UNION ALL SELECT 'C06', 'Ký hiệu thiếu giờ vào', '', 1
        UNION ALL SELECT 'C07', 'Ký hiệu vắng (mặc định không chấm công)', '', 1
        UNION ALL SELECT 'C08', 'Ký hiệu đúng giờ ca có qua đêm', '', 1
        UNION ALL SELECT 'C09', 'Ký hiệu ngày không xếp ca', '', 1
    ) AS v
    LEFT JOIN hr_attendance.attendance_symbols a ON a.code = v.code
    WHERE a.code IS NULL;


    -- Ký hiệu Vắng
    -- Quy ước:
    -- - Hiển thị cố định A01..A15
    -- - description: mô tả
    -- - symbol: ký hiệu
    -- - is_used: sử dụng
    -- - is_paid: tính công
    -- Lưu ý: các dòng DROP TABLE bên dưới chỉ nên dùng khi cài mới
    -- hoặc khi gặp lỗi #1932 (table doesn't exist in engine). Nếu DB đang có dữ liệu,
    -- hãy xóa/disable các dòng DROP TABLE.
    DROP TABLE IF EXISTS hr_attendance.absence_symbols;

    CREATE TABLE hr_attendance.absence_symbols (
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

    /* Seed: A01..A15 (nếu chưa có) */
    INSERT INTO hr_attendance.absence_symbols (code, description, symbol, is_used, is_paid)
    SELECT v.code, v.description, v.symbol, v.is_used, v.is_paid
    FROM (
        SELECT 'A01' AS code, '' AS description, '' AS symbol, 0 AS is_used, 0 AS is_paid
        UNION ALL SELECT 'A02', '', '', 0, 0
        UNION ALL SELECT 'A03', '', '', 0, 0
        UNION ALL SELECT 'A04', '', '', 0, 0
        UNION ALL SELECT 'A05', '', '', 0, 0
        UNION ALL SELECT 'A06', '', '', 0, 0
        UNION ALL SELECT 'A07', '', '', 0, 0
        UNION ALL SELECT 'A08', '', '', 0, 0
        UNION ALL SELECT 'A09', '', '', 0, 0
        UNION ALL SELECT 'A10', '', '', 0, 0
        UNION ALL SELECT 'A11', '', '', 0, 0
        UNION ALL SELECT 'A12', '', '', 0, 0
        UNION ALL SELECT 'A13', '', '', 0, 0
        UNION ALL SELECT 'A14', '', '', 0, 0
        UNION ALL SELECT 'A15', '', '', 0, 0
    ) v
    LEFT JOIN hr_attendance.absence_symbols a ON a.code = v.code
    WHERE a.code IS NULL;


    -- Chọn ngày Cuối tuần
    -- Quy ước:
    -- - Hiển thị cố định Thứ 2..Chủ nhật
    -- - is_weekend: checkbox "Cuối tuần"
    -- Lưu ý: các dòng DROP TABLE bên dưới chỉ nên dùng khi cài mới
    -- hoặc khi gặp lỗi #1932 (table doesn't exist in engine). Nếu DB đang có dữ liệu,
    -- hãy xóa/disable các dòng DROP TABLE.
    DROP TABLE IF EXISTS hr_attendance.weekend_settings;

    CREATE TABLE hr_attendance.weekend_settings (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        day_name VARCHAR(20) NOT NULL,
        is_weekend TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_weekend_settings_day_name (day_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    /* Seed: Thứ 2..Chủ nhật (nếu chưa có) */
    INSERT INTO hr_attendance.weekend_settings (day_name, is_weekend)
    SELECT v.day_name, v.is_weekend
    FROM (
        SELECT 'Thứ 2' AS day_name, 0 AS is_weekend
        UNION ALL SELECT 'Thứ 3', 0
        UNION ALL SELECT 'Thứ 4', 0
        UNION ALL SELECT 'Thứ 5', 0
        UNION ALL SELECT 'Thứ 6', 0
        UNION ALL SELECT 'Thứ 7', 1
        UNION ALL SELECT 'Chủ nhật', 1
    ) v
    LEFT JOIN hr_attendance.weekend_settings w ON w.day_name = v.day_name
    WHERE w.day_name IS NULL;

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
