#!/usr/bin/env python3
"""Build the release archive: sun-cycle-bg.zip — the card plus its artwork.

HACS installs a dashboard plugin by downloading one file, so until now a fresh
install got sun-cycle-bg.js and nothing else: every image had to be copied to
/config/www by hand before `planets:` or `milky_way:` drew anything. With
`zip_release` in hacs.json, HACS downloads this archive from the release
instead and unpacks all of it into

    /config/www/community/ha-sun-cycle-bg/

served as /hacsfiles/ha-sun-cycle-bg/... — which is exactly where the card's
default paths point. So a fresh system is ready with `planets: true` and a
`milky_way:` block that names no files at all.

    python3 tools/make_release_zip.py          # -> dist/sun-cycle-bg.zip
    gh release create vX.Y.Z dist/sun-cycle-bg.zip ...

The archive is flat on purpose: HACS unpacks it as-is, so what is at its root
is what ends up beside the card.
"""
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "dist" / "sun-cycle-bg.zip"

# (path in the repository, path inside the archive)
ZAWARTOSC = [("sun-cycle-bg.js", "sun-cycle-bg.js")]
for nazwa in ("sun.png", "moon.png", "milky-way.jpg", "milky-way-cutout.webp"):
    ZAWARTOSC.append((f"demo/assets/{nazwa}", nazwa))
for ciało in ("mercury", "venus", "earth", "mars", "jupiter", "saturn",
              "uranus", "neptune", "pluto"):
    ZAWARTOSC.append((f"demo/assets/planets/{ciało}.png", f"planets/{ciało}.png"))
ZAWARTOSC.append(("demo/assets/MILKY-WAY-CREDIT.md", "CREDITS.md"))


def main() -> int:
    OUT.parent.mkdir(exist_ok=True)
    brakuje = [z for z, _ in ZAWARTOSC if not (ROOT / z).exists()]
    if brakuje:
        raise SystemExit("brak plików: " + ", ".join(brakuje))
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in ZAWARTOSC:
            z.write(ROOT / src, dst)
    rozmiar = OUT.stat().st_size
    print(f"{OUT} — {len(ZAWARTOSC)} plików, {rozmiar // 1024} kB")
    for src, dst in ZAWARTOSC:
        print(f"  {dst:28} {(ROOT / src).stat().st_size // 1024:5} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
