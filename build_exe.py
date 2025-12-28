"""build_exe.py

Build tool đóng gói project thành .exe (Windows) bằng PyInstaller.

Mục tiêu:
- Không mất ảnh/icon (copy nguyên thư mục assets/ vào bản build).
- Hạn chế lỗi MySQL khi bundle (collect submodules/data cho mysql.connector).
- Hỗ trợ SVG (QtSvg) khi chạy bản đóng gói.

Cách dùng:
- Build dạng thư mục (khuyến nghị, ổn định nhất):
    python build_exe.py

- Build 1 file exe (tự giải nén khi chạy):
    python build_exe.py --onefile

Ghi chú:
- Cần cài PyInstaller trước: pip install pyinstaller
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore


def _add_data_arg(src: Path, dest_relative: str) -> str:
    """Tạo tham số --add-data cho PyInstaller.

    Trên Windows, format là: SRC;DEST
    """
    sep = os.pathsep  # ';' on Windows
    return f"{src}{sep}{dest_relative}"


def _ensure_valid_ico(icon_path: Path) -> Path | None:
    """Return a valid .ico path for PyInstaller.

    In this repo, assets/icons/app.ico is actually a PNG (misnamed).
    If needed and Pillow is available, convert it to assets/icons/app_converted.ico.
    """
    if not icon_path.exists():
        return None

    try:
        head = icon_path.read_bytes()[:8]
    except Exception:
        return None

    is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
    if not is_png:
        return icon_path

    converted = icon_path.with_name("app_converted.ico")
    if converted.exists() and converted.stat().st_mtime >= icon_path.stat().st_mtime:
        return converted

    if Image is None:
        print(
            "⚠️ Icon file is PNG but named .ico, and Pillow is not available to convert it:\n"
            f"- {icon_path}\n"
            "Gợi ý: cài Pillow (pip install pillow) hoặc cung cấp file .ico chuẩn."
        )
        return None

    try:
        img = Image.open(icon_path)
        img.save(
            converted,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
        return converted
    except Exception as exc:
        print(f"⚠️ Không thể convert icon sang .ico: {exc}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build EXE bằng PyInstaller")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Đóng gói thành 1 file .exe (mặc định: onedir)",
    )
    parser.add_argument(
        "--name",
        default="myapp",
        help="Tên app output (mặc định: myapp)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Xóa cache build cũ trước khi build",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    entry = project_root / "main.py"
    if not entry.exists():
        print(f"❌ Không tìm thấy entrypoint: {entry}")
        return 2

    def _run_pyinstaller(pyinstaller_args: list[str]) -> int:
        """Run PyInstaller without static imports (keeps Pylance quiet).

        Strategy:
        1) If PyInstaller module exists, import dynamically and call its run().
        2) Fallback to `python -m PyInstaller ...`.
        """

        if importlib.util.find_spec("PyInstaller") is not None:
            try:
                pyinstaller_main = importlib.import_module("PyInstaller.__main__")
                pyinstaller_main.run(pyinstaller_args)
                return 0
            except SystemExit as exc:
                return int(getattr(exc, "code", 1) or 0)
            except Exception:
                # fallback below
                pass

        try:
            completed = subprocess.run(
                [sys.executable, "-m", "PyInstaller", *pyinstaller_args],
                check=False,
            )
            return int(completed.returncode)
        except FileNotFoundError:
            print("❌ Không chạy được PyInstaller.")
            print("   Cài đặt: pip install pyinstaller")
            return 3

    assets_dir = project_root / "assets"
    icon_ico = assets_dir / "icons" / "app.ico"

    py_args: list[str] = []
    py_args += ["--noconfirm"]
    py_args += ["--name", str(args.name)]

    # GUI app
    py_args += ["--noconsole"]

    if args.clean:
        py_args += ["--clean"]

    py_args += ["--onedir" if not args.onefile else "--onefile"]

    # PyInstaller 6 uses a contents directory (default: _internal) for onedir builds.
    # User requirement: place runtime/libs directly next to the exe.
    if not args.onefile:
        py_args += ["--contents-directory", "."]

    # Icon exe
    icon_for_exe = _ensure_valid_ico(icon_ico)
    if icon_for_exe is not None:
        py_args += ["--icon", str(icon_for_exe)]

    # Ensure relative imports work
    py_args += ["--paths", str(project_root)]

    # Keep assets (icons/images)
    if assets_dir.exists():
        py_args += ["--add-data", _add_data_arg(assets_dir, "assets")]  # whole folder

    # Keep empty folders used at runtime (optional but harmless)
    database_dir = project_root / "database"
    if database_dir.exists():
        py_args += ["--add-data", _add_data_arg(database_dir, "database")]

    # Include SQL script if you ship it with the app
    sql_file = project_root / "creater_database.SQL"
    if sql_file.exists():
        # dest is a directory; place file at bundle root
        py_args += ["--add-data", _add_data_arg(sql_file, ".")]

    # PySide6 + SVG support
    py_args += ["--collect-all", "PySide6"]
    py_args += ["--hidden-import", "PySide6.QtSvg"]
    py_args += ["--hidden-import", "PySide6.QtSvgWidgets"]

    # MySQL connector: pull submodules/plugins to reduce auth/plugin missing errors
    py_args += ["--collect-submodules", "mysql.connector"]
    py_args += ["--collect-data", "mysql"]
    py_args += ["--collect-data", "mysql.connector"]
    py_args += ["--hidden-import", "mysql.connector.plugins"]
    py_args += ["--hidden-import", "mysql.connector.aio"]

    # If your MySQL server uses caching_sha2_password/sha256_password,
    # mysql-connector-python may rely on cryptography.
    if importlib.util.find_spec("cryptography") is not None:
        py_args += ["--collect-all", "cryptography"]

    # Entrypoint
    py_args += [str(entry)]

    print("📦 PyInstaller args:")
    print(" ".join([f'"{a}"' if " " in a else a for a in py_args]))

    code = _run_pyinstaller(py_args)
    if code != 0:
        return code

    dist_dir = project_root / "dist" / args.name
    if args.onefile:
        print(f"✅ Build xong. File exe ở: {project_root / 'dist'}")
    else:
        print(f"✅ Build xong. Thư mục chạy ở: {dist_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
