#!/usr/bin/env python3
"""Turn a photograph of the Milky Way into a layer with a transparent sky.

A planet is cut out by finding its silhouette (tools/cutout_planets.py). A band
of the Galaxy has no silhouette — it fades into the sky, and the sky is the
part that has to go. So alpha comes from brightness itself: black sky becomes
transparent, star clouds stay opaque, and everything between keeps exactly as
much of itself as it is bright. Composited over the card's own night sky the
result adds light without ever pasting a black rectangle on it.

Two knobs decide how it reads:

  --floor   the level treated as empty sky (below it: fully transparent).
            Measured, not chosen: on this photograph the band's core sits at
            0.35, the corners between 0.02 and 0.08, and the 35th percentile
            (0.055) sits just above the brightest corner — which is where the
            veil stops and the band starts. The median, 0.079, is already
            inside the band and eats its faint outer parts. A floor at the 2nd percentile (0.012, the first
            attempt) leaves everything up to 0.08 faintly lit, and over a
            night sky that reads as a grey rectangle where the file is.
  --gamma   how fast alpha rises above that floor. Above 1 the faint dust goes
            quieter and the bright clouds keep their weight, which is what
            keeps the layer from looking like fog.
  --vignette
            where the elliptical fade to nothing starts, in half-widths. The
            sky has no straight edges, so neither can the layer: fading each
            side separately leaves a visible vertical line where the stars stop.
            The fade ends at --vignette-end, inside the file rather than on its
            border, because the last visible star is what draws the edge and a
            star is still visible at 5 % opacity.

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
    ap.add_argument("--gamma", type=float, default=1.4)
    ap.add_argument("--vignette", type=float, default=0.30,
                    help="0-1; promien (w polowach boku), od ktorego zaczyna sie zanik")
    ap.add_argument("--vignette-end", type=float, default=0.88,
                    help="0-1.4; promien, przy ktorym krycie jest juz zerem")
    ap.add_argument("--width", type=int, default=0, help="resize, 0 = keep")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    if a.width and a.width != im.width:
        im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
    rgb = np.asarray(im).astype(np.float32) / 255.0
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

    floor = a.floor if a.floor is not None else float(np.percentile(lum, 35))
    alpha = np.clip((lum - floor) / max(1e-6, 1.0 - floor), 0.0, 1.0) ** a.gamma

    # Wygaszenie brzegow. Zdjecie jest kadrem, a niebo nie ma kadru — i nie ma
    # tez prostych krawedzi. Rampy na czterech bokach (pierwsza wersja) daly
    # dokladnie to, co widac na mapie alfy: pionowa krawedz po lewej i prawej,
    # pozioma u gory, bo gwiazdy sa punktami i przy dodawaniu swiatla widac je
    # jeszcze przy kryciu 0,1 — wiec rampa czyta sie jako „gwiazdy sie koncza",
    # nie jako zanik.
    #
    # Wiec winieta eliptyczna: promien liczony wzgledem polowy boku, zanik
    # smoothstep od `vignette` do krawedzi wpisanej elipsy i dalej. Zaden brzeg
    # pliku nie jest wtedy linia prosta, a gestosc gwiazd rzednie stopniowo
    # przez jedna trzecia kadru zamiast urywac sie na ostatnich procentach.
    if a.vignette < a.vignette_end:
        h, w = alpha.shape
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rx = (xx - (w - 1) / 2) / ((w - 1) / 2)
        ry = (yy - (h - 1) / 2) / ((h - 1) / 2)
        r = np.sqrt(rx * rx + ry * ry)
        t = np.clip((a.vignette_end - r) / max(1e-6, a.vignette_end - a.vignette), 0.0, 1.0)
        # smoothstep do potegi: gwiazda to punkt i widac ja jeszcze przy 0,05,
        # wiec zanik musi schodzic do zera szybciej, niz podpowiada oko na
        # gladkim tle — i konczyc sie WEWNATRZ pliku, nie na jego krawedzi,
        # inaczej ostatnie gwiazdy ukladaja sie w prosta linie brzegu kadru
        alpha *= (t * t * (3 - 2 * t)) ** 1.6
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
    print(f"prog tla: {floor:.4f} (35. centyl kadru), gamma {a.gamma}")
    print(f"w pelni kryjace: {kryje:.1f} % powierzchni, w pelni przezroczyste: {puste:.1f} %")
    kraw = max(float(alpha[0].max()), float(alpha[-1].max()),
               float(alpha[:, 0].max()), float(alpha[:, -1].max()))
    print(f"najjasniejszy piksel na krawedzi pliku: {kraw:.4f} (ma byc 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
