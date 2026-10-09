#!/usr/bin/env python3
"""Build the leaf-sprites proposal page: demo/tlo-liscie.html

The real card from src/ is pasted in, with the salon panel's config and a
weather entity the page drives itself: season, wind, `leaves:` mode, quality,
time of day. `Date` is swapped for a simulated clock before the card loads,
because the card picks the leaf set from the month. Below the scene every
sprite of every season on a dark and a light ground.

The sprites are read from ZASOBY (/local/sun-cycle/ on the production HA), so
leaves-{autumn,spring,summer}.webp have to be there next to sun.png.

    python3 tools/build_leaves_poc.py
    export BW_SESSION=$(bw unlock --raw)
    python3 ~/CodeHub/hassio/ha-panel-salon-sekcje/scripts/poc_upload.py demo/tlo-liscie.html
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build_weather_poc import KARTA, ROOT, ZASOBY, konfig_z_panelu   # noqa: E402

SZABLON = pathlib.Path(__file__).parent / "liscie_poc.html"
OUT = ROOT / "demo" / "tlo-liscie.html"
META = {
    "tytul": "Tło: liście na wietrze według pory roku",
    "grupa": "Tło (sun-cycle-bg)",
    "status": "aktualne",
    "kolejnosc": 105,
    "opis": ("Propozycja do decyzji: wiatr w sun-cycle-bg niesie zamiast kolorowych elips "
             "sprite'y liści i kwiatów według pory roku. Jesień: klon i dąb; wiosna: płatki i kwiaty "
             "wiśni, młode liście buka i lipy; lato: liście lipy i klonu, mak, stokrotki, jaskier. "
             "Obrazy z google/gemini-nano-banana-2.1 przez OpenRouter. Prawdziwa karta z gałęzi "
             "feat/leaf-sprites, przełącznik pory roku, trybu leaves, wiatru i pory dnia, galeria "
             "wszystkich sprite'ów na ciemnym i jasnym tle."),
}


def main() -> int:
    wersja = KARTA.read_text().split("\n")[0][3:40].split(" —")[0]
    html = (SZABLON.read_text()
            .replace("__KARTA__", KARTA.read_text())
            .replace("__KONFIG__", json.dumps(konfig_z_panelu(), ensure_ascii=False))
            .replace("__ZASOBY__", ZASOBY)
            .replace("__WERSJA__", wersja)
            .replace("__ZBUDOWANO__", datetime.date.today().isoformat()))
    zostalo = [k for k in ("__KARTA__", "__KONFIG__", "__ZASOBY__", "__WERSJA__", "__ZBUDOWANO__")
               if k in html]
    if zostalo:
        sys.exit(f"niepodstawione: {zostalo}")
    OUT.write_text(html)
    OUT.with_suffix(".meta.json").write_text(json.dumps(META, ensure_ascii=False, indent=1) + "\n")
    print(f"{OUT} ({len(html) // 1024} kB), karta {wersja}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
