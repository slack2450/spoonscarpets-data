#!/usr/bin/env python3
"""Validate carpets.json integrity and unquantized librsvg/Cairo seam continuity."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "carpets.json"
PATTERNS_DIR = ROOT / "patterns"


def check_catalog() -> list[str]:
    errors: list[str] = []
    if not CATALOG_PATH.exists():
        return [f"Missing catalog: {CATALOG_PATH}"]

    data = json.loads(CATALOG_PATH.read_text())
    pubs = data.get("pubs", [])
    seen_refs: set[str] = set()
    vec_count = 0
    no_carpet_count = 0

    for pub in pubs:
        ref = str(pub.get("ref", ""))
        if not ref:
            errors.append(f"Pub missing ref: {pub}")
            continue
        if ref in seen_refs:
            errors.append(f"Duplicate ref: {ref}")
        seen_refs.add(ref)

        if pub.get("noCarpet"):
            no_carpet_count += 1
            continue

        pat = pub.get("pattern")
        if not pat:
            errors.append(f"Pub {ref} ({pub.get('name')}) has neither pattern nor noCarpet")
            continue

        vec_count += 1
        svg_path = ROOT / pat["path"]
        if not svg_path.exists():
            errors.append(f"Missing SVG for ref {ref}: {svg_path}")
        else:
            sz = svg_path.stat().st_size
            if sz < 200:
                errors.append(f"Suspiciously small SVG for ref {ref}: {sz} bytes")

    meta = data.get("meta", {})
    if meta.get("totalPubs") != len(pubs):
        errors.append(f"meta.totalPubs={meta.get('totalPubs')} != {len(pubs)}")
    if meta.get("vectorizedPubs") != vec_count:
        errors.append(f"meta.vectorizedPubs={meta.get('vectorizedPubs')} != {vec_count}")
    if meta.get("noCarpetPubs") != no_carpet_count:
        errors.append(f"meta.noCarpetPubs={meta.get('noCarpetPubs')} != {no_carpet_count}")

    expected_svgs = {f"{p['ref']}.svg" for p in pubs if "pattern" in p}
    actual_svgs = {p.name for p in PATTERNS_DIR.glob("*.svg")}
    extra = sorted(actual_svgs - expected_svgs)
    if extra:
        errors.append(f"Unreferenced SVG files in patterns/: {extra[:10]}")

    return errors


def _render_region(svg_path: Path, x: float, y: float, dx: float, dy: float, out_w: int, out_h: int):
    import ctypes as C
    from ctypes.util import find_library
    import xml.etree.ElementTree as ET
    import numpy as np

    root = ET.parse(svg_path).getroot()
    w = int(float(root.attrib.get("width", "512")))
    h = int(float(root.attrib.get("height", "512")))

    Z, I, D = C.c_void_p, C.c_int, C.c_double
    c, r, g = [C.CDLL(find_library(n)) for n in ("cairo", "rsvg-2", "gobject-2.0")]

    def fn(lib, name, ret, *args):
        f = getattr(lib, name)
        f.restype, f.argtypes = ret, args
        return f

    data = svg_path.read_bytes()
    svg = fn(r, "rsvg_handle_new_from_data", Z, C.c_char_p, C.c_size_t, Z)(data, len(data), None)
    assert svg, f"Failed to load SVG: {svg_path}"
    try:
        surf = fn(c, "cairo_image_surface_create", Z, I, I, I)(0, out_w, out_h)
        ctx = fn(c, "cairo_create", Z, Z)(surf)
        fn(c, "cairo_scale", None, Z, D, D)(ctx, out_w / dx, out_h / dy)
        fn(c, "cairo_translate", None, Z, D, D)(ctx, -x, -y)
        assert fn(r, "rsvg_handle_render_document", I, Z, Z, Z, Z)(
            svg, ctx, (D * 4)(0, 0, float(w), float(h)), None
        )
        fn(c, "cairo_surface_flush", None, Z)(surf)
        stride = fn(c, "cairo_image_surface_get_stride", I, Z)(surf)
        ptr = fn(c, "cairo_image_surface_get_data", Z, Z)(surf)
        raw = C.string_at(ptr, stride * out_h)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(out_h, stride // 4, 4)[:, :out_w, :]
        rgb = arr[:, :, [2, 1, 0]].copy()  # BGRA -> RGB
        fn(c, "cairo_destroy", None, Z)(ctx)
        fn(c, "cairo_surface_destroy", None, Z)(surf)
        return rgb
    finally:
        fn(g, "g_object_unref", None, Z)(svg)


def render_svg_to_rgb(svg_path: Path, width: int | None = None):
    import xml.etree.ElementTree as ET

    root = ET.parse(svg_path).getroot()
    w = int(float(root.attrib.get("width", "512")))
    h = int(float(root.attrib.get("height", "512")))
    out_w = width if width is not None else w
    out_h = max(1, int(round(h * (out_w / w))))
    return _render_region(svg_path, 0, 0, float(w), float(h), out_w, out_h)


def check_svg_seam(svg_path: Path, threshold: int = 64) -> tuple[int, int, int, int]:
    import xml.etree.ElementTree as ET
    import numpy as np

    root = ET.parse(svg_path).getroot()
    w = int(float(root.attrib.get("width", "512")))
    h = int(float(root.attrib.get("height", "512")))

    left = _render_region(svg_path, 0, 0, 1, h, 128, 4 * h)[:, 0].astype(np.int16)
    right = _render_region(svg_path, w - 1, 0, 1, h, 128, 4 * h)[:, -1].astype(np.int16)
    top = _render_region(svg_path, 0, 0, w, 1, 4 * w, 128)[0].astype(np.int16)
    bottom = _render_region(svg_path, 0, h - 1, w, 1, 4 * w, 128)[-1].astype(np.int16)

    lr_diff = np.abs(left - right).max(axis=1)
    tb_diff = np.abs(top - bottom).max(axis=1)

    lr_over = int((lr_diff > threshold).sum())
    tb_over = int((tb_diff > threshold).sum())
    return lr_over, tb_over, int(lr_diff.max()), int(tb_diff.max())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate catalog and SVG seams.")
    parser.add_argument("svgs", nargs="*", help="Specific SVG paths to seam-check")
    parser.add_argument("--catalog-only", action="store_true", help="Only validate carpets.json")
    parser.add_argument("--all", action="store_true", help="Seam-check every SVG in patterns/")
    parser.add_argument("--threshold", type=int, default=64, help="Max allowed per-channel seam delta")
    args = parser.parse_args()

    errors = check_catalog()
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("Catalog OK")

    if args.catalog_only:
        return 0

    targets = sorted(PATTERNS_DIR.glob("*.svg")) if args.all else [Path(s) for s in args.svgs]
    if not targets:
        return 0

    failed = 0
    for svg in targets:
        lr_over, tb_over, lr_max, tb_max = check_svg_seam(svg, args.threshold)
        status = "PASS" if (lr_over == 0 and tb_over == 0) else "FAIL"
        print(f"[{status}] {svg.name}: lr_over={lr_over} (max={lr_max}), tb_over={tb_over} (max={tb_max})")
        if status == "FAIL":
            failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
