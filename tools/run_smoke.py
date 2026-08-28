#!/usr/bin/env python3
"""Run test/smoke.html headless and print what it measured.

The page builds the card against stubbed view chrome at a frozen instant and
stores its readings in document.title as JSON once `window.__smokeDone` is
set. This script opens it in a headless Chromium, waits for that flag and
prints one line per scene, then the console errors it caught (expect none).

    python3 tools/run_smoke.py                 # uses playwright's own chromium
    CHROMIUM=/usr/bin/chromium-browser python3 tools/run_smoke.py

Needs: playwright (pip install playwright; playwright install chromium).
"""
import json
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "test" / "smoke.html"


def main():
    errors = []
    with sync_playwright() as pw:
        kw = {"args": ["--allow-file-access-from-files"]}
        if os.environ.get("CHROMIUM"):
            kw["executable_path"] = os.environ["CHROMIUM"]
        browser = pw.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)
        page.goto(PAGE.as_uri())
        page.wait_for_function("window.__smokeDone === true", timeout=15000)
        for name, reading in json.loads(page.title()):
            print(f"## {name}")
            print(json.dumps(reading, ensure_ascii=False))
        browser.close()
    print("ERRORS:", errors)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
