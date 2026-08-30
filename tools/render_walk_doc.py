#!/usr/bin/env python3
"""Render docs/planets-walk.gif — what 1.7.0 changed, side by side.

Two real <sun-cycle-bg-card> instances on one page, fed the same planet at the
same instants. The left one gets states the way Sol publishes them *without*
the promise attributes, which is what every version before 1.7.0 saw: the disc
sits still and then hops a whole degree. The right one gets `next_target` and
`next_update` too, so the card walks it there in the time the sensor says it
has. Nothing here is drawn or faked — both panels are the shipped card, and
the only difference between them is the two attributes.

Time is compressed: a degree of azimuth takes Sol about five minutes and would
make an unwatchable animation, so the promises here run 2.5 s. The motion is
otherwise exactly what the card does.

Captured as video (Playwright records at a constant frame rate, so the walk is
sampled evenly) and converted with ffmpeg.

    python3 tools/render_walk_doc.py        # -> docs/planets-walk.gif

Needs: playwright (with chromium), ffmpeg.
"""
import http.server
import pathlib
import shutil
import socketserver
import subprocess
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent.parent
DOCS = ROOT / "docs"
PORT = 8794
PANEL_W, PANEL_H = 430, 250
GAP = 10
KROK_S = 2.5          # seconds per degree of azimuth in this animation
KROKOW = 5            # how many degrees to walk
FPS = 10
# The panel is 430 px wide, the kiosk this was built for is 1280 px across a
# 260-degree window: 4.9 px per degree. Narrowing the window here to 87 deg
# puts the same 4.9 px per degree on the smaller frame, so the hop is the size
# it really is on a wall — not magnified for the picture.
OKNO = [140, 227]
SZEROKOSC_GIF = 760   # the README column is narrower than the captured frame

STRONA = """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;background:#0d1015;font:600 12px/1 system-ui,sans-serif;color:#c9d3e2}
  .rzad{display:flex;gap:%dpx;padding:0}
  figure{margin:0}
  figcaption{padding:7px 2px 8px;letter-spacing:.06em;text-transform:uppercase;font-size:11px}
  .kadr{width:%dpx;height:%dpx;position:relative;overflow:hidden;border-radius:10px}
  hui-view-background{position:absolute;inset:0;display:block}
</style>
<div class="rzad">
  <figure><div class="kadr" id="a"></div><figcaption>before 1.7.0 — a degree at a time</figcaption></figure>
  <figure><div class="kadr" id="b"></div><figcaption>1.7.0 — walked to where it is going</figcaption></figure>
</div>
<script>
class A extends HTMLElement{} class B extends HTMLElement{} class C extends HTMLElement{}
customElements.define('hui-view-container', A);
customElements.define('hui-view-background', B);
customElements.define('hui-view', C);
</script>
<script src="/sun-cycle-bg.js"></script>
<script>
const DISCS = %s, OBRAZKI = '/demo/assets/planets/';
const CIALA = ['saturn', 'jupiter', 'mars'];
// where the three sit at the start; the animation walks them all west
const START = { saturn: [158, 27], jupiter: [180, 34], mars: [206, 16] };
const karty = {};
function zbuduj(id) {
  const host = document.getElementById(id);
  const cont = document.createElement('hui-view-container');
  cont.style.cssText = 'display:block;position:relative;width:100%%;height:100%%';
  cont.appendChild(document.createElement('hui-view-background'));
  cont.appendChild(document.createElement('hui-view'));
  host.appendChild(cont);
  const card = document.createElement('sun-cycle-bg-card');
  card.setConfig({
    azimuth: %s,
    stars: { count: 90, sizes: 'mixed', size: 0.6, glow: 0.4, twinkle: 0.5, drift: 0 },
    moon: false,
    planets: { images: OBRAZKI, discs: DISCS, size: 5, scale: 'diameters',
               glow: 0.5, labels: true },
  });
  cont.insertBefore(card, cont.firstChild);
  karty[id] = card;
}
zbuduj('a'); zbuduj('b');

/* One update, delivered to both cards. `zObietnica` decides whether the sensor
   carries next_target/next_update — that single difference is the whole
   subject of this picture. */
function podaj(card, krok, zObietnica, okresMs) {
  const t = Date.now();
  const states = { 'sun.sun': { attributes: { elevation: -16, azimuth: 300 } } };
  for (const b of CIALA) {
    const [az0, alt0] = START[b];
    const az = az0 - krok, alt = alt0 - krok * 0.5;
    const az_s = { state: String(az), last_changed: new Date(t).toISOString(), attributes: {} };
    const alt_s = { state: String(alt), last_changed: new Date(t).toISOString(), attributes: {} };
    if (zObietnica) {
      az_s.attributes = { next_target: String(az - 1),
                          next_update: new Date(t + okresMs).toISOString() };
      alt_s.attributes = { next_target: String(alt - 0.5),
                           next_update: new Date(t + okresMs).toISOString() };
    }
    states['sensor.sol_' + b + '_azimuth'] = az_s;
    states['sensor.sol_' + b + '_elevation'] = alt_s;
  }
  card.hass = { states, config: { latitude: 52, longitude: 14.5 } };
}
window.krok = (n, okresMs) => {
  podaj(karty.a, n, false, okresMs);
  podaj(karty.b, n, true, okresMs);
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
    import json
    discs = json.loads((ROOT / "demo" / "assets" / "planets" / "discs.json").read_text())
    strona = DOCS / "_walk_frame.html"
    strona.write_text(STRONA % (GAP, PANEL_W, PANEL_H, json.dumps(discs),
                                json.dumps(OKNO)))
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sun-cycle-walk-"))
    szer = PANEL_W * 2 + GAP
    wys = PANEL_H + 30
    srv = serwuj()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            ctx = br.new_context(viewport={"width": szer, "height": wys},
                                 record_video_dir=str(tmp),
                                 record_video_size={"width": szer, "height": wys})
            pg = ctx.new_page()
            bledy = []
            pg.on("pageerror", lambda e: bledy.append(str(e)))
            pg.goto(f"http://127.0.0.1:{PORT}/docs/_walk_frame.html",
                    wait_until="networkidle")
            # first update places the discs; the recording starts after it, so
            # the loop does not open on a card sliding in from nowhere
            pg.evaluate("([n, ms]) => window.krok(n, ms)", [0, int(KROK_S * 1000)])
            pg.wait_for_timeout(1200)
            for n in range(1, KROKOW + 1):
                pg.evaluate("([n, ms]) => window.krok(n, ms)", [n, int(KROK_S * 1000)])
                pg.wait_for_timeout(int(KROK_S * 1000))
            sciezka = pg.video.path()
            ctx.close()          # the file is only finalised on close
            br.close()
    finally:
        srv.shutdown()
        strona.unlink()

    wideo = pathlib.Path(sciezka)
    paleta = tmp / "paleta.png"
    out = DOCS / "planets-walk.gif"
    # trim the first second (the placing update) and the last frame stutter
    wspolne = ["-ss", "1.2", "-t", str(KROK_S * KROKOW - 0.3), "-i", str(wideo)]
    # 64 colours is plenty for a night sky and roughly halves the file
    lancuch = f"fps={FPS},scale={SZEROKOSC_GIF}:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", *wspolne, "-vf",
                    f"{lancuch},palettegen=max_colors=64:stats_mode=diff",
                    str(paleta)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", *wspolne, "-i", str(paleta), "-lavfi",
                    f"{lancuch}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
                    str(out)], check=True, capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{out} ({out.stat().st_size // 1024} kB)")
    print("konsola:", bledy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
