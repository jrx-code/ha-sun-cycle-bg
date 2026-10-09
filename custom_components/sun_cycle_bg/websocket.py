"""Websocket commands the card and its editor use.

    sun_cycle_bg/profile/list        any user   -> {"profiles": {name: {updated, updated_by}}}
    sun_cycle_bg/profile/get         any user   -> {"profile", "config" (or None), "updated", "updated_by"}
    sun_cycle_bg/profile/subscribe   any user   -> the same as events, now and after every change
    sun_cycle_bg/profile/set         admin only -> writes a whole profile
    sun_cycle_bg/profile/delete      admin only

Reading is open to every logged-in user on purpose: a wall kiosk runs as a
non-admin user and has to follow the profile live.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .store import ProfileError, ProfileStore

NAME = vol.All(str, vol.Length(min=1, max=64))


def _store(hass: HomeAssistant) -> ProfileStore:
    return hass.data[DOMAIN]


def _payload(store: ProfileStore, name: str) -> dict[str, Any]:
    entry = store.get(name)
    return {
        "profile": name,
        "config": entry["config"] if entry else None,
        "updated": entry["updated"] if entry else None,
        "updated_by": entry.get("updated_by") if entry else None,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for cmd in (ws_list, ws_get, ws_subscribe, ws_set, ws_delete):
        websocket_api.async_register_command(hass, cmd)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/profile/list"})
@callback
def ws_list(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
            msg: dict[str, Any]) -> None:
    store = _store(hass)
    connection.send_result(msg["id"], {"profiles": {
        n: {"updated": e["updated"], "updated_by": e.get("updated_by")}
        for n, e in store.profiles.items()}})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/profile/get",
    vol.Required("profile"): NAME,
})
@callback
def ws_get(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
           msg: dict[str, Any]) -> None:
    connection.send_result(msg["id"], _payload(_store(hass), msg["profile"]))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/profile/subscribe",
    vol.Required("profile"): NAME,
})
@callback
def ws_subscribe(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                 msg: dict[str, Any]) -> None:
    store, name = _store(hass), msg["profile"]

    @callback
    def changed() -> None:
        connection.send_event(msg["id"], _payload(store, name))

    connection.subscriptions[msg["id"]] = store.async_subscribe(name, changed)
    connection.send_result(msg["id"])
    # the current value right away: a fresh subscriber and one that came back
    # after a reconnect both start from what is stored now
    changed()


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/profile/set",
    vol.Required("profile"): NAME,
    vol.Required("config"): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                 msg: dict[str, Any]) -> None:
    user = connection.user.name if connection.user else None
    try:
        entry = await _store(hass).async_set(msg["profile"], msg["config"], user)
    except ProfileError as err:
        connection.send_error(msg["id"], "invalid_profile", str(err))
        return
    connection.send_result(msg["id"], {"profile": msg["profile"], "updated": entry["updated"]})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/profile/delete",
    vol.Required("profile"): NAME,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection,
                    msg: dict[str, Any]) -> None:
    deleted = await _store(hass).async_delete(msg["profile"])
    connection.send_result(msg["id"], {"deleted": deleted})
