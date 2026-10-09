# Changelog

All notable changes to this card. Versions before 1.16.0 are described in the
[GitHub releases](https://github.com/jrx-code/hassio-sun-cycle-bg/releases).

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
