-- Tạo bảng company cho MySQL
-- Lưu ý: chạy trong database đã cấu hình (Database.CONFIG["database"]).

CREATE TABLE IF NOT EXISTS company (
    id INT NOT NULL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    company_address VARCHAR(255) NULL,
    company_phone VARCHAR(50) NULL,
    company_logo LONGBLOB NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Tạo bảng job_titles (Khai báo Chức danh)
CREATE TABLE IF NOT EXISTS job_titles (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_job_titles_title_name (title_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Tạo bảng departments (Khai báo Phòng ban)
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


-- Tạo bảng holidays (Khai báo Ngày lễ)
-- Quy ước: cho phép trùng ngày nếu khác thông tin; chỉ chặn trùng hoàn toàn (date + info)
CREATE TABLE IF NOT EXISTS holidays (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    holiday_date DATE NOT NULL,
    holiday_info VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Nếu bảng holidays đã tồn tại với unique theo holiday_date, chạy thủ công:
-- ALTER TABLE holidays DROP INDEX uq_holidays_holiday_date;
-- ALTER TABLE holidays ADD UNIQUE KEY uq_holidays_date_info (holiday_date, holiday_info);
