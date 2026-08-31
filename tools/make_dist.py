#!/usr/bin/env python3
"""Fill dist/ — the card plus its artwork, which is what HACS installs.

HACS installs a dashboard plugin by downloading one file, so a fresh install
used to get sun-cycle-bg.js and nothing else: every image had to be copied to
/config/www by hand before `planets:` or `milky_way:` drew anything. Its rule
for plugins that need more than a script is a directory:

    "If your plugin requires files that are not js files, place all files
     (including the card file) in the dist directory"   — hacs.xyz

So dist/ holds the card and the pictures, HACS copies all of it into
/config/www/community/ha-sun-cycle-bg/, served as /hacsfiles/ha-sun-cycle-bg/…
— exactly where the card's default paths point. A fresh system is then ready
with `planets: true` and a `milky_way:` block that names no files at all.

    python3 tools/make_dist.py          # -> dist/

The card itself stays at the root of the repository: that is the file the tools
and the tuning pages read, and dist/ carries a copy of it. Run this before
tagging, or dist/ ships the previous version of the card.

(zip_release was tried first and is wrong here: HACS then registers the archive
itself as the Lovelace resource, and the dashboard loads a zip as a module.)
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
DIST = ROOT / "dist"

# (path in the repository, path inside the archive)
ZAWARTOSC = [("sun-cycle-bg.js", "sun-cycle-bg.js")]
for nazwa in ("sun.png", "moon.png", "milky-way.jpg", "milky-way-cutout.webp"):
    ZAWARTOSC.append((f"demo/assets/{nazwa}", nazwa))
for ciało in ("mercury", "venus", "earth", "mars", "jupiter", "saturn",
              "uranus", "neptune", "pluto"):
    ZAWARTOSC.append((f"demo/assets/planets/{ciało}.png", f"planets/{ciało}.png"))
ZAWARTOSC.append(("demo/assets/MILKY-WAY-CREDIT.md", "CREDITS.md"))


def main() -> int:
    DIST.mkdir(exist_ok=True)
    brakuje = [z for z, _ in ZAWARTOSC if not (ROOT / z).exists()]
    if brakuje:
        raise SystemExit("brak plików: " + ", ".join(brakuje))
    razem = 0
    for src, dst in ZAWARTOSC:
        cel = DIST / dst
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_bytes((ROOT / src).read_bytes())
        razem += cel.stat().st_size
        print(f"  {dst:28} {cel.stat().st_size // 1024:5} kB")
    print(f"{DIST}: {len(ZAWARTOSC)} plików, {razem // 1024} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
