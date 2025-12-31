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
    python build_installer.py --iscc "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import re
import shutil
import subprocess
import sys
import time
import hashlib
from pathlib import Path
import zipfile

try:
    from PIL import Image, ImageOps  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageOps = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent
ISS_PATH = PROJECT_ROOT / "installer" / "myapp.iss"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _zip_dir(src_dir: Path, out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(src_dir.rglob("*")):
            if p.is_dir():
                continue
            zf.write(p, arcname=str(p.relative_to(src_dir)))


def _init_logger(project_root: Path) -> logging.Logger:
    log_dir = project_root / "dist" / "build_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"build_installer_{ts}.log"

    logger = logging.getLogger("build_installer")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers if script is re-entered in same process.
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)

    logger.info("Build log: %s", log_file)
    logger.info("Project root: %s", project_root)
    logger.info("Python: %s", sys.executable)
    logger.info("Args: %s", " ".join(sys.argv))
    return logger


def _run(cmd: list[str], *, cwd: Path, logger: logging.Logger) -> None:
    logger.info("▶ %s", " ".join(cmd))
    # Stream stdout+stderr to both console and log file.
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        logger.info(line.rstrip("\n"))

    rc = proc.wait()
    if rc != 0:
        logger.error("Command failed with exit code %s", rc)
        raise SystemExit(rc)


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
    """Ensure SetupIconFile points to a real .ico (not a renamed PNG).

    - Prefer using an existing assets/icons/app_converted.ico if present.
    - Otherwise attempt to generate it from assets/icons/app.ico (which in this repo
      may actually be a PNG file) or assets/icons/app.png.
    """

    dst_ico = root / "assets" / "icons" / "app_converted.ico"
    if dst_ico.exists():
        # Validate content: in this repo, some .ico files are actually PNGs.
        try:
            head = dst_ico.read_bytes()[:8]
        except Exception:
            head = b""

        is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
        # ICO header starts with: 00 00 01 00
        is_ico = len(head) >= 4 and head[:4] == b"\x00\x00\x01\x00"
        if not is_png and is_ico:
            return

        # Existing file is not a valid ICO; regenerate below.
        try:
            dst_ico.unlink()
        except Exception:
            pass

    src = root / "assets" / "icons" / "app.ico"
    if not src.exists():
        src = root / "assets" / "icons" / "app.png"
    if not src.exists():
        raise SystemExit(
            "Không tìm thấy icon nguồn để tạo app_converted.ico.\n"
            f"- Expected: {root / 'assets' / 'icons' / 'app.ico'} hoặc app.png"
        )

    if Image is None:
        raise SystemExit(
            "Thiếu Pillow nên không thể tạo icon .ico cho Inno Setup.\n"
            "- Cài: pip install pillow\n"
            f"- Hoặc tự đặt sẵn file: {dst_ico}"
        )

    try:
        img = Image.open(src)
        try:
            if ImageOps is not None:
                img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        try:
            img = img.convert("RGBA")
        except Exception:
            pass

        # Avoid distorted icons when source is not square: pad to square with transparency.
        try:
            w, h = img.size
            if int(w) > 0 and int(h) > 0 and int(w) != int(h):
                side = max(int(w), int(h))
                canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                canvas.paste(img, ((side - int(w)) // 2, (side - int(h)) // 2))
                img = canvas
        except Exception:
            pass

        img.save(
            dst_ico,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    except Exception as exc:
        raise SystemExit(f"Không thể tạo icon .ico cho Inno Setup: {exc}")


def _ensure_dist_ui_settings(project_root: Path, dist_dir: Path) -> None:
    """Make sure ui_settings.json exists in built output.

    Một số lỗi hay gặp khi đóng gói/cài đặt:
    - Thiếu file database/ui_settings.json trong dist => app crash khi đọc/ghi.
    Script này đảm bảo file tồn tại trước khi build installer.
    """

    src = project_root / "database" / "ui_settings.json"
    dst = dist_dir / "database" / "ui_settings.json"

    if dst.exists():
        return

    if not src.exists():
        raise SystemExit(
            "Không tìm thấy file cấu hình UI settings để đóng gói.\n"
            f"- Expected: {src}"
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _ensure_dist_folder(project_root: Path, dist_dir: Path, folder_name: str) -> None:
    """Ensure a whole folder exists inside dist output.

    This is a safety net to avoid missing runtime data (templates/config/assets)
    when building the installer.
    """

    src = project_root / folder_name
    dst = dist_dir / folder_name

    if dst.exists():
        return
    if not src.exists():
        return

    shutil.copytree(src, dst)


def main() -> int:
    logger = _init_logger(PROJECT_ROOT)

    parser = argparse.ArgumentParser(description="Build EXE + Installer (Inno Setup)")
    parser.add_argument("--clean", action="store_true", help="Clean PyInstaller cache")
    parser.add_argument(
        "--iscc",
        default=None,
        help="Đường dẫn ISCC.exe (nếu không có trong PATH)",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Đóng gói bản release vào releases/<version>/ (copy app folder + installer + checksum)",
    )
    parser.add_argument(
        "--release-dir",
        default=str(PROJECT_ROOT / "releases"),
        help="Thư mục releases (mặc định: ./releases)",
    )
    parser.add_argument(
        "--portable-zip",
        action="store_true",
        help="Tạo thêm file portable .zip của dist/<app> trong releases/<version>/",
    )
    args = parser.parse_args()

    defines = _parse_iss_defines(ISS_PATH)
    app_internal_name = (defines.get("MyAppInternalName") or "attendance").strip()
    app_version = (defines.get("MyAppVersion") or "0.0.0").strip()

    # 1) Build app exe (onedir)
    cmd = [sys.executable, "build_exe.py", "--name", app_internal_name]
    if args.clean:
        cmd.append("--clean")
    _run(cmd, cwd=PROJECT_ROOT, logger=logger)

    dist_dir = PROJECT_ROOT / "dist" / app_internal_name
    exe_path = dist_dir / f"{app_internal_name}.exe"
    if not exe_path.exists():
        raise SystemExit(
            "Build xong nhưng không thấy file exe mong đợi:\n"
            f"- Expected: {exe_path}\n"
            "Gợi ý: kiểm tra PyInstaller output trong dist/"
        )

    # Ensure required runtime data exists in dist (avoid ui_settings missing).
    _ensure_dist_ui_settings(PROJECT_ROOT, dist_dir)

    # Ensure other runtime data folders exist in dist.
    _ensure_dist_folder(PROJECT_ROOT, dist_dir, "assets")
    _ensure_dist_folder(PROJECT_ROOT, dist_dir, "database")
    _ensure_dist_folder(PROJECT_ROOT, dist_dir, "excel")

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
    _run([iscc, str(ISS_PATH)], cwd=ISS_PATH.parent, logger=logger)

    logger.info("✅ Done")
    logger.info("- EXE: %s", exe_path)
    logger.info("- Installer folder: %s", PROJECT_ROOT / "dist" / "installer")

    if args.release:
        releases_dir = Path(args.release_dir)
        release_root = releases_dir / app_version
        release_app_dir = release_root / app_internal_name
        release_installer_dir = release_root / "installer"
        release_installer_dir.mkdir(parents=True, exist_ok=True)

        # 3) Snapshot app folder for this version
        if release_app_dir.exists():
            shutil.rmtree(release_app_dir)
        release_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(dist_dir, release_app_dir)

        # 4) Copy installer
        release_installer = release_installer_dir / installer_out.name
        if release_installer.exists():
            _try_remove(release_installer)
        shutil.copy2(installer_out, release_installer)

        # 5) Optional portable zip
        portable_zip: Path | None = None
        if args.portable_zip:
            portable_zip = (
                release_root / f"{app_internal_name}_portable_{app_version}.zip"
            )
            _zip_dir(release_app_dir, portable_zip)

        # 6) Checksums
        checksums = release_root / "checksums.sha256"
        lines = [
            f"{_sha256_file(release_installer)}  {release_installer.name}",
        ]
        if portable_zip is not None and portable_zip.exists():
            lines.append(f"{_sha256_file(portable_zip)}  {portable_zip.name}")
        checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")

        logger.info("- Release: %s", release_root)
        logger.info("- Release installer: %s", release_installer)
        if portable_zip is not None:
            logger.info("- Release portable zip: %s", portable_zip)
        logger.info("- Release checksums: %s", checksums)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
