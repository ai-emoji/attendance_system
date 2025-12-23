"""services.backup_services

Backup/restore database bằng MySQL client tools (mysqldump/mysql).

Ghi chú:
- Tránh truyền password trên command line: dùng env MYSQL_PWD.
- Nếu máy chưa có mysqldump/mysql trong PATH thì sẽ báo lỗi rõ ràng.
"""

from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

from core.database import Database


class BackupService:
    def _resolve_mysql_tool(self, exe_name: str) -> str | None:
        """Resolve path for mysql client executables.

        Priority:
        1) Explicit env var (MYSQLDUMP_PATH / MYSQL_PATH)
        2) MYSQL_BIN_DIR + exe
        3) PATH via shutil.which
        4) Common Windows install locations (MySQL/MariaDB/XAMPP/WAMP)
        """

        exe = exe_name
        if os.name == "nt" and not exe.lower().endswith(".exe"):
            exe = f"{exe}.exe"

        env_key = (
            "MYSQLDUMP_PATH"
            if exe_name.lower().startswith("mysqldump")
            else "MYSQL_PATH"
        )
        explicit = (os.environ.get(env_key) or "").strip()
        if explicit:
            p = Path(explicit)
            if p.exists() and p.is_file():
                return str(p)

        bin_dir = (os.environ.get("MYSQL_BIN_DIR") or "").strip()
        if bin_dir:
            p = Path(bin_dir) / exe
            if p.exists() and p.is_file():
                return str(p)

        found = shutil.which(exe_name) or shutil.which(exe)
        if found:
            return found

        # Common locations
        candidates: list[Path] = []
        if os.name == "nt":
            candidates.extend(
                [
                    Path(r"C:\Program Files\MySQL"),
                    Path(r"C:\Program Files (x86)\MySQL"),
                    Path(r"C:\Program Files\MariaDB"),
                    Path(r"C:\Program Files (x86)\MariaDB"),
                    Path(r"C:\xampp\mysql\bin"),
                    Path(r"C:\wamp64\bin\mysql"),
                ]
            )

        for base in candidates:
            try:
                if not base.exists():
                    continue

                # If base is already a bin dir (e.g., xampp\mysql\bin)
                direct = base / exe
                if direct.exists() and direct.is_file():
                    return str(direct)

                # Search common MySQL Server version folders: ...\MySQL Server 8.0\bin\mysqldump.exe
                for match in base.glob(f"**/bin/{exe}"):
                    if match.exists() and match.is_file():
                        return str(match)
            except Exception:
                continue

        return None

    def _get_mysql_cli_config(self) -> tuple[str, int, str, str, str]:
        cfg = Database.CONFIG
        host = str(cfg.get("host") or "").strip()
        port = int(cfg.get("port") or 3306)
        user = str(cfg.get("user") or "").strip()
        password = str(cfg.get("password") or "")
        database = str(cfg.get("database") or "").strip()
        return host, port, user, password, database

    def backup_to_file(self, output_file: str) -> tuple[bool, str]:
        output_path = Path(output_file)
        if not str(output_path).strip():
            return False, "Vui lòng chọn đường dẫn file backup."

        if output_path.suffix.lower() != ".sql":
            output_path = output_path.with_suffix(".sql")

        host, port, user, password, database = self._get_mysql_cli_config()
        if not host or not user or not database:
            return False, "Chưa cấu hình kết nối CSDL. Vào 'Kết nối CSDL SQL' trước."

        output_path.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["MYSQL_PWD"] = password

        mysqldump = self._resolve_mysql_tool("mysqldump")
        if not mysqldump:
            return (
                False,
                "Không tìm thấy 'mysqldump'. Cài MySQL Client Tools hoặc thêm thư mục bin vào PATH (hoặc set MYSQL_BIN_DIR/MYSQLDUMP_PATH).",
            )

        cmd = [
            mysqldump,
            "--host",
            host,
            "--port",
            str(port),
            "--user",
            user,
            "--databases",
            database,
            "--single-transaction",
            "--triggers",
            "--routines",
            "--events",
            "--add-drop-database",
            "--add-drop-table",
        ]

        try:
            with output_path.open("wb") as f:
                proc = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=False,
                )
            if proc.returncode != 0:
                err = (proc.stderr or b"").decode(errors="ignore").strip()
                return False, f"Backup thất bại: {err or 'Không rõ lỗi.'}"

            # Basic completeness check: file exists and is not empty
            try:
                if not output_path.exists():
                    return False, "Backup thất bại: không tạo được file .sql."
                size = int(output_path.stat().st_size or 0)
                if size <= 0:
                    return False, "Backup thất bại: file .sql rỗng."
                if size < 1024:
                    # Very small dump is suspicious (often means error was redirected elsewhere)
                    return (
                        False,
                        "Backup không đầy đủ: file .sql quá nhỏ. Vui lòng kiểm tra lại cấu hình/mysqldump.",
                    )
                size_mb = size / (1024 * 1024)
                return True, f"Backup thành công: {output_path} ({size_mb:.2f} MB)"
            except Exception:
                return True, f"Backup thành công: {output_path}"
        except FileNotFoundError:
            return (
                False,
                "Không tìm thấy 'mysqldump'. Cài MySQL Client Tools hoặc thêm thư mục bin vào PATH (hoặc set MYSQL_BIN_DIR/MYSQLDUMP_PATH).",
            )
        except Exception as exc:
            return False, f"Backup thất bại: {exc}"

    def restore_from_file(self, sql_file: str) -> tuple[bool, str]:
        sql_path = Path(sql_file)
        if not str(sql_path).strip() or not sql_path.exists():
            return False, "Vui lòng chọn file .sql hợp lệ."

        host, port, user, password, database = self._get_mysql_cli_config()
        if not host or not user or not database:
            return False, "Chưa cấu hình kết nối CSDL. Vào 'Kết nối CSDL SQL' trước."

        env = os.environ.copy()
        env["MYSQL_PWD"] = password

        mysql = self._resolve_mysql_tool("mysql")
        if not mysql:
            return (
                False,
                "Không tìm thấy 'mysql'. Cài MySQL Client Tools hoặc thêm thư mục bin vào PATH (hoặc set MYSQL_BIN_DIR/MYSQL_PATH).",
            )

        cmd = [
            mysql,
            "--host",
            host,
            "--port",
            str(port),
            "--user",
            user,
            database,
        ]

        try:
            with sql_path.open("rb") as f:
                proc = subprocess.run(
                    cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    check=False,
                )
            if proc.returncode != 0:
                err = (proc.stderr or b"").decode(errors="ignore").strip()
                return False, f"Khôi phục thất bại: {err or 'Không rõ lỗi.'}"
            return True, "Khôi phục thành công."
        except FileNotFoundError:
            return (
                False,
                "Không tìm thấy 'mysql'. Cài MySQL Client Tools hoặc thêm thư mục bin vào PATH (hoặc set MYSQL_BIN_DIR/MYSQL_PATH).",
            )
        except Exception as exc:
            return False, f"Khôi phục thất bại: {exc}"
