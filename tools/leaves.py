#!/usr/bin/env python3
"""Leaf sprites for the wind: generate, key out, pack.

    OPENROUTER_API_KEY=... python3 tools/leaves.py generate [autumn spring summer]
    python3 tools/leaves.py cut          # needs numpy and Pillow

`generate` asks google/gemini-nano-banana-2.1 through OpenRouter for one sheet
per season on a flat pure blue ground (no object is blue) and stores it in
demo/assets/leaves-src/<season>.png. About 0.04 USD a sheet (2026-10-09).

`cut` keys the blue out (alpha from how much bluer a pixel is than the brighter
of red and green, then the blue spill pulled down on the fringe), finds every
object as a connected region, and packs them row by row into one strip of
128 px square cells per season: demo/assets/leaves-<season>.webp. The card
takes the cell count from LEAF_SETS, so keep it in step with what this prints.
"""
import base64
import json
import os
import pathlib
import sys
import urllib.request
from collections import deque

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "demo" / "assets" / "leaves-src"
OUT = ROOT / "demo" / "assets"
MODEL = "google/gemini-nano-banana-2.1"
CELL = 128

COMMON = ("Sprite sheet: exactly 12 separate objects arranged in a neat 4 columns by 3 rows grid, each object "
          "fully isolated with wide empty space around it, nothing touching or overlapping, nothing cut off by the edge. "
          "Top-down flat view, realistic natural detail, soft even light, no cast shadows, no text, no frame. "
          "Background: one perfectly flat, uniform, solid pure blue colour #0000FF everywhere, no gradient, no texture. "
          "No blue colour on any object.")
SHEETS = {
    "autumn": "Autumn leaves: 6 Norway maple leaves (Acer platanoides, five pointed lobes) and 6 English oak leaves "
              "(Quercus robur, rounded lobes), in real autumn colours: scarlet red, deep orange, golden yellow, ochre, "
              "russet brown, some with mixed red-yellow-green blotches.",
    "spring": "Spring: 5 single loose pink cherry blossom petals (Prunus serrulata, notched tip), 3 small whole "
              "white-pink cherry/apple blossom flowers with five petals, and 4 fresh young light green leaves "
              "(beech and lime) just unfolded.",
    "summer": "Summer: 6 rich green summer leaves (small-leaved lime / linden heart-shaped leaves and maple leaves, "
              "various greens), 3 single red poppy petals (Papaver rhoeas), and 3 small whole flower heads: two white "
              "daisies with yellow centres and one yellow buttercup.",
}


def generate(names):
    key = os.environ["OPENROUTER_API_KEY"]
    SRC.mkdir(parents=True, exist_ok=True)
    for name in names:
        body = {"model": MODEL, "modalities": ["image", "text"],
                "messages": [{"role": "user", "content": SHEETS[name] + " " + COMMON}]}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(body).encode(),
                                     {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        r = json.load(urllib.request.urlopen(req, timeout=300))
        url = r["choices"][0]["message"]["images"][0]["image_url"]["url"]
        (SRC / f"{name}.png").write_bytes(base64.b64decode(url.split(",", 1)[1]))
        print(name, "cost", r.get("usage", {}).get("cost"))


def cut():
    import numpy as np
    from PIL import Image
    for name in SHEETS:
        im = np.asarray(Image.open(SRC / f"{name}.png").convert("RGB")).astype(np.float32)
        r, g, b = im[..., 0], im[..., 1], im[..., 2]
        ex = b - np.maximum(r, g)                       # blue excess
        bg = np.median(ex[:20, :20])
        a = np.clip((0.75 * bg - ex) / (0.5 * bg), 0, 1)
        b2 = np.where(a < 1, np.minimum(b, np.maximum(r, g) + (b - np.maximum(r, g)) * a), b)
        rgba = np.dstack([r, g, b2, a * 255]).clip(0, 255).astype(np.uint8)
        mask = a > 0.5
        H, W = mask.shape
        lab = np.zeros((H, W), np.int32)
        boxes = []
        for y0 in range(0, H, 2):
            for x0 in range(0, W, 2):
                if not mask[y0, x0] or lab[y0, x0]:
                    continue
                n = len(boxes) + 1
                q = deque([(y0, x0)])
                lab[y0, x0] = n
                ys, xs, cnt = [y0, y0], [x0, x0], 0
                while q:
                    y, x = q.popleft()
                    cnt += 1
                    ys = [min(ys[0], y), max(ys[1], y)]
                    xs = [min(xs[0], x), max(xs[1], x)]
                    for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n
                            q.append((yy, xx))
                boxes.append((cnt, ys, xs, n))
        boxes = sorted((b for b in boxes if b[0] > 2000), key=lambda b: (round(b[1][0] / 150), b[2][0]))
        strip = Image.new("RGBA", (CELL * len(boxes), CELL), (0, 0, 0, 0))
        for i, (_, ys, xs, n) in enumerate(boxes):
            y0, y1 = max(0, ys[0] - 4), min(H, ys[1] + 5)
            x0, x1 = max(0, xs[0] - 4), min(W, xs[1] + 5)
            crop = rgba[y0:y1, x0:x1].copy()
            own = np.isin(lab[y0:y1, x0:x1], (0, n))       # drop bits of neighbours
            crop[..., 3] = np.where(own, crop[..., 3], 0)
            sp = Image.fromarray(crop)
            s = (CELL - 8) / max(sp.size)
            sp = sp.resize((max(1, round(sp.size[0] * s)), max(1, round(sp.size[1] * s))), Image.LANCZOS)
            strip.alpha_composite(sp, (i * CELL + (CELL - sp.size[0]) // 2, (CELL - sp.size[1]) // 2))
        strip.save(OUT / f"leaves-{name}.webp", "WEBP", quality=88, method=6)
        print(name, len(boxes), "cells", (OUT / f"leaves-{name}.webp").stat().st_size, "B")


if __name__ == "__main__":
    if sys.argv[1:2] == ["generate"]:
        generate(sys.argv[2:] or list(SHEETS))
    elif sys.argv[1:2] == ["cut"]:
        cut()
    else:
        sys.exit(__doc__)
