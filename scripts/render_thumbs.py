#!/usr/bin/env python3
"""Render lightweight 3x3 tiled WebP thumbnails for fast gallery grids."""

from __future__ import annotations

import argparse
import concurrent.futures
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERNS_DIR = ROOT / "patterns"
DEFAULT_OUT = ROOT / "dist" / "thumbs"


def render_one(svg_path: Path, out_dir: Path, size: int, quality: int, force: bool) -> str:
    from PIL import Image
    from verify_seams import render_svg_to_rgb

    out_path = out_dir / f"{svg_path.stem}.webp"
    if not force and out_path.exists() and out_path.stat().st_mtime >= svg_path.stat().st_mtime:
        return "skipped"

    # Render single tile at ~size/2 then tile 3x3 and crop/resize to square
    target_w = max(160, size // 2)
    rgb = render_svg_to_rgb(svg_path, width=target_w)
    tile = Image.fromarray(rgb, mode="RGB")
    tw, th = tile.size

    tiled = Image.new("RGB", (tw * 3, th * 3))
    for gy in range(3):
        for gx in range(3):
            tiled.paste(tile, (gx * tw, gy * th))

    # Center-crop to square and resize to target thumbnail size
    side = min(tiled.width, tiled.height)
    left = (tiled.width - side) // 2
    top = (tiled.height - side) // 2
    thumb = tiled.crop((left, top, left + side, top + side)).resize((size, size), Image.Resampling.LANCZOS)
    thumb.save(out_path, "WEBP", quality=quality, method=4)
    return "rendered"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render 3x3 WebP thumbnails from patterns/*.svg")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--quality", type=int, default=82)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    svgs = sorted(PATTERNS_DIR.glob("*.svg"))
    rendered = skipped = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(render_one, svg, args.out, args.size, args.quality, args.force) for svg in svgs]
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            if res == "rendered":
                rendered += 1
            else:
                skipped += 1

    print(f"Thumbnails complete: {rendered} rendered, {skipped} up-to-date -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
