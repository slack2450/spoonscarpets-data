# Wetherspoons carpet vectorization playbook

Deliver one standalone SVG repeat and one 3×3 PNG per pub. Keep the reference photos intact. In a parallel batch, give each pub its own working directory and use the assigned output names.

## 1. Establish the yarns and the scale

- Inspect the original at full resolution and at room-view size. Mark a few distinctive features you can find again, such as a hooked curl, a bud with three crossbars, or the hatched side of a diamond.
- Sample **2–6 flat yarn colours** from the interiors of well-lit shapes. Take medians of several small patches per yarn. Check the same motif elsewhere on the floor. A tone that follows a window, shadow or viewing distance usually belongs to the lighting. A tone that occupies the same bounded shape each repeat is evidence for a separate yarn.
- Use roughly **3–4 mm per tuft** as a working estimate when the photo supplies physical scale. Give important gaps, stems and outlines several tufts where the reference supports them. With no scale reference, estimate the tuft pitch from a sharp foreground detail or use the narrowest clearly repeated woven mark as a guide.
- Use solid fills and strokes. Exclude gradients, translucent shading, wool noise, filters and hairline veins. Raw pixel contours follow pile, JPEG artifacts and blur. Use the pixels to locate joins, tips and band edges, then redraw those features at woven scale.
- **Mottled or stippled grounds**: When a carpet genuinely mixes two ground yarns (e.g. espresso and tan), cluster the mottle into intentional woven-scale patches that respect where the dark yarn hugs scroll edges and where the lighter yarn opens into pockets. Never trace microscopic TV-static speckles that bury the foreground scrollwork, and check whether warm tungsten pub lighting has shifted cool yarns (like duck-egg blue or silver) toward muddy grey-green.

## 2. Recover the repeat before drawing

| Input | Procedure |
|---|---|
| Near top-down | Check both families of parallel lines and the diagonals of a known square. Deskew when needed. Measure between equivalent landmarks in both directions. |
| Oblique floor or aisle | Mask furniture, stairs, glare and other flooring. Fit a plane homography from at least four well-spaced, non-collinear correspondences. Two families of receding parallels give vanishing directions. Use a known square, a right angle plus a length ratio, or equivalent design evidence to set the top-down proportions. A horizon alone leaves the aspect ratio ambiguous. |
| Several photos | Rectify each view independently. Use the widest unobstructed view for spacing and the closest for silhouettes. Test quarter-turns, half-turns and translations to register their cells. Fold observations into one cell, weighting sharp, unobstructed areas. Retain a coverage mask for gaps. |
| Less than one repeat | Preserve the visible motifs individually. Extend cropped ribbons to plausible joins using their measured widths and tangents. Record that the unseen portion was reconstructed. |

For an oblique repeat, fit **H** from tile coordinates to photo pixels and keep its inverse. Resample the photo onto a regular top-down grid. On a copy used for alignment, subtract a broad local luminance average. Find candidate translations using masked, overlap-normalized autocorrelation. Confirm two independent offsets against several **same-handed** landmarks. An inner diamond or mirrored fan can give a strong half-period peak. Refine H and the offsets together until translated copies align near and far. Keep the original RGB for palette sampling. If straight floor rails bow near the image edge, correct lens distortion or fit the central region. Guessing a focal length to make one diamond look square can stretch the rest of the repeat.

## 3. Draw the layers in order

1. **Ground and bands.** Lay down an opaque ground rectangle. Fit the centre and both edges of each wavy band. Follow changes in width and curvature. Where a rail obscures a band, use a registered copy or a confirmed reflection to recover its continuation.
2. **Motifs.** Mark stems, branch junctions, curl centres, petal tips and openings before fitting Béziers. The Observatory’s close view resolved the open lip of a C-scroll where the aisle photo showed a blob. The David Macbeth Moir had four differently turned roses and individually gridded buds. Preserve those differences.
3. **Frames and fine lattice.** Draw these independently of the background. At The Mare Pool, the cream frame rectified to a square over elongated, wavy diamonds. Two sides had transverse yarn blocks and two had twin rails. Construct the blocks at the observed pitch, then add the thinner diagonal lattice.
4. **Export.** Set explicit integer `width`, `height`, a matching `viewBox="0 0 W H"` and a descriptive `<title>`. Use literal six-digit hex colours. Reuse repeated geometry with `<defs>` and `<use>`. Aim for about **10–200 KB**. Simplify surplus nodes while retaining corners, openings and hatch gaps.

## 4. Make the geometry periodic

If the repeat is staggered, choose a rectangular supercell that returns to the same phase on both axes. A half-drop often needs two rows or columns. For a tile of size W × H, draw each boundary-crossing shape **whole**. Place translated copies at `(i·W, j·H)` for every integer pair whose bounds intersect the tile, including stroke width, joins and caps. Offsets −1, 0 and +1 usually suffice for a local motif. Include diagonal copies at corners and extend the range for longer paths. Let the viewport clip the result. For a continuous ribbon, carry its tangent, width and hatch phase through the join. Quantize shared control points once, before translating them.

For fitted raster-derived bands, wrap the sample field in both axes before smoothing or contour fitting. Preserve the same crossing and neighbouring control points on opposite edges. Independent edge simplification can move one crossing even when the underlying field is periodic.

## 5. Render and verify

Run this from the pub’s output directory. It uses the **librsvg/Cairo** renderer used for the carpet previews, through Python’s standard-library ctypes binding. It writes a 2×-resolution tile repeated 3×3 in the SVG’s own palette. The edge test separately samples the **unquantized SVG** just inside each opposite edge.

```bash
/usr/bin/python3 - gpt-6-2-astra.svg gpt-6-2-astra-preview.png <<'PY'
import ctypes as C, sys, re
from ctypes.util import find_library
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

src, dst = sys.argv[1:]
root = ET.parse(src).getroot()
W, H = int(root.attrib["width"]), int(root.attrib["height"])
Z, I, D = C.c_void_p, C.c_int, C.c_double
c, r, g = [C.CDLL(find_library(n)) for n in ("cairo", "rsvg-2", "gobject-2.0")]
def fn(lib, name, ret, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = ret, args
    return f

with open(src, "rb") as stream:
    data = stream.read()
svg = fn(r, "rsvg_handle_new_from_data", Z, C.c_char_p, C.c_size_t, Z)(data, len(data), None)
assert svg
def render(x, y, dx, dy, w, h):
    surf = fn(c, "cairo_image_surface_create", Z, I, I, I)(0, w, h)  # ARGB32
    ctx = fn(c, "cairo_create", Z, Z)(surf)
    fn(c, "cairo_scale", None, Z, D, D)(ctx, w/dx, h/dy)
    fn(c, "cairo_translate", None, Z, D, D)(ctx, -x, -y)
    assert fn(r, "rsvg_handle_render_document", I, Z, Z, Z, Z)(
        svg, ctx, (D*4)(0, 0, W, H), None)
    fn(c, "cairo_surface_flush", None, Z)(surf)
    buf = fn(c, "cairo_image_surface_get_data", Z, Z)(surf)
    pixels = C.string_at(buf, 4*w*h)
    fn(c, "cairo_destroy", None, Z)(ctx)
    fn(c, "cairo_surface_destroy", None, Z)(surf)
    return np.array(Image.frombytes("RGBA", (w,h), pixels, "raw", "BGRA"))

tile = render(0, 0, W, H, 2*W, 2*H)
assert tile[:, :, 3].min() == 255, "Transparent ground or edge"
inks = sorted({v.lower() for e in root.iter() for k, v in e.attrib.items()
               if k in ("fill", "stroke") and re.fullmatch(r"#[0-9a-fA-F]{6}", v)})
assert 2 <= len(inks) <= 6, inks
palette = b"".join(bytes.fromhex(v[1:]) for v in inks)
lut = Image.new("P", (1, 1))
lut.putpalette(palette)
idx = Image.fromarray(tile[:, :, :3]).quantize(palette=lut, dither=Image.Dither.NONE)
preview = Image.fromarray(np.tile(np.asarray(idx), (3, 3)), mode="P")
preview.putpalette(palette)
preview.save(dst, bits=4)

pairs = [
    ("left/right", render(0, 0, 1, H, 128, 4*H)[:, 0],
                   render(W-1, 0, 1, H, 128, 4*H)[:, -1]),
    ("top/bottom", render(0, 0, W, 1, 4*W, 128)[0],
                   render(0, H-1, W, 1, 4*W, 128)[-1]),
]
for label, a, b in pairs:
    delta = np.abs(a.astype(int) - b.astype(int)).max(axis=1)
    print(label, "mean", round(delta.mean(), 3), "max", delta.max(),
          "positions with delta > 64", np.flatnonzero(delta > 64)[:20])
fn(g, "g_object_unref", None, Z)(svg)
PY
```

Inspect the **whole 3×3** at room scale, then zoom into both joins and a four-tile intersection. Follow individual rails, curls and hatch runs through them. Opposite strip samples lie 1/128 tile unit apart. Small differences at sloping antialiased edges are expected. A sustained difference identifies a strip to inspect. Nine identical raster copies alone cannot validate continuity.

Finally, **back-project the finished SVG**. For each visible floor pixel `(x,y)`, compute `(a,b,c) = inverse(H) · (x,y,1)`. Sample the rendered tile at `((a/c) mod W, (b/c) mod H)` when H uses tile units. If H uses normalized cell coordinates, apply the saved cell-origin offset and scale by W and H first. Compare side by side or blink against the original, checking foreground **and** distance. Uniform drift points to phase, growing drift to the perspective fit, and a local mismatch to the drawing. Report tile dimensions, colour count, SVG byte size, seam checks and any inferred geometry.


## 6. Safe Execution (Avoid Human Approval Prompts)

When running inside a delegated worker:
- Keep **all** file reads/writes inside your assigned `batch-XX/<ref>/` directory (plus reading this playbook). Do not write to `/tmp`, home directories, or other pub folders.
- **Never** run shell commands that commonly trigger human approval prompts — specifically avoid `rm`, `rm -rf`, `mv`, `chmod`, `chown`, `curl`, `wget`, `pip install`, `apt`, `sudo`, or git write commands.
- Prefer pure Python scripts (`python3 - <<'EOF' ... EOF` or a single script inside your pub folder) using pre-installed libraries (`PIL`, `numpy`, `scipy`, `cv2`, `cairosvg` / `rsvg-convert` / `gi.repository.Rsvg`). Overwrite files in place instead of deleting/moving them, and if you must remove a temporary file inside your own folder, use Python's `pathlib.Path.unlink(missing_ok=True)` rather than shell `rm`.
