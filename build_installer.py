"""build_installer.py

Chạy 1 lệnh để:
1) Build app EXE (PyInstaller onedir) -> dist/<app_internal_name>/<app_internal_name>.exe
2) Build installer (Inno Setup) -> dist/installer/<app_internal_name>-setup.exe

Yêu cầu:
- Python env đã có PyInstaller (pip install pyinstaller)
- Máy có Inno Setup 6 (ISCC.exe)

Cách dùng:
  python build_installer.py

Tuỳ chọn:
  python build_installer.py --clean
  python build_installer.py --iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
ISS_PATH = PROJECT_ROOT / "installer" / "myapp.iss"


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("▶", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _parse_iss_defines(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"Không tìm thấy Inno script: {path}")

    defines: dict[str, str] = {}
    pattern = re.compile(r"^\s*#define\s+(?P<key>\w+)\s+\"(?P<val>.*)\"\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            defines[m.group("key")] = m.group("val")
    return defines


def _find_iscc(explicit: str | None) -> str:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        raise SystemExit(f"Không tìm thấy ISCC tại: {p}")

    # 1) PATH
    which = shutil.which("iscc") or shutil.which("ISCC")
    if which:
        return which

    # 2) Common install locations
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    raise SystemExit(
        "Không tìm thấy Inno Setup Compiler (ISCC.exe).\n"
        "- Cài Inno Setup 6\n"
        '- Hoặc chạy kèm: python build_installer.py --iscc "<path_to_ISCC.exe>"'
    )


def _try_remove(path: Path, *, attempts: int = 6, delay_sec: float = 0.5) -> None:
    if not path.exists():
        return

    last_exc: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            path.unlink()
            return
        except Exception as exc:
            last_exc = exc
            time.sleep(max(0.0, delay_sec))

    raise SystemExit(
        "Không thể ghi đè installer vì file đang được sử dụng:\n"
        f"- {path}\n"
        "Hãy đóng file (Explorer/antivirus/đang chạy) rồi chạy lại.\n"
        f"Chi tiết lỗi: {last_exc}"
    )


def _ensure_inno_setup_icon(root: Path) -> None:
    """Inno Setup's SetupIconFile must be a real .ico (not a renamed PNG)."""
    # In this repo, assets/icons/app.ico is actually a PNG file.
    src_png = root / "assets" / "icons" / "app.ico"
    if not src_png.exists():
        src_png = root / "assets" / "icons" / "app.png"
    dst_ico = root / "assets" / "icons" / "app_converted.ico"

    if not src_png.exists():
        return

    # Only (re)generate when needed
    if dst_ico.exists() and dst_ico.stat().st_mtime >= src_png.stat().st_mtime:
        return

    try:
        img = Image.open(src_png)
        img.save(
            dst_ico,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    except Exception as e:
        raise RuntimeError(f"Không thể tạo icon .ico cho Inno Setup: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build EXE + Installer (Inno Setup)")
    parser.add_argument("--clean", action="store_true", help="Clean PyInstaller cache")
    parser.add_argument(
        "--iscc",
        default=None,
        help="Đường dẫn ISCC.exe (nếu không có trong PATH)",
    )
    args = parser.parse_args()

    defines = _parse_iss_defines(ISS_PATH)
    app_internal_name = (defines.get("MyAppInternalName") or "attendance").strip()

    # 1) Build app exe (onedir)
    cmd = [sys.executable, "build_exe.py", "--name", app_internal_name]
    if args.clean:
        cmd.append("--clean")
    _run(cmd, cwd=PROJECT_ROOT)

    dist_dir = PROJECT_ROOT / "dist" / app_internal_name
    exe_path = dist_dir / f"{app_internal_name}.exe"
    if not exe_path.exists():
        raise SystemExit(
            "Build xong nhưng không thấy file exe mong đợi:\n"
            f"- Expected: {exe_path}\n"
            "Gợi ý: kiểm tra PyInstaller output trong dist/"
        )

    # Ensure SetupIconFile points to a valid .ico before compiling .iss
    _ensure_inno_setup_icon(PROJECT_ROOT)
    icon_path = PROJECT_ROOT / "assets" / "icons" / "app_converted.ico"
    if not icon_path.exists():
        raise SystemExit(
            "Không tìm thấy icon .ico cho Inno Setup (SetupIconFile).\n"
            f"- Expected: {icon_path}\n"
            "Gợi ý: kiểm tra file nguồn icon trong assets/icons và thử chạy lại."
        )

    # 2) Build installer via Inno
    installer_out = (
        PROJECT_ROOT / "dist" / "installer" / f"{app_internal_name}-setup.exe"
    )
    _try_remove(installer_out)

    iscc = _find_iscc(args.iscc)
    _run([iscc, str(ISS_PATH)], cwd=ISS_PATH.parent)

    print("✅ Done")
    print(f"- EXE: {exe_path}")
    print(f"- Installer folder: {PROJECT_ROOT / 'dist' / 'installer'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
