"""
Module quản lý kết nối cơ sở dữ liệu MySQL.

Cung cấp:
- Kết nối đến MySQL qua context manager
- Xử lý lỗi kết nối tự động
- Logging chi tiết
"""

import json
import logging
import time
import hashlib
from pathlib import Path
from datetime import date, datetime
from typing import Optional

_MYSQL_CONNECTOR = None


def _mysql_connector_module():
    """Lazy import mysql.connector to avoid slow UI startup.

    Importing mysql-connector-python can be expensive on some machines,
    so we only import it when a DB operation is actually performed.
    """

    global _MYSQL_CONNECTOR
    if _MYSQL_CONNECTOR is None:
        import mysql.connector  # type: ignore

        _MYSQL_CONNECTOR = mysql.connector
    return _MYSQL_CONNECTOR


from core.resource import DB_CONNECTION_TIMEOUT, resource_path, user_data_dir


# Cấu hình logging
logger = logging.getLogger(__name__)

# Connection-log throttling (avoid spamming logs when many short DB ops run).
_LAST_CONNECT_LOG_KEY: str | None = None
_LAST_CONNECT_LOG_TS: float = 0.0


class Database:
    """
    Quản lý kết nối MySQL.

    Sử dụng:
        with Database.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """

    # Cấu hình kết nối (không hard-code thông tin nhạy cảm).
    # Sẽ được load từ database/db_config.json khi khởi động,
    # và có thể được cập nhật khi người dùng lưu ở dialog "Kết nối CSDL SQL".
    CONFIG: dict = {
        "host": "",
        "port": 3306,
        "user": "",
        "password": "",
        "database": "",
        "charset": "utf8mb4",
        "use_unicode": True,
        # Avoid long UI freezes on unreachable DB.
        "connection_timeout": int(DB_CONNECTION_TIMEOUT),
    }

    # One-time schema sanity checks (best-effort).
    _SCHEMA_CHECKED: bool = False

    # Per-year table creation cache (best-effort).
    _YEAR_TABLES_ENSURED: set[tuple[str, int]] = set()

    @staticmethod
    def _column_exists(
        cursor, schema_name: str | None, table_name: str, column_name: str
    ) -> bool:
        try:
            tn = str(table_name or "").strip()
            cn = str(column_name or "").strip()
            if not tn or not cn:
                return False
            if schema_name:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
                    (schema_name, tn, cn),
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_NAME=%s AND COLUMN_NAME=%s",
                    (tn, cn),
                )
            row = cursor.fetchone()
            try:
                return bool(row and int(row[0]) > 0)
            except Exception:
                return False
        except Exception:
            return False

    @staticmethod
    def _ensure_table_columns_best_effort(
        conn,
        *,
        table_name: str,
        columns: list[tuple[str, str]],
        log_prefix: str,
    ) -> None:
        """Best-effort add missing columns to an existing table.

        columns: list of (column_name, alter_sql_fragment)
          - alter_sql_fragment example: "ADD COLUMN in_1_symbol VARCHAR(50) NULL"
        """

        cursor = None
        try:
            schema_name = str(Database.CONFIG.get("database") or "").strip() or None
            tn = str(table_name or "").strip()
            if not tn:
                return
            cursor = Database.get_cursor(conn, dictionary=False)
            for col_name, alter_fragment in columns or []:
                cn = str(col_name or "").strip()
                frag = str(alter_fragment or "").strip()
                if not cn or not frag:
                    continue
                if Database._column_exists(cursor, schema_name, tn, cn):
                    continue

                try:
                    cursor.execute(f"ALTER TABLE `{tn}` {frag}")
                    conn.commit()
                    logger.info("✅ Auto-migrate: %s added %s.%s", log_prefix, tn, cn)
                except Exception:
                    logger.warning(
                        "⚠️ Không thể tự động thêm cột %s.%s. Vui lòng chạy script cập nhật CSDL (creater_database.SQL).",
                        tn,
                        cn,
                        exc_info=True,
                    )
        except Exception:
            logger.debug("Schema ensure columns failed (%s)", log_prefix, exc_info=True)
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def _parse_date_any(v: object | None) -> date | None:
        if v is None:
            return None
        if isinstance(v, date) and not isinstance(v, datetime):
            return v
        if isinstance(v, datetime):
            try:
                return v.date()
            except Exception:
                return None
        s = str(v or "").strip()
        if not s:
            return None
        # Accept both 'YYYY-MM-DD' and datetime-like strings.
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            return None

    @staticmethod
    def _year_from_work_date(v: object | None) -> int | None:
        d = Database._parse_date_any(v)
        if d is None:
            return None
        try:
            y = int(d.year)
            return y if 1900 <= y <= 2100 else None
        except Exception:
            return None

    @staticmethod
    def years_between(from_date: object | None, to_date: object | None) -> list[int]:
        d0 = Database._parse_date_any(from_date)
        d1 = Database._parse_date_any(to_date)
        if d0 is None and d1 is None:
            return []
        if d0 is None:
            d0 = d1
        if d1 is None:
            d1 = d0
        if d0 is None or d1 is None:
            return []
        if d0 > d1:
            d0, d1 = d1, d0
        try:
            return list(range(int(d0.year), int(d1.year) + 1))
        except Exception:
            return []

    @staticmethod
    def year_table(base_table: str, year: int) -> str:
        bt = str(base_table or "").strip()
        y = int(year)
        return f"{bt}_{y}" if bt else ""

    @staticmethod
    def ensure_year_table(conn, base_table: str, year: int) -> str:
        """Ensure yearly table exists (CREATE TABLE .. LIKE base table).

        Returns the yearly table name, even if creation fails (best-effort).
        """

        bt = str(base_table or "").strip()
        try:
            y = int(year)
        except Exception:
            y = None
        if not bt or y is None:
            return bt

        yt = Database.year_table(bt, y)
        key = (bt, int(y))
        if key in Database._YEAR_TABLES_ENSURED:
            return yt

        cursor = None
        try:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(f"CREATE TABLE IF NOT EXISTS `{yt}` LIKE `{bt}`")
            try:
                conn.commit()
            except Exception:
                pass

            # Best-effort: ensure new columns exist on existing yearly tables too.
            # Older DBs may have attendance_audit_YYYY created before new columns existed.
            if bt == "attendance_audit":
                Database._ensure_table_columns_best_effort(
                    conn,
                    table_name=str(yt),
                    columns=[
                        ("total", "ADD COLUMN total DECIMAL(10,2) NULL"),
                        ("shift_code", "ADD COLUMN shift_code VARCHAR(255) NULL"),
                        ("in_1_symbol", "ADD COLUMN in_1_symbol VARCHAR(50) NULL"),
                        (
                            "import_locked",
                            "ADD COLUMN import_locked TINYINT(1) NOT NULL DEFAULT 0",
                        ),
                    ],
                    log_prefix=f"{bt}_{y}",
                )

            Database._YEAR_TABLES_ENSURED.add(key)
            return yt
        except Exception:
            # No CREATE permission or other error: keep running with best effort.
            logger.warning(
                "⚠️ Không thể tự tạo bảng theo năm %s (base=%s). Vui lòng chạy script CSDL hoặc cấp quyền CREATE.",
                yt,
                bt,
                exc_info=True,
            )
            return yt
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def _ensure_schema(conn) -> None:
        """Best-effort schema upgrades to keep app compatible across DB versions."""

        if Database._SCHEMA_CHECKED:
            return
        Database._SCHEMA_CHECKED = True

        # Ensure new columns exist (do not crash the app if no ALTER permission).
        cursor = None
        try:
            schema_name = str(Database.CONFIG.get("database") or "").strip() or None
            cursor = Database.get_cursor(conn, dictionary=False)

            # work_shifts.overtime_round_minutes (used for overtime rounding: TC1/TC2/TC3)
            if schema_name:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='work_shifts' AND COLUMN_NAME='overtime_round_minutes'",
                    (schema_name,),
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_NAME='work_shifts' AND COLUMN_NAME='overtime_round_minutes'",
                )

            row = cursor.fetchone()
            exists = False
            try:
                exists = bool(row and int(row[0]) > 0)
            except Exception:
                exists = False

            if not exists:
                try:
                    cursor.execute(
                        "ALTER TABLE work_shifts "
                        "ADD COLUMN overtime_round_minutes INT NOT NULL DEFAULT 0"
                    )
                    conn.commit()
                    logger.info(
                        "✅ Auto-migrate: added work_shifts.overtime_round_minutes"
                    )
                except Exception:
                    logger.warning(
                        "⚠️ Không thể tự động thêm cột work_shifts.overtime_round_minutes. "
                        "Vui lòng chạy script cập nhật CSDL (creater_database.SQL).",
                        exc_info=True,
                    )

            # attendance_audit: keep compatibility with newer UI/service logic.
            # NOTE: yearly tables are handled in ensure_year_table().
            Database._ensure_table_columns_best_effort(
                conn,
                table_name="attendance_audit",
                columns=[
                    ("total", "ADD COLUMN total DECIMAL(10,2) NULL"),
                    ("shift_code", "ADD COLUMN shift_code VARCHAR(255) NULL"),
                    ("in_1_symbol", "ADD COLUMN in_1_symbol VARCHAR(50) NULL"),
                ],
                log_prefix="attendance_audit",
            )
        except Exception:
            logger.debug("Schema ensure failed", exc_info=True)
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def load_config_from_file(config_file: str | None = None) -> None:
        """Load cấu hình kết nối từ file JSON.

        Mặc định: database/db_config.json (qua resource_path).
        """

        if config_file:
            path = Path(config_file)
        else:
            user_path = user_data_dir("pmctn") / "database" / "db_config.json"
            path = (
                user_path
                if user_path.exists()
                else Path(resource_path("database/db_config.json"))
            )
        try:
            if not path.exists() or not path.is_file():
                return

            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                return

            host = str(data.get("host") or "").strip()
            user = str(data.get("user") or "").strip()
            password = str(data.get("password") or "")
            database = str(data.get("database") or "").strip()

            port = data.get("port")
            try:
                port_int = int(port) if port is not None and str(port).strip() else 3306
            except Exception:
                port_int = 3306

            # Chỉ update các trường liên quan kết nối
            Database.CONFIG.update(
                {
                    "host": host,
                    "port": port_int,
                    "user": user,
                    "password": password,
                    "database": database,
                }
            )
        except Exception as exc:
            logger.debug(f"Không thể load db_config.json: {exc}")

    @staticmethod
    def is_configured(*, reload: bool = True) -> bool:
        """Return True if DB connection settings look configured (host/user/database not empty)."""

        try:
            if reload:
                Database.load_config_from_file()
        except Exception:
            # Best-effort: treat as not configured.
            return False

        host = str(Database.CONFIG.get("host") or "").strip()
        user = str(Database.CONFIG.get("user") or "").strip()
        database = str(Database.CONFIG.get("database") or "").strip()
        return bool(host and user and database)

    @staticmethod
    def connect(ensure_schema: bool = True):
        """
        Kết nối đến MySQL.

        Returns:
            MySQLConnection: Đối tượng kết nối

        Raises:
            mysql.connector.Error: Nếu kết nối thất bại
        """
        # Luôn reload cấu hình trước khi kết nối (để thay đổi từ dialog/file có hiệu lực ngay).
        Database.load_config_from_file()

        # Nếu chưa cấu hình đầy đủ thì báo rõ ràng.
        host = str(Database.CONFIG.get("host") or "").strip()
        user = str(Database.CONFIG.get("user") or "").strip()
        database = str(Database.CONFIG.get("database") or "").strip()
        if not host or not user or not database:
            raise RuntimeError(
                "Chưa cấu hình kết nối CSDL. Vào 'Kết nối CSDL SQL' để thiết lập (host/user/database)."
            )

        mc = _mysql_connector_module()

        try:
            connect_kwargs = dict(Database.CONFIG)

            # Enable mysql-connector connection pooling to reduce overhead.
            # NOTE: Closing a pooled connection returns it to the pool.
            try:
                host_p = str(connect_kwargs.get("host") or "").strip().lower()
                user_p = str(connect_kwargs.get("user") or "").strip().lower()
                db_p = str(connect_kwargs.get("database") or "").strip().lower()
                port_p = int(connect_kwargs.get("port") or 3306)
                pool_sig = f"{host_p}:{port_p}/{db_p}@{user_p}".encode("utf-8")
                pool_hash = hashlib.sha1(pool_sig).hexdigest()[:12]
                connect_kwargs.setdefault("pool_name", f"pmctn_{pool_hash}")
                connect_kwargs.setdefault("pool_size", 5)
                connect_kwargs.setdefault("pool_reset_session", True)
            except Exception:
                # Best-effort: if pooling args fail for any reason, continue without pooling.
                pass

            try:
                timeout = connect_kwargs.get("connection_timeout")
                timeout_int = (
                    int(timeout) if timeout is not None else int(DB_CONNECTION_TIMEOUT)
                )
            except Exception:
                timeout_int = int(DB_CONNECTION_TIMEOUT)
            connect_kwargs["connection_timeout"] = max(1, int(timeout_int))

            conn = mc.connect(**connect_kwargs)

            # Log success only when meaningful (first connect, config changed, or after a quiet period).
            try:
                host_l = str(connect_kwargs.get("host") or "").strip().lower()
                user_l = str(connect_kwargs.get("user") or "").strip().lower()
                db_l = str(connect_kwargs.get("database") or "").strip().lower()
                port_l = int(connect_kwargs.get("port") or 3306)
                key = f"{host_l}:{port_l}/{db_l}@{user_l}"
            except Exception:
                key = ""

            global _LAST_CONNECT_LOG_KEY, _LAST_CONNECT_LOG_TS
            now = time.monotonic()
            if key and (
                key != _LAST_CONNECT_LOG_KEY or (now - _LAST_CONNECT_LOG_TS) > 60
            ):
                logger.info("✅ Kết nối MySQL thành công")
                _LAST_CONNECT_LOG_KEY = key
                _LAST_CONNECT_LOG_TS = now
            else:
                logger.debug("✅ Kết nối MySQL thành công")

            # Best-effort schema checks (once per process)
            if ensure_schema:
                try:
                    Database._ensure_schema(conn)
                except Exception:
                    pass

            return conn
        except mc.Error as err:
            if err.errno == mc.errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error("❌ Tên đăng nhập hoặc mật khẩu sai")
            elif err.errno == mc.errorcode.ER_BAD_DB_ERROR:
                logger.error("❌ Database không tồn tại")
            else:
                logger.error(f"❌ Lỗi kết nối MySQL: {err}")
            raise
        except Exception as err:
            logger.error(f"❌ Lỗi không xác định: {err}")
            raise

    @staticmethod
    def get_cursor(conn, dictionary: bool = True):
        """
        Tạo cursor từ kết nối.

        Args:
            conn: Kết nối MySQL
            dictionary (bool): True = DictCursor, False = cursor bình thường

        Returns:
            cursor: MySQLCursor hoặc DictCursor
        """
        if dictionary:
            return conn.cursor(dictionary=True)
        return conn.cursor()

    @staticmethod
    def execute_query(
        query: str, params: Optional[tuple] = None, fetch: str = "all"
    ) -> Optional[list]:
        """
        Thực thi query và lấy kết quả (SELECT).

        Args:
            query (str): Câu SQL
            params (tuple): Tham số query (sử dụng %s)
            fetch (str): "all", "one", hoặc "none"

        Returns:
            list hoặc dict: Kết quả query

        Example:
            result = Database.execute_query("SELECT * FROM users WHERE id = %s", (1,), "one")
        """
        cursor = None
        mc = _mysql_connector_module()
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch == "one":
                    return cursor.fetchone()
                elif fetch == "all":
                    return cursor.fetchall()
                else:
                    return None
        except mc.Error as err:
            logger.error(
                f"❌ Lỗi execute_query: {err}\n   Query: {query}\n   Params: {params}"
            )
            raise
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def execute_update(query: str, params: Optional[tuple] = None) -> int:
        """
        Thực thi query cập nhật/xóa/thêm (INSERT, UPDATE, DELETE).

        Args:
            query (str): Câu SQL
            params (tuple): Tham số query (sử dụng %s)

        Returns:
            int: Số dòng bị ảnh hưởng

        Example:
            affected = Database.execute_update("DELETE FROM users WHERE id = %s", (1,))
        """
        cursor = None
        mc = _mysql_connector_module()
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn)
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                affected = cursor.rowcount
                logger.info(
                    f"✅ Thực thi UPDATE/INSERT/DELETE thành công: {affected} dòng bị ảnh hưởng"
                )
                return affected
        except mc.Error as err:
            logger.error(
                f"❌ Lỗi execute_update: {err}\n   Query: {query}\n   Params: {params}"
            )
            raise
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def execute_insert(query: str, params: Optional[tuple] = None) -> int:
        """
        Thực thi INSERT và trả về ID được tạo.

        Args:
            query (str): Câu SQL INSERT
            params (tuple): Tham số query (sử dụng %s)

        Returns:
            int: ID của record vừa thêm (last_insert_id)

        Example:
            new_id = Database.execute_insert("INSERT INTO users (name, email) VALUES (%s, %s)", ("John", "john@example.com"))
        """
        cursor = None
        mc = _mysql_connector_module()
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn)
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                insert_id = cursor.lastrowid
                logger.info(f"✅ INSERT thành công, ID: {insert_id}")
                return insert_id
        except mc.Error as err:
            logger.error(
                f"❌ Lỗi execute_insert: {err}\n   Query: {query}\n   Params: {params}"
            )
            raise
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    @staticmethod
    def test_connection() -> bool:
        """
        Kiểm tra kết nối MySQL.

        Returns:
            bool: True nếu kết nối thành công
        """
        try:
            with Database.connect() as conn:
                return True
        except Exception:
            return False
