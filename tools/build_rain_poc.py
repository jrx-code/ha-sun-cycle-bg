#!/usr/bin/env python3
"""Build the rain and rain-on-glass proposal page: demo/tlo-deszcz.html

Four variants on one stage over the real card (salon panel config, simulated
clock): A is the card's own rain and glass drops, B a single 2D canvas, C a
single WebGL1 full-screen shader, D the raindrop-fx library (MIT) loaded from
cdn.jsdelivr.net for comparison. Only one variant runs at a time.

    python3 tools/build_rain_poc.py
    # local check: demo/tlo-deszcz.html?assets=assets/
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_weather_poc import KARTA, ROOT, ZASOBY, konfig_z_panelu   # noqa: E402

SZABLON = pathlib.Path(__file__).parent / "deszcz_poc.html"
OUT = ROOT / "demo" / "tlo-deszcz.html"
META = {
    "tytul": "Tło: deszcz i krople, propozycje",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 106,
    "opis": ("Propozycja do decyzji: nowy deszcz i krople na szybie dla sun-cycle-bg. "
             "A: to, co karta ma dziś. B: jedno płótno 2D, cienkie zwężane smugi w 4 głębokościach "
             "z alfą od jasności nieba, porywami, welonem i rzadkimi rozbryzgami, szyba z mgłą z "
             "rozmytego nieba i soczewkami z odwróconym obrazem. C: jeden shader WebGL, smugi "
             "proceduralne, krople zjeżdżające ze śladem w mgle i refrakcją. D: raindrop-fx (MIT) "
             "dla porównania. Przełącznik opadu, wiatru, pory dnia, kropel i rozdzielczości, "
             "licznik FPS. Cel: Raspberry Pi 5, jedno płótno, 0,5 rozdzielczości, 30 kl./s."),
}
KLUCZE = ("__KARTA__", "__KONFIG__", "__ZASOBY__", "__WERSJA__", "__ZBUDOWANO__")


def main() -> int:
    wersja = KARTA.read_text().split("\n")[0][3:40].split(" —")[0]
    html = (SZABLON.read_text()
            .replace("__KARTA__", KARTA.read_text())
            .replace("__KONFIG__", json.dumps(konfig_z_panelu(), ensure_ascii=False))
            .replace("__ZASOBY__", ZASOBY)
            .replace("__WERSJA__", wersja)
            .replace("__ZBUDOWANO__", datetime.date.today().isoformat()))
    zostalo = [k for k in KLUCZE if k in html]
    if zostalo:
        sys.exit(f"niepodstawione: {zostalo}")
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB), karta {wersja}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
