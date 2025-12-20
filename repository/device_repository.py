"""repository.device_repository

SQL CRUD cho bảng devices.

Ghi chú:
- Repository chỉ làm SQL thuần.
- Bảng dự kiến (MySQL):
    devices(
        id INT AUTO_INCREMENT PRIMARY KEY,
        device_no INT,
        device_name VARCHAR(255),
        ip_address VARCHAR(50),
        password VARCHAR(50),
        port INT
    )
"""

from __future__ import annotations

import logging
from typing import Any

from core.database import Database


logger = logging.getLogger(__name__)


class DeviceRepository:
    def list_devices(self) -> list[dict[str, Any]]:
        query = (
            "SELECT id, device_no, device_name, ip_address, password, port "
            "FROM devices ORDER BY id ASC"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query)
                return list(cursor.fetchall() or [])
        except Exception:
            logger.exception("Lỗi list_devices")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def get_device(self, device_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT id, device_no, device_name, ip_address, password, port "
            "FROM devices WHERE id = %s LIMIT 1"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(query, (int(device_id),))
                return cursor.fetchone()
        except Exception:
            logger.exception("Lỗi get_device")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def create_device(
        self,
        device_no: int,
        device_name: str,
        ip_address: str,
        password: str,
        port: int,
    ) -> int:
        query = (
            "INSERT INTO devices (device_no, device_name, ip_address, password, port) "
            "VALUES (%s, %s, %s, %s, %s)"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (int(device_no), device_name, ip_address, password, int(port)),
                )
                conn.commit()
                return int(cursor.lastrowid)
        except Exception:
            logger.exception("Lỗi create_device")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def update_device(
        self,
        device_id: int,
        device_no: int,
        device_name: str,
        ip_address: str,
        password: str,
        port: int,
    ) -> int:
        query = (
            "UPDATE devices SET device_no = %s, device_name = %s, ip_address = %s, "
            "password = %s, port = %s WHERE id = %s"
        )

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(
                    query,
                    (
                        int(device_no),
                        device_name,
                        ip_address,
                        password,
                        int(port),
                        int(device_id),
                    ),
                )
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi update_device")
            raise
        finally:
            if cursor is not None:
                cursor.close()

    def delete_device(self, device_id: int) -> int:
        query = "DELETE FROM devices WHERE id = %s"

        cursor = None
        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=False)
                cursor.execute(query, (int(device_id),))
                conn.commit()
                return int(cursor.rowcount)
        except Exception:
            logger.exception("Lỗi delete_device")
            raise
        finally:
            if cursor is not None:
                cursor.close()
