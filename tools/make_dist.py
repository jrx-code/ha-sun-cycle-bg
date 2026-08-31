#!/usr/bin/env python3
"""Fill dist/ — the card plus its artwork, which is what HACS installs.

HACS's rule for a plugin that needs more than a script is a directory:

    "If your plugin requires files that are not js files, place all files
     (including the card file) in the dist directory"   — hacs.xyz

and it means the directory *instead of* the root, not as well as. HACS picks
the content path in repositories/plugin.py:

    for filename in valid_filenames:      # hacs.json -> sun-cycle-bg.js
        if filename in all_paths:         # a copy in the root wins here
            self.content.path.remote = "" # ... and only that file is fetched
            return
        if not content_in_root and f"dist/{filename}" in all_paths:
            self.content.path.remote = "dist"

So the card source lives in src/, not in the root: with a root copy present
the second branch is never reached and a fresh install gets the script alone —
no sun, no moon, no planets, no photograph, and `planets: true` drawing
nothing. That is what happened until 1.11.3, unnoticed on the one system that
had the pictures left over from the withdrawn 1.10.0 zip release.

    python3 tools/make_dist.py          # -> dist/

Run it before tagging, or dist/ ships the previous version of the card.

(zip_release was tried first and is wrong here too: HACS then registers the
archive itself as the Lovelace resource, and the dashboard loads a zip as a
module.)
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
DIST = ROOT / "dist"

# (path in the repository, path inside the archive)
ZAWARTOSC = [("src/sun-cycle-bg.js", "sun-cycle-bg.js")]
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
