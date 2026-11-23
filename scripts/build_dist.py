#!/usr/bin/env python3
"""Assemble dist/ (carpets.json + patterns/ + thumbs/) for Cloudflare R2 upload."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dist/ bundle for R2 deployment")
    parser.add_argument("--skip-thumbs", action="store_true", help="Skip WebP thumbnail generation")
    args = parser.parse_args()

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Validate catalog
    subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_seams.py"), "--catalog-only"], check=True)

    # 2. Copy carpets.json
    shutil.copy2(ROOT / "data" / "carpets.json", DIST_DIR / "carpets.json")

    # 3. Copy patterns/*.svg and floors/*.svg
    for folder in ("patterns", "floors"):
        src_dir = ROOT / folder
        if not src_dir.exists():
            continue
        dst_dir = DIST_DIR / folder
        dst_dir.mkdir(parents=True, exist_ok=True)
        for svg in sorted(src_dir.glob("*.svg")):
            dst = dst_dir / svg.name
            if not dst.exists() or dst.stat().st_mtime < svg.stat().st_mtime:
                shutil.copy2(svg, dst)

    # 4. Render 3x3 WebP thumbnails
    if not args.skip_thumbs:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "render_thumbs.py"), "--out", str(DIST_DIR / "thumbs")],
            check=True,
        )

    print(f"Built dist/ at {DIST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
