#!/usr/bin/env python3
"""Build the weather-effects proposal page: demo/tlo-pogoda.html

A decision page, not a feature. It answers two questions with the real card on
screen:

  1. Which of the effects dynamic-weather-card v2026.10.0 shipped (rain, snow,
     hail, fog, lightning, wind, raindrops on the glass, aurora) would make
     sense as a weather layer over sun-cycle-bg, and what they cost.
  2. Can the meteors follow the real shower calendar instead of the fixed
     28/h from one point of the frame the panel runs today.

The card itself is pasted in at build time (same rule as the configurator), and
`Date` is swapped for a simulated clock before it loads, so the moon, the Milky
Way and the planets follow the time slider together with the sun. The weather
layer and the shower model are prototype code living only on this page.

Shower data: IMO Meteor Shower Calendar 2027, Table 5 (working list of visual
showers, maxima in solar longitude J2000, so valid for any year) and Table 6
(radiant positions through the year, reduced here to a linear daily drift).
https://www.imo.net/ShCal27s.pdf, fetched 2026-10-08. The 2026 calendar is not
online while imo.net is being rebuilt; solar longitudes do not depend on it.

    python3 tools/build_weather_poc.py
    export BW_SESSION=$(bw unlock --raw)
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py \\
        demo/tlo-pogoda.html
"""
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
KARTA = ROOT / "src" / "sun-cycle-bg.js"
SZABLON = pathlib.Path(__file__).parent / "pogoda_poc.html"
OUT = ROOT / "demo" / "tlo-pogoda.html"
PANEL = ROOT.parent / "ha-panel-salon-sekcje" / "config" / "dashboard.json"
ZASOBY = "/local/sun-cycle/"

META = {
    "tytul": "Tło: pogoda i roje meteorów",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 104,
    "opis": ("Propozycja do decyzji: efekty z dynamic-weather-card v2026.10.0 (chmury w trzech "
             "warstwach, deszcz z rozbryzgami, krople na szybie, śnieg, grad, mgła, błyskawice, "
             "wiatr z liśćmi, zorza) narysowane nad prawdziwą kartą sun-cycle-bg z konfiguracją "
             "z panelu, w kadrze 16:5. Do tego meteory według kalendarza IMO: 38 rojów z "
             "radiantem, dryfem i ZHR, liczone dla naszej szerokości z Księżycem i zachmurzeniem, "
             "zamiast dzisiejszych stałych 28/h z jednego punktu. Wykres roku, tabela maksimów, "
             "tabela porównania z release'em i lista decyzji."),
}

# code, Polish name, activity (MM-DD from, to), peak solar longitude J2000,
# radiant RA/Dec at peak, drift deg/day in RA and Dec, V km/s, r, ZHR (None = variable),
# daytime shower (radiant too close to the sun to be seen visually).
# Table 5 for everything but the drift; drift read off Table 6 between the two
# dates closest to the maximum.
ROJE = [
    ("QUA", "Kwadrantydy", "12-28", "01-12", 283.15, 230, 49, 0.6, -0.2, 41, 2.1, 80),
    ("GUM", "γ-Ursae Minorydy", "01-10", "01-22", 298.0, 228, 67, 0.8, -0.4, 31, 3.0, 3),
    ("ACE", "α-Centaurydy", "01-31", "02-20", 319.4, 211, -58, 1.2, -0.3, 58, 2.0, 6),
    ("LYR", "Lirydy", "04-14", "04-30", 32.32, 271, 34, 1.1, 0.0, 49, 2.1, 18),
    ("PPU", "π-Puppidy", "04-15", "04-28", 33.5, 110, -45, 0.5, -0.1, 18, 2.0, None),
    ("ETA", "η-Akwarydy", "04-19", "05-28", 45.5, 338, -1, 0.9, 0.4, 66, 2.4, 50),
    ("ELY", "η-Lirydy", "05-05", "05-14", 50.0, 291, 43, 1.0, 0.1, 43, 3.0, 3),
    ("ARI", "Arietydy dzienne", "05-14", "06-24", 76.7, 43, 24, 1.0, 0.0, 38, 2.8, 30, True),
    ("JBO", "Bootydy czerwcowe", "06-22", "07-02", 90.3, 221, 48, 0.1, -0.1, 18, 2.2, None),
    ("JPE", "Pegazydy lipcowe", "07-01", "07-20", 108.0, 347, 11, 0.9, 0.2, 63, 3.0, 3),
    ("GDR", "γ-Drakonidy lipcowe", "07-25", "07-31", 125.13, 280, 51, 1.0, 0.0, 27, 3.0, 5),
    ("CAP", "α-Kaprikornidy", "07-03", "08-15", 128.0, 307, -10, 0.9, 0.3, 23, 2.5, 5),
    ("SDA", "δ-Akwarydy płd.", "07-12", "08-23", 128.0, 340, -16, 0.8, 0.2, 41, 2.5, 25),
    ("ERI", "η-Erydanidy", "07-31", "08-19", 135.0, 41, -11, 0.9, 0.3, 64, 3.0, 3),
    ("PER", "Perseidy", "07-17", "08-24", 140.0, 48, 58, 1.35, 0.2, 59, 2.2, 110),
    ("KCG", "κ-Cygnidy", "08-03", "08-28", 144.0, 286, 59, 0.5, 0.7, 23, 3.0, 3),
    ("AUR", "Aurygidy", "08-28", "09-05", 158.6, 91, 39, 1.1, 0.0, 66, 2.5, 6),
    ("SPE", "ε-Perseidy wrześniowe", "09-05", "09-21", 166.7, 48, 40, 1.1, 0.1, 64, 2.5, 8),
    ("SLY", "Linkydy wrześniowe", "09-10", "10-08", 170.0, 113, 56, 1.3, -0.2, 60, 3.0, 3),
    ("DSX", "Sekstantydy dzienne", "09-20", "10-06", 188.0, 156, -2, 0.8, 0.0, 32, 2.5, 5, True),
    ("OCT", "Kamelopardalidy paźdz.", "10-05", "10-06", 192.58, 164, 79, 0.0, 0.0, 47, 2.5, 5),
    ("DRA", "Drakonidy", "10-06", "10-10", 195.4, 263, 56, 0.0, 0.0, 20, 2.6, 5),
    ("EGE", "ε-Geminidy", "10-14", "10-27", 205.0, 102, 27, 1.0, 0.0, 70, 3.0, 3),
    ("ORI", "Orionidy", "10-02", "11-07", 208.0, 95, 16, 0.65, 0.1, 66, 2.5, 20),
    ("LMI", "Leo Minorydy", "10-19", "10-27", 211.0, 162, 37, 1.0, -0.4, 62, 3.0, 2),
    ("STA", "Taurydy płd.", "09-20", "11-20", 223.0, 52, 15, 0.8, 0.2, 27, 2.3, 7),
    ("NTA", "Taurydy płn.", "10-20", "12-10", 230.0, 58, 22, 0.8, 0.15, 29, 2.3, 5),
    ("LEO", "Leonidy", "11-06", "11-30", 235.27, 152, 22, 0.6, -0.3, 71, 2.5, 15),
    ("AMO", "α-Monocerotydy", "11-15", "11-25", 239.32, 117, 1, 0.8, -0.2, 65, 2.4, None),
    ("NOO", "Orionidy listopadowe", "11-14", "12-06", 246.0, 91, 16, 0.6, 0.0, 43, 3.0, 3),
    ("PHO", "Feniksydy", "11-20", "12-05", 249.5, 8, -27, 0.6, -0.1, 15, 2.8, None),
    ("AND", "Andromedydy", "11-12", "12-10", 254.0, 25, 51, 0.0, 0.0, 18, 3.0, 5),
    ("PUP", "Puppidy-Velidy", "12-01", "12-15", 255.0, 123, -45, 0.45, 0.0, 44, 2.9, 10),
    ("MON", "Monocerotydy", "12-01", "12-19", 257.0, 100, 8, 0.85, 0.0, 41, 3.0, 3),
    ("HYD", "σ-Hydrydy", "12-03", "12-20", 257.0, 125, 2, 0.8, -0.2, 58, 3.0, 7),
    ("GEM", "Geminidy", "12-04", "12-20", 262.2, 112, 33, 1.0, 0.0, 35, 2.6, 150),
    ("URS", "Ursydy", "12-17", "12-26", 270.7, 217, 76, 0.0, -0.4, 33, 2.8, 10),
    ("COM", "Comae Berenicydy", "12-04", "01-30", 271.0, 164, 29, 0.9, -0.3, 65, 3.0, 3),
]


def roje_json() -> list:
    out = []
    for r in ROJE:
        kod, nazwa, od, do, lam, ra, dec, dra, ddec, v, rr, zhr, *dzien = r
        out.append({"kod": kod, "nazwa": nazwa, "od": od, "do": do, "lam": lam,
                    "ra": ra, "dec": dec, "dra": dra, "ddec": ddec, "v": v, "r": rr,
                    "zhr": zhr, "dzienny": bool(dzien and dzien[0])})
    return out


def konfig_z_panelu() -> dict:
    """The sun-cycle-bg config the salon panel runs, as committed in its repo."""
    dash = json.loads(PANEL.read_text())
    znalezione = []

    def szukaj(o):
        if isinstance(o, dict):
            if o.get("type") == "custom:sun-cycle-bg-card":
                znalezione.append(o)
                return
            for v in o.values():
                szukaj(v)
        elif isinstance(o, list):
            for v in o:
                szukaj(v)

    szukaj(dash)
    if not znalezione:
        sys.exit(f"brak custom:sun-cycle-bg-card w {PANEL}")
    return znalezione[0]


def main() -> int:
    for p in (KARTA, SZABLON, PANEL):
        if not p.exists():
            sys.exit(f"brak {p}")
    konfig = konfig_z_panelu()
    pogoda = json.loads((ROOT / "demo" / "pogoda_snapshot.json").read_text())
    migawka = json.loads((ROOT / "demo" / "sol_snapshot.json").read_text())
    wersja = KARTA.read_text().split("\n")[0][3:40].split(" —")[0]
    chwila = datetime.datetime.fromisoformat(pogoda["pobrano"]).astimezone(
        datetime.timezone(datetime.timedelta(hours=2)))   # CEST; snapshot z października
    pobrano = chwila.strftime("%d.%m.%Y %H:%M")
    html = (SZABLON.read_text()
            .replace("__KARTA__", KARTA.read_text())
            .replace("__ROJE__", json.dumps(roje_json(), ensure_ascii=False))
            .replace("__POGODA__", json.dumps(pogoda, ensure_ascii=False))
            .replace("__MIGAWKA__", json.dumps(migawka, ensure_ascii=False))
            .replace("__KONFIG__", json.dumps(konfig, ensure_ascii=False))
            .replace("__ZASOBY__", ZASOBY)
            .replace("__WERSJA__", wersja)
            .replace("__ZBUDOWANO__", datetime.date.today().isoformat())
            .replace("__POBRANO__", pobrano))
    zostalo = [k for k in ("__KARTA__", "__ROJE__", "__POGODA__", "__MIGAWKA__", "__KONFIG__",
                           "__ZASOBY__", "__WERSJA__", "__ZBUDOWANO__", "__POBRANO__") if k in html]
    if zostalo:
        sys.exit(f"niepodstawione: {zostalo}")
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(
        json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB), karta {wersja}, rojów {len(ROJE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
