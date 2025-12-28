"""tools/patchlib.py

Thư viện apply patch dùng chung cho:
- tools/apply_patch.py (CLI)
- tools/updater.py (Updater đóng gói thành version.exe)
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


BUFFER_SIZE = 1024 * 1024  # 1MB


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_manifest(zf: zipfile.ZipFile) -> dict[str, Any]:
    try:
        raw = zf.read("manifest.json")
    except KeyError:
        raise SystemExit("Patch zip thiếu manifest.json")
    try:
        import json

        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SystemExit(f"manifest.json không hợp lệ: {exc}")


@dataclass(frozen=True)
class ApplyPatchResult:
    backup_dir: Path
    updated_files: int
    deleted_files: int


def apply_patch_zip(
    *,
    patch_path: Path,
    target_dir: Path,
    backup_dir: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> ApplyPatchResult:
    patch_path = Path(patch_path).resolve()
    target_dir = Path(target_dir).resolve()

    if not patch_path.exists() or not patch_path.is_file():
        raise SystemExit(f"Patch file không tồn tại: {patch_path}")
    if not target_dir.exists() or not target_dir.is_dir():
        raise SystemExit(
            f"Target dir không tồn tại hoặc không phải thư mục: {target_dir}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resolved_backup = (
        Path(backup_dir).resolve()
        if backup_dir
        else (target_dir / f"backup_{timestamp}")
    )

    with zipfile.ZipFile(patch_path, "r") as zf:
        manifest = load_manifest(zf)
        files = manifest.get("files") or []
        deletes = manifest.get("deletes") or []

        if not isinstance(files, list) or not isinstance(deletes, list):
            raise SystemExit("Manifest format không đúng")

        # Pre-checks
        problems: list[str] = []
        for item in files:
            rel = str(item.get("path") or "")
            if not rel:
                problems.append("Manifest có file path rỗng")
                continue
            expected_old = item.get("old_sha256")
            expected_new = item.get("new_sha256")
            if not expected_new:
                problems.append(f"Thiếu new_sha256 cho {rel}")
                continue

            dest = target_dir / Path(rel)
            if expected_old and dest.exists() and not force:
                actual_old = sha256_file(dest)
                if actual_old.lower() != str(expected_old).lower():
                    problems.append(
                        f"Hash không khớp (có thể không phải bản {manifest.get('from_version')}): {rel}"
                    )

        for item in deletes:
            rel = str(item.get("path") or "")
            expected_old = item.get("old_sha256")
            if not rel or not expected_old:
                problems.append("Manifest deletes thiếu path/old_sha256")
                continue
            dest = target_dir / Path(rel)
            if dest.exists() and not force:
                actual_old = sha256_file(dest)
                if actual_old.lower() != str(expected_old).lower():
                    problems.append(f"Hash delete không khớp: {rel}")

        if problems:
            details = "\n".join([f" - {p}" for p in problems])
            raise SystemExit(
                "❌ Không thể apply patch do:\n"
                + details
                + "\nDùng --force để bỏ qua (không khuyến nghị)."
            )

        if dry_run:
            return ApplyPatchResult(
                backup_dir=resolved_backup,
                updated_files=len(files),
                deleted_files=len(deletes),
            )

        safe_mkdir(resolved_backup)

        with tempfile.TemporaryDirectory(prefix="patch_extract_") as tmp:
            tmp_dir = Path(tmp)

            # Extract changed files to temp
            for item in files:
                rel = str(item["path"])
                # Ensure path stays inside target
                if rel.startswith("../") or rel.startswith("..\\") or ":" in rel:
                    raise SystemExit(f"Đường dẫn không an toàn trong patch: {rel}")
                out_file = tmp_dir / Path(rel)
                safe_mkdir(out_file.parent)
                with zf.open(rel) as src, out_file.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

            # Apply deletes first (backup then delete)
            for item in deletes:
                rel = str(item["path"])
                dest = target_dir / Path(rel)
                if dest.exists():
                    backup_path = resolved_backup / Path(rel)
                    safe_mkdir(backup_path.parent)
                    shutil.copy2(dest, backup_path)
                    dest.unlink()

            # Apply changes: backup then replace
            for item in files:
                rel = str(item["path"])
                expected_new = str(item["new_sha256"])

                src = tmp_dir / Path(rel)
                dest = target_dir / Path(rel)
                safe_mkdir(dest.parent)

                if dest.exists():
                    backup_path = resolved_backup / Path(rel)
                    safe_mkdir(backup_path.parent)
                    shutil.copy2(dest, backup_path)

                tmp_copy = dest.with_suffix(dest.suffix + ".tmp")
                if tmp_copy.exists():
                    tmp_copy.unlink()
                shutil.copy2(src, tmp_copy)
                os.replace(tmp_copy, dest)

                actual_new = sha256_file(dest)
                if actual_new.lower() != expected_new.lower():
                    raise SystemExit(f"Verify failed for {rel}")

    return ApplyPatchResult(
        backup_dir=resolved_backup,
        updated_files=len(files),
        deleted_files=len(deletes),
    )
