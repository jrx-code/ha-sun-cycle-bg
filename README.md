# Sun Cycle Background

A living day-cycle background for Home Assistant dashboards. One invisible
Lovelace card paints the whole view from the **real position of the sun**
(`sun.sun` elevation) and keeps it gently moving around the clock:

- **Sky** — the gradient shifts continuously through night → dawn → sunrise →
  golden hour → noon and back. Palette is interpolated between
  elevation-keyed anchors, so seasons and latitudes work automatically
  (a winter noon simply never reaches the full-noon palette).
- **Sun** — a warm halo that literally *rises from below the frame edge*,
  climbs toward the top by noon and sets in reverse. Gone at night.
- **Rays** — soft light shafts sway ±4° on a 24 s cycle; their brightness
  follows the sun (0 at night, full at noon). Clipped and masked so they
  never cause scrollbars or hard edges.
- **Moon** — after sunset a silver disc with a soft halo rises on the left,
  shimmering slightly (7 s scale/opacity pulse). Sets before sunrise.
- **Stars** — a built-in field of twinkling stars that also **drifts across
  the sky**: stars rise at the right edge and set at the left (seamless
  wrap, default 30 min per screen width). Stars fade out at dawn and
  return at dusk.

Because everything is keyed to solar elevation, the panel on your wall
matches the sky outside your window: pink dawn at dawn, golden hour at
golden hour, stars at night.

## Performance

Designed for wall-mounted kiosk tablets:

- every animation is **transform/opacity only** — runs entirely on the
  compositor, no layout, no paint, no JS animation loops,
- one animated layer each for rays, moon and stars,
- the palette repaints only when the sun moves ≥ 0.15° (about every 30 s),
- the star field is 5 DOM nodes total (multi-point `box-shadow` stars,
  group-level twinkle).

## Install

### HACS (custom repository)

1. HACS → menu → *Custom repositories* → add this repo URL, category
   **Dashboard** (Lovelace).
2. Install **Sun Cycle Background**, reload resources when prompted.

### Manual

1. Copy `sun-cycle-bg.js` to `/config/www/`.
2. Add a dashboard resource: URL `/local/sun-cycle-bg.js`, type
   **JavaScript module**.

## Usage

Add the (invisible) card to every view you want painted — e.g. at the end of
a column, or via a shared include / dashboard generator:

```yaml
type: custom:sun-cycle-bg-card
```

All options, with defaults:

```yaml
type: custom:sun-cycle-bg-card
sun_entity: sun.sun     # any entity with an `elevation` attribute
stars:                  # `stars: false` disables the built-in field
  count: 90             # total stars
  drift: 1800           # seconds per screen-width of drift, 0 = static
```

If your dashboard already has its own star layer with the element id
`star-twinkle-layer`, its opacity is driven too (fades at dawn, returns at
dusk) — set `stars: false` to avoid doubling the field.

## Tuning the palette

The whole look lives in one table at the top of `sun-cycle-bg.js` — `STOPS`:
seven anchors keyed by sun elevation (−18° … 52°), each holding the sky
gradient (3 × RGB), the sun halo (RGBA + vertical position), ray strength,
star opacity and the moon (alpha + vertical position). Everything between
anchors is linear RGB interpolation. Edit the numbers, bump your resource
version, reload.

## Demo

Open [`demo/simulator.html`](demo/simulator.html) in a browser — a 24 h
slider (with an autoplay button: full day in 60 s) that runs the exact same
palette function against a simulated sun elevation.

## How it works

The card renders nothing itself. On every sun update it:

1. paints `hui-view-background` with the interpolated sky + sun halo,
2. maintains three absolutely-positioned layers in `hui-view-container`
   (inserted before `hui-view`, so they sit above the background and below
   every card): clipped ray layer, moon, star field,
3. injects its keyframe CSS once per shadow root.

Layers are deduplicated on re-create and die with their container — there is
deliberately no cleanup on disconnect, which would race view-to-view
navigation.

## License

MIT
