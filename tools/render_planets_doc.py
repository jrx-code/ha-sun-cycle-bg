#!/usr/bin/env python3
"""Render docs/planets.png — the planet strip in the README.

Like tools/render_docs.py, the picture comes from running code rather than from
a drawing: this builds the real <sun-cycle-bg-card> against stubbed view chrome
and stubbed `sensor.sol_*` states, and photographs three panels of it.

The discs are the cutouts in demo/assets/planets, placed by the `discs.json`
that tools/cutout_planets.py wrote next to them.

    python3 tools/render_planets_doc.py         # -> docs/planets.png

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
PORT = 8793
PANEL_W, PANEL_H = 420, 262      # matches docs/phases.png
PRZERWA = 6

# Positions are made up, not snapshotted: a real evening has three planets up
# and the strip is about showing the feature. Altitudes and azimuths are
# plausible for a September evening at 52 N — an ecliptic arc from the WSW
# horizon to the SE.
SKY = {
    "mercury": (243, 3), "venus": (255, 11), "mars": (231, 18),
    "jupiter": (196, 34), "saturn": (152, 31), "uranus": (119, 22),
    "neptune": (98, 13), "pluto": (176, 25),
}
# elevation of the sun, caption
PANELE = [
    (-16.0, "night — full opacity"),
    (-4.0, "dusk — fading in"),
    (24.0, "day — day: 0.35"),
]

STRONA = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#0d1015}#host{width:%dpx;height:%dpx}
/* the card paints hui-view-background; Home Assistant's own stylesheet is what
   gives that element its box, so the stand-in needs the same two rules or the
   sky is painted onto a zero-height element and never shows */
hui-view-background{position:absolute;inset:0;display:block}</style>
<div id="host"></div>
<script>
class A extends HTMLElement{} class B extends HTMLElement{} class C extends HTMLElement{}
customElements.define('hui-view-container', A);
customElements.define('hui-view-background', B);
customElements.define('hui-view', C);
</script>
<script src="/sun-cycle-bg.js"></script>
<script>
const SKY = %s, DISCS = %s;
window.render = (elev) => {
  const host = document.getElementById('host');
  host.innerHTML = '';
  const cont = document.createElement('hui-view-container');
  cont.style.cssText = 'display:block;position:relative;width:%dpx;height:%dpx;overflow:hidden';
  cont.appendChild(document.createElement('hui-view-background'));
  cont.appendChild(document.createElement('hui-view'));
  host.appendChild(cont);
  const card = document.createElement('sun-cycle-bg-card');
  card.setConfig({
    stars: { count: 120, sizes: 'mixed', size: 0.6, glow: 0.4, twinkle: 0.5, drift: 0 },
    // the moon runs on the real clock and would land wherever it happens to
    // be — on top of Saturn, in the first cut of this strip
    moon: false,
    planets: { images: '/demo/assets/planets/', discs: DISCS, size: 3.4,
               scale: 'diameters', glow: 0.5, day: 0.35, labels: true },
  });
  cont.insertBefore(card, cont.firstChild);
  const states = { 'sun.sun': { attributes: { elevation: elev, azimuth: 288 } } };
  for (const [b, v] of Object.entries(SKY)) {
    states['sensor.sol_' + b + '_azimuth'] = { state: String(v[0]) };
    states['sensor.sol_' + b + '_elevation'] = { state: String(v[1]) };
  }
  card.hass = { states, config: { latitude: 52, longitude: 14.5 } };
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
    discs = json.loads((ROOT / "demo" / "assets" / "planets" / "discs.json").read_text())
    strona = ROOT / "docs" / "_planets_frame.html"
    strona.write_text(STRONA % (PANEL_W, PANEL_H, json.dumps(SKY),
                                json.dumps(discs), PANEL_W, PANEL_H))
    srv = serwuj()
    klatki = []
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": PANEL_W, "height": PANEL_H},
                             device_scale_factor=2)
            bledy = []
            pg.on("pageerror", lambda e: bledy.append(str(e)))
            pg.on("console", lambda m: bledy.append(f"{m.type}: {m.text}")
                  if m.type in ("error", "warning") else None)
            for elev, _ in PANELE:
                pg.goto(f"http://127.0.0.1:{PORT}/docs/_planets_frame.html")
                pg.evaluate("e => window.render(e)", elev)
                # the discs carry `transition: opacity 2s linear`; grabbing a
                # frame early photographs the fade, not the state
                pg.wait_for_timeout(2600)
                klatki.append(pg.locator("#host").screenshot())
            br.close()
    finally:
        srv.shutdown()
        strona.unlink()

    from PIL import Image
    import io
    obrazy = [Image.open(io.BytesIO(k)) for k in klatki]
    w, h = obrazy[0].size
    strip = Image.new("RGB", (w * len(obrazy) + PRZERWA * 2 * (len(obrazy) - 1), h),
                      (13, 16, 21))
    for i, im in enumerate(obrazy):
        strip.paste(im, (i * (w + PRZERWA * 2), 0))
    out = DOCS / "planets.png"
    strip.save(out, optimize=True)
    print(f"{out} {strip.size} ({out.stat().st_size // 1024} kB)")
    print("konsola:", bledy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
