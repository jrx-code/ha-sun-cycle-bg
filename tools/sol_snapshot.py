#!/usr/bin/env python3
"""Snapshot the Sol integration into demo/sol_snapshot.json.

The tuning page is served from /local without a token, so it cannot ask Home
Assistant anything; the planet positions it draws are baked in at build time,
exactly the way the ISS page bakes its passes. Re-run this to refresh them.

    export HA_URL=https://your-ha:8123 HA_TOKEN=...
    python3 tools/sol_snapshot.py
"""
import datetime
import json
import os
import pathlib
import ssl
import subprocess
import sys
import urllib.request

HA_URL = os.environ.get("HA_URL", "http://homeassistant.local:8123")
BW_ITEM = os.environ.get("HA_BW_ITEM", "")   # Bitwarden item holding the HA token
OUT = pathlib.Path(__file__).parent.parent / "demo" / "sol_snapshot.json"
BODIES = ["mercury", "venus", "mars", "jupiter", "saturn", "uranus",
          "neptune", "pluto"]


def token() -> str:
    if os.environ.get("HA_TOKEN"):
        return os.environ["HA_TOKEN"]
    sesja = os.environ.get("BW_SESSION")
    if not sesja or not BW_ITEM:
        raise SystemExit("ustaw HA_TOKEN albo BW_SESSION=$(bw unlock --raw) + HA_BW_ITEM")
    return subprocess.run(["bw", "get", "password", BW_ITEM, "--session", sesja],
                          capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    req = urllib.request.Request(
        HA_URL.rstrip("/") + "/api/states",
        headers={"Authorization": "Bearer " + token()})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        stany = {s["entity_id"]: s for s in json.load(r)}

    dane = {"pobrano": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "slonce": {}, "planety": {}}
    sun = stany.get("sun.sun")
    if sun:
        dane["slonce"] = {"elevation": sun["attributes"].get("elevation"),
                          "azimuth": sun["attributes"].get("azimuth")}
    for b in BODIES:
        wpis = {}
        for pole in ("azimuth", "elevation", "rise", "set"):
            s = stany.get(f"sensor.sol_{b}_{pole}")
            if s:
                wpis[pole] = s["state"]
        if wpis:
            dane["planety"][b] = wpis
    OUT.write_text(json.dumps(dane, indent=2) + "\n")
    up = [b for b, w in dane["planety"].items() if float(w.get("elevation", -99)) > 0]
    print(f"{OUT}: {len(dane['planety'])} ciał, nad horyzontem: {', '.join(up) or '—'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
