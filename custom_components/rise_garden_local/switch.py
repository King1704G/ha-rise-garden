"""Switch platform (local): the water pump ('wpump on|off').

The controller's own pump cycle (see 'wpc') still runs, so a manual state is likely
overridden at the next cycle boundary.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import RiseGardenLocal, RiseLocalError
from .const import DOMAIN
from .entity import RiseLocalEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    client: RiseGardenLocal = store["client"]
    unit_id = await client.unit_id() or entry.unique_id or "rise"
    async_add_entities([RiseLocalPump(store["coordinator"], client, unit_id)])


class RiseLocalPump(RiseLocalEntity, SwitchEntity):
    """Water circulation pump."""

    _attr_name = "Pump"
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:water-pump"

    def __init__(self, coordinator, client: RiseGardenLocal, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._client = client
        self._attr_unique_id = f"{unit_id}_pump"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("pump"))

    async def _set(self, on: bool) -> None:
        try:
            await self._client.set_pump(on)
        except RiseLocalError as err:
            _LOGGER.error("Failed to set pump: %s", err)
            return
        self.coordinator.data["pump"] = 1 if on else 0
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
