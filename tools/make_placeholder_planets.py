#!/usr/bin/env python3
"""Draw the placeholder planet discs: demo/assets/planets/<body>.png

The card ships no planet artwork, the same way it ships no sun or moon —
`planets.images` points at files of yours. But the documentation needs
*something* to photograph, and a screenshot made from someone else's planet
renders would redistribute them as surely as committing the files would. So
these nine discs are drawn here, from nothing: a shaded sphere per body, with
bands for the gas giants, a cap for Mars, a ring for Saturn. They are the
repository's own artwork under its MIT licence, they look like planets from
across a room, and nobody should mistake them for photographs.

    python3 tools/make_placeholder_planets.py            # -> demo/assets/planets

Real photographs look far better on a dashboard. Cut your own out of renders
with tools/cutout_planets.py and point `images:` at those.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

OUT = pathlib.Path(__file__).parent.parent / "demo" / "assets" / "planets"
SIZE = 256
# base colour, pole colour, band strength (0 = smooth), ring
BODIES = {
    "mercury": ((150, 143, 134), (120, 114, 106), 0.0, None),
    "venus":   ((226, 199, 141), (208, 180, 128), 0.15, None),
    "earth":   ((58, 106, 168), (232, 238, 244), 0.0, None),
    "mars":    ((193, 104, 66), (226, 214, 205), 0.08, None),
    "jupiter": ((214, 183, 148), (188, 156, 128), 0.55, None),
    "saturn":  ((222, 199, 155), (196, 172, 136), 0.35, (1.42, 2.30)),
    "uranus":  ((166, 219, 224), (150, 202, 210), 0.10, (1.25, 1.55)),
    "neptune": ((62, 100, 200), (52, 84, 176), 0.18, None),
    "pluto":   ((176, 160, 146), (214, 206, 198), 0.0, None),
}
# where the light comes from, in disc radii; the same for every body so the
# set reads as one scene
LIGHT = np.array([-0.55, -0.35, 0.76])


def sphere(body, rgb, pole, bands, rng):
    """Lambert-shaded ball with limb darkening, on a transparent square."""
    n = SIZE
    y, x = np.mgrid[0:n, 0:n]
    # Everything drawn — ball or outermost ring — fills 0.92 of the file, so
    # the ball shrinks by exactly as much as its rings stick out. The card
    # divides the ball diameter back out through `discs`, so a ringed planet
    # is not punished for its rings.
    ring = BODIES[body][3]
    r = n * 0.46 / (ring[1] if ring else 1.0)
    cx = cy = n / 2
    dx, dy = (x - cx) / r, (y - cy) / r
    d2 = dx * dx + dy * dy
    inside = d2 <= 1.0
    dz = np.sqrt(np.clip(1 - d2, 0, 1))
    normal = np.stack([dx, dy, dz], -1)
    lam = np.clip(normal @ LIGHT, 0, 1)
    # terminator softened, plus a little ambient so the night side is not void
    shade = 0.06 + 0.94 * lam ** 0.85

    lat = np.clip(dy, -1, 1)
    base = np.array(rgb, dtype=np.float32)
    polar = np.array(pole, dtype=np.float32)
    col = base[None, None, :] * np.ones((n, n, 1), np.float32)
    # poles blend towards the second colour: caps on Mars, haze on the giants
    t = (np.abs(lat) ** 3)[..., None]
    col = col * (1 - t) + polar[None, None, :] * t
    if bands:
        # latitude bands: a few sine harmonics, so they read as belts rather
        # than as noise, with a slight random phase per body
        f = sum(np.sin(lat * k * np.pi + rng.uniform(0, 6.28)) / (i + 1)
                for i, k in enumerate((3.0, 5.0, 9.0, 17.0)))
        col = col * (1 + bands * 0.16 * f[..., None])
    if body == "earth":
        # a couple of continents, so the blue ball is not a marble
        land = np.zeros((n, n), np.float32)
        for _ in range(7):
            lx, ly = rng.uniform(-0.8, 0.8), rng.uniform(-0.7, 0.7)
            rr = rng.uniform(0.18, 0.42)
            land += np.exp(-(((dx - lx) ** 2 + (dy - ly) ** 2) / (rr * rr)))
        land = np.clip(land, 0, 1)[..., None]
        col = col * (1 - land) + np.array([104, 138, 92], np.float32) * land
        cloud = np.zeros((n, n), np.float32)
        for _ in range(9):
            lx, ly = rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)
            # squashed east-west, the way a cloud band is; clipped before the
            # exponent, or a far-off centre overflows float32
            q = np.clip(((dx - lx) ** 2 + ((dy - ly) * 4) ** 2) / 0.05, 0, 60)
            cloud += np.exp(-q)
        c = np.clip(cloud, 0, 0.8)[..., None]
        col = col * (1 - c) + 245 * c

    rgba = np.zeros((n, n, 4), np.float32)
    rgba[..., :3] = np.clip(col * shade[..., None], 0, 255)
    # one pixel of feather at the limb, so the disc is not a cut-out
    edge = np.clip((1.0 - np.sqrt(d2)) * r, 0, 1)
    rgba[..., 3] = np.where(inside, 255 * edge, 0)
    return rgba, r, cx, cy


def rings(rgba, r, cx, cy, inner, outer, rng):
    """A tilted annulus behind and in front of the ball."""
    n = SIZE
    y, x = np.mgrid[0:n, 0:n]
    dx = (x - cx) / r
    dy = (y - cy) / r / 0.28          # squash: the ring plane seen near edge-on
    rad = np.sqrt(dx * dx + dy * dy)
    band = (rad >= inner) & (rad <= outer)
    # a couple of gaps, and a fade towards both rims
    t = (rad - inner) / (outer - inner)
    a = np.clip(np.sin(np.clip(t, 0, 1) * np.pi) * 1.15, 0, 1)
    a *= 1 - 0.75 * np.exp(-((t - 0.55) ** 2) / 0.0022)      # Cassini-ish gap
    a = np.where(band, a, 0) * 0.72
    ring = np.zeros((n, n, 4), np.float32)
    ring[..., :3] = np.array([228, 214, 186], np.float32)
    ring[..., 3] = a * 255
    # the ball is opaque, so compositing the ring under it is enough; the part
    # crossing the disc in front is faked by keeping a little of it on top
    out = ring.copy()
    alpha = rgba[..., 3:4] / 255
    out[..., :3] = rgba[..., :3] * alpha + out[..., :3] * (1 - alpha)
    out[..., 3:4] = np.clip(rgba[..., 3:4] + out[..., 3:4] * (1 - alpha), 0, 255)
    front = (dy > 0) & band
    f = (a * 0.5)[..., None] * front[..., None]
    out[..., :3] = out[..., :3] * (1 - f) + np.array([228, 214, 186], np.float32) * f
    out[..., 3:4] = np.maximum(out[..., 3:4], (f * 255))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(11)
    discs = {}
    for body, (rgb, pole, bands, ring) in BODIES.items():
        rgba, r, cx, cy = sphere(body, rgb, pole, bands, rng)
        if ring:
            rgba = rings(rgba, r, cx, cy, ring[0], ring[1], rng)
        Image.fromarray(rgba.astype(np.uint8), "RGBA").save(OUT / f"{body}.png",
                                                            optimize=True)
        discs[body] = [round(2 * r / SIZE, 4), 0.5, 0.5]
        print(f"{body}.png  disc={discs[body]}")
    # the placement numbers for these files, ready to paste under `discs:`
    (OUT / "discs.json").write_text(json.dumps(discs, indent=2) + "\n")
    print(f"-> {OUT / 'discs.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
