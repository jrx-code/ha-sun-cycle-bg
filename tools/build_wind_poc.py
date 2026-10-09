#!/usr/bin/env python3
"""Build the wind proposal page: demo/tlo-wiatr.html

Five ways to show wind without speed lines (dust and down, a flow field, veils
of air, a treeline with grass, scud) next to what the card draws today, over the
real card with the salon panel's config. The WebGL helpers are taken from the
effects page template (tools/pogoda2_poc.html), so both pages share them.

    python3 tools/build_wind_poc.py            # demo/tlo-wiatr.html (dust, flow, veils, trees, scud)
    python3 tools/build_wind_poc.py zawijasy   # demo/tlo-wiatr-zawijasy.html (curly wind lines)
    # local check: demo/<page>.html?assets=assets/
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_weather_poc import KARTA, ROOT, ZASOBY, konfig_z_panelu   # noqa: E402

EFEKTY = pathlib.Path(__file__).parent / "pogoda2_poc.html"
SZABLON = pathlib.Path(__file__).parent / "wiatr_poc.html"
OUT = ROOT / "demo" / "tlo-wiatr.html"
META = {
    "tytul": "Tło: wiatr, 5 propozycji",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 108,
    "opis": ("Propozycja do decyzji: wiatr bez kresek. A: to, co karta rysuje dziś (smugi). 1: pył i puch "
             "dmuchawców w polu zawirowań, 2: pole przepływu ze śladami jak na mapach wiatru, 3: welony "
             "powietrza (shader), 4: linia drzew i trawa uginana falą porywu, 5: strzępy chmur pędzące z "
             "wiatrem (shader). Porywy jako fronty przechodzące przez kadr. Suwaki wiatru i porywów, pora "
             "dnia, liście, rozdzielczość, licznik FPS."),
}
STRONY = {
    "": (SZABLON, OUT, META),
    "zawijasy": (pathlib.Path(__file__).parent / "wiatr2_poc.html", ROOT / "demo" / "tlo-wiatr-zawijasy.html", {
        "tytul": "Tło: wiatr, linie z zawijasami",
        "grupa": "Tło (sun-cycle-bg)",
        "status": "aktualne",
        "kolejnosc": 109,
        "opis": ("Propozycja do decyzji: wiatr jako stylizowane linie, które rysują się, zawijają i znikają. "
                 "1 Wind Waker (biała wstęga z pętlą), 2 pędzel (kaligraficzne pociągnięcie ze spiralnym "
                 "haczykiem), 3 wiązka trzech nitek (styl anemo), 4 trochoida (rząd pętelek), 5 ornament "
                 "(esy-floresy ze spiralami na końcach). A: dzisiejsze smugi."),
    }),
}
KLUCZE = ("__KARTA__", "__KONFIG__", "__ZASOBY__", "__WERSJA__", "__ZBUDOWANO__", "__GL_HELPERS__")


def gl_helpers() -> str:
    """const VS ... efektGL(): the block between `const VS =` and the first effect on the effects page."""
    src = EFEKTY.read_text()
    a = src.index("const VS = ")
    b = src.index("/* ================= Chmury B")
    return src[a:b].rstrip() + "\n"


def main() -> int:
    szablon, out, meta = STRONY[sys.argv[1] if len(sys.argv) > 1 else ""]
    wersja = KARTA.read_text().split("\n")[0][3:40].split(" —")[0]
    html = (szablon.read_text()
            .replace("__GL_HELPERS__", gl_helpers())
            .replace("__KARTA__", KARTA.read_text())
            .replace("__KONFIG__", json.dumps(konfig_z_panelu(), ensure_ascii=False))
            .replace("__ZASOBY__", ZASOBY)
            .replace("__WERSJA__", wersja)
            .replace("__ZBUDOWANO__", datetime.date.today().isoformat()))
    zostalo = [k for k in KLUCZE if k in html]
    if zostalo:
        sys.exit(f"niepodstawione: {zostalo}")
    out.write_text(html)
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    print(f"{out} ({len(html) // 1024} kB), karta {wersja}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
