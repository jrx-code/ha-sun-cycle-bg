#!/usr/bin/env python3
"""Render the README artwork docs from demo/simulator.html.

The demo is the only place that draws the card's look outside Home Assistant,
so the documentation images are captured from it rather than drawn by hand —
that way they cannot drift away from the code the way they did before 1.1.1.

    python3 tools/render_docs.py            # -> docs/artwork.gif + artwork.png

Both come from `?art=1`, the mode that draws the discs from demo/assets the way
`sun_image` / `moon_image` do on the card. The plain look already has its own
pair (docs/cycle.gif, docs/phases.png) and is left alone.

Needs: playwright (with chromium), ffmpeg, ImageMagick.
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
PORT = 8791

# 3 September, 52 N: the moon is 65 % lit and high in a dark sky, so the
# terminator is actually visible on the artwork instead of a plain full disc.
DZIEN, SZEROKOSC, ZIARNO = 245, 52, 42
KLATEK = 36                      # one per 40 minutes — a full day
GIF_W, GIF_H = 640, 360
PANEL_W, PANEL_H = 420, 262      # matches the existing docs/phases.png strip
PRZERWA = 6
# Sun elevations to pick the strip panels by, in the order they are shown.
FAZY = [("night", -20.0), ("dawn", -4.0), ("noon", None), ("sunset", 0.0)]


def serwuj():
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(
        *a, directory=str(ROOT), **k)
    # Set on the class, before binding: an instance attribute is assigned after
    # __init__ has already bound the socket, so a re-run inside the TIME_WAIT
    # window dies with "address already in use".
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def url(t, art=True):
    return (f"http://127.0.0.1:{PORT}/demo/simulator.html?bare=1&seed={ZIARNO}"
            f"&d={DZIEN}&lat={SZEROKOSC}&t={t}" + ("&art=1" if art else ""))


# Both discs carry `transition: opacity 1s linear`, so a frame grabbed straight
# after moving the clock shows the previous instant fading out — the first cut of
# these docs had a sun sitting in the night panel because of exactly that.
OSIAD = 1150

USTAW = """(min) => {
  const s = document.getElementById('t');
  s.value = min;
  s.dispatchEvent(new Event('input'));
  const m = /sun (-?[\\d.]+)/.exec(document.getElementById('phinfo').textContent);
  const ks = document.getElementById('moon');
  return { sun: m ? parseFloat(m[1]) : null,
           moonY: parseFloat(ks.style.top), moonA: parseFloat(ks.style.opacity) };
}"""


def main():
    srv = serwuj()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="sun-cycle-docs-"))
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch()

            # --- animation: one full day ---------------------------------
            page = br.new_page(viewport={"width": GIF_W, "height": GIF_H})
            page.goto(url(0), wait_until="networkidle")
            scena = page.locator("#scene")
            for i in range(KLATEK):
                page.evaluate(USTAW, i * 1440 // KLATEK)
                page.wait_for_timeout(OSIAD)
                scena.screenshot(path=str(tmp / f"f{i:02d}.png"))
            page.close()

            # --- strip: four phases of the same day -----------------------
            page = br.new_page(viewport={"width": PANEL_W, "height": PANEL_H})
            page.goto(url(0), wait_until="networkidle")
            scena = page.locator("#scene")
            probki = []
            for t in range(0, 1440, 5):
                st = page.evaluate(USTAW, t)
                probki.append((t, st["sun"], st["moonY"], st["moonA"]))
            panele = []
            for nazwa, cel in FAZY:
                if cel is None:
                    t = max(probki, key=lambda p: p[1])[0]
                elif nazwa == "night":
                    # The darkest hour is not the best picture: pick a moon that
                    # is bright and clear of the top edge rather than clipped.
                    ok = [p for p in probki if p[1] < -15 and 18 < p[2] < 75 and p[3] > 0.9]
                    t = min(ok, key=lambda p: p[1])[0] if ok else \
                        min(probki, key=lambda p: p[1])[0]
                else:
                    # after noon for sunset, before it for dawn
                    okno = [p for p in probki if p[0] > 720] if nazwa == "sunset" \
                        else [p for p in probki if p[0] <= 720]
                    t = min(okno, key=lambda p: abs(p[1] - cel))[0]
                page.evaluate(USTAW, t)
                page.wait_for_timeout(OSIAD)
                sciezka = tmp / f"p_{nazwa}.png"
                scena.screenshot(path=str(sciezka))
                panele.append(sciezka)
                print(f"{nazwa:7s} t={t//60:02d}:{t%60:02d}")
            page.close()
            br.close()

        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-framerate", "9",
            "-i", str(tmp / "f%02d.png"),
            # One palette for the whole day, ordered dithering: this is almost
            # all smooth sky gradient, and error-diffusion dithering scatters it
            # into visible speckle that also costs a third more bytes.
            "-filter_complex", "[0:v]split[a][b];[a]palettegen=max_colors=256[p];"
                               "[b][p]paletteuse=dither=bayer:bayer_scale=5",
            "-loop", "0", str(DOCS / "artwork.gif")], check=True)
        subprocess.run(["montage", *[str(p) for p in panele], "-tile", "4x1",
                        "-geometry", f"+{PRZERWA // 2}+0", "-background", "#0d1015",
                        str(DOCS / "artwork.png")], check=True)
        for f in ("artwork.gif", "artwork.png"):
            print(f, (DOCS / f).stat().st_size, "B")
    finally:
        srv.shutdown()
        srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
