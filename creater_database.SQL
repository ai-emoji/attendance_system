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
