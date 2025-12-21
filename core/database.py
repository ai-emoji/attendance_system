"""
Module quản lý kết nối cơ sở dữ liệu MySQL.

Cung cấp:
- Kết nối đến MySQL qua context manager
- Xử lý lỗi kết nối tự động
- Logging chi tiết
"""

import mysql.connector
import logging
from typing import Optional


# Cấu hình logging
logger = logging.getLogger(__name__)


class Database:
    """
    Quản lý kết nối MySQL.

    Sử dụng:
        with Database.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """

    # Cấu hình kết nối - có thể thay đổi
    CONFIG = {
        "host": "192.168.1.64",
        "user": "duongduong",
        "password": "duongphuc123",
        "database": "hr_attendance",
        "charset": "utf8mb4",
        "use_unicode": True,
    }

    @staticmethod
    def connect():
        """
        Kết nối đến MySQL.

        Returns:
            MySQLConnection: Đối tượng kết nối

        Raises:
            mysql.connector.Error: Nếu kết nối thất bại
        """
        try:
            conn = mysql.connector.connect(**Database.CONFIG)
            logger.info("✅ Kết nối MySQL thành công")
            return conn
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error("❌ Tên đăng nhập hoặc mật khẩu sai")
            elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
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
        except mysql.connector.Error as err:
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
        except mysql.connector.Error as err:
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
        except mysql.connector.Error as err:
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
