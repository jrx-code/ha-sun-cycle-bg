"""Sun Cycle Background: the card, its shared profiles and its settings page.

One integration, one config entry, no entities:

- the card (`custom:sun-cycle-bg-card`) and its pictures are served from
  `www/` at /sun_cycle_bg/; the integration keeps a dashboard resource for its
  loader (`/sun_cycle_bg/loader.js?v=<version>`) itself: created on setup,
  moved to the new version after an update, removed with the integration;
- named card configs ("profiles") are kept in `.storage/sun_cycle_bg` and
  served over the websocket API, so the cards of a dashboard (one per view)
  share one config and a dashboard deployed whole carries `profile: <name>`;
- the settings page is a panel registered with `config_panel_domain`: the
  frontend puts a Configure button on the entry that opens it, and without a
  title it stays out of the sidebar.

A dashboard resource rather than frontend.add_extra_js_url: on a test
instance the extra module now and then never ran (about 1 page load in 75,
the card file fetched and the card never registered), while the resource is
how 1.x was loaded for months on a wall kiosk without that.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .store import ProfileStore
from .websocket import async_register

_LOGGER = logging.getLogger(__name__)

PANEL_URL = "sun-cycle-bg"
STATIC_URL = f"/{DOMAIN}"
LOADER = f"{STATIC_URL}/loader.js"
WWW = Path(__file__).parent / "www"


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
    await _async_resource(hass, f"{LOADER}?v={version}")
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
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """The integration is deleted: take its dashboard resource with it."""
    resources = await _storage_resources(hass)
    if resources is None:
        return
    for item in list(resources.async_items()):
        if item["url"].split("?")[0] == LOADER:
            await resources.async_delete_item(item["id"])


async def _storage_resources(hass: HomeAssistant):
    data = hass.data.get(LOVELACE_DATA)
    if data is None or data.resource_mode != "storage":
        return None
    # loads the collection from storage when nothing has read it yet
    await data.resources.async_get_info()
    return data.resources


async def _async_resource(hass: HomeAssistant, url: str) -> None:
    """One dashboard resource for the loader, at this version."""
    resources = await _storage_resources(hass)
    if resources is None:
        _LOGGER.warning(
            "Dashboard resources are kept in YAML: add %s (type module) to them "
            "yourself, the sun-cycle-bg card is not loaded otherwise", url)
        return
    ours = [i for i in resources.async_items() if i["url"].split("?")[0] == LOADER]
    for extra in ours[1:]:
        await resources.async_delete_item(extra["id"])
    if not ours:
        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.info("Added the dashboard resource %s", url)
    elif ours[0]["url"] != url or ours[0].get("type") != "module":
        await resources.async_update_item(ours[0]["id"], {"res_type": "module", "url": url})
        _LOGGER.info("Moved the dashboard resource to %s", url)
