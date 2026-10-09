"""Named card configs kept in .storage, with change callbacks.

A profile is the config of `custom:sun-cycle-bg-card` without `type` and
`profile`: every card that names the profile gets it, merged under its own
YAML. Kept in .storage/sun_cycle_bg, so it travels with HA backups.
"""
from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import MAX_PROFILE_BYTES, STORAGE_KEY, STORAGE_VERSION

# keys that belong to the card in the dashboard, never to a shared profile
CARD_KEYS = ("type", "profile")


class ProfileError(ValueError):
    """A profile write that cannot be taken."""


def clean_config(config: Any) -> dict[str, Any]:
    """The part of a card config a profile may hold, or ProfileError."""
    if not isinstance(config, dict):
        raise ProfileError("config must be an object")
    clean = {k: v for k, v in config.items() if k not in CARD_KEYS}
    size = len(json.dumps(clean))
    if size > MAX_PROFILE_BYTES:
        raise ProfileError(f"profile is {size} bytes, the limit is {MAX_PROFILE_BYTES}")
    return clean


class ProfileStore:
    """Profiles by name, persisted, with per-name subscribers."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.profiles: dict[str, dict[str, Any]] = {}
        self._subs: dict[str, list[Callable[[], None]]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.profiles = data.get("profiles", {})

    def get(self, name: str) -> dict[str, Any] | None:
        return self.profiles.get(name)

    async def async_set(self, name: str, config: Any, user: str | None) -> dict[str, Any]:
        entry = {"config": clean_config(config), "updated": dt_util.utcnow().isoformat(),
                 "updated_by": user}
        self.profiles[name] = entry
        await self._store.async_save({"profiles": self.profiles})
        self._notify(name)
        return entry

    async def async_delete(self, name: str) -> bool:
        if name not in self.profiles:
            return False
        del self.profiles[name]
        await self._store.async_save({"profiles": self.profiles})
        self._notify(name)
        return True

    @callback
    def async_subscribe(self, name: str, cb: Callable[[], None]) -> Callable[[], None]:
        self._subs.setdefault(name, []).append(cb)

        @callback
        def unsub() -> None:
            subs = self._subs.get(name, [])
            if cb in subs:
                subs.remove(cb)

        return unsub

    def _notify(self, name: str) -> None:
        for cb in list(self._subs.get(name, [])):
            cb()
