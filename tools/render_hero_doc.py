#!/usr/bin/env python3
"""Render docs/hero.png — one wide night frame with everything switched on.

The other documentation images each isolate a feature. This one is the opposite:
a single view with the sky, the star field, the Milky Way, the moon on its own
ephemeris and the planets that were actually up, so a reader can see in one
picture what the card does to a dashboard.

Nothing here is arranged. The instant is frozen at 2026-08-30 00:00 local, the
planet positions are the `sensor.sol_*` readings captured at that instant in
demo/sol_snapshot.json (four bodies above the horizon: Saturn, Neptune, Pluto,
Uranus), the sun elevation is the one from the same snapshot, and the moon and
the band are computed by the card for that clock and that latitude. What you
see is what the card would have drawn on the wall that night.

    python3 tools/render_hero_doc.py            # -> docs/hero.png

Needs: playwright (with chromium).
"""
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent.parent
DOCS = ROOT / "docs"
PORT = 8796
W, H = 1280, 460
# the moment demo/sol_snapshot.json was taken, as UTC
CHWILA = "2026-08-29T22:00:11Z"
LAT, LON = 53.5182, 14.4570

STRONA = """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;background:#0d1015}
  #kadr{width:%dpx;height:%dpx;position:relative;overflow:hidden}
  hui-view-background{position:absolute;inset:0;display:block}
</style>
<div id="kadr"></div>
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
const SNAP = %s;
window.rysuj = () => {
  const host = document.getElementById('kadr');
  const cont = document.createElement('hui-view-container');
  cont.style.cssText = 'display:block;position:relative;width:100%%;height:100%%';
  cont.appendChild(document.createElement('hui-view-background'));
  cont.appendChild(document.createElement('hui-view'));
  host.appendChild(cont);
  const card = document.createElement('sun-cycle-bg-card');
  card.setConfig({
    assets: '/demo/assets/',
    stars: { count: 160, sizes: 'mixed', size: 0.55, glow: 0.3, twinkle: 0.5,
             rotate: true, flares: { count: 3 } },
    milky_way: { projection: 'equirect' },
    planets: { size: 1.6, scale: 'diameters', glow: 0.45, labels: true },
  });
  cont.insertBefore(card, cont.firstChild);
  const states = { 'sun.sun': { attributes: SNAP.slonce } };
  for (const [b, v] of Object.entries(SNAP.planety)) {
    states['sensor.sol_' + b + '_azimuth'] = { state: v.azimuth };
    states['sensor.sol_' + b + '_elevation'] = { state: v.elevation };
  }
  card.hass = { states, config: { latitude: %s, longitude: %s } };
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
    snap = json.loads((ROOT / "demo" / "sol_snapshot.json").read_text())
    strona = DOCS / "_hero_frame.html"
    strona.write_text(STRONA % (W, H, CHWILA, json.dumps(snap), LAT, LON))
    srv = serwuj()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            # 1.5x, not 2x: the README shows this about 900 px wide, and the
            # 2x frame cost 2 MB for detail nobody sees
            pg = br.new_page(viewport={"width": W, "height": H},
                             device_scale_factor=1.5)
            bledy = []
            pg.on("pageerror", lambda e: bledy.append(str(e)))
            pg.on("console", lambda m: bledy.append(f"{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
            pg.goto(f"http://127.0.0.1:{PORT}/docs/_hero_frame.html",
                    wait_until="networkidle")
            pg.evaluate("() => window.rysuj()")
            pg.wait_for_timeout(3500)      # obrazy tarcz + tranzycje krycia
            out = DOCS / "hero.png"
            pg.locator("#kadr").screenshot(path=str(out))
            # ile z tego naprawde narysowano — pusta klatka to zawsze mozliwosc
            miara = pg.evaluate("""() => {
              const licz = (c) => { const g = c.getContext('2d');
                const d = g.getImageData(0, 0, c.width, c.height).data;
                let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 2) n++;
                return n; };
              const mw = document.querySelector('.sun-cycle-milky');
              return {
                pas: mw ? licz(mw) : null,
                warstwy: [...document.querySelectorAll('[class^=sun-cycle-]')]
                  .map(e => e.className),
                planety: document.querySelectorAll('.sun-cycle-planets img').length,
              };
            }""")
            br.close()
    finally:
        srv.shutdown()
        strona.unlink()
    from PIL import Image
    Image.open(out).save(out, optimize=True)      # playwright nie optymalizuje
    print(f"{out} ({out.stat().st_size // 1024} kB)")
    print("pas:", miara["pas"], "px ze swiatlem; tarcz planet:", miara["planety"])
    print("warstwy:", miara["warstwy"])
    print("konsola:", bledy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
