"""tools/make_patch.py

Tạo gói patch (zip) từ 2 bản build PyInstaller onedir.

Patch zip chứa:
- manifest.json: thông tin phiên bản + danh sách file thay đổi + hash
- các file thay đổi (đường dẫn tương đối giống trong thư mục build)

Ví dụ:
  python tools/make_patch.py \
    --from-dir releases/1.0.1/myapp \
    --to-dir dist/myapp \
    --from-version 1.0.1 \
    --to-version 1.0.2 \
    --out patches/patch_1.0.1_to_1.0.2.zip
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import zipfile


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


def iter_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


@dataclass(frozen=True)
class ChangedFile:
    rel_path: str
    old_sha256: str | None
    new_sha256: str
    size: int


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tạo patch zip giữa 2 bản build onedir"
    )
    parser.add_argument(
        "--from-dir",
        required=True,
        help="Thư mục build cũ (ví dụ releases/1.0.1/myapp)",
    )
    parser.add_argument(
        "--to-dir", required=True, help="Thư mục build mới (ví dụ dist/myapp)"
    )
    parser.add_argument(
        "--from-version", required=True, help="Version nguồn (ví dụ 1.0.1)"
    )
    parser.add_argument(
        "--to-version", required=True, help="Version đích (ví dụ 1.0.2)"
    )
    parser.add_argument("--out", required=True, help="Đường dẫn file patch zip output")
    args = parser.parse_args()

    from_dir = Path(args.from_dir).resolve()
    to_dir = Path(args.to_dir).resolve()
    out_path = Path(args.out).resolve()

    if not from_dir.exists() or not from_dir.is_dir():
        raise SystemExit(f"from-dir không tồn tại hoặc không phải thư mục: {from_dir}")
    if not to_dir.exists() or not to_dir.is_dir():
        raise SystemExit(f"to-dir không tồn tại hoặc không phải thư mục: {to_dir}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Map old files by relative path
    old_files: dict[str, Path] = {
        rel_posix(p, from_dir): p for p in iter_files(from_dir)
    }
    new_files: dict[str, Path] = {rel_posix(p, to_dir): p for p in iter_files(to_dir)}

    changed: list[ChangedFile] = []
    deletes: list[dict[str, str]] = []  # {path, old_sha256}

    # Changed / new
    for rel_path, new_path in sorted(new_files.items()):
        old_path = old_files.get(rel_path)
        new_hash = sha256_file(new_path)
        if old_path is None:
            changed.append(
                ChangedFile(
                    rel_path=rel_path,
                    old_sha256=None,
                    new_sha256=new_hash,
                    size=new_path.stat().st_size,
                )
            )
            continue

        old_hash = sha256_file(old_path)
        if old_hash != new_hash or old_path.stat().st_size != new_path.stat().st_size:
            changed.append(
                ChangedFile(
                    rel_path=rel_path,
                    old_sha256=old_hash,
                    new_sha256=new_hash,
                    size=new_path.stat().st_size,
                )
            )

    # Deletes
    for rel_path, old_path in sorted(old_files.items()):
        if rel_path not in new_files:
            deletes.append({"path": rel_path, "old_sha256": sha256_file(old_path)})

    manifest = {
        "type": "patch",
        "from_version": str(args.from_version),
        "to_version": str(args.to_version),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "from_dir": str(from_dir),
            "to_dir": str(to_dir),
        },
        "files": [
            {
                "path": c.rel_path,
                "old_sha256": c.old_sha256,
                "new_sha256": c.new_sha256,
                "size": c.size,
            }
            for c in changed
        ],
        "deletes": deletes,
    }

    # Write zip
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for c in changed:
            src = to_dir / Path(c.rel_path)
            zf.write(src, arcname=c.rel_path)

    print(f"✅ Patch created: {out_path}")
    print(f"   Files changed: {len(changed)}")
    print(f"   Files deleted: {len(deletes)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
