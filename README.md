# Sun Cycle Background

![Full day cycle — 24 h in 4 s](docs/cycle.gif)

*The sun on its real arc: night, dawn, noon, sunset (52° N, early September):*

![Night, dawn, noon and sunset phases](docs/phases.png)

A living day-cycle background for Home Assistant dashboards. One invisible
Lovelace card paints the whole view from the **real position of the sun and
moon**, and keeps it gently moving around the clock:

- **Sky** — the gradient shifts continuously through night → dawn → sunrise →
  golden hour → noon and back. Palette is interpolated between
  elevation-keyed anchors, so seasons and latitudes work automatically
  (a winter noon simply never reaches the full-noon palette).
- **Sun on its real diurnal arc** — `sun.sun` publishes both `azimuth` and
  `elevation`, so the sun rises in the east, culminates in the south and sets
  in the west along a path tilted by (90° − your latitude), exactly like the
  sky outside. The arc flattens in winter and towers in summer on its own,
  because the data does.
- **Twilight glow that stays at the horizon** — the scattered light of dusk
  and dawn is a wide, flat band along the bottom of the sky, centred on the
  sun's azimuth. It widens as the sun sinks (light scatters along the whole
  horizon, not just towards the sun) and fades out before its centre can drift
  off-frame. The disc keeps its own aureole, which grows back to its full
  daytime size above ~14°, so broad daylight looks exactly as it did.
- **Crepuscular rays** — a wide, blurred fan spreads from the sun near the
  horizon and, as the sun climbs, fades smoothly (smoothstep over 0–22° of
  elevation) into a plain aureole. No hard edges, no visible switch, nothing
  left once the sun is well below the horizon.
- **Moon with its own ephemeris** — position *and* phase are computed from a
  compact lunar series, so the moon keeps its own schedule instead of
  mirroring the sun (on a given night it may be up for 8 hours while the sun
  was up for 14), and it is drawn as the actual crescent / half / gibbous
  shape, bright limb facing the sun.
- **Stars** — a field of twinkling stars moving **east to west**, like the
  sky. Cheap linear drift by default; optional rotation about the celestial
  pole (`stars.rotate: true`) for real arcs.

Because everything is keyed to solar elevation, the panel on your wall
matches the sky outside your window: pink dawn at dawn, golden hour at
golden hour, stars at night.

## Performance

Designed for wall-mounted kiosk tablets:

- every animation is **transform/opacity only** — runs entirely on the
  compositor, no layout, no paint, no JS animation loops,
- one animated layer each for rays, moon and stars,
- the palette repaints only when the sun moves ≥ 0.15° in elevation or ≥ 0.6°
  in azimuth (about every half minute),
- the star field is 5 painted nodes per copy — 10 for the drifting strip, 5
  when rotating (multi-point `box-shadow` stars, group-level twinkle),
- the whole astronomy pass is a few dozen floating-point operations per
  repaint — no dependencies, no network.

Measured with this card running on a 1280×400 Raspberry Pi 5 kiosk (32-bit
Chromium, blur enabled): **60 fps**.

`stars.rotate: true` is the one option with a real cost. Rotating a field
about the pole means the layer has to cover the entire disc it sweeps, which
is several times the frame area, so the star count scales up to keep the same
on-screen density. Fine for panel-sized views; skip it on a 4K dashboard.

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
sun_entity: sun.sun     # any entity with `elevation` (and ideally `azimuth`)
twilight_palette: false # true = warmer amber dusk anchors instead of mauve
azimuth: [50, 310]      # sky window mapped across the frame, degrees
rays:
  blur: 28              # px of blur on the ray fan; 0 disables the filter
  strength: 0.5         # peak ray opacity, reached at the horizon
moon: true              # false hides the moon entirely
stars:                  # `stars: false` disables the built-in field
  count: 90             # stars visible on screen
  drift: 1800           # seconds per screen-width of drift, 0 = static
  rotate: false         # true = rotate about the celestial pole instead

# Optional artwork for the two discs — see below. Left out, both stay drawn.
sun_image: null         # e.g. /local/sun-cycle/sun.png
sun_image_width: 10.5   # disc diameter, % of the view width
sun_image_blur: 11.5    # % of that diameter, not px; 0 disables the blur
sun_image_disc: [1, 0.5, 0.5]
moon_image: null
moon_image_width: 0     # 0 keeps the CSS default (15%, capped at 190 px)
moon_image_disc: [1, 0.5, 0.5]
```

## Drawing the discs from your own artwork

The sun has no drawn disc: by default it *is* the aureole and the ray fan. The
moon is drawn as a circle with the real terminator. Point `sun_image` and
`moon_image` at your own files and those places are taken over by pictures,
while every glow stays rendered — the twilight band, the disc aureole, the ray
fan and the moon halo. The two options are independent.

**No artwork ships with the card.** These are paths to your files (`/local/...`),
so the card itself carries no images and you keep whatever licence your own
artwork has. The two PNGs under `demo/assets/` exist only to drive
`demo/images-poc.html`; they are the repository owner's own artwork and fall
under this repository's MIT licence like the rest of it.

`*_image_disc` is `[diameter / image width, cx / image width, cy / image
height]` — where the disc actually sits inside the file. Artwork rarely fills
its frame: a sun render carries rays sticking out on one side, a moon render
carries a baked glow. Placing such a file by its own centre puts the disc
beside its aureole, so measure the disc from the alpha channel and pass it
here. The default `[1, 0.5, 0.5]` means a disc filling a square image.

![A full day with the discs drawn from artwork](docs/artwork.gif)

*The same four phases with `sun_image` and `moon_image` set — night, dawn,
noon, sunset (52° N, 3 September, a 65 %-lit moon):*

![Night, dawn, noon and sunset drawn from artwork](docs/artwork.png)

Two details that are not obvious:

- **Blur is a share of the disc diameter, never a pixel figure.** The same card
  runs in a 430 px card and on a 1920 px kiosk, and a pixel value tuned in one
  is four times wrong in the other. A sharp-edged disc reads as a sticker
  pasted on the sky; something around 10 % of the diameter looks like a sun.
- **The sun disc fades out below −3° elevation.** The projection parks anything
  under the horizon on the bottom edge instead of pushing it out of frame, so
  an un-faded disc would sit there glowing all night.

Both discs are graded to the sky palette — the sun reddens and dims towards the
horizon, the moon pales at dusk and reaches full brightness deep in the night —
so a flat image does not read as pasted on. The moon image is clipped by the
terminator, so the phase still shows with the artwork as the lit texture; the
mask turns towards the sun while the image counter-rotates, keeping the maria
upright.

The default azimuth window (50° → 310°) assumes the frame looks south: east
on the left, west on the right, wide enough that a midsummer sunrise (67°)
and sunset (293°) both land inside the frame. Narrow it to zoom in on the
southern sky, or flip the two numbers for a north-facing view.

The moon needs your coordinates; it reads them from Home Assistant's own
configuration (`hass.config.latitude` / `longitude`), so there is nothing to
set up.

If your dashboard already has its own star layer with the element id
`star-twinkle-layer`, its opacity is driven too (fades at dawn, returns at
dusk) — set `stars: false` to avoid doubling the field.

## Tuning the palette

The whole look lives in one table at the top of `sun-cycle-bg.js` — `STOPS`:
seven anchors keyed by sun elevation (−18° … 52°), each holding the sky
gradient (3 × RGB), the sun halo colour (RGBA) and the star opacity.
Everything between anchors is linear RGB interpolation. Positions are no
longer in the table — the sun and moon are placed from their real coordinates.
Edit the numbers, bump your resource version, reload.

### Accuracy

The built-in astronomy is a low-precision series, and it is checked, not
assumed. Against Home Assistant's own `astral` values it lands within 0.24°
in elevation and 0.57° in azimuth, gives exactly 180.0° azimuth at solar
culmination, and reproduces HA's sunrise time to about 20 seconds. The lunar
series is checked against textbook geometry: 1.6° from the sun at new moon,
179.6° opposite at full moon. On a 1280 px frame, half a degree of azimuth is
about three pixels.

`test/smoke.html` runs the card against stubbed view chrome at a frozen
instant and prints the resulting sun/moon positions, ray opacity, phase and
the twilight band's geometry — open it in a browser after changing anything.

## Demo

Open [`demo/simulator.html`](demo/simulator.html) in a browser. It runs the
same astronomy and the same placement the card uses, with sliders for time of
day, date and latitude, plus an autoplay button (full day in 60 s). Move the
latitude slider to watch the diurnal arc stand up towards the equator and lie
down towards the pole; move the date slider to watch it rise and fall with the
seasons.

The frames above were rendered from it — it accepts `?t=<minutes>`,
`?d=<day of year>`, `?lat=<degrees>`, `?seed=<n>` (deterministic stars),
`?bare=1` (just the scene, no chrome) and `?art=1` (discs drawn from
`demo/assets` instead of the render). `tools/render_docs.py` drives it
headlessly and rebuilds `docs/artwork.gif` and `docs/artwork.png`, so the
documentation cannot drift away from the code.

[`demo/images-poc.html`](demo/images-poc.html) is the page the artwork numbers
were tuned on: four ways of drawing the discs on one shared instant, with
sliders for disc size and blur.

## How it works

The card renders nothing itself. On every sun update it:

1. maps the sun's azimuth and elevation onto the frame and paints
   `hui-view-background` with the interpolated sky plus the sun's aureole at
   that spot,
2. maintains three absolutely-positioned layers in `hui-view-container`
   (inserted before `hui-view`, so they sit above the background and below
   every card): the ray fan, the moon (an inline SVG whose lit path is the
   real terminator), and the star field,
3. computes the moon's position and phase from the current time and the
   dashboard's coordinates,
4. injects its keyframe CSS once per shadow root.

Layers are deduplicated on re-create and die with their container — there is
deliberately no cleanup on disconnect, which would race view-to-view
navigation.

## License

MIT
