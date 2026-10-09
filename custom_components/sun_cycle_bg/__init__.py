"""Sun Cycle Background: the card, its shared profiles and its settings page.

One integration, one config entry, no entities:

- the card (`custom:sun-cycle-bg-card`) and its pictures are served from
  `www/` and loaded on every frontend page through `frontend.add_extra_js_url`,
  so no dashboard resource is needed;
- named card configs ("profiles") are kept in `.storage/sun_cycle_bg` and
  served over the websocket API, so the cards of a dashboard (one per view)
  share one config and a dashboard deployed whole carries `profile: <name>`;
- the settings page is a panel registered with `config_panel_domain`: the
  frontend puts a Configure button on the entry that opens it, and without a
  title it stays out of the sidebar.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .store import ProfileStore
from .websocket import async_register

PANEL_URL = "sun-cycle-bg"
STATIC_URL = f"/{DOMAIN}"
WWW = Path(__file__).parent / "www"
DATA_LOADER = f"{DOMAIN}_loader"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data:
        store = ProfileStore(hass)
        await store.async_load()
        hass.data[DOMAIN] = store
        # websocket commands and static paths cannot be unregistered; register
        # them once and keep them across reloads of the entry
        async_register(hass)
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(WWW), cache_headers=False)])
    # the version in the URLs: after an update the browser fetches the new files
    version = (await async_get_integration(hass, DOMAIN)).version
    loader = f"{STATIC_URL}/loader.js?v={version}"
    hass.data[DATA_LOADER] = loader
    frontend.add_extra_js_url(hass, loader)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="sun-cycle-bg-panel",
        module_url=f"{STATIC_URL}/panel.js?v={version}",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    if loader := hass.data.pop(DATA_LOADER, None):
        frontend.remove_extra_js_url(hass, loader)
    return True
