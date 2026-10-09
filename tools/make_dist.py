#!/usr/bin/env python3
"""Copy the card and its artwork into the integration: custom_components/sun_cycle_bg/www/

Since 2.0.0 the repository is one Home Assistant integration (HACS category
Integration). HACS installs `custom_components/sun_cycle_bg/`, and the
integration serves `www/` at /sun_cycle_bg/ and loads the card on every
frontend page through its loader (www/loader.js), so the card, its pictures,
the profile store and the settings page arrive together.

The card is written in src/, the pictures live in demo/assets/ (the tuning
pages use them too). www/ holds copies, and a copy that nobody refreshes ships
the previous card under the new version, so CI runs this script and fails when
it changes anything. www/loader.js and www/panel.js are sources, not copies;
this script leaves them alone.

    python3 tools/make_dist.py        # before every commit that touches src/ or the art

Pictures are flat in www/ (planets included): the card asks for
`<base><body>.png` first and retries `planets/<body>.png` only for manual
installs copied from an older dist/.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
WWW = ROOT / "custom_components" / "sun_cycle_bg" / "www"

# (path in the repository, name in www/)
ZAWARTOSC = [("src/sun-cycle-bg.js", "sun-cycle-bg.js")]
for nazwa in ("sun.png", "moon.png", "milky-way.jpg", "milky-way-cutout.webp",
              "leaves-autumn.webp", "leaves-spring.webp", "leaves-summer.webp"):
    ZAWARTOSC.append((f"demo/assets/{nazwa}", nazwa))
for ciało in ("mercury", "venus", "earth", "mars", "jupiter", "saturn",
              "uranus", "neptune", "pluto"):
    ZAWARTOSC.append((f"demo/assets/planets/{ciało}.png", f"{ciało}.png"))
ZAWARTOSC.append(("demo/assets/MILKY-WAY-CREDIT.md", "CREDITS.md"))
# written by hand, kept in www/ itself
ZRODLA_W_WWW = ("loader.js", "panel.js")


def main() -> int:
    WWW.mkdir(parents=True, exist_ok=True)
    brakuje = [z for z, _ in ZAWARTOSC if not (ROOT / z).exists()]
    brakuje += [f"www/{n}" for n in ZRODLA_W_WWW if not (WWW / n).exists()]
    if brakuje:
        raise SystemExit("brak plików: " + ", ".join(brakuje))
    razem = 0
    for src, dst in ZAWARTOSC:
        cel = WWW / dst
        dane = (ROOT / src).read_bytes()
        if not cel.exists() or cel.read_bytes() != dane:
            cel.write_bytes(dane)
        razem += len(dane)
        print(f"  {dst:28} {len(dane) // 1024:5} kB")
    print(f"{WWW.relative_to(ROOT)}: {len(ZAWARTOSC)} plików, {razem // 1024} kB (+ {', '.join(ZRODLA_W_WWW)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
