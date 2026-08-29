#!/usr/bin/env python3
"""Cut a planet out of a render on a black starfield -> square RGBA PNG.

The source files (p_<planet>.jpg) are 1168x784 renders: one planet, a black
background, a scattering of stars. Pasting such a file on the sky would paste
its black box too, so the background has to become alpha.

Thresholding alone does not do it, for two reasons:

  - the stars are bright, so they survive any threshold that keeps the planet;
  - the night side of a planet fades into the background, so a threshold high
    enough to drop the sky also eats the terminator.

So: threshold low (the sky is genuinely black, ~0-6), label the connected
components, keep the largest one -- that is the planet with its rings, never a
star -- fill its holes, and take alpha from the luminance ramp only in the few
pixels around the silhouette edge, so the limb stays soft and everything inside
stays fully opaque. Saturn's rings are thin and dim: they are kept because they
touch the disc, and a small dilation closes the gap where they cross the
shadow.

    python3 tools/cutout_planets.py "~/Pobrane/planety i efekty" out/ [--size 256]
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

# the files are named in Polish; the card addresses planets the way the
# Sol integration does — sensor.sol_<body>_elevation — so the cutouts are
# written out under those names
NAMES = {
    "p_merkury": "mercury", "p_wenus": "venus", "p_ziemia": "earth",
    "p_mars": "mars", "p_jowisz": "jupiter", "p_saturn": "saturn",
    "p_uran": "uranus", "p_neptun": "neptune", "p_pluton": "pluto",
}

# alpha ramp: fully transparent at or below LO, fully opaque from HI up
LO, HI = 6.0, 26.0


def disc_spec(img: Image.Image):
    """[diameter, cx, cy] of the planet body inside the square file, as
    fractions of its width/height — the card's `*_image_disc` convention.

    Sizing by the file would shrink Saturn to a quarter of everyone else: its
    rings are two thirds of the frame. So the body is measured separately, and
    it is the *body* the card scales. The rings are faint, the body is not, so
    alpha > 128 isolates it; the largest component of that is the disc.
    """
    a = np.asarray(img)[:, :, 3]
    m = a > 128
    # Boundary pixels of the lit silhouette, then a circle fitted to them by
    # RANSAC. Neither a bounding box nor a distance transform survives this
    # set of files: a box measures Saturn's rings (0.95 of the file instead of
    # 0.42 for the ball), and a transform measures the lit crescent when a
    # planet is shown half in shadow (Mars, Mercury). A circle fit is right
    # for both — rings and terminator are outliers, and the arc that is left
    # still defines the whole disc.
    w, h = img.size
    edge = m & ~ndimage.binary_erosion(m)
    ys, xs = np.nonzero(edge)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    best, rng = None, np.random.default_rng(7)
    for _ in range(600):
        p3 = pts[rng.choice(len(pts), 3, replace=False)]
        c = _circle3(p3)
        # A ring arc fits a circle too — a huge one, centred off the file.
        # The ball cannot be either, so those candidates are dropped before
        # they can win on inlier count.
        if c is None or not (0.05 * w < c[2] < 0.55 * w):
            continue
        if not (0 <= c[0] < w and 0 <= c[1] < h):
            continue
        d = np.abs(np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1]) - c[2])
        n = int((d < 1.5).sum())
        if best is None or n > best[0]:
            best = (n, c)
    cx, cy, r = _refine(pts, best[1])
    return [round(2 * r / w, 4), round(cx / w, 4), round(cy / h, 4)]


def _circle3(p):
    """Circle through three points, or None if they are collinear."""
    (x1, y1), (x2, y2), (x3, y3) = p
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-6:
        return None
    s1, s2, s3 = x1 * x1 + y1 * y1, x2 * x2 + y2 * y2, x3 * x3 + y3 * y3
    cx = (s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)) / d
    cy = (s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)) / d
    return cx, cy, float(np.hypot(x1 - cx, y1 - cy))


def _refine(pts, c):
    """Least-squares circle over the RANSAC inliers, twice."""
    cx, cy, r = c
    for _ in range(2):
        d = np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r)
        inl = pts[d < 2.0]
        if len(inl) < 8:
            break
        A = np.column_stack([inl[:, 0], inl[:, 1], np.ones(len(inl))])
        b = inl[:, 0] ** 2 + inl[:, 1] ** 2
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        cx, cy = sol[0] / 2, sol[1] / 2
        r = float(np.sqrt(sol[2] + cx * cx + cy * cy))
    return float(cx), float(cy), r


def cutout(path: pathlib.Path, size: int):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    mask = lum > LO
    # close 1 px gaps (ring shadow, faint limb) before labelling, so the rings
    # stay attached to the disc and count as one component with it
    mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    lab, n = ndimage.label(mask)
    if n == 0:
        raise SystemExit(f"{path.name}: nothing above the threshold")
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)
    keep = ndimage.binary_fill_holes(keep)

    # alpha: the luminance ramp inside the silhouette, zero outside it. The
    # ramp only bites in the edge pixels; the body is far above HI.
    alpha = np.clip((lum - LO) / (HI - LO), 0.0, 1.0)
    alpha = np.where(keep, np.maximum(alpha, 0.0), 0.0)
    # one soft pixel of feather so the limb does not read as a cut-out sticker
    alpha = ndimage.gaussian_filter(alpha, 0.7)
    alpha = np.where(ndimage.binary_dilation(keep, np.ones((3, 3))), alpha, 0.0)

    ys, xs = np.where(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    rgba = np.dstack([a, alpha * 255.0]).astype(np.uint8)[y0:y1, x0:x1]

    # square canvas, centred: the card places a planet by the centre of its box
    h, w = rgba.shape[:2]
    side = max(h, w)
    out = np.zeros((side, side, 4), dtype=np.uint8)
    oy, ox = (side - h) // 2, (side - w) // 2
    out[oy:oy + h, ox:ox + w] = rgba
    img = Image.fromarray(out, "RGBA")
    if size and side > size:
        img = img.resize((size, size), Image.LANCZOS)
        side = size
    # fitted after the resize, so the fit sees the same edge everywhere and
    # does not chase crater rims at full resolution
    disc = disc_spec(img)
    # The night side of a planet is nearly black, so the luminance ramp left
    # it half transparent — over a twilight sky the terminator would show the
    # sky through the planet. Inside the fitted disc the body is opaque; the
    # ramp still owns everything outside it, which is what keeps the gaps
    # between Saturn's rings and its ball see-through.
    yy, xx = np.mgrid[0:side, 0:side]
    rr = np.hypot(xx - disc[1] * side, yy - disc[2] * side)
    solid = np.clip((disc[0] / 2 * side - rr) / 1.5 + 1, 0, 1)
    a = np.asarray(img).copy()
    a[:, :, 3] = np.maximum(a[:, :, 3], (solid * 255).astype(np.uint8))
    return Image.fromarray(a, "RGBA"), disc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--size", type=int, default=256)
    args = ap.parse_args()
    src, dst = pathlib.Path(args.src).expanduser(), pathlib.Path(args.dst).expanduser()
    dst.mkdir(parents=True, exist_ok=True)
    meta = {}
    for f in sorted(src.glob("p_*.jpg")):
        img, disc = cutout(f, args.size)
        name = NAMES.get(f.stem, f.stem)
        out = dst / (name + ".png")
        img.save(out, optimize=True)
        meta[name] = disc
        print(f"{f.name} -> {out.name} {img.size} disc={meta[name]} "
              f"{out.stat().st_size // 1024} kB")
    (dst / "discs.json").write_text(json.dumps(meta, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
