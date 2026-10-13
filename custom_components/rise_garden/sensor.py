"""Sensor platform for Rise Gardens."""
import logging
from datetime import datetime, timezone
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


def _extract_crops(detail: dict) -> list[dict]:
    """Flatten all crops from a garden detail response into a list."""
    crops = []

    for tray in detail.get("trays", []):
        for section in tray.get("tray_sections", []):
            order = 1
            for row in section.get("netcups", []):
                for netcup in row:
                    if raw_crop := netcup.get("crop"):
                        crop = dict(raw_crop)
                        crop.setdefault("tray_location", "garden")
                        crop.setdefault("order", order)
                        crops.append(crop)
                    order += 1

    for nursery in detail.get("nurseries", []):
        for tray in nursery.get("trays", []):
            for section in tray.get("tray_sections", []):
                for idx, raw_crop in enumerate(section.get("crops", []), start=1):
                    crop = dict(raw_crop)
                    crop.setdefault("tray_location", "nursery")
                    crop.setdefault("order", crop.get("order") or idx)
                    crops.append(crop)

    return crops


def _crop_map(detail: dict) -> dict[int, dict]:
    """Return {crop_id: crop} from a garden detail response."""
    return {crop["id"]: crop for crop in _extract_crops(detail)}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rise Gardens sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    gardens_list = coordinator.data.get("gardens_list", {})
    garden_details = coordinator.data.get("garden_details", {})

    for garden in gardens_list.get("gardens", []):
        garden_id = garden["id"]
        garden_name = garden["name"]

        entities.append(RiseGardenWaterSensor(coordinator, garden_id, garden_name))
        entities.append(RiseGardenOnlineSensor(coordinator, garden_id, garden_name))
        entities.append(RiseGardenTasksSensor(coordinator, garden_id, garden_name))
        entities.append(RiseGardenTemperatureSensor(coordinator, garden_id, garden_name))
        entities.append(RiseGardenWaterDepthSensor(coordinator, garden_id, garden_name))

        detail = garden_details.get(garden_id, {})
        for crop in _extract_crops(detail):
            entities.append(
                RiseGardenCropSensor(coordinator, garden_id, garden_name, crop)
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
        if not garden:
            return {}
        user_tasks = garden.get("user_tasks", {})
        return {
            "major_tasks": user_tasks.get("major_task", []),
            "minor_tasks": user_tasks.get("minor_task", []),
        }


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


class RiseGardenCropSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single plant/crop in a Rise Garden."""

    _attr_icon = "mdi:sprout"

    def __init__(
        self,
        coordinator,
        garden_id: int,
        garden_name: str,
        crop: dict,
    ) -> None:
        super().__init__(coordinator)
        self._garden_id = garden_id
        self._garden_name = garden_name
        self._crop_id = crop["id"]
        name_str = f"{crop.get('name', '')} {crop.get('variety', '')}".strip()
        self._attr_name = f"{garden_name} {name_str}"
        self._attr_unique_id = f"rise_garden_crop_{self._crop_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, str(self._garden_id))},
            "name": f"Rise Garden {self._garden_name}",
            "manufacturer": "Rise Gardens",
            "model": "Indoor Garden",
        }

    def _get_crop(self) -> dict | None:
        detail = self.coordinator.data.get("garden_details", {}).get(self._garden_id, {})
        return _crop_map(detail).get(self._crop_id)

    @property
    def available(self) -> bool:
        return self._get_crop() is not None

    @property
    def native_value(self) -> str | None:
        crop = self._get_crop()
        return crop.get("stage_name") if crop else None

    @property
    def entity_picture(self) -> str | None:
        crop = self._get_crop()
        if crop:
            url = crop.get("image_transparent_small") or crop.get("image_transparent_big")
            return url or None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        crop = self._get_crop()
        if not crop:
            return {}

        attrs: dict[str, Any] = {
            "name": crop.get("name"),
            "variety": crop.get("variety"),
            "genre": crop.get("genre"),
            "harvest_date": crop.get("harvest_date"),
            "is_ready_to_harvest": crop.get("is_ready_to_harvest"),
            "harvest_count": crop.get("harvest_count"),
            "buy_url": crop.get("buy_url"),
            "tray_location": crop.get("tray_location"),
            "order": crop.get("order"),
            "image_url": (
                crop.get("image_transparent_small")
                or crop.get("image_transparent_big")
            ),
        }

        harvest_date_str = crop.get("harvest_date")
        if harvest_date_str:
            try:
                harvest_dt = datetime.fromisoformat(harvest_date_str)
                days = (harvest_dt - datetime.now(timezone.utc)).days
                attrs["days_until_harvest"] = max(0, days)
            except (ValueError, TypeError):
                pass

        return attrs
