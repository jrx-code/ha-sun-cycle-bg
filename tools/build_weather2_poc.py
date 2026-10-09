#!/usr/bin/env python3
"""Build the proposal page for the remaining weather effects: demo/tlo-pogoda-efekty.html

Seven effects (clouds, snow, hail, fog, lightning, wind and leaves, aurora),
each in two variants over the real card (salon panel config, simulated
clock): A is what the card draws today, B a proposal on one canvas (WebGL
shader or Canvas 2D). Only one runs at a time.

    python3 tools/build_weather2_poc.py
    # local check: demo/tlo-pogoda-efekty.html?assets=assets/
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_weather_poc import KARTA, ROOT, ZASOBY, konfig_z_panelu   # noqa: E402

SZABLON = pathlib.Path(__file__).parent / "pogoda2_poc.html"
OUT = ROOT / "demo" / "tlo-pogoda-efekty.html"
META = {
    "tytul": "Tło: pozostałe efekty pogody, propozycje",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 107,
    "opis": ("Propozycja do decyzji: nowe chmury, śnieg, grad, mgła, burza, wiatr z liśćmi i zorza dla "
             "sun-cycle-bg, tak jak deszcz. Dla każdego efektu A: to, co karta ma dziś, B: propozycja na "
             "jednym płótnie. Chmury, śnieg, mgła i zorza to shadery WebGL (chmury w perspektywie ze "
             "światłem od słońca, śnieg w 6 głębokościach z bokeh, mgła wykładnicza z kłębiącymi się "
             "ławicami, kurtyny zorzy z promieniami i barwą od wysokości), grad, burza i wiatr to Canvas 2D "
             "(odbijające się ziarna, kanał błyskawicy z rozgałęzieniami i kilkoma wyładowaniami, liście z "
             "fizyką trzepotania). Natężenie, wiatr, pora dnia, rozdzielczość, licznik FPS. Cel: Raspberry "
             "Pi 5, jedno płótno, 0,5 rozdzielczości, 30 kl./s."),
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
