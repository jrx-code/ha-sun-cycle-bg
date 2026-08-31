#!/usr/bin/env python3
"""Render docs/milky-way.png — the band strip in the README.

Three panels, all drawn by the real <sun-cycle-bg-card> against stubbed view
chrome, with the clock frozen so the sky is where it is said to be:

  1. the shipped photograph, placed where it was measured to belong
     (projection: frame, the card's own defaults),
  2. the same instant from an all-sky panorama (projection: equirect),
  3. the same again with the sun up — which is empty, because that is what the
     card does in daylight.

Freezing the clock matters: the card reads the current time to place the band,
so a picture taken at build time would show whatever the sky happened to be
doing, and at midday that is nothing at all.

    python3 tools/render_milkyway_doc.py        # -> docs/milky-way.png

Needs: playwright (with chromium).
"""
import http.server
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent.parent
DOCS = ROOT / "docs"
PORT = 8795
PANEL_W, PANEL_H = 430, 250
GAP = 8
# 30 August, 21:00 local at 53.5 N: the galactic centre is due south at +7 deg
# and Cygnus stands overhead — the band is across the frame and the sky is dark
CHWILA = "2026-08-30T19:00:00Z"
LAT, LON = 53.5182, 14.4570

PANELE = [
    (-16.0, "frame", "one photograph, at its true scale and place"),
    (-16.0, "equirect", "an all-sky panorama, same instant"),
    (12.0, "frame", "sun up — nothing, as it should be"),
]

STRONA = """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;background:#0d1015;font:600 11px/1 system-ui,sans-serif;color:#c9d3e2}
  .rzad{display:flex;gap:%dpx}
  figure{margin:0}
  figcaption{padding:7px 2px 8px;letter-spacing:.05em;text-transform:uppercase}
  .kadr{width:%dpx;height:%dpx;position:relative;overflow:hidden;border-radius:10px}
  hui-view-background{position:absolute;inset:0;display:block}
</style>
<div class="rzad" id="rzad"></div>
<script>
const ZAMROZONE = new Date('%s');
const PrawdziwaData = Date;
Date = class extends PrawdziwaData {
  constructor(...a) { return a.length ? new PrawdziwaData(...a) : new PrawdziwaData(ZAMROZONE); }
  static now() { return ZAMROZONE.getTime(); }
};
class A extends HTMLElement{} class B extends HTMLElement{} class C extends HTMLElement{}
customElements.define('hui-view-container', A);
customElements.define('hui-view-background', B);
customElements.define('hui-view', C);
</script>
<script src="/src/sun-cycle-bg.js"></script>
<script>
window.panel = (elev, rzutowanie, podpis) => {
  const fig = document.createElement('figure');
  fig.innerHTML = '<div class="kadr"></div><figcaption>' + podpis + '</figcaption>';
  document.getElementById('rzad').appendChild(fig);
  const host = fig.querySelector('.kadr');
  const cont = document.createElement('hui-view-container');
  cont.style.cssText = 'display:block;position:relative;width:100%%;height:100%%';
  cont.appendChild(document.createElement('hui-view-background'));
  cont.appendChild(document.createElement('hui-view'));
  host.appendChild(cont);
  const card = document.createElement('sun-cycle-bg-card');
  const rowniki = rzutowanie === 'equirect';
  // Nothing is placed by hand here: `assets:` points the card's own defaults at
  // the repository copies, and `milky_way: {}` is exactly what a fresh install
  // writes — so the strip in the README shows the shipped placement, measured
  // fov and all, not a picture tuned for the picture's sake.
  card.setConfig({
    assets: '/demo/assets/',
    stars: { count: 110, sizes: 'mixed', size: 0.5, glow: 0.05, twinkle: 0.45, drift: 0 },
    moon: false,
    milky_way: rowniki ? { projection: 'equirect' } : {},
    planets: { size: 1.2, scale: 'diameters', glow: 0.35 },
  });
  cont.insertBefore(card, cont.firstChild);
  card.hass = {
    states: { 'sun.sun': { attributes: { elevation: elev, azimuth: 250 } } },
    config: { latitude: %s, longitude: %s },
  };
};
</script>
"""


def serwuj():
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(ROOT), **k)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    strona = DOCS / "_milky_frame.html"
    strona.write_text(STRONA % (GAP, PANEL_W, PANEL_H, CHWILA, LAT, LON))
    srv = serwuj()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            szer = PANEL_W * len(PANELE) + GAP * (len(PANELE) - 1)
            pg = br.new_page(viewport={"width": szer, "height": PANEL_H + 30},
                             device_scale_factor=2)
            bledy = []
            pg.on("pageerror", lambda e: bledy.append(str(e)))
            pg.on("console", lambda m: bledy.append(f"{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
            pg.goto(f"http://127.0.0.1:{PORT}/docs/_milky_frame.html",
                    wait_until="networkidle")
            for elev, rzut, podpis in PANELE:
                pg.evaluate("([e, r, p]) => window.panel(e, r, p)", [elev, rzut, podpis])
            pg.wait_for_timeout(3000)          # obrazy + tranzycje krycia
            out = DOCS / "milky-way.png"
            pg.locator(".rzad").screenshot(path=str(out))
            swiatlo = pg.evaluate("""() => [...document.querySelectorAll('.sun-cycle-milky')]
              .map(c => { const g = c.getContext('2d');
                const d = g.getImageData(0, 0, c.width, c.height).data;
                let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 2) n++;
                return n; })""")
            br.close()
    finally:
        srv.shutdown()
        strona.unlink()
    print(f"{out} ({out.stat().st_size // 1024} kB)")
    print("pikseli ze swiatlem w panelach:", swiatlo)
    print("konsola:", bledy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
