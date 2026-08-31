#!/usr/bin/env python3
"""Turn a photograph of the Milky Way into a layer with a transparent sky.

A planet is cut out by finding its silhouette (tools/cutout_planets.py). A band
of the Galaxy has no silhouette — it fades into the sky, and the sky is the
part that has to go. So alpha comes from brightness itself: black sky becomes
transparent, star clouds stay opaque, and everything between keeps exactly as
much of itself as it is bright. Composited over the card's own night sky the
result adds light without ever pasting a black rectangle on it.

Two knobs decide how it reads:

  --floor   the level treated as empty sky (below it: fully transparent). Set
            it from the picture's own background, not by taste — the default
            is measured off the darkest 2 % of the frame.
  --gamma   how fast alpha rises above that floor. Above 1 the faint dust goes
            quieter and the bright clouds keep their weight, which is what
            keeps the layer from looking like fog.

Colour is left alone. The card dims and tints the whole layer anyway, and a
photograph that has been colour-managed twice looks like a print.

    python3 tools/cutout_milkyway.py ~/Pobrane/milky-way.jpg

The result is committed as demo/assets/milky-way-cutout.webp — the owner's own
photograph, MIT like the rest of the repository. The intermediate PNG is not:
it is two and a half times the bytes for a picture nothing reads.
"""
import argparse
import pathlib
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "demo" / "assets" / "milky-way-cutout.png"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--floor", type=float, default=None, help="0-1; default: measured")
    ap.add_argument("--gamma", type=float, default=1.35)
    ap.add_argument("--feather", type=float, default=0.12,
                    help="0-0.5; szerokosc wygaszania brzegow w ulamku boku")
    ap.add_argument("--width", type=int, default=0, help="resize, 0 = keep")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    if a.width and a.width != im.width:
        im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
    rgb = np.asarray(im).astype(np.float32) / 255.0
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    floor = a.floor if a.floor is not None else float(np.percentile(lum, 2))
    alpha = np.clip((lum - floor) / max(1e-6, 1.0 - floor), 0.0, 1.0) ** a.gamma

    # Wygaszenie brzegow. Zdjecie jest kadrem, a niebo nie ma kadru: bez tego
    # na panelu widac prostokat tam, gdzie plik sie konczy — sprawdzone, widac
    # go wyraznie. Rampa cosinusowa na kazdym boku, mnozona, wiec rogi gasna
    # dwa razy szybciej niz boki, co jest wlasnie tym, czego oko oczekuje.
    if a.feather > 0:
        h, w = alpha.shape
        def rampa(n, ile):
            r = np.ones(n, np.float32)
            k = max(1, int(round(n * ile)))
            t = np.linspace(0, 1, k, dtype=np.float32)
            gladko = 0.5 - 0.5 * np.cos(np.pi * t)
            r[:k] = gladko
            r[-k:] = gladko[::-1]
            return r
        alpha *= rampa(h, a.feather)[:, None] * rampa(w, a.feather)[None, :]

    out = np.zeros((*lum.shape, 4), np.uint8)
    out[..., :3] = np.clip(rgb * 255, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    dst = pathlib.Path(a.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    obraz = Image.fromarray(out, "RGBA")
    obraz.save(dst, optimize=True)
    # WebP as well: same picture with alpha at a quarter of the bytes, and the
    # page has to fetch it over the house network before it can draw anything
    webp = dst.with_suffix(".webp")
    obraz.save(webp, quality=88, method=6)

    kryje = float((alpha > 0.9).mean()) * 100
    puste = float((alpha < 0.02).mean()) * 100
    print(f"{dst} {im.size} {dst.stat().st_size // 1024} kB")
    print(f"{webp} {webp.stat().st_size // 1024} kB")
    print(f"prog tla: {floor:.4f} (zmierzony na 2. centylu), gamma {a.gamma}")
    print(f"w pelni kryjace: {kryje:.1f} % powierzchni, w pelni przezroczyste: {puste:.1f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
