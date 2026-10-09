# Changelog

All notable changes to this card. Versions before 1.16.0 are described in the
[GitHub releases](https://github.com/jrx-code/hassio-sun-cycle-bg/releases).

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
