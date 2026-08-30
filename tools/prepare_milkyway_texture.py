#!/usr/bin/env python3
"""Turn ESO's all-sky panorama into the texture the card samples.

Source: "The Milky Way panorama", ESO/S. Brunier (GigaGalaxy Zoom), 6000x3000,
equirectangular in galactic coordinates — https://www.eso.org/public/images/eso0932a/
Licence: Creative Commons Attribution 4.0 International, per
https://www.eso.org/public/outreach/copyright/ ("images and videos on ESO's
public website are licensed under CC BY 4.0 unless specifically noted"). The
credit line "ESO/S. Brunier" must travel with the file — it is in the page, in
the README and in the file's own EXIF comment after this script runs.

Verified mapping (measured, not assumed — sampling the file at known objects):
  x -> l = (180 - 360 * x / W) mod 360        y -> b = (0.5 - y / H) * 180
  galactic centre 140 vs anticentre 62 vs pole 9 (mean levels), and both
  Magellanic Clouds land where their catalogue coordinates say: LMC 34.5
  against 12.9 for empty sky beside it.

    python3 tools/prepare_milkyway_texture.py ~/Pobrane/eso0932a.jpg

The output is deliberately small: a dashboard shows a slice of sky a few
hundred pixels tall, so 2048x1024 is already finer than the frame can print.
"""
import argparse
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "demo" / "assets" / "milky-way.jpg"
KREDYT = "The Milky Way panorama - ESO/S. Brunier - CC BY 4.0 - eso.org/public/images/eso0932a/"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="eso0932a.jpg, 6000x3000")
    ap.add_argument("--width", type=int, default=2048)
    ap.add_argument("--quality", type=int, default=82)
    a = ap.parse_args()
    im = Image.open(a.src).convert("RGB")
    if im.width != 2 * im.height:
        raise SystemExit(f"{a.src}: {im.size} — equirectangular means 2:1")
    im = im.resize((a.width, a.width // 2), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, quality=a.quality, optimize=True, progressive=True, comment=KREDYT)
    print(f"{OUT} {im.size} {OUT.stat().st_size // 1024} kB")
    print(f"kredyt w EXIF: {KREDYT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
