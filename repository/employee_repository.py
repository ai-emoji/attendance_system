"""repository.employee_repository

CRUD truy vấn bảng employees.
"""

from __future__ import annotations

from typing import Any

from core.database import Database


class EmployeeRepository:
    _import_schema_checked: bool = False
    _has_contract1_term: bool = False
    _has_sort_order: bool = False

    def ensure_import_schema(self) -> None:
        """Ensure extra columns needed for Excel import exist.

        - contract1_term: stores values like '01 năm', '02 năm'
        - sort_order: preserves Excel/preview STT order (1..N)
        """

        if EmployeeRepository._import_schema_checked:
            return

        try:
            with Database.connect() as conn:
                cursor = Database.get_cursor(conn, dictionary=True)
                cursor.execute(
                    """
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'employees'
                      AND COLUMN_NAME IN ('contract1_term', 'sort_order')
                    """
                )
                cols = {
                    str(r.get("COLUMN_NAME") or "").strip().lower()
                    for r in (cursor.fetchall() or [])
                }

                EmployeeRepository._has_contract1_term = "contract1_term" in cols
                EmployeeRepository._has_sort_order = "sort_order" in cols

                alters: list[str] = []
                if not EmployeeRepository._has_contract1_term:
                    alters.append("ADD COLUMN contract1_term VARCHAR(50) NULL")
                if not EmployeeRepository._has_sort_order:
                    alters.append("ADD COLUMN sort_order INT NULL")

                if alters:
                    # Execute as a single ALTER to keep it fast.
                    sql = "ALTER TABLE employees " + ", ".join(alters)
                    cur2 = Database.get_cursor(conn, dictionary=False)
                    cur2.execute(sql)
                    conn.commit()

                    # Refresh flags
                    EmployeeRepository._has_contract1_term = True
                    EmployeeRepository._has_sort_order = True
        except Exception:
            # If the DB user lacks INFORMATION_SCHEMA/ALTER permissions, keep the app usable.
            EmployeeRepository._has_contract1_term = False
            EmployeeRepository._has_sort_order = False

        EmployeeRepository._import_schema_checked = True

    def get_employee_by_code(self, employee_code: str) -> dict[str, Any] | None:
        self.ensure_import_schema()
        sql = """
            SELECT
                id,
                {sort_order_col}
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
                {contract1_term_col}
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
            WHERE employee_code = %s
            LIMIT 1
        """
        code = str(employee_code or "").strip()
        if not code:
            return None

        sort_order_col = (
            "sort_order,"
            if EmployeeRepository._has_sort_order
            else "NULL AS sort_order,"
        )
        contract1_term_col = (
            "contract1_term,"
            if EmployeeRepository._has_contract1_term
            else "NULL AS contract1_term,"
        )

        sql = sql.format(
            sort_order_col=sort_order_col, contract1_term_col=contract1_term_col
        )
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=True)
            cursor.execute(sql, (code,))
            return cursor.fetchone()

    def get_employee(self, employee_id: int) -> dict[str, Any] | None:
        self.ensure_import_schema()
        sql = """
            SELECT
                id,
                {sort_order_col}
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
                {contract1_term_col}
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
        sort_order_col = (
            "sort_order,"
            if EmployeeRepository._has_sort_order
            else "NULL AS sort_order,"
        )
        contract1_term_col = (
            "contract1_term,"
            if EmployeeRepository._has_contract1_term
            else "NULL AS contract1_term,"
        )
        sql = sql.format(
            sort_order_col=sort_order_col, contract1_term_col=contract1_term_col
        )
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=True)
            cursor.execute(sql, (int(employee_id),))
            return cursor.fetchone()

    def create_employee(self, data: dict[str, Any]) -> int:
        self.ensure_import_schema()
        if (
            EmployeeRepository._has_contract1_term
            and EmployeeRepository._has_sort_order
        ):
            sql = """
                INSERT INTO employees (
                    sort_order,
                    employee_code, full_name, start_date, title_id, department_id,
                    date_of_birth, gender, national_id, id_issue_date, id_issue_place,
                    address, phone, insurance_no, tax_code, degree, major,
                    contract1_signed, contract1_term, contract1_no, contract1_sign_date, contract1_expire_date,
                    contract2_indefinite, contract2_no, contract2_sign_date,
                    children_count, child_dob_1, child_dob_2, child_dob_3, child_dob_4,
                    note
                ) VALUES (
                    %s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s
                )
            """
        else:
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
            if (
                EmployeeRepository._has_contract1_term
                and EmployeeRepository._has_sort_order
            ):
                cursor.execute(
                    sql,
                    (
                        data.get("sort_order"),
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
                        data.get("contract1_term"),
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
            else:
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

    def get_next_sort_order(self) -> int | None:
        """Return the next STT (sort_order) value for a newly created employee.

        - If employees.sort_order exists: returns MAX(sort_order) + 1 (or 1 if empty).
        - If the column does not exist: returns None.
        """

        self.ensure_import_schema()
        if not EmployeeRepository._has_sort_order:
            return None

        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM employees")
            row = cursor.fetchone()
            try:
                return int(row[0]) if row and row[0] is not None else 1
            except Exception:
                return 1

    def update_employee(self, employee_id: int, data: dict[str, Any]) -> int:
        self.ensure_import_schema()
        if (
            EmployeeRepository._has_contract1_term
            and EmployeeRepository._has_sort_order
        ):
            sql = """
                UPDATE employees
                SET
                    sort_order = COALESCE(%s, sort_order),
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
                    contract1_term = COALESCE(%s, contract1_term),
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
        else:
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
            if (
                EmployeeRepository._has_contract1_term
                and EmployeeRepository._has_sort_order
            ):
                cursor.execute(
                    sql,
                    (
                        data.get("sort_order"),
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
                        data.get("contract1_term"),
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
            else:
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

    def delete_employees_bulk(self, employee_ids: list[int]) -> int:
        ids = [int(i) for i in (employee_ids or []) if int(i) > 0]
        if not ids:
            return 0

        # Avoid extremely long IN lists.
        placeholders = ",".join(["%s"] * len(ids))
        sql = f"DELETE FROM employees WHERE id IN ({placeholders})"
        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute(sql, tuple(ids))
            conn.commit()
            return int(cursor.rowcount)

    def resequence_sort_order(self) -> None:
        """Renumber employees.sort_order to be 1..N in current list order.

        This keeps STT contiguous after deletions when sort_order is used.
        """

        self.ensure_import_schema()
        if not EmployeeRepository._has_sort_order:
            return

        with Database.connect() as conn:
            cursor = Database.get_cursor(conn, dictionary=False)
            cursor.execute("SET @row := 0")
            cursor.execute(
                """
                UPDATE employees e
                JOIN (
                    SELECT id, (@row := @row + 1) AS rn
                    FROM employees
                    ORDER BY (sort_order IS NULL) ASC, sort_order ASC, id ASC
                ) t ON t.id = e.id
                SET e.sort_order = t.rn
                """
            )
            conn.commit()

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

        self.ensure_import_schema()
        if EmployeeRepository._has_sort_order:
            stt_expr = "COALESCE(e.sort_order, (SELECT COUNT(*) FROM employees e2 WHERE e2.id > e.id) + 1)"
            order_by = "ORDER BY (e.sort_order IS NULL) ASC, e.sort_order ASC, e.id ASC"
        else:
            stt_expr = "(SELECT COUNT(*) FROM employees e2 WHERE e2.id > e.id) + 1"
            order_by = "ORDER BY e.id DESC"

        contract1_term_sel = (
            "e.contract1_term"
            if EmployeeRepository._has_contract1_term
            else "NULL AS contract1_term"
        )

        sql = f"""
            SELECT
                e.id,
                {stt_expr} AS stt,
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
                {contract1_term_sel},
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
            {order_by}
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
            try:
                stt_val = int(r.get("stt") or 0)
            except Exception:
                stt_val = 0
            out.append(
                {
                    "id": r.get("id"),
                    # STT comes from sort_order (Excel order) when available; otherwise falls back to stable rank.
                    "stt": stt_val if stt_val > 0 else idx,
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
                    "contract1_term": r.get("contract1_term"),
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

        self.ensure_import_schema()

        if not items:
            return 0, 0

        if (
            EmployeeRepository._has_contract1_term
            and EmployeeRepository._has_sort_order
        ):
            sql = """
                INSERT INTO employees (
                    sort_order,
                    employee_code, full_name, start_date, title_id, department_id,
                    date_of_birth, gender, national_id, id_issue_date, id_issue_place,
                    address, phone, insurance_no, tax_code, degree, major,
                    contract1_signed, contract1_term, contract1_no, contract1_sign_date, contract1_expire_date,
                    contract2_indefinite, contract2_no, contract2_sign_date,
                    children_count, child_dob_1, child_dob_2, child_dob_3, child_dob_4,
                    note
                ) VALUES (
                    %s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    sort_order = VALUES(sort_order),
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
                    contract1_term = VALUES(contract1_term),
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
        else:
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

            if (
                EmployeeRepository._has_contract1_term
                and EmployeeRepository._has_sort_order
            ):
                params.append(
                    (
                        it.get("sort_order"),
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
                        it.get("contract1_term"),
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
            else:
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
