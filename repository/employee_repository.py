"""repository.employee_repository

CRUD truy vấn bảng employees.
"""

from __future__ import annotations

from typing import Any

from core.database import Database


class EmployeeRepository:
    def get_employee(self, employee_id: int) -> dict[str, Any] | None:
        sql = """
            SELECT
                id,
                employee_code,
                full_name,
                start_date,
                title_id,
                department_id,
                date_of_birth,
                gender,
                national_id,
                id_issue_date,
                id_issue_place,
                address,
                phone,
                insurance_no,
                tax_code,
                degree,
                major,
                contract1_signed,
                contract1_no,
                contract1_sign_date,
                contract1_expire_date,
                contract2_indefinite,
                contract2_no,
                contract2_sign_date,
                children_count,
                child_dob_1,
                child_dob_2,
                child_dob_3,
                child_dob_4,
                note
            FROM employees
            WHERE id = %s
            LIMIT 1
        """
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=True)
            cursor.execute(sql, (int(employee_id),))
            return cursor.fetchone()

    def create_employee(self, data: dict[str, Any]) -> int:
        sql = """
            INSERT INTO employees (
                employee_code, full_name, start_date, title_id, department_id,
                date_of_birth, gender, national_id, id_issue_date, id_issue_place,
                address, phone, insurance_no, tax_code, degree, major,
                contract1_signed, contract1_no, contract1_sign_date, contract1_expire_date,
                contract2_indefinite, contract2_no, contract2_sign_date,
                children_count, child_dob_1, child_dob_2, child_dob_3, child_dob_4,
                note
            ) VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,%s,
                %s
            )
        """
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(
                sql,
                (
                    data.get("employee_code"),
                    data.get("full_name"),
                    data.get("start_date"),
                    data.get("title_id"),
                    data.get("department_id"),
                    data.get("date_of_birth"),
                    data.get("gender"),
                    data.get("national_id"),
                    data.get("id_issue_date"),
                    data.get("id_issue_place"),
                    data.get("address"),
                    data.get("phone"),
                    data.get("insurance_no"),
                    data.get("tax_code"),
                    data.get("degree"),
                    data.get("major"),
                    1 if data.get("contract1_signed") else 0,
                    data.get("contract1_no"),
                    data.get("contract1_sign_date"),
                    data.get("contract1_expire_date"),
                    1 if data.get("contract2_indefinite") else 0,
                    data.get("contract2_no"),
                    data.get("contract2_sign_date"),
                    data.get("children_count"),
                    data.get("child_dob_1"),
                    data.get("child_dob_2"),
                    data.get("child_dob_3"),
                    data.get("child_dob_4"),
                    data.get("note"),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_employee(self, employee_id: int, data: dict[str, Any]) -> int:
        sql = """
            UPDATE employees
            SET
                employee_code = %s,
                full_name = %s,
                start_date = %s,
                title_id = %s,
                department_id = %s,
                date_of_birth = %s,
                gender = %s,
                national_id = %s,
                id_issue_date = %s,
                id_issue_place = %s,
                address = %s,
                phone = %s,
                insurance_no = %s,
                tax_code = %s,
                degree = %s,
                major = %s,
                contract1_signed = %s,
                contract1_no = %s,
                contract1_sign_date = %s,
                contract1_expire_date = %s,
                contract2_indefinite = %s,
                contract2_no = %s,
                contract2_sign_date = %s,
                children_count = %s,
                child_dob_1 = %s,
                child_dob_2 = %s,
                child_dob_3 = %s,
                child_dob_4 = %s,
                note = %s
            WHERE id = %s
        """
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(
                sql,
                (
                    data.get("employee_code"),
                    data.get("full_name"),
                    data.get("start_date"),
                    data.get("title_id"),
                    data.get("department_id"),
                    data.get("date_of_birth"),
                    data.get("gender"),
                    data.get("national_id"),
                    data.get("id_issue_date"),
                    data.get("id_issue_place"),
                    data.get("address"),
                    data.get("phone"),
                    data.get("insurance_no"),
                    data.get("tax_code"),
                    data.get("degree"),
                    data.get("major"),
                    1 if data.get("contract1_signed") else 0,
                    data.get("contract1_no"),
                    data.get("contract1_sign_date"),
                    data.get("contract1_expire_date"),
                    1 if data.get("contract2_indefinite") else 0,
                    data.get("contract2_no"),
                    data.get("contract2_sign_date"),
                    data.get("children_count"),
                    data.get("child_dob_1"),
                    data.get("child_dob_2"),
                    data.get("child_dob_3"),
                    data.get("child_dob_4"),
                    data.get("note"),
                    int(employee_id),
                ),
            )
            conn.commit()
            return int(cursor.rowcount)

    def list_distinct_id_issue_places(self) -> list[str]:
        sql = """
            SELECT DISTINCT id_issue_place
            FROM employees
            WHERE id_issue_place IS NOT NULL AND TRIM(id_issue_place) <> ''
            ORDER BY id_issue_place ASC
            LIMIT 200
        """
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall() or []
        return [
            str(r.get("id_issue_place") or "").strip()
            for r in rows
            if str(r.get("id_issue_place") or "").strip()
        ]

    def delete_employee(self, employee_id: int) -> int:
        sql = "DELETE FROM employees WHERE id = %s"
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(sql, (int(employee_id),))
            conn.commit()
            return int(cursor.rowcount)

    def list_employees(
        self,
        employee_code: str | None = None,
        full_name: str | None = None,
        department_id: int | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []

        if employee_code:
            where.append("e.employee_code LIKE %s")
            params.append(f"%{employee_code}%")

        if full_name:
            where.append("e.full_name LIKE %s")
            params.append(f"%{full_name}%")

        if department_id:
            where.append("e.department_id = %s")
            params.append(int(department_id))

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
            SELECT
                e.id,
                e.employee_code,
                e.full_name,
                e.start_date,
                jt.title_name,
                d.department_name,
                e.date_of_birth,
                e.gender,
                e.national_id,
                e.id_issue_date,
                e.id_issue_place,
                e.address,
                e.phone,
                e.insurance_no,
                e.tax_code,
                e.degree,
                e.major,
                e.contract1_signed,
                e.contract1_no,
                e.contract1_sign_date,
                e.contract1_expire_date,
                e.contract2_indefinite,
                e.contract2_no,
                e.contract2_sign_date,
                e.children_count,
                e.child_dob_1,
                e.child_dob_2,
                e.child_dob_3,
                e.child_dob_4,
                e.note
            FROM employees e
            LEFT JOIN job_titles jt ON jt.id = e.title_id
            LEFT JOIN departments d ON d.id = e.department_id
            {where_sql}
            ORDER BY e.id DESC
        """

        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=True)
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall() or []

        # Convert date objects to ISO string for UI
        def to_str(v: Any) -> Any:
            if v is None:
                return None
            try:
                # mysql-connector returns datetime.date
                return v.isoformat()
            except Exception:
                return v

        out: list[dict[str, Any]] = []
        for idx, r in enumerate(rows, start=1):
            out.append(
                {
                    "id": r.get("id"),
                    "stt": idx,
                    "employee_code": r.get("employee_code"),
                    "full_name": r.get("full_name"),
                    "start_date": to_str(r.get("start_date")),
                    "title_name": r.get("title_name"),
                    "department_name": r.get("department_name"),
                    "date_of_birth": to_str(r.get("date_of_birth")),
                    "gender": r.get("gender"),
                    "national_id": r.get("national_id"),
                    "id_issue_date": to_str(r.get("id_issue_date")),
                    "id_issue_place": r.get("id_issue_place"),
                    "address": r.get("address"),
                    "phone": r.get("phone"),
                    "insurance_no": r.get("insurance_no"),
                    "tax_code": r.get("tax_code"),
                    "degree": r.get("degree"),
                    "major": r.get("major"),
                    "contract1_signed": bool(int(r.get("contract1_signed") or 0)),
                    "contract1_no": r.get("contract1_no"),
                    "contract1_sign_date": to_str(r.get("contract1_sign_date")),
                    "contract1_expire_date": to_str(r.get("contract1_expire_date")),
                    "contract2_indefinite": bool(
                        int(r.get("contract2_indefinite") or 0)
                    ),
                    "contract2_no": r.get("contract2_no"),
                    "contract2_sign_date": to_str(r.get("contract2_sign_date")),
                    "children_count": r.get("children_count"),
                    "child_dob_1": to_str(r.get("child_dob_1")),
                    "child_dob_2": to_str(r.get("child_dob_2")),
                    "child_dob_3": to_str(r.get("child_dob_3")),
                    "child_dob_4": to_str(r.get("child_dob_4")),
                    "note": r.get("note"),
                }
            )
        return out

    def upsert_many(self, items: list[dict[str, Any]]) -> tuple[int, int]:
        """Upsert by employee_code. Returns (inserted_or_updated, skipped)."""

        if not items:
            return 0, 0

        sql = """
            INSERT INTO employees (
                employee_code, full_name, start_date, title_id, department_id,
                date_of_birth, gender, national_id, id_issue_date, id_issue_place,
                address, phone, insurance_no, tax_code, degree, major,
                contract1_signed, contract1_no, contract1_sign_date, contract1_expire_date,
                contract2_indefinite, contract2_no, contract2_sign_date,
                children_count, child_dob_1, child_dob_2, child_dob_3, child_dob_4,
                note
            ) VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,%s,
                %s
            )
            ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                start_date = VALUES(start_date),
                title_id = VALUES(title_id),
                department_id = VALUES(department_id),
                date_of_birth = VALUES(date_of_birth),
                gender = VALUES(gender),
                national_id = VALUES(national_id),
                id_issue_date = VALUES(id_issue_date),
                id_issue_place = VALUES(id_issue_place),
                address = VALUES(address),
                phone = VALUES(phone),
                insurance_no = VALUES(insurance_no),
                tax_code = VALUES(tax_code),
                degree = VALUES(degree),
                major = VALUES(major),
                contract1_signed = VALUES(contract1_signed),
                contract1_no = VALUES(contract1_no),
                contract1_sign_date = VALUES(contract1_sign_date),
                contract1_expire_date = VALUES(contract1_expire_date),
                contract2_indefinite = VALUES(contract2_indefinite),
                contract2_no = VALUES(contract2_no),
                contract2_sign_date = VALUES(contract2_sign_date),
                children_count = VALUES(children_count),
                child_dob_1 = VALUES(child_dob_1),
                child_dob_2 = VALUES(child_dob_2),
                child_dob_3 = VALUES(child_dob_3),
                child_dob_4 = VALUES(child_dob_4),
                note = VALUES(note)
        """

        params: list[tuple[Any, ...]] = []
        skipped = 0
        for it in items:
            code = str(it.get("employee_code") or "").strip()
            name = str(it.get("full_name") or "").strip()
            if not code or not name:
                skipped += 1
                continue

            params.append(
                (
                    code,
                    name,
                    it.get("start_date"),
                    it.get("title_id"),
                    it.get("department_id"),
                    it.get("date_of_birth"),
                    it.get("gender"),
                    it.get("national_id"),
                    it.get("id_issue_date"),
                    it.get("id_issue_place"),
                    it.get("address"),
                    it.get("phone"),
                    it.get("insurance_no"),
                    it.get("tax_code"),
                    it.get("degree"),
                    it.get("major"),
                    1 if it.get("contract1_signed") else 0,
                    it.get("contract1_no"),
                    it.get("contract1_sign_date"),
                    it.get("contract1_expire_date"),
                    1 if it.get("contract2_indefinite") else 0,
                    it.get("contract2_no"),
                    it.get("contract2_sign_date"),
                    it.get("children_count"),
                    it.get("child_dob_1"),
                    it.get("child_dob_2"),
                    it.get("child_dob_3"),
                    it.get("child_dob_4"),
                    it.get("note"),
                )
            )

        if not params:
            return 0, skipped

        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.executemany(sql, params)
            conn.commit()
            affected = int(cursor.rowcount or 0)

        return affected, skipped
