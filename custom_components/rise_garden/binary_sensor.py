"""Binary sensor platform for Rise Gardens."""
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rise Gardens binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    gardens_list = coordinator.data.get("gardens_list", {})
    for garden in gardens_list.get("gardens", []):
        garden_id = garden["id"]
        garden_name = garden["name"]
        entities.append(RiseGardenCareNeededSensor(coordinator, garden_id, garden_name))

    async_add_entities(entities)


class RiseGardenCareNeededSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for whether a Rise Garden needs care."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:leaf"

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        super().__init__(coordinator)
        self._garden_id = garden_id
        self._garden_name = garden_name
        self._attr_name = f"{garden_name} Care Needed"
        self._attr_unique_id = f"rise_garden_{garden_id}_care_needed"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, str(self._garden_id))},
            "name": f"Rise Garden {self._garden_name}",
            "manufacturer": "Rise Gardens",
            "model": "Indoor Garden",
        }

    def _get_garden(self) -> dict | None:
        for garden in self.coordinator.data.get("gardens_list", {}).get("gardens", []):
            if garden["id"] == self._garden_id:
                return garden
        return None

    @property
    def is_on(self) -> bool:
        garden = self._get_garden()
        return bool(garden.get("is_care_needed")) if garden else False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        garden = self._get_garden()
        if not garden:
            return {}

        user_tasks = garden.get("user_tasks", {})
        return {
            "next_care_at": garden.get("next_care_at"),
            "number_of_tasks": garden.get("number_of_tasks", 0),
            "major_tasks": user_tasks.get("major_task", []),
            "minor_tasks": user_tasks.get("minor_task", []),
        }
