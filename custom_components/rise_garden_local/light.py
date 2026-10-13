"""Light platform (local) — the grow light, one entity per channel ('lamp <1-3> <0-100>')."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RiseGardenLocal, RiseLocalError
from .const import DOMAIN, LAMP_CHANNELS
from .entity import RiseLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    unit_id = await store["client"].unit_id() or entry.unique_id or "rise"
    async_add_entities(
        [RiseLocalLight(store["coordinator"], store["client"], unit_id, ch) for ch in LAMP_CHANNELS]
    )


class RiseLocalLight(RiseLocalEntity, LightEntity):
    """One grow-light channel. Firmware stores level 0-100; HA uses 0-255 brightness.

    The controller's own schedule (ltimer) still runs, so a manual level is likely
    overridden at the next schedule step.
    """

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_icon = "mdi:led-strip-variant"

    def __init__(self, coordinator, client: RiseGardenLocal, unit_id: str, channel: int) -> None:
        super().__init__(coordinator, unit_id)
        self._client = client
        self._channel = channel
        self._key = f"lamp{channel}"
        self._attr_name = f"Grow light {channel}"
        self._attr_unique_id = f"{unit_id}_lamp_{channel}"

    @property
    def _level(self) -> int | None:
        return self.coordinator.data.get(self._key)

    @property
    def is_on(self) -> bool:
        return bool(self._level)

    @property
    def brightness(self) -> int | None:
        lvl = self._level
        return None if lvl is None else round(lvl * 2.55)

    @property
    def extra_state_attributes(self) -> dict:
        return {"schedule_utc": self.coordinator.data.get("light_schedule")}

    async def _set_level(self, level: int) -> None:
        level = max(0, min(100, level))
        try:
            await self._client.set_lamp(self._channel, level)
        except RiseLocalError as err:
            _LOGGER.error("Failed to set lamp %s: %s", self._channel, err)
            return
        # Optimistic update, then confirm on next poll.
        self.coordinator.data[self._key] = level
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        if ATTR_BRIGHTNESS in kwargs:
            await self._set_level(round(kwargs[ATTR_BRIGHTNESS] / 2.55))
        else:
            await self._set_level(100)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_level(0)
