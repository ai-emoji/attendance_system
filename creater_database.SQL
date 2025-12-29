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

    -- Drop theo thứ tự phụ thuộc FK (child -> parent)
    DROP TABLE IF EXISTS hr_attendance.attendance_audit;
    DROP TABLE IF EXISTS hr_attendance.download_attendance;
    DROP TABLE IF EXISTS hr_attendance.attendance_raw;

    DROP TABLE IF EXISTS hr_attendance.employee_schedule_assignments;

    DROP TABLE IF EXISTS hr_attendance.arrange_schedule_detail_shifts;
    DROP TABLE IF EXISTS hr_attendance.arrange_schedule_details;
    DROP TABLE IF EXISTS hr_attendance.arrange_schedules;
    DROP TABLE IF EXISTS hr_attendance.arrange_schedule_day_types;

    DROP TABLE IF EXISTS hr_attendance.work_shifts;
    DROP TABLE IF EXISTS hr_attendance.devices;
    DROP TABLE IF EXISTS hr_attendance.holidays;

    DROP TABLE IF EXISTS hr_attendance.employees;
    DROP TABLE IF EXISTS hr_attendance.departments;
    DROP TABLE IF EXISTS hr_attendance.job_titles;

    DROP TABLE IF EXISTS hr_attendance.attendance_symbols;

    DROP TABLE IF EXISTS hr_attendance.company;
     

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
        department_id INT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_job_titles_title_name (title_name),
        KEY idx_job_titles_department_id (department_id)
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
        name_on_mcc VARCHAR(255) NULL COMMENT 'Employee name from machine (or resolved name)',
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
        name_on_mcc VARCHAR(255) NULL COMMENT 'Employee name from machine (or resolved name)',
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


    -- attendance_audit: dữ liệu chấm công theo ca đã tổng hợp (dùng cho màn "Chấm công Theo ca" - MainContent2)
    -- Ghi chú:
    -- - Đây là bảng lưu kết quả/tổng hợp để UI gọi lại từ DB
    -- - Nếu chưa có dữ liệu, UI sẽ hiển thị rỗng
    CREATE TABLE IF NOT EXISTS hr_attendance.attendance_audit (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,

        attendance_code VARCHAR(50) NOT NULL COMMENT 'Mã chấm công (user_id trên máy)',
        device_no INT NOT NULL COMMENT 'Số máy chấm công (snapshot từ máy)',
        device_id INT NULL COMMENT 'ID máy chấm công (FK tới bảng devices)',
        device_name VARCHAR(255) NULL COMMENT 'Tên máy chấm công (snapshot)',
        employee_id INT NULL COMMENT 'ID nhân viên (FK tới bảng employees)',
        employee_code VARCHAR(50) NULL COMMENT 'Mã nhân viên (employee_code)',
        full_name VARCHAR(255) NULL COMMENT 'Họ và tên nhân viên',
        work_date DATE NOT NULL COMMENT 'Ngày chấm công',
        weekday VARCHAR(20) NULL COMMENT 'Thứ trong tuần (chuỗi hiển thị)',
        in_1_symbol VARCHAR(50) NULL COMMENT 'Ký hiệu import/override (VD: OFF, V, Lễ...)',
        in_1 TIME NULL COMMENT 'Giờ vào lần 1',
        out_1 TIME NULL COMMENT 'Giờ ra lần 1',
        in_2 TIME NULL COMMENT 'Giờ vào lần 2',
        out_2 TIME NULL COMMENT 'Giờ ra lần 2',
        in_3 TIME NULL COMMENT 'Giờ vào lần 3',
        out_3 TIME NULL COMMENT 'Giờ ra lần 3',
        late VARCHAR(20) NULL COMMENT 'Đi trễ (chuỗi/tổng hợp theo rule)',
        early VARCHAR(20) NULL COMMENT 'Về sớm (chuỗi/tổng hợp theo rule)',
        hours DECIMAL(10,2) NULL COMMENT 'Tổng giờ làm (giờ)',
        work DECIMAL(10,2) NULL COMMENT 'Số công (ví dụ 1.0, 0.5)',
        `leave` DECIMAL(10,2) NULL COMMENT 'Số giờ/công nghỉ phép',
        hours_plus VARCHAR(10) NULL COMMENT 'Ký hiệu cộng thêm cho giờ (ví dụ "+", áp dụng theo điều kiện từ in_1..out_3)',
        work_plus  VARCHAR(10) NULL COMMENT 'Ký hiệu cộng thêm cho công (ví dụ "+", áp dụng theo điều kiện từ in_1..out_3)',
        leave_plus VARCHAR(10) NULL COMMENT 'Ký hiệu cộng thêm cho phép (ví dụ "+", áp dụng theo điều kiện từ in_1..out_3)',
        tc1 DECIMAL(10,2) NULL COMMENT 'Giờ tăng ca 1 (giờ)',
        tc2 DECIMAL(10,2) NULL COMMENT 'Giờ tăng ca 2 (giờ)',
        tc3 DECIMAL(10,2) NULL COMMENT 'Giờ tăng ca 3 (giờ)',
        total DECIMAL(10,2) NULL COMMENT 'Tổng công (work + work_plus) - cache cho UI',
        schedule VARCHAR(255) NULL COMMENT 'Tên lịch/ca áp dụng (chuỗi hiển thị)',
        shift_code VARCHAR(255) NULL COMMENT 'Mã ca (chuỗi hiển thị) - dùng khi import/khóa công',
        CONSTRAINT fk_attendance_audit_device
            FOREIGN KEY (device_id)
            REFERENCES hr_attendance.devices (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,

        CONSTRAINT fk_attendance_audit_employee
            FOREIGN KEY (employee_id)
            REFERENCES hr_attendance.employees (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,

        -- Nếu = 1: dữ liệu đã được chỉnh bằng "Import dữ liệu chấm công" -> không tự động ghi đè khi sync
        import_locked TINYINT(1) NOT NULL DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        UNIQUE KEY uq_attendance_audit_code_date_device (attendance_code, work_date, device_no),

        KEY idx_attendance_audit_work_date (work_date),
        KEY idx_attendance_audit_employee_date (employee_id, work_date),
        KEY idx_attendance_audit_employee_code_date (employee_code, work_date)
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
        overtime_round_minutes INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_work_shifts_shift_code (shift_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    -- Add column overtime_round_minutes if missing (migrate for existing DB)
    SET @col_ot_round := (
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'work_shifts'
          AND COLUMN_NAME = 'overtime_round_minutes'
    );
    SET @sql_add_ot_round := IF(
        @col_ot_round = 0,
        'ALTER TABLE hr_attendance.work_shifts ADD COLUMN overtime_round_minutes INT NOT NULL DEFAULT 0 AFTER out_window_end',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_add_ot_round; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    /* Seed ca mặc định (nếu chưa có) để module Sắp xếp lịch trình dùng ngay */
    /* Lưu ý: chỉ seed các cột cơ bản để tránh lỗi khi DB đã có work_shifts theo schema cũ */
    INSERT INTO hr_attendance.work_shifts (shift_code, time_in, time_out)
    SELECT v.shift_code, v.time_in, v.time_out
    FROM (
        SELECT 'HC'  AS shift_code, '08:00:00' AS time_in, '17:00:00' AS time_out
        UNION ALL SELECT 'SA', '08:00:00', '12:00:00'
        UNION ALL SELECT 'CH', '13:00:00', '17:00:00'
        UNION ALL SELECT 'Ca1','06:00:00', '14:00:00'
        UNION ALL SELECT 'Ca2','14:00:00', '22:00:00'
    ) v
    LEFT JOIN hr_attendance.work_shifts s ON s.shift_code = v.shift_code
    WHERE s.shift_code IS NULL;


    -- =========================
    -- Sắp xếp ca theo lịch trình
    -- =========================

    -- Danh mục loại ngày (seed cố định) để UI hiển thị Thứ 2..Chủ nhật + Ngày lễ
    CREATE TABLE IF NOT EXISTS hr_attendance.arrange_schedule_day_types (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        day_key VARCHAR(20) NOT NULL,
        day_name VARCHAR(20) NOT NULL,
        day_order INT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_arrange_schedule_day_types_key (day_key),
        UNIQUE KEY uq_arrange_schedule_day_types_order (day_order)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    INSERT IGNORE INTO hr_attendance.arrange_schedule_day_types (day_key, day_name, day_order)
    VALUES
        ('mon', 'Thứ 2', 1),
        ('tue', 'Thứ 3', 2),
        ('wed', 'Thứ 4', 3),
        ('thu', 'Thứ 5', 4),
        ('fri', 'Thứ 6', 5),
        ('sat', 'Thứ 7', 6),
        ('sun', 'Chủ nhật', 7),
        ('holiday', 'Ngày lễ', 8);


    -- Bảng lịch làm việc
    CREATE TABLE IF NOT EXISTS hr_attendance.arrange_schedules (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        schedule_name VARCHAR(255) NOT NULL,
        -- in|out (cách chọn vào/ra)
        in_out_mode VARCHAR(10) NULL,
        ignore_absent_sat TINYINT(1) NOT NULL DEFAULT 0,
        ignore_absent_sun TINYINT(1) NOT NULL DEFAULT 0,
        ignore_absent_holiday TINYINT(1) NOT NULL DEFAULT 0,
        holiday_count_as_work TINYINT(1) NOT NULL DEFAULT 0,
        day_is_out_time TINYINT(1) NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_arrange_schedules_name (schedule_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Chi tiết lịch làm việc theo từng ngày
    CREATE TABLE IF NOT EXISTS hr_attendance.arrange_schedule_details (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        schedule_id INT NOT NULL,
        day_key VARCHAR(20) NOT NULL,
        day_name VARCHAR(20) NOT NULL,
        day_order INT NOT NULL,
        shift1_id INT NULL,
        shift2_id INT NULL,
        shift3_id INT NULL,
        shift4_id INT NULL,
        shift5_id INT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_arrange_schedule_details_schedule_day (schedule_id, day_key),
        KEY idx_arrange_schedule_details_schedule (schedule_id),
        CONSTRAINT fk_arrange_schedule_details_schedule
            FOREIGN KEY (schedule_id)
            REFERENCES hr_attendance.arrange_schedules (id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        CONSTRAINT fk_arrange_schedule_details_shift1
            FOREIGN KEY (shift1_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_arrange_schedule_details_shift2
            FOREIGN KEY (shift2_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE,
        CONSTRAINT fk_arrange_schedule_details_shift3
            FOREIGN KEY (shift3_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
        ,
        CONSTRAINT fk_arrange_schedule_details_shift4
            FOREIGN KEY (shift4_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
        ,
        CONSTRAINT fk_arrange_schedule_details_shift5
            FOREIGN KEY (shift5_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Danh sách ca theo từng ngày (không giới hạn số ca)
    -- Lưu theo thứ tự position = 1..n
    CREATE TABLE IF NOT EXISTS hr_attendance.arrange_schedule_detail_shifts (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        schedule_id INT NOT NULL,
        day_key VARCHAR(20) NOT NULL,
        position INT NOT NULL,
        shift_id INT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_arrange_schedule_detail_shifts_sched_day_pos (schedule_id, day_key, position),
        KEY idx_arrange_schedule_detail_shifts_schedule (schedule_id),
        KEY idx_arrange_schedule_detail_shifts_day_key (day_key),
        CONSTRAINT fk_arrange_schedule_detail_shifts_schedule
            FOREIGN KEY (schedule_id)
            REFERENCES hr_attendance.arrange_schedules (id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        CONSTRAINT fk_arrange_schedule_detail_shifts_shift
            FOREIGN KEY (shift_id)
            REFERENCES hr_attendance.work_shifts (id)
            ON DELETE SET NULL
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- =========================
    -- Sắp xếp lịch Làm việc (gán lịch trình cho nhân viên)
    -- =========================

    CREATE TABLE IF NOT EXISTS hr_attendance.employee_schedule_assignments (
        id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        employee_id INT NOT NULL,
        schedule_id INT NOT NULL,
        effective_from DATE NOT NULL,
        effective_to DATE NULL,
        note TEXT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_employee_schedule_assignments_emp_from (employee_id, effective_from),
        KEY idx_employee_schedule_assignments_employee (employee_id),
        KEY idx_employee_schedule_assignments_schedule (schedule_id),
        CONSTRAINT fk_employee_schedule_assignments_employee
            FOREIGN KEY (employee_id)
            REFERENCES hr_attendance.employees (id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        CONSTRAINT fk_employee_schedule_assignments_schedule
            FOREIGN KEY (schedule_id)
            REFERENCES hr_attendance.arrange_schedules (id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


    -- Ký hiệu Chấm công
    -- Quy ước:
    -- - Lưu theo dạng nhiều dòng (giống absence_symbols)
    -- - code cố định C01..C10
    -- - description: mô tả
    -- - symbol: ký hiệu
    -- - is_visible: checkbox "Hiện"
    -- Lưu ý: các dòng DROP TABLE bên dưới chỉ nên dùng khi cài mới
    -- hoặc khi gặp lỗi #1932 (table doesn't exist in engine). Nếu DB đang có dữ liệu,
    -- hãy xóa/disable các dòng DROP TABLE.
    DROP TABLE IF EXISTS hr_attendance.attendance_symbols;

    CREATE TABLE IF NOT EXISTS hr_attendance.attendance_symbols (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(3) NOT NULL,
        description VARCHAR(255) NULL,
        symbol VARCHAR(50) NULL,
        is_visible TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_attendance_symbols_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

    /* Seed: C01..C10 (nếu chưa có) */
    INSERT INTO hr_attendance.attendance_symbols (code, description, symbol, is_visible)
    SELECT v.code, v.description, v.symbol, v.is_visible
    FROM (
        SELECT 'C01' AS code, 'Ký hiệu đi trễ' AS description, 'Tr' AS symbol, 1 AS is_visible
        UNION ALL SELECT 'C02', 'Ký hiệu về sớm', 'Sm', 1
        UNION ALL SELECT 'C03', 'Ký hiệu đúng giờ', 'X', 1
        UNION ALL SELECT 'C04', 'Ký hiệu tăng ca', '+', 1
        UNION ALL SELECT 'C05', 'Ký hiệu thiếu giờ ra', 'KR', 1
        UNION ALL SELECT 'C06', 'Ký hiệu thiếu giờ vào', 'KV', 1
        UNION ALL SELECT 'C07', 'Ký hiệu vắng (mặc định không chấm công)', 'V', 1
        UNION ALL SELECT 'C08', 'Ký hiệu đúng giờ ca có qua đêm', 'Đ', 1
        UNION ALL SELECT 'C09', 'Ký hiệu ngày không xếp ca', 'OFF', 1
        UNION ALL SELECT 'C10', 'Ký hiệu nghỉ lễ', 'Le', 1
    ) AS v
    LEFT JOIN hr_attendance.attendance_symbols a ON a.code = v.code
    WHERE a.code IS NULL;


    -- =========================
    -- Ghi chú migrate thủ công
    -- =========================
    -- Migrate cho bản cũ của module "Sắp xếp ca theo lịch trình":
    -- Nếu DB hiện tại thiếu 2 cột "Tên ca 4", "Tên ca 5" (tương ứng shift4_id, shift5_id)
    -- thì chạy các lệnh bên dưới (KHÔNG cần DROP TABLE, không mất dữ liệu).
    --
    -- Lưu ý:
    -- - Các lệnh dưới đây dùng prepared statement để tránh lỗi khi đã tồn tại cột/FK.
    -- - Chạy trong database hr_attendance.

    -- Add columns shift4_id / shift5_id if missing
    SET @col_shift4 := (
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'arrange_schedule_details'
          AND COLUMN_NAME = 'shift4_id'
    );
    SET @sql_add_shift4 := IF(
        @col_shift4 = 0,
        'ALTER TABLE hr_attendance.arrange_schedule_details ADD COLUMN shift4_id INT NULL AFTER shift3_id',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_add_shift4; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    SET @col_shift5 := (
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'arrange_schedule_details'
          AND COLUMN_NAME = 'shift5_id'
    );
    SET @sql_add_shift5 := IF(
        @col_shift5 = 0,
        'ALTER TABLE hr_attendance.arrange_schedule_details ADD COLUMN shift5_id INT NULL AFTER shift4_id',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_add_shift5; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    -- Add foreign keys for shift4_id / shift5_id if missing
    SET @fk_shift4 := (
        SELECT COUNT(*)
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'arrange_schedule_details'
          AND CONSTRAINT_NAME = 'fk_arrange_schedule_details_shift4'
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    );
    SET @sql_fk_shift4 := IF(
        @fk_shift4 = 0,
        'ALTER TABLE hr_attendance.arrange_schedule_details\n'
        '  ADD CONSTRAINT fk_arrange_schedule_details_shift4\n'
        '  FOREIGN KEY (shift4_id) REFERENCES hr_attendance.work_shifts (id)\n'
        '  ON DELETE SET NULL ON UPDATE CASCADE',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_fk_shift4; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    SET @fk_shift5 := (
        SELECT COUNT(*)
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'arrange_schedule_details'
          AND CONSTRAINT_NAME = 'fk_arrange_schedule_details_shift5'
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    );
    SET @sql_fk_shift5 := IF(
        @fk_shift5 = 0,
        'ALTER TABLE hr_attendance.arrange_schedule_details\n'
        '  ADD CONSTRAINT fk_arrange_schedule_details_shift5\n'
        '  FOREIGN KEY (shift5_id) REFERENCES hr_attendance.work_shifts (id)\n'
        '  ON DELETE SET NULL ON UPDATE CASCADE',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_fk_shift5; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    -- Create table arrange_schedule_detail_shifts if missing (unlimited shifts)
    SET @tbl_shifts := (
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = 'hr_attendance'
          AND TABLE_NAME = 'arrange_schedule_detail_shifts'
    );
    SET @sql_create_tbl_shifts := IF(
        @tbl_shifts = 0,
        'CREATE TABLE hr_attendance.arrange_schedule_detail_shifts (\n'
        '  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,\n'
        '  schedule_id INT NOT NULL,\n'
        '  day_key VARCHAR(20) NOT NULL,\n'
        '  position INT NOT NULL,\n'
        '  shift_id INT NULL,\n'
        '  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n'
        '  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,\n'
        '  UNIQUE KEY uq_arrange_schedule_detail_shifts_sched_day_pos (schedule_id, day_key, position),\n'
        '  KEY idx_arrange_schedule_detail_shifts_schedule (schedule_id),\n'
        '  KEY idx_arrange_schedule_detail_shifts_day_key (day_key),\n'
        '  CONSTRAINT fk_arrange_schedule_detail_shifts_schedule FOREIGN KEY (schedule_id) REFERENCES hr_attendance.arrange_schedules (id) ON DELETE CASCADE ON UPDATE CASCADE,\n'
        '  CONSTRAINT fk_arrange_schedule_detail_shifts_shift FOREIGN KEY (shift_id) REFERENCES hr_attendance.work_shifts (id) ON DELETE SET NULL ON UPDATE CASCADE\n'
        ') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
        'SELECT 1'
    );
    PREPARE stmt FROM @sql_create_tbl_shifts; EXECUTE stmt; DEALLOCATE PREPARE stmt;

    -- Nếu bạn đang dùng bản cũ (attendance_symbols dạng 1 dòng nhiều cột), cần migrate thủ công:
    -- 1) Đổi tên bảng cũ để backup: RENAME TABLE attendance_symbols TO attendance_symbols_old;
    -- 2) Chạy lại đoạn CREATE + INSERT attendance_symbols (mới) bên trên.
    -- 3) Nếu cần, copy dữ liệu từ bảng cũ sang bảng mới theo mapping code.
    -- Nếu bảng holidays đã tồn tại với unique theo holiday_date, chạy thủ công:
    -- ALTER TABLE holidays DROP INDEX uq_holidays_holiday_date;
    -- ALTER TABLE holidays ADD UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info);
