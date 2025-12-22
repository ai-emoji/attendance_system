"""services.csdl_services

Service cho chức năng "Kết nối CSDL SQL".
- Validate cấu hình
- Apply vào core.database.Database.CONFIG
- Test connection
"""

from __future__ import annotations

import mysql.connector

from core.database import Database
from repository.csdl_repository import CSDLConfig, CSDLRepository


class CSDLService:
    def __init__(self, repo: CSDLRepository | None = None) -> None:
        self._repo = repo or CSDLRepository()

    @staticmethod
    def _format_connect_exception(exc: BaseException) -> str:
        # mysql-connector-python thường bọc nhiều lớp lỗi; ưu tiên đọc errno/message.
        if isinstance(exc, mysql.connector.Error):
            errno = getattr(exc, "errno", None)
            msg = str(exc).strip()

            # Các lỗi phổ biến khi kết nối
            if errno == 1045:
                return "Sai user hoặc mật khẩu (1045)."
            if errno == 1044:
                return "User không có quyền truy cập database (1044)."
            if errno == 1049:
                return "Database không tồn tại (1049)."
            if errno in (2003, 2013):
                return (
                    f"Không kết nối được tới MySQL ({errno}). "
                    "Kiểm tra host/port, MySQL đang chạy, firewall, và quyền mở cổng 3306."
                )
            if errno == 2005:
                return "Không phân giải được host MySQL (2005). Kiểm tra lại Host (đúng IP/tên máy)."
            if errno == 1130:
                details = f" Chi tiết: {msg}" if msg else ""
                return (
                    "Host của bạn không được phép kết nối vào MySQL (1130). "
                    "Cần cấp quyền user@host trên máy MySQL và/hoặc mở bind-address/firewall. "
                    "Gợi ý: trên server chạy GRANT cho đúng host (vd 'user'@'%' hoặc 'user'@'192.168.1.%') "
                    "và đảm bảo MySQL lắng nghe cổng 3306 (bind-address) + firewall cho phép."
                    + details
                )

            # Trường hợp người dùng báo '1103' — trong MySQL thường là lỗi tên bảng.
            if errno == 1103:
                return (
                    "MySQL báo lỗi 1103 (thường liên quan tên bảng không hợp lệ). "
                    "Nếu bạn đang 'test connection' mà gặp mã này, vui lòng kiểm tra lại message chi tiết/log."
                )

            # Fallback: hiển thị nguyên văn kèm mã lỗi nếu có.
            return f"{msg}" if errno is None else f"{msg} (errno={errno})"

        # Lỗi mạng/DNS thường là OSError (Windows có thể hiện mã 11001/11002/11003...).
        if isinstance(exc, OSError):
            errno = getattr(exc, "errno", None)
            msg = str(exc).strip()
            if errno in (11001, 11002, 11003, 11004):
                return f"Lỗi DNS/host ({errno}). Kiểm tra lại Host, hoặc thử nhập bằng IP thay vì tên máy. Chi tiết: {msg}"
            if errno is not None:
                return f"Lỗi hệ điều hành khi kết nối (errno={errno}): {msg}"
            return f"Lỗi hệ điều hành khi kết nối: {msg}"

        return str(exc).strip() or repr(exc)

    def load_config(self) -> CSDLConfig:
        saved = self._repo.load()
        if saved is not None:
            return saved

        # Không fallback vào cấu hình hard-code. Khi chưa có file, để trống để người dùng nhập.
        return CSDLConfig(host="", port=3306, user="", password="", database="")

    def validate(self, config: CSDLConfig) -> tuple[bool, str]:
        if not config.host:
            return False, "Vui lòng nhập Host."

        host = str(config.host).strip()
        if "://" in host:
            return (
                False,
                "Host không được chứa http:// hoặc https:// (chỉ nhập IP/tên máy).",
            )
        # Tránh nhầm 'host:port' (với IPv4/hostname). IPv6 có nhiều dấu ':' nên không áp quy tắc này.
        if host.count(":") == 1:
            maybe_host, maybe_port = host.split(":", 1)
            if maybe_host and maybe_port.isdigit():
                return (
                    False,
                    "Host không được kèm :port. Hãy nhập Host và Port ở 2 ô riêng.",
                )

        if not config.user:
            return False, "Vui lòng nhập User."
        if not config.database:
            return False, "Vui lòng nhập Database."
        if config.port <= 0:
            return False, "Port không hợp lệ."
        return True, "OK"

    def test_connection(self, config: CSDLConfig) -> tuple[bool, str]:
        ok, msg = self.validate(config)
        if not ok:
            return False, msg

        try:
            conn = mysql.connector.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                charset=Database.CONFIG.get("charset") or "utf8mb4",
                use_unicode=bool(Database.CONFIG.get("use_unicode", True)),
                connection_timeout=5,
            )
            try:
                conn.close()
            except Exception:
                pass
            return True, "Kết nối thành công."
        except Exception as exc:
            return False, f"Kết nối thất bại: {self._format_connect_exception(exc)}"

    def apply_and_save(self, config: CSDLConfig) -> tuple[bool, str]:
        ok, msg = self.test_connection(config)
        if not ok:
            return False, msg

        # Apply vào Database.CONFIG
        Database.CONFIG.update(
            {
                "host": config.host,
                "port": int(config.port),
                "user": config.user,
                "password": config.password,
                "database": config.database,
            }
        )
        self._repo.save(config)
        return True, "Đã lưu cấu hình và kết nối OK."
