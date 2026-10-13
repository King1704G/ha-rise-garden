"""Binary sensor (local): cloud/MQTT connection status.

Handy when de-clouding: watch this flip to 'disconnected' after you firewall
the controller off the internet, while everything else keeps working.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import RiseLocalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    unit_id = await store["client"].unit_id() or entry.unique_id or "rise"
    async_add_entities([RiseLocalCloudSensor(store["coordinator"], unit_id)])


class RiseLocalCloudSensor(RiseLocalEntity, BinarySensorEntity):
    """True when the controller reports an active MQTT link to the Rise cloud."""

    _attr_name = "Cloud connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, unit_id: str) -> None:
        super().__init__(coordinator, unit_id)
        self._attr_unique_id = f"{unit_id}_cloud"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("mqtt"))
