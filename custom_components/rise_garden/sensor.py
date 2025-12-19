"""Sensor platform for Rise Gardens."""
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfLength
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
    """Set up Rise Gardens sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    gardens_list = coordinator.data.get("gardens_list", {})
    for garden in gardens_list.get("gardens", []):
        garden_id = garden["id"]
        garden_name = garden["name"]

        # Water level sensor
        entities.append(
            RiseGardenWaterSensor(coordinator, garden_id, garden_name)
        )

        # Online status sensor
        entities.append(
            RiseGardenOnlineSensor(coordinator, garden_id, garden_name)
        )

        # Tasks pending sensor
        entities.append(
            RiseGardenTasksSensor(coordinator, garden_id, garden_name)
        )

        # Temperature sensor
        entities.append(
            RiseGardenTemperatureSensor(coordinator, garden_id, garden_name)
        )

        # Water depth sensor
        entities.append(
            RiseGardenWaterDepthSensor(coordinator, garden_id, garden_name)
        )

    async_add_entities(entities)


class RiseGardenBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Rise Garden sensors."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._garden_id = garden_id
        self._garden_name = garden_name

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, str(self._garden_id))},
            "name": f"Rise Garden {self._garden_name}",
            "manufacturer": "Rise Gardens",
            "model": "Indoor Garden",
        }

    def _get_garden_data(self) -> dict[str, Any] | None:
        """Get garden data from coordinator."""
        gardens_list = self.coordinator.data.get("gardens_list", {})
        for garden in gardens_list.get("gardens", []):
            if garden["id"] == self._garden_id:
                return garden
        return None

    def _get_device_data(self) -> dict[str, Any] | None:
        """Get device data from coordinator."""
        device_data = self.coordinator.data.get("device_data", {})
        return device_data.get(str(self._garden_id))


class RiseGardenWaterSensor(RiseGardenBaseSensor):
    """Water level sensor for Rise Garden."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the water sensor."""
        super().__init__(coordinator, garden_id, garden_name)
        self._attr_name = f"{garden_name} Water Level"
        self._attr_unique_id = f"rise_garden_{garden_id}_water"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:water"

    @property
    def native_value(self) -> float | None:
        """Return the water level."""
        garden = self._get_garden_data()
        if garden:
            water_led = garden.get("water_led_index")
            if water_led is not None:
                # Convert water LED index to percentage (0-5 scale to 0-100%)
                return min(100, max(0, water_led * 20))
        return None

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return PERCENTAGE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        garden = self._get_garden_data()
        if garden:
            return {
                "water_distance": garden.get("water_distance"),
                "water_led_index": garden.get("water_led_index"),
            }
        return {}


class RiseGardenOnlineSensor(RiseGardenBaseSensor):
    """Online status sensor for Rise Garden."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the online sensor."""
        super().__init__(coordinator, garden_id, garden_name)
        self._attr_name = f"{garden_name} Online"
        self._attr_unique_id = f"rise_garden_{garden_id}_online"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self) -> str:
        """Return the online status."""
        garden = self._get_garden_data()
        if garden:
            return "Online" if garden.get("is_online") else "Offline"
        return "Unknown"

    @property
    def icon(self) -> str:
        """Return the icon based on status."""
        garden = self._get_garden_data()
        if garden and garden.get("is_online"):
            return "mdi:wifi"
        return "mdi:wifi-off"


class RiseGardenTasksSensor(RiseGardenBaseSensor):
    """Tasks sensor for Rise Garden."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the tasks sensor."""
        super().__init__(coordinator, garden_id, garden_name)
        self._attr_name = f"{garden_name} Pending Tasks"
        self._attr_unique_id = f"rise_garden_{garden_id}_tasks"
        self._attr_icon = "mdi:clipboard-list"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of pending tasks."""
        garden = self._get_garden_data()
        if garden:
            return garden.get("number_of_tasks", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        garden = self._get_garden_data()
        if garden:
            user_tasks = garden.get("user_tasks", {})
            major_tasks = user_tasks.get("major_task", [])
            minor_tasks = user_tasks.get("minor_task", [])

            return {
                "major_tasks": [t.get("title") for t in major_tasks],
                "minor_tasks": [t.get("title") for t in minor_tasks],
                "is_care_needed": garden.get("is_care_needed"),
                "next_care_at": garden.get("next_care_at"),
            }
        return {}


class RiseGardenTemperatureSensor(RiseGardenBaseSensor):
    """Temperature sensor for Rise Garden."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, garden_id, garden_name)
        self._attr_name = f"{garden_name} Temperature"
        self._attr_unique_id = f"rise_garden_{garden_id}_temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        """Return the temperature."""
        device_data = self._get_device_data()
        if device_data:
            # 'at' is ambient temperature in Celsius
            return device_data.get("at")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device_data = self._get_device_data()
        if device_data:
            return {
                "kit_id": device_data.get("kit"),
                "pump_status": device_data.get("wp"),
            }
        return {}


class RiseGardenWaterDepthSensor(RiseGardenBaseSensor):
    """Water depth sensor for Rise Garden."""

    def __init__(self, coordinator, garden_id: int, garden_name: str) -> None:
        """Initialize the water depth sensor."""
        super().__init__(coordinator, garden_id, garden_name)
        self._attr_name = f"{garden_name} Water Depth"
        self._attr_unique_id = f"rise_garden_{garden_id}_water_depth"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
        self._attr_icon = "mdi:water"

    @property
    def native_value(self) -> float | None:
        """Return the water depth in mm."""
        device_data = self._get_device_data()
        if device_data:
            return device_data.get("water_depth")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device_data = self._get_device_data()
        if device_data:
            return {
                "water_distance": device_data.get("water_distance"),
                "light_level": device_data.get("l1"),
            }
        return {}
