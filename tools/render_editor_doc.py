#!/usr/bin/env python3
"""Render docs/thumbnail.png and docs/editor.png — the picker entry and the form.

Both come from the card itself, not from a screenshot of Home Assistant: the
thumbnail is what `getStubConfig()` plus a hass carrying nothing but a midday
sun produces, which is exactly the picker's situation, and the form is the
element `getConfigElement()` returns, fed a config with a few things changed so
the badges have something to count.

    python3 tools/render_editor_doc.py      # -> docs/thumbnail.png, docs/editor.png

Needs: playwright (with chromium) and pillow.
"""
import http.server
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).parent.parent
DOCS = ROOT / "docs"
PORT = 8797

STRONA = """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;background:#101418;
    font:14px system-ui,"Segoe UI",Roboto,sans-serif;color:#e8ebf1}
  /* the editor styles itself from Home Assistant's variables; the page has to
     stand in for the theme or the form renders on nothing */
  :root{--primary-text-color:#e8ebf1;--secondary-text-color:#96a0b0;
    --divider-color:rgba(255,255,255,.14);--primary-color:#03a9f4;
    --card-background-color:#171c22;--error-color:#e0574a;}
  #karta{width:520px}
  #edytor{width:470px;background:#171c22;border-radius:12px;padding:10px 12px}
  hui-view-background{position:absolute;inset:0;display:block}
</style>
<div id="karta"></div>
<div id="edytor"></div>
<script>class B extends HTMLElement{} customElements.define('hui-view-background', B);</script>
<script src="/src/sun-cycle-bg.js"></script>
<script>
const K = customElements.get('sun-cycle-bg-card');

// the picker: the stub config and a hass with nothing in it but a midday sun
const karta = document.createElement('sun-cycle-bg-card');
karta.setConfig(Object.assign({type:'custom:sun-cycle-bg-card', assets:'/demo/assets/'},
                              K.getStubConfig()));
document.getElementById('karta').appendChild(karta);
karta.hass = { states:{'sun.sun':{attributes:{elevation:41,azimuth:180}}},
               config:{latitude:52,longitude:14.5} };

// the form, with enough changed that the badges have something to say
const ed = K.getConfigElement();
ed.addEventListener('config-changed', (e) =>
  ed.setConfig(Object.assign({type:'custom:sun-cycle-bg-card'}, e.detail.config)));
ed.setConfig({type:'custom:sun-cycle-bg-card', stars:{count:150, twinkle:0.6},
              planets:{size:1.2, labels:true}, milky_way:{projection:'equirect'}});
document.getElementById('edytor').appendChild(ed);
const R = ed.shadowRoot;
for (const d of R.querySelectorAll('.scb-grupa')) {
  const t = d.querySelector('.scb-tyt').textContent;
  d.open = (t === 'Stars' || t === 'YAML');
}
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
    strona = DOCS / "_editor_frame.html"
    strona.write_text(STRONA)
    srv = serwuj()
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            pg = br.new_page(viewport={"width": 560, "height": 1400},
                             device_scale_factor=2)
            bledy = []
            pg.on("pageerror", lambda e: bledy.append(str(e)))
            pg.on("console", lambda m: bledy.append(f"{m.type}: {m.text}")
                  if m.type == "error" else None)
            pg.goto(f"http://127.0.0.1:{PORT}/docs/_editor_frame.html",
                    wait_until="networkidle")
            pg.wait_for_timeout(3500)
            pg.locator("#karta").screenshot(path=str(DOCS / "thumbnail.png"))
            pg.locator("#edytor").screenshot(path=str(DOCS / "editor.png"))
            miara = pg.evaluate("""() => {
              const box = document.querySelector('.sun-cycle-standalone');
              const ed = document.querySelector('sun-cycle-bg-card-editor');
              return {
                planet: [...box.querySelectorAll('.sun-cycle-planets div[data-body]')]
                  .filter(e => Number(e.style.opacity || 0) > 0.05).length,
                warstwy: box.querySelectorAll('[class^=sun-cycle-]').length,
                grupy: ed.shadowRoot.querySelectorAll('.scb-grupa').length,
                baner: !!ed.shadowRoot.querySelector('.scb-blad'),
              };
            }""")
            br.close()
    finally:
        srv.shutdown()
        strona.unlink()

    from PIL import Image
    for nazwa in ("thumbnail.png", "editor.png"):
        p = DOCS / nazwa
        Image.open(p).save(p, optimize=True)
        print(f"{p} ({p.stat().st_size // 1024} kB)")
    print("podglad:", miara)
    print("konsola:", bledy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
