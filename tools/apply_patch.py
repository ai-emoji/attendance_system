"""tools/apply_patch.py

Apply patch zip (tạo bởi tools/make_patch.py) vào thư mục cài đặt/build onedir.

Lưu ý (Windows): không thể replace myapp.exe khi app đang chạy.
Hãy đóng app trước khi apply.

Ví dụ:
  python tools/apply_patch.py --patch patches/patch_1.0.1_to_1.0.2.zip --target-dir "C:/Users/<you>/AppData/Local/myapp"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.patchlib import apply_patch_zip


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply patch zip to a PyInstaller onedir folder"
    )
    parser.add_argument("--patch", required=True, help="Đường dẫn patch zip")
    parser.add_argument(
        "--target-dir", required=True, help="Thư mục app hiện tại (onedir) cần cập nhật"
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Thư mục backup (mặc định: <target>/backup_<timestamp>)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Chỉ kiểm tra, không ghi file"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bỏ qua kiểm tra old_sha256 (không khuyến nghị)",
    )
    args = parser.parse_args()

    result = apply_patch_zip(
        patch_path=Path(args.patch),
        target_dir=Path(args.target_dir),
        backup_dir=Path(args.backup_dir) if args.backup_dir else None,
        dry_run=bool(args.dry_run),
        force=bool(args.force),
    )

    if args.dry_run:
        print("✅ Dry-run OK")
        print(f"   Will update: {result.updated_files} files")
        print(f"   Will delete: {result.deleted_files} files")
        return 0

    print("✅ Patch applied successfully")
    print(f"   Backup: {result.backup_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
