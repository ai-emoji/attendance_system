"""ui.dialog.login_dialog

Dialog đăng nhập cho ứng dụng.

Yêu cầu:
- Khi khởi tạo app: hiển thị dialog đăng nhập trước.
- Đăng nhập thành công -> vào MainWindow.
- Lưu dữ liệu tài khoản ở database/ui_login.json.
- Tạo sẵn tài khoản mặc định: tamnien / tamnien123.

Ghi chú:
- Dữ liệu mật khẩu được lưu dạng hash + salt (không lưu plain-text).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import base64
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.resource import (
    COLOR_BG_HEADER,
    COLOR_BORDER,
    COLOR_BUTTON_CANCEL,
    COLOR_BUTTON_CANCEL_HOVER,
    COLOR_BUTTON_PRIMARY,
    COLOR_BUTTON_PRIMARY_HOVER,
    COLOR_ERROR,
    COLOR_SUCCESS,
    CONTENT_FONT,
    FONT_WEIGHT_NORMAL,
    FONT_WEIGHT_SEMIBOLD,
    INPUT_COLOR_BG,
    INPUT_COLOR_BORDER,
    INPUT_COLOR_BORDER_FOCUS,
    INPUT_HEIGHT_DEFAULT,
    INPUT_WIDTH_DEFAULT,
    MAIN_CONTENT_BG_COLOR,
    UI_FONT,
)


from core.resource import user_data_dir


_LOGIN_JSON_PATH = user_data_dir("pmctn") / "database" / "ui_login.json"
_DEFAULT_USER = "tamnien"
_DEFAULT_PASS = "tamnien123"
_DEFAULT_RECOVERY_QUESTION = "duongphuc1510"
_MODE_LOGIN = "login"
_MODE_CHANGE_PASSWORD = "change_password"
_MODE_RECOVER_PASSWORD = "recover_password"


@dataclass(frozen=True)
class _UserRecord:
    username: str
    salt_hex: str
    hash_hex: str
    iterations: int


def _derive_recovery_key(question: str) -> bytes:
    q = (question or "").encode("utf-8", errors="ignore")
    return hashlib.sha256(q).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not data:
        return b""
    if not key:
        return data
    out = bytearray(len(data))
    klen = len(key)
    for i, b in enumerate(data):
        out[i] = b ^ key[i % klen]
    return bytes(out)


def _encrypt_password_recovery(plain_password: str, *, question: str) -> str:
    pw = (plain_password or "").encode("utf-8", errors="ignore")
    key = _derive_recovery_key(question)
    enc = _xor_bytes(pw, key)
    return base64.urlsafe_b64encode(enc).decode("ascii", errors="ignore")


def _decrypt_password_recovery(enc_b64: str, *, question: str) -> str:
    if not enc_b64:
        return ""
    try:
        raw = base64.urlsafe_b64decode((enc_b64 or "").encode("ascii", errors="ignore"))
    except Exception:
        return ""
    key = _derive_recovery_key(question)
    dec = _xor_bytes(raw, key)
    try:
        return dec.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _pbkdf2_sha256(password: str, salt: bytes, iterations: int) -> bytes:
    pw = (password or "").encode("utf-8", errors="ignore")
    return hashlib.pbkdf2_hmac("sha256", pw, salt, int(iterations))


def _make_record(
    username: str, password: str, *, iterations: int = 200_000
) -> _UserRecord:
    salt = secrets.token_bytes(16)
    digest = _pbkdf2_sha256(password, salt, iterations)
    return _UserRecord(
        username=str(username or "").strip(),
        salt_hex=salt.hex(),
        hash_hex=digest.hex(),
        iterations=int(iterations),
    )


def _load_login_store() -> dict:
    try:
        if _LOGIN_JSON_PATH.exists():
            with _LOGIN_JSON_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {
        "version": 1,
        "users": [],
        "last_username": "",
        "logged_in": False,
        "recovery_question": _DEFAULT_RECOVERY_QUESTION,
    }


def _save_login_store(data: dict) -> None:
    _LOGIN_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _LOGIN_JSON_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data or {}, f, ensure_ascii=False, indent=2)
    try:
        tmp.replace(_LOGIN_JSON_PATH)
    except Exception:
        # Fallback: best-effort
        with _LOGIN_JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(data or {}, f, ensure_ascii=False, indent=2)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def ensure_default_account() -> None:
    data = _load_login_store()

    # Enforce default recovery question (fixed, cannot be edited).
    data["recovery_question"] = _DEFAULT_RECOVERY_QUESTION

    users = data.get("users")
    if not isinstance(users, list):
        users = []

    # Only auto-create the default account on first run (empty store).
    # If users already exist, do NOT recreate the default user, otherwise
    # renaming/removing it would keep coming back.
    has_any_user = False
    for u0 in users:
        try:
            if not isinstance(u0, dict):
                continue
            if str(u0.get("username") or "").strip():
                has_any_user = True
                break
        except Exception:
            continue

    exists_idx: int | None = None
    for i, u in enumerate(users):
        try:
            if str(u.get("username") or "").strip().lower() == _DEFAULT_USER.lower():
                exists_idx = int(i)
                break
        except Exception:
            continue

    # If default user exists but missing credentials, repair it.
    must_create = False
    if exists_idx is not None:
        try:
            cur = users[exists_idx] if isinstance(users[exists_idx], dict) else {}
            salt = str(cur.get("salt") or "").strip()
            h = str(cur.get("hash") or "").strip()
            if not salt or not h:
                must_create = True
        except Exception:
            must_create = True
    elif not has_any_user:
        # First-run: no accounts exist -> create the default one.
        must_create = True

    if must_create:
        rec = _make_record(_DEFAULT_USER, _DEFAULT_PASS)
        item = {
            "username": rec.username,
            "salt": rec.salt_hex,
            "hash": rec.hash_hex,
            "iterations": rec.iterations,
            "password_enc": _encrypt_password_recovery(
                _DEFAULT_PASS, question=_DEFAULT_RECOVERY_QUESTION
            ),
        }
        if exists_idx is None:
            users.append(item)
        else:
            try:
                users[exists_idx] = item
            except Exception:
                users.append(item)

    data["version"] = int(data.get("version") or 1)
    data["users"] = users
    if not isinstance(data.get("last_username"), str):
        data["last_username"] = ""
    if not isinstance(data.get("logged_in"), bool):
        data["logged_in"] = False
    data["recovery_question"] = _DEFAULT_RECOVERY_QUESTION
    _save_login_store(data)


def verify_login(username: str, password: str) -> bool:
    u = str(username or "").strip()
    p = str(password or "")
    if not u or not p:
        return False

    data = _load_login_store()
    users = data.get("users")
    if not isinstance(users, list):
        return False

    for item in users:
        try:
            if str(item.get("username") or "").strip().lower() != u.lower():
                continue
            salt_hex = str(item.get("salt") or "").strip()
            hash_hex = str(item.get("hash") or "").strip()
            iters = int(item.get("iterations") or 200_000)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            got = _pbkdf2_sha256(p, salt, iters)
            return secrets.compare_digest(got, expected)
        except Exception:
            continue
    return False


def set_last_username(username: str) -> None:
    data = _load_login_store()
    data["last_username"] = str(username or "").strip()
    _save_login_store(data)


def get_last_username() -> str:
    data = _load_login_store()
    try:
        return str(data.get("last_username") or "").strip()
    except Exception:
        return ""


def is_login_required() -> bool:
    data = _load_login_store()
    try:
        return not bool(data.get("logged_in"))
    except Exception:
        return True


def set_logged_in(value: bool) -> None:
    data = _load_login_store()
    data["logged_in"] = bool(value)
    _save_login_store(data)


def update_password(username: str, new_password: str) -> bool:
    u = str(username or "").strip()
    p = str(new_password or "")
    if not u or not p:
        return False

    data = _load_login_store()
    users = data.get("users")
    if not isinstance(users, list):
        users = []

    idx: int | None = None
    for i, item in enumerate(users):
        try:
            if str(item.get("username") or "").strip().lower() == u.lower():
                idx = int(i)
                break
        except Exception:
            continue

    if idx is None:
        return False

    rec = _make_record(u, p)
    users[idx] = {
        "username": rec.username,
        "salt": rec.salt_hex,
        "hash": rec.hash_hex,
        "iterations": rec.iterations,
        "password_enc": _encrypt_password_recovery(
            p, question=_DEFAULT_RECOVERY_QUESTION
        ),
    }
    data["users"] = users
    data["recovery_question"] = _DEFAULT_RECOVERY_QUESTION
    _save_login_store(data)
    return True


def update_credentials(
    current_username: str, new_username: str, new_password: str
) -> bool:
    """Update both username and password for an existing account.

    - If `new_username` is blank, keep the current username.
    - Prevent renaming to an existing username (case-insensitive).
    """

    cur_u = str(current_username or "").strip()
    nu = str(new_username or "").strip()
    p = str(new_password or "")
    if not cur_u or not p:
        return False

    if not nu:
        nu = cur_u

    data = _load_login_store()
    users = data.get("users")
    if not isinstance(users, list):
        users = []

    idx: int | None = None
    for i, item in enumerate(users):
        try:
            if str(item.get("username") or "").strip().lower() == cur_u.lower():
                idx = int(i)
                break
        except Exception:
            continue
    if idx is None:
        return False

    # Prevent duplicate username
    if nu.lower() != cur_u.lower():
        for j, item in enumerate(users):
            try:
                if j == idx:
                    continue
                if str(item.get("username") or "").strip().lower() == nu.lower():
                    return False
            except Exception:
                continue

    rec = _make_record(nu, p)
    users[idx] = {
        "username": rec.username,
        "salt": rec.salt_hex,
        "hash": rec.hash_hex,
        "iterations": rec.iterations,
        "password_enc": _encrypt_password_recovery(
            p, question=_DEFAULT_RECOVERY_QUESTION
        ),
    }

    data["users"] = users
    data["last_username"] = rec.username
    data["recovery_question"] = _DEFAULT_RECOVERY_QUESTION
    _save_login_store(data)
    return True


def recover_password(username: str, recovery_question_input: str) -> str | None:
    u = str(username or "").strip()
    q = str(recovery_question_input or "").strip()
    if not u or not q:
        return None

    data = _load_login_store()

    # Question is fixed; enforce default regardless of file edits.
    expected_q = _DEFAULT_RECOVERY_QUESTION
    if q != expected_q:
        return None

    users = data.get("users")
    if not isinstance(users, list):
        return None

    for item in users:
        try:
            if str(item.get("username") or "").strip().lower() != u.lower():
                continue
            enc = str(item.get("password_enc") or "").strip()
            if not enc:
                return ""
            return _decrypt_password_recovery(enc, question=expected_q)
        except Exception:
            continue
    return None


class LoginDialog(QDialog):
    def __init__(self, parent=None, *, mode: str = _MODE_LOGIN) -> None:
        super().__init__(parent)
        ensure_default_account()
        self._mode = str(mode or _MODE_LOGIN)
        self._password_changed = False
        self._show_forgot_link = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setModal(True)
        self.setWindowTitle(
            "Đăng nhập" if self._mode == _MODE_LOGIN else "Đổi mật khẩu"
        )
        self.setFixedWidth(420)
        self.setStyleSheet(f"background: {MAIN_CONTENT_BG_COLOR};")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        font_normal = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_NORMAL >= 400:
            font_normal.setWeight(QFont.Weight.Normal)

        font_button = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            font_button.setWeight(QFont.Weight.DemiBold)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel(
            "Đăng nhập hệ thống" if self._mode == _MODE_LOGIN else "Đổi mật khẩu"
        )
        title_font = QFont(UI_FONT, CONTENT_FONT)
        if FONT_WEIGHT_SEMIBOLD >= 500:
            title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)

        form = QWidget(self)
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)

        def _mk_label(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setFont(font_normal)
            return lb

        def _mk_line_edit(*, placeholder: str, password: bool = False) -> QLineEdit:
            le = QLineEdit(self)
            le.setFont(font_normal)
            le.setFixedHeight(INPUT_HEIGHT_DEFAULT)
            le.setMinimumWidth(INPUT_WIDTH_DEFAULT)
            le.setPlaceholderText(placeholder)
            le.setStyleSheet(
                "\n".join(
                    [
                        f"QLineEdit {{ background: {INPUT_COLOR_BG}; border: 1px solid {INPUT_COLOR_BORDER}; padding: 0 8px; border-radius: 6px; }}",
                        f"QLineEdit:focus {{ border: 1px solid {INPUT_COLOR_BORDER_FOCUS}; }}",
                    ]
                )
            )
            if password:
                le.setEchoMode(QLineEdit.EchoMode.Password)
            return le

        self.lbl_user = _mk_label("Tài khoản")
        self.inp_user = _mk_line_edit(placeholder="Nhập tài khoản")

        self.lbl_new_user = _mk_label("Tài khoản mới")
        self.inp_new_user = _mk_line_edit(
            placeholder="Nhập tài khoản mới (nếu muốn đổi)"
        )

        self.lbl_pass = _mk_label("Mật khẩu")
        self.inp_pass = _mk_line_edit(placeholder="Nhập mật khẩu", password=True)

        self.lbl_new_pass = _mk_label("Mật khẩu mới")
        self.inp_new_pass = _mk_line_edit(
            placeholder="Nhập mật khẩu mới", password=True
        )

        self.lbl_recovery_question = _mk_label("Câu hỏi bí mật")
        self.inp_recovery_question = _mk_line_edit(
            placeholder="Nhập câu hỏi bí mật", password=True
        )

        # Prefill last username if available
        try:
            last = get_last_username()
            if last:
                self.inp_user.setText(last)
        except Exception:
            pass

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMinimumHeight(18)
        self.lbl_status.setFont(font_normal)

        # Shown only after failed login; replaces the old "Tìm lại" button.
        self.lbl_forgot_link = QLabel('<a href="recover">Tìm lại mật khẩu</a>')
        try:
            self.lbl_forgot_link.setFont(font_normal)
            self.lbl_forgot_link.setTextFormat(Qt.TextFormat.RichText)
            self.lbl_forgot_link.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextBrowserInteraction
            )
            self.lbl_forgot_link.setOpenExternalLinks(False)
            self.lbl_forgot_link.linkActivated.connect(lambda _h: self._on_forgot())
            self.lbl_forgot_link.setStyleSheet(
                f"color: {COLOR_BUTTON_PRIMARY}; text-decoration: underline;"
            )
        except Exception:
            pass
        self.lbl_forgot_link.setVisible(False)

        form_layout.addWidget(self.lbl_user)
        form_layout.addWidget(self.inp_user)
        form_layout.addWidget(self.lbl_new_user)
        form_layout.addWidget(self.inp_new_user)
        form_layout.addWidget(self.lbl_pass)
        form_layout.addWidget(self.inp_pass)
        form_layout.addWidget(self.lbl_new_pass)
        form_layout.addWidget(self.inp_new_pass)
        form_layout.addWidget(self.lbl_recovery_question)
        form_layout.addWidget(self.inp_recovery_question)
        form_layout.addWidget(self.lbl_status)
        form_layout.addWidget(self.lbl_forgot_link)

        btn_row = QWidget(self)
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        self.btn_primary = QPushButton(
            "Đăng nhập" if self._mode == _MODE_LOGIN else "Đổi mật khẩu"
        )
        self.btn_primary.setFont(font_button)
        self.btn_primary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary.setFixedHeight(36)
        self.btn_primary.setAutoDefault(True)
        self.btn_primary.setDefault(True)
        self.btn_primary.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_PRIMARY}; color: {COLOR_BG_HEADER}; border: none; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_PRIMARY_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_toggle_mode = QPushButton(
            "Đổi mật khẩu" if self._mode == _MODE_LOGIN else "Quay lại"
        )
        self.btn_toggle_mode.setFont(font_button)
        self.btn_toggle_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_mode.setFixedHeight(36)
        self.btn_toggle_mode.setAutoDefault(False)
        self.btn_toggle_mode.setDefault(False)
        self.btn_toggle_mode.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_CANCEL}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_CANCEL_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_cancel = QPushButton("Thoát")
        self.btn_cancel.setFont(font_button)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(36)
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setStyleSheet(
            "\n".join(
                [
                    f"QPushButton {{ background-color: {COLOR_BUTTON_CANCEL}; color: {COLOR_BG_HEADER}; border: 1px solid {COLOR_BORDER}; border-radius: 8px; padding: 0 14px; }}",
                    f"QPushButton:hover {{ background-color: {COLOR_BUTTON_CANCEL_HOVER}; }}",
                    "QPushButton:pressed { opacity: 0.85; }",
                ]
            )
        )

        self.btn_primary.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_toggle_mode.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_cancel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        btn_layout.addWidget(self.btn_primary, 1)
        btn_layout.addWidget(self.btn_toggle_mode, 1)
        btn_layout.addWidget(self.btn_cancel, 1)

        root.addWidget(title)
        root.addWidget(form)
        root.addStretch(1)
        root.addWidget(btn_row)

        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_primary.clicked.connect(self._on_primary)
        self.btn_toggle_mode.clicked.connect(self._on_toggle_mode)
        self.inp_user.returnPressed.connect(self.btn_primary.click)
        self.inp_new_user.returnPressed.connect(self.btn_primary.click)
        self.inp_pass.returnPressed.connect(self.btn_primary.click)
        self.inp_new_pass.returnPressed.connect(self.btn_primary.click)
        self.inp_recovery_question.returnPressed.connect(self.btn_primary.click)

        self._apply_mode_ui()

        # Focus
        self._focus_for_mode()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Ensure the dialog is placed within a visible screen area.
        try:
            screen = None
            try:
                parent = self.parent()
                if parent is not None and hasattr(parent, "screen"):
                    screen = parent.screen()
            except Exception:
                screen = None

            if screen is None:
                try:
                    screen = self.screen()
                except Exception:
                    screen = None

            if screen is None:
                try:
                    screen = QApplication.primaryScreen()
                except Exception:
                    screen = None

            if screen is None:
                return

            available = screen.availableGeometry()
            frame = self.frameGeometry()
            frame.moveCenter(available.center())

            x = frame.left()
            y = frame.top()
            x = max(available.left(), min(x, available.right() - frame.width() + 1))
            y = max(available.top(), min(y, available.bottom() - frame.height() + 1))
            self.move(QPoint(x, y))
        except Exception:
            pass

    def _apply_mode_ui(self) -> None:
        is_change = self._mode == _MODE_CHANGE_PASSWORD
        is_recover = self._mode == _MODE_RECOVER_PASSWORD
        try:
            self.lbl_new_user.setVisible(is_change)
            self.inp_new_user.setVisible(is_change)
            self.lbl_new_pass.setVisible(is_change)
            self.inp_new_pass.setVisible(is_change)
            self.lbl_recovery_question.setVisible(is_recover)
            self.inp_recovery_question.setVisible(is_recover)
        except Exception:
            pass

        try:
            if is_recover:
                self.btn_primary.setText("Hiển thị")
            else:
                self.btn_primary.setText(
                    "Đăng nhập" if not is_change else "Đổi mật khẩu"
                )
        except Exception:
            pass

        try:
            if is_recover:
                self.btn_toggle_mode.setText("Quay lại")
            else:
                self.btn_toggle_mode.setText(
                    "Đổi mật khẩu" if not is_change else "Quay lại"
                )
        except Exception:
            pass

        try:
            self.lbl_forgot_link.setVisible(
                self._mode == _MODE_LOGIN and bool(self._show_forgot_link)
            )
        except Exception:
            pass

        try:
            if is_recover:
                self.setWindowTitle("Tìm lại mật khẩu")
            else:
                self.setWindowTitle("Đăng nhập" if not is_change else "Đổi mật khẩu")
        except Exception:
            pass

        try:
            self.lbl_status.setText("")
        except Exception:
            pass

    def _focus_for_mode(self) -> None:
        try:
            if self._mode == _MODE_RECOVER_PASSWORD:
                if self.inp_user.text().strip():
                    self.inp_recovery_question.setFocus()
                else:
                    self.inp_user.setFocus()
                return

            if self._mode == _MODE_CHANGE_PASSWORD:
                if self.inp_user.text().strip():
                    self.inp_pass.setFocus()
                else:
                    self.inp_user.setFocus()
                return

            # login mode
            if self.inp_user.text().strip():
                self.inp_pass.setFocus()
            else:
                self.inp_user.setFocus()
        except Exception:
            pass

    def _on_toggle_mode(self) -> None:
        self._show_forgot_link = False
        if self._mode == _MODE_RECOVER_PASSWORD:
            self._mode = _MODE_LOGIN
        elif self._mode == _MODE_CHANGE_PASSWORD:
            self._mode = _MODE_LOGIN
        else:
            self._mode = _MODE_CHANGE_PASSWORD
        self._apply_mode_ui()
        self._focus_for_mode()

    def _on_forgot(self) -> None:
        self._show_forgot_link = False
        self._mode = _MODE_RECOVER_PASSWORD
        try:
            self.lbl_status.setText("")
        except Exception:
            pass
        self._apply_mode_ui()
        self._focus_for_mode()

    def _on_primary(self) -> None:
        if self._mode == _MODE_RECOVER_PASSWORD:
            self._on_recover_password()
            return
        if self._mode == _MODE_CHANGE_PASSWORD:
            self._on_change_password()
            return
        self._on_login()

    def _set_status(self, message: str, ok: bool) -> None:
        self.lbl_status.setStyleSheet(f"color: {COLOR_SUCCESS if ok else COLOR_ERROR};")
        self.lbl_status.setText(str(message or ""))

    def _on_login(self) -> None:
        u = (self.inp_user.text() or "").strip()
        p = self.inp_pass.text() or ""

        if not u or not p:
            self._set_status("Vui lòng nhập tài khoản và mật khẩu.", ok=False)
            return

        if verify_login(u, p):
            try:
                set_last_username(u)
            except Exception:
                pass
            try:
                set_logged_in(True)
            except Exception:
                pass
            # If user re-logged in after changing password, allow normal close.
            self._password_changed = False
            self._show_forgot_link = False
            self._set_status("Đăng nhập thành công.", ok=True)
            self.accept()
            return

        self._set_status("Sai tài khoản hoặc mật khẩu.", ok=False)
        self._show_forgot_link = True
        try:
            self.lbl_forgot_link.setVisible(self._mode == _MODE_LOGIN)
        except Exception:
            pass
        try:
            self.inp_pass.selectAll()
            self.inp_pass.setFocus()
        except Exception:
            pass

    def _on_change_password(self) -> None:
        u = (self.inp_user.text() or "").strip()
        new_u = (self.inp_new_user.text() or "").strip()
        cur = self.inp_pass.text() or ""
        new = self.inp_new_pass.text() or ""

        if not u or not cur or not new:
            self._set_status("Vui lòng nhập đầy đủ thông tin.", ok=False)
            return

        if not verify_login(u, cur):
            self._set_status("Sai tài khoản hoặc mật khẩu hiện tại.", ok=False)
            try:
                self.inp_pass.selectAll()
                self.inp_pass.setFocus()
            except Exception:
                pass
            return

        # Update both username (optional) and password.
        if not update_credentials(u, new_u, new):
            if new_u.strip() and new_u.strip().lower() != u.lower():
                self._set_status(
                    "Không thể đổi (tài khoản mới đã tồn tại hoặc lỗi dữ liệu).",
                    ok=False,
                )
            else:
                self._set_status(
                    "Không thể đổi mật khẩu (tài khoản không tồn tại).", ok=False
                )
            return

        # Normalize the displayed username to the (possibly updated) new username.
        effective_u = (new_u or u).strip()
        try:
            if effective_u:
                self.inp_user.setText(effective_u)
        except Exception:
            pass

        try:
            set_last_username(effective_u)
        except Exception:
            pass
        try:
            # Force re-login after changing password.
            set_logged_in(False)
        except Exception:
            pass

        self._password_changed = True

        # Switch back to login mode and require user to log in again.
        self._mode = _MODE_LOGIN
        self._apply_mode_ui()
        try:
            self.inp_pass.clear()
            self.inp_new_user.clear()
            self.inp_new_pass.clear()
        except Exception:
            pass
        self._set_status("Đổi thông tin thành công. Vui lòng đăng nhập lại.", ok=True)
        self._focus_for_mode()

    def _on_recover_password(self) -> None:
        # Recover password for the account currently being entered/logged in.
        u = (self.inp_user.text() or "").strip()
        q = (self.inp_recovery_question.text() or "").strip()

        if not u or not q:
            self._set_status("Vui lòng nhập tài khoản và câu hỏi bí mật.", ok=False)
            return

        pw = recover_password(u, q)
        if pw is None:
            self._set_status("Sai câu hỏi bí mật.", ok=False)
            try:
                self.inp_recovery_question.selectAll()
                self.inp_recovery_question.setFocus()
            except Exception:
                pass
            return

        if pw == "":
            self._set_status("Không có dữ liệu mật khẩu cũ để hiển thị.", ok=False)
            return

        # Show password via QMessageBox (not inline on label).
        try:
            QMessageBox.information(
                self,
                "Mật khẩu",
                f"Mật khẩu tài khoản {u}: {pw}",
            )
        except Exception:
            pass
        self._set_status("Đã hiển thị mật khẩu.", ok=True)

    def _on_cancel(self) -> None:
        # After password change, user must re-login; if they cancel, exit app.
        if self._password_changed:
            try:
                QApplication.quit()
            except Exception:
                pass
            return
        self.reject()

    def closeEvent(self, event) -> None:
        # Handle clicking window [X] after password change.
        if self._password_changed:
            try:
                QApplication.quit()
            except Exception:
                pass
        try:
            super().closeEvent(event)
        except Exception:
            pass
