"""build_updater_exe.py

Chạy 1 lệnh để:
1) Build app EXE (PyInstaller onedir) -> dist/<app>/<app>.exe
2) Build updater EXE (PyInstaller spec) -> dist/version/version.exe
3) Tự tạo gói update (zip) dựa trên thay đổi so với bản release gần nhất:
   - Nếu có releases/<from_version>/<app>/ : tạo patch diff (có deletes, có old_sha256)
   - Nếu chưa có release trước: tạo "full update" (ghi old_sha256=None cho mọi file)

Output:
- Zip update: updates/update_<app>_<to_version>.zip
- Update json: updates/update_<to_version>.json (trỏ tới zip ở trên + sha256)
- Snapshot release mới: releases/<to_version>/<app>/ (để lần sau diff)

Cách dùng:
  python build_updater_exe.py

Tuỳ chọn:
  python build_updater_exe.py --clean
  python build_updater_exe.py --to-version 1.0.3
  python build_updater_exe.py --from-version 1.0.2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ISS_PATH = PROJECT_ROOT / "installer" / "myapp.iss"
UPDATER_SPEC = PROJECT_ROOT / "version.spec"

BUFFER_SIZE = 1024 * 1024


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("▶", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(cwd), check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


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


def _version_key(v: str) -> tuple[int, ...]:
    # Accept 1.2.3 or 1.2
    parts = []
    for p in (v or "").strip().split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _find_latest_release_version(releases_dir: Path) -> str | None:
    if not releases_dir.exists():
        return None
    versions = [p.name for p in releases_dir.iterdir() if p.is_dir()]
    if not versions:
        return None
    versions.sort(key=_version_key)
    return versions[-1]


def _iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def _rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _create_full_update_zip(*, to_dir: Path, to_version: str, out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    files = []
    for p in _iter_files(to_dir):
        rel = _rel_posix(p, to_dir)
        files.append(
            {
                "path": rel,
                "old_sha256": None,
                "new_sha256": sha256_file(p),
                "size": p.stat().st_size,
            }
        )

    manifest = {
        "type": "patch",
        "from_version": "",
        "to_version": str(to_version),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"mode": "full"},
        "files": files,
        "deletes": [],
    }

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for item in files:
            src = to_dir / Path(item["path"])
            zf.write(src, arcname=item["path"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build updater + auto update package")
    parser.add_argument("--clean", action="store_true", help="Clean PyInstaller cache")
    parser.add_argument(
        "--to-version",
        default=None,
        help="Version đích (mặc định: lấy từ installer/myapp.iss)",
    )
    parser.add_argument(
        "--from-version",
        default=None,
        help="Version nguồn (mặc định: release gần nhất trong releases/)",
    )
    args = parser.parse_args()

    defines = _parse_iss_defines(ISS_PATH)
    app_internal_name = (
        defines.get("MyAppInternalName") or "phần mềm chấm công tam niên"
    ).strip()
    to_version = (args.to_version or defines.get("MyAppVersion") or "0.0.0").strip()

    # 1) Build app (onedir)
    cmd = [sys.executable, "build_exe.py", "--name", app_internal_name]
    if args.clean:
        cmd.append("--clean")
    _run(cmd, cwd=PROJECT_ROOT)

    to_dir = PROJECT_ROOT / "dist" / app_internal_name
    exe_path = to_dir / f"{app_internal_name}.exe"
    if not exe_path.exists():
        raise SystemExit(f"Không thấy exe sau build: {exe_path}")

    # 2) Build updater exe (version.exe)
    if not UPDATER_SPEC.exists():
        raise SystemExit(f"Không tìm thấy spec updater: {UPDATER_SPEC}")

    py_cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]
    if args.clean:
        py_cmd.append("--clean")
    py_cmd.append(str(UPDATER_SPEC))
    _run(py_cmd, cwd=PROJECT_ROOT)

    # 3) Create update package
    releases_dir = PROJECT_ROOT / "releases"
    latest_release = _find_latest_release_version(releases_dir)

    from_version = (args.from_version or latest_release or "").strip()

    # If the latest release equals to_version, try to pick previous release
    if from_version and _version_key(from_version) == _version_key(to_version):
        # choose previous version if possible
        versions = (
            [p.name for p in releases_dir.iterdir() if p.is_dir()]
            if releases_dir.exists()
            else []
        )
        versions.sort(key=_version_key)
        if len(versions) >= 2:
            from_version = versions[-2]
        else:
            from_version = ""

    out_zip = PROJECT_ROOT / "updates" / f"update_{app_internal_name}_{to_version}.zip"

    if from_version:
        from_dir = releases_dir / from_version / app_internal_name
        if from_dir.exists() and from_dir.is_dir():
            # Create diff patch using existing tool
            patch_cmd = [
                sys.executable,
                str(PROJECT_ROOT / "tools" / "make_patch.py"),
                "--from-dir",
                str(from_dir),
                "--to-dir",
                str(to_dir),
                "--from-version",
                str(from_version),
                "--to-version",
                str(to_version),
                "--out",
                str(out_zip),
            ]
            _run(patch_cmd, cwd=PROJECT_ROOT)
        else:
            # fallback to full update
            _create_full_update_zip(
                to_dir=to_dir, to_version=to_version, out_zip=out_zip
            )
            from_version = ""
    else:
        _create_full_update_zip(to_dir=to_dir, to_version=to_version, out_zip=out_zip)

    zip_sha = sha256_file(out_zip)

    update_json_path = PROJECT_ROOT / "updates" / f"update_{to_version}.json"
    update_payload = {
        "from_version": from_version,
        "to_version": to_version,
        "patch": out_zip.name,
        "sha256": zip_sha,
    }
    update_json_path.write_text(
        json.dumps(update_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 4) Snapshot release for next diff
    release_target = releases_dir / to_version / app_internal_name
    if release_target.exists():
        shutil.rmtree(release_target)
    release_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(to_dir, release_target)

    print("✅ Done")
    print(f"- App EXE: {exe_path}")
    # version.spec currently produces a single-file exe at dist/version.exe
    updater_exe = PROJECT_ROOT / "dist" / "version.exe"
    if updater_exe.exists():
        print(f"- Updater EXE: {updater_exe}")
    else:
        print(f"- Updater output: {PROJECT_ROOT / 'dist'}")
    print(f"- Update zip: {out_zip}")
    print(f"- Update json: {update_json_path}")
    print(f"- Release snapshot: {release_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
