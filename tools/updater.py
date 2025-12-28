"""tools/updater.py

Updater tối giản cho mô hình Updater + Patch.

Luồng:
1) Đọc update.json (local hoặc URL)
2) Download patch zip (nếu là URL)
3) Verify SHA256 patch zip (nếu update.json có trường sha256)
4) Apply patch bằng tools/apply_patch.py
5) Launch lại myapp.exe (tuỳ chọn)

Ví dụ:
  python tools/updater.py --update-json updates/update_1.0.2.json --target-dir "$env:LOCALAPPDATA/myapp"

  python tools/updater.py --update-json https://your-host/update_1.0.2.json --target-dir "C:/Users/<you>/AppData/Local/myapp"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any

import ctypes

from tools.patchlib import apply_patch_zip


BUFFER_SIZE = 1024 * 1024


_INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
_FILE_ATTRIBUTE_HIDDEN = 0x2
_FILE_ATTRIBUTE_SYSTEM = 0x4


def _set_hidden_system(path: Path) -> None:
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        attrs = kernel32.GetFileAttributesW(str(path))
        if attrs == _INVALID_FILE_ATTRIBUTES:
            return
        new_attrs = int(attrs) | _FILE_ATTRIBUTE_HIDDEN | _FILE_ATTRIBUTE_SYSTEM
        kernel32.SetFileAttributesW(str(path), new_attrs)
    except Exception:
        # Best-effort; do not fail update if we cannot set attributes
        return


def _rehide_app_folders(target_dir: Path) -> None:
    for folder_name in ("assets", "database"):
        folder = target_dir / folder_name
        if not folder.exists():
            continue
        _set_hidden_system(folder)
        try:
            for child in folder.rglob("*"):
                _set_hidden_system(child)
        except Exception:
            continue

    # Also hide the SQL bootstrap file if shipped.
    _set_hidden_system(target_dir / "creater_database.SQL")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def is_url(value: str) -> bool:
    v = (value or "").strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def read_text_from_url(url: str) -> str:
    with urllib.request.urlopen(url) as resp:  # nosec - user-controlled URL by design
        data = resp.read()
    return data.decode("utf-8")


def download_to_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp:  # nosec - user-controlled URL by design
        with dest.open("wb") as f:
            while True:
                chunk = resp.read(BUFFER_SIZE)
                if not chunk:
                    break
                f.write(chunk)


def load_update_json(source: str) -> dict[str, Any]:
    if is_url(source):
        raw = read_text_from_url(source)
    else:
        raw = Path(source).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"update.json không hợp lệ: {exc}")

    if not isinstance(payload, dict):
        raise SystemExit("update.json phải là object JSON")
    return payload


def resolve_patch_ref(update_source: str, patch_ref: str) -> str:
    """Resolve patch reference.

    - If patch_ref is URL: return as-is.
    - If update_source is URL and patch_ref is relative: join with update_source.
    - If update_source is local file and patch_ref is relative: resolve relative to update_source's folder.
    """

    patch_ref = (patch_ref or "").strip()
    update_source = (update_source or "").strip()
    if not patch_ref:
        return patch_ref

    if is_url(patch_ref):
        return patch_ref

    if is_url(update_source):
        # Allow patch path like "patch.zip" or "../patches/patch.zip" or "/patches/patch.zip"
        return urllib.parse.urljoin(update_source, patch_ref)

    # Local file mode
    patch_path = Path(patch_ref)
    if patch_path.is_absolute():
        return str(patch_path)

    # Primary: relative to update.json location
    try:
        base_dir = Path(update_source).resolve().parent
        return str((base_dir / patch_path).resolve())
    except Exception:
        # Fallback: relative to current working directory
        return str(patch_path.resolve())


def apply_patch(patch_path: Path, target_dir: Path, force: bool) -> None:
    apply_patch_zip(
        patch_path=patch_path,
        target_dir=target_dir,
        backup_dir=None,
        dry_run=False,
        force=force,
    )

    # Keep bundled folders hidden after patch updates.
    _rehide_app_folders(target_dir)


def _default_base_dir() -> Path:
    # When frozen (PyInstaller onefile), sys.executable points to version.exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _default_update_json() -> str | None:
    # 1) env var (useful for QA/automation)
    env = (os.environ.get("MYAPP_UPDATE_JSON") or "").strip()
    if env:
        return env

    # 2) update.json placed next to version.exe
    candidate = _default_base_dir() / "update.json"
    if candidate.exists():
        return str(candidate)
    return None


def _default_target_dir() -> str | None:
    # Default install dir per installer: C:\Program Files\attendance
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        return str(Path(program_files) / "attendance")

    # Fallback (older installs/dev): %LOCALAPPDATA%\attendance
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return str(Path(local_app_data) / "attendance")
    return None


def _pause_if_needed(enabled: bool) -> None:
    if not enabled:
        return
    try:
        input("\nNhấn Enter để thoát...")
    except EOFError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Updater + Patch (minimal)")
    parser.add_argument(
        "--update-json",
        default=None,
        help="Đường dẫn hoặc URL tới update.json (mặc định: update.json cạnh version.exe hoặc env MYAPP_UPDATE_JSON)",
    )
    parser.add_argument(
        "--target-dir",
        default=None,
        help="Thư mục cài app (onedir) để cập nhật (mặc định: %LOCALAPPDATA%\\myapp)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bỏ qua kiểm tra old_sha256 (không khuyến nghị)",
    )
    parser.add_argument(
        "--no-launch", action="store_true", help="Không mở lại app sau khi update"
    )
    parser.add_argument(
        "--exe",
        default="phần mềm chấm công tam niên.exe",
        help="Tên file exe để launch lại (mặc định: phần mềm chấm công tam niên.exe)",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="Giữ cửa sổ console để xem thông báo (hữu ích khi double-click)",
    )
    args = parser.parse_args()

    update_source = (args.update_json or "").strip() or _default_update_json()
    target_dir_str = (args.target_dir or "").strip() or _default_target_dir()

    # Nếu user không truyền tham số thì bật pause mặc định để không bị out ngay
    auto_pause = args.pause or (not (args.update_json and args.target_dir))

    try:
        if not update_source:
            raise SystemExit(
                "❌ Thiếu update.json\n"
                "- Cách 1: đặt file update.json cạnh version.exe\n"
                "- Cách 2: chạy kèm tham số --update-json <URL|PATH>\n"
                "- Cách 3: set env MYAPP_UPDATE_JSON=<URL|PATH>"
            )

        if not target_dir_str:
            raise SystemExit(
                "❌ Không xác định được target-dir\n"
                "- Hãy chạy kèm --target-dir <PATH>"
            )

        target_dir = Path(target_dir_str).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            raise SystemExit(
                f"Target dir không tồn tại hoặc không phải thư mục: {target_dir}"
            )

        update = load_update_json(update_source)

        patch_ref_raw = str(update.get("patch") or "").strip()
        patch_ref = resolve_patch_ref(update_source, patch_ref_raw)
        if not patch_ref:
            raise SystemExit(
                "update.json thiếu trường 'patch' (URL hoặc đường dẫn patch zip)"
            )

        expected_zip_sha = str(update.get("sha256") or "").strip().lower() or None

        with tempfile.TemporaryDirectory(prefix="updater_") as tmp:
            tmp_dir = Path(tmp)
            patch_path = tmp_dir / "patch.zip"

            if is_url(patch_ref):
                print(f"⬇️  Download patch: {patch_ref}")
                download_to_file(patch_ref, patch_path)
            else:
                src = Path(patch_ref).resolve()
                if not src.exists() or not src.is_file():
                    raise SystemExit(
                        "Patch file không tồn tại: "
                        + str(src)
                        + "\n"
                        + "- patch trong update.json đang là: "
                        + patch_ref_raw
                        + "\n"
                        + "- Bạn cần tạo patch zip hoặc sửa patch thành URL/đường dẫn đúng."
                    )
                patch_path = src

            if expected_zip_sha:
                actual = sha256_file(patch_path).lower()
                if actual != expected_zip_sha:
                    raise SystemExit(
                        "SHA256 patch zip không khớp (download hỏng hoặc bị thay đổi)"
                    )

            print("🧩 Applying patch...")
            apply_patch(patch_path=patch_path, target_dir=target_dir, force=args.force)

        if args.no_launch:
            print("✅ Update done (no-launch)")
            _pause_if_needed(auto_pause)
            return 0

        exe_path = target_dir / args.exe
        if not exe_path.exists():
            print(f"⚠️  Không tìm thấy exe để launch: {exe_path}")
            print("✅ Update done")
            _pause_if_needed(auto_pause)
            return 0

        print(f"🚀 Launch: {exe_path}")
        subprocess.Popen([str(exe_path)], cwd=str(target_dir))
        print("✅ Update done")
        _pause_if_needed(auto_pause)
        return 0

    except SystemExit as exc:
        code = getattr(exc, "code", 1)
        if isinstance(code, str):
            print(code)
            code = 1
        elif code is None:
            code = 0
        _pause_if_needed(auto_pause)
        return int(code)
    except Exception as exc:
        print(f"❌ Lỗi không mong muốn: {exc}")
        _pause_if_needed(auto_pause)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
