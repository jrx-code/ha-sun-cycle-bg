# Changelog

All notable changes to this card. Versions before 1.16.0 are described in the
[GitHub releases](https://github.com/jrx-code/hassio-sun-cycle-bg/releases).

## 2.1.2

### Fixed
- An overcast or rainy night stuttered on the Raspberry Pi 5 kiosk: the star field kept twinkling under the sky veil that hides it, and its animated elements with hundreds of box-shadows were composited every frame (measured there with `quality: low`: 91 % janky frames with the field, 11 % with it hidden). When it rains, snows or hails, or the veil reaches 0.8 opacity, the field fades out over 2 s and leaves the page (`display: none`), and comes back with the same fade when the sky clears. `veil: false` keeps the stars.

## 2.1.1

### Fixed
- The rain shader never ran on the Raspberry Pi 5 kiosk: its Android WebView (Chrome 144, V3D 7.1) offers no WebGL 1 context, only WebGL 2, and the card fell back to the classic rain. It now asks for WebGL 2 first (the GLSL ES 1.00 shaders run there unchanged) and WebGL 1 second.

## 2.1.0

### Changed
- Rain, the splashes and the drops on the glass are drawn by one WebGL shader (`weather.rain_style: shader`, the default): thin faint streaks in four depths that fade against a bright sky, splash rings along the ground, and fogged glass with sliding lens drops that show the sky upside down. Why: the classic strips were evenly bright lines and the DOM drops had no glass and no image in them, and on the Pi 5 kiosk a single small fragment pass costs less than several full-frame strip layers. Cost rules: one canvas at 0.75 / 0.5 / 0.4 of the frame (`high` / `medium` / `low`, at most 1280 px wide), 30 fps cap (20 on `low`), no loop when nothing falls and the glass is dry, the page is hidden or the card is detached; the sky texture is rebuilt only when the weather print changes; *reduce motion* gets one still frame.
- Fallback: without WebGL, or if the shader does not compile or link, or if the context keeps getting lost, the card warns once in the console and draws the classic rain. `rain_style: classic` keeps the 2.0 rain and glass as they were.

### Added
- `weather.rain_style` (`shader` | `classic`) in the card editor, and `window.sunCycleBg.rainShaderState()` for tests. ([#35](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/35))

## 2.0.0

### Changed (breaking: the HACS category)
- The repository is one Home Assistant integration, `sun_cycle_bg`, instead of a Dashboard plugin. It serves the card and its pictures from `custom_components/sun_cycle_bg/www/` at `/sun_cycle_bg/` and keeps the dashboard resource for them itself (`/sun_cycle_bg/loader.js?v=<version>`). Upgrading: remove the Dashboard entry in HACS (and its resource), add the repository as Integration, install, restart, add the integration. Card configs are unchanged. ([#33](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/33))
- `dist/` is gone; `tools/make_dist.py` fills the integration's `www/`, and CI checks it against `src/` and `demo/assets/`, the manifest, and that card, manifest and tag carry one version.

### Added
- Shared profiles: `profile: <name>` takes the card config from `.storage/sun_cycle_bg`, live over a websocket subscription, with the card's own YAML laid over it object by object; the last profile seen is cached in the browser. Reading is open to every user (a non-admin wall kiosk follows changes without a reload), writing to administrators.
- A settings page behind the integration's Configure button: profiles (new, duplicate, rename, delete), which dashboards use which, the card's form next to a preview, Save and Discard.
- Entity fields in the form are Home Assistant entity pickers, searchable and limited to the fitting domains.
- A brand icon (`brand/icon.png`, `icon@2x.png`), which Home Assistant 2026.9 serves for custom integrations.
- A card loaded twice (a leftover 1.x resource) keeps the first copy and warns instead of failing.

## 1.28.0

### Added
- The wind carries pictures instead of coloured ellipses: Norway maple and English oak leaves in autumn colours; cherry petals, blossom and young beech and lime leaves in spring; lime and maple leaves, poppy petals, daisies and a buttercup in summer. One strip of 128 px cells per season (`leaves-*.webp`, shipped in `dist/`), generated with google/gemini-nano-banana-2.1 and keyed out by `tools/leaves.py`. ([#31](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/31))
- `weather.leaves: seasons`: the spring, summer and autumn sets in their season, nothing in winter. `always` now blows the dry autumn leaves in winter instead of green ellipses.
- `weather.season_entity`: the season from a sensor such as HA's Season integration; without it the month decides.

### Changed
- Leaves are bigger (38 to 70 px on a 1080 px frame), drift slower (5 to 9 s across at 45 km/h) and take half of the wind's spawns instead of a third, or the sprites read as specks.

### Fixed
- The leaf set did not change at a month boundary until the weather changed: the weather fingerprint now includes the season.

## 1.27.0

### Changed
- Meteor showers (`showers: imo`) peak with their measured shape instead of a fall-off stretched over the activity window: exponential slopes per side from Jenniskens (1994, table 3b) for 19 showers, the Perseids as a peak on a broad background. Width at half maximum: Quadrantids 64 h to 8 h, Geminids 58 h to 29 h, Leonids 173 h to 38 h, Perseids 147 h to 57 h. Other showers keep the old profile. ([#29](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/29))

## 1.26.2

### Changed
- `weather.quality` now also sets how many depth layers rain, snow and hail use (`high` 3, `medium` 2, `low` 1), and `low` drops the splash band. On a 1920 x 1080 RPi5 kiosk the cost of precipitation is the number of full-frame layers the GPU composites, not the number of drops: pouring at `medium` went from 7.2 % janky frames, and `low` with fewer drops alone only reached 6.4 %. ([#27](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/27))

## 1.26.1

### Fixed
- Overcast clouds stayed bright white over the grey veil; past 50 % cover they now take on the veil's tone and lose some opacity, which is how an overcast sky looks and keeps light dashboard text readable over them. Found deploying 1.26.0 on a 1920 x 1080 kiosk. ([#25](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/25))

## 1.26.0

### Added
- Meteor showers from the IMO calendar (`stars.meteors.showers: imo`): 38 showers with radiant drift and activity profile, the antihelion source and a sporadic background; the rate follows the radiant's altitude, the limiting magnitude and the moon, and with `weather:` set, cloud and precipitation. Each streak runs away from its own radiant, coloured and timed by entry velocity. `boost`, `limiting_magnitude`, `moon`. ([#13](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/13))

## 1.25.0

### Added
- Aurora from a Kp index (`weather.aurora`: `kp_entity`, `min_kp`, `placement: edges | sky`): only with data, at night, under thin cover; at the frame edges where the north is by default. Curtains painted once, drifting and breathing on transform and opacity. ([#12](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/12))

## 1.24.0

### Added
- Raindrops on the glass, off by default (`weather.glass: true`): drops land, sit and dry while it rains; big ones slide down in fits and starts and leave a trail. One element and one Web Animation each. ([#11](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/11))

## 1.23.0

### Added
- Wind: gust streaks across the sky from ~22 km/h or the windy conditions, and tumbling leaves (`weather.wind`, `weather.leaves`: `autumn` / `always` / `off`). One element and one Web Animation each, a timer only for when. ([#10](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/10))
- `weather.gust_entity`, or the weather entity's own `wind_gust_speed`.

## 1.22.0

### Added
- Lightning for `lightning`, `lightning-rainy` and `exceptional`: a timer picks the moment, the strike is a sky flash with return strokes plus a forked SVG bolt or an intra-cloud glow, opacity-only and removed when done (`weather.lightning`). ([#9](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/9))

### Changed
- The weather layer keeps named timers, one per effect, and clears them all when it is taken down.

## 1.21.0

### Added
- Fog: a haze thickening towards the horizon and thick banks crawling with the wind, coloured from the sky; from the condition, AstroWeather's fog fraction, or visibility under 1 km. Thick fog raises the veil (`weather.fog`). ([#8](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/8))

## 1.20.0

### Added
- Hail: pellets in two depths with rain behind them, and a band of pellets bouncing at the horizon on staggered transform and opacity loops (`weather.hail`). ([#7](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/7))

## 1.19.0

### Added
- Snow in three depths, swaying as it falls, slanted further than rain by the same wind; sleet as rain and snow together (`weather.snow`). ([#6](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/6))

## 1.18.0

### Added
- Rain in three depths, slanted by the wind with `skewX`, falling on a transform loop over a tile painted once. ([#5](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/5))
- Splashes along the horizon on staggered opacity loops (`weather.splashes`).
- `weather.precipitation_entity`: a measured rate in mm/h sets the intensity.

### Changed
- A loop restarted for a new speed keeps its position; only a change of direction mirrors it.

## 1.17.0

### Added
- Clouds at three heights (cirrus, alto, cumulus) and a stratus deck past 75 %
  low cover, drifting with the wind's speed and bearing, lit from the sun's
  elevation (white by day, warm undersides at dusk, dark at night, moonlit).
  Compositor-only: one painted strip per height on a transform loop.
  `weather.clouds`, on by default when `weather:` is set.
  ([#4](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/4))

## 1.16.0

### Added
- `weather:` block: the sky follows a Home Assistant weather entity
  (condition, cloud cover, wind, visibility), optionally with cover per height
  and fog from a second entity (`clouds_entity`, AstroWeather attributes).
  Off unless set. ([#3](https://github.com/jrx-code/hassio-sun-cycle-bg/issues/3))
- Sky veil: overcast greys and dims the whole sky, coloured from the card's
  palette, darker in a storm, with a minute-long transition.
- `weather.quality` (`high` / `medium` / `low`) for the effects that follow.
- A Weather section in the visual editor.
