# Changelog

All notable changes to this card. Versions before 1.16.0 are described in the
[GitHub releases](https://github.com/jrx-code/hassio-sun-cycle-bg/releases).

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
