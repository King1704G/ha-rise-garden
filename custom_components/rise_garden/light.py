"""Light platform for Rise Gardens."""
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
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
    """Set up Rise Gardens lights."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []

    gardens_list = coordinator.data.get("gardens_list", {})
    for garden in gardens_list.get("gardens", []):
        garden_id = garden["id"]
        garden_name = garden["name"]

        entities.append(
            RiseGardenLight(coordinator, api, garden_id, garden_name, hass)
        )

    async_add_entities(entities)


class RiseGardenLight(CoordinatorEntity, LightEntity):
    """Light entity for Rise Garden."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(
        self,
        coordinator,
        api,
        garden_id: int,
        garden_name: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._api = api
        self._garden_id = garden_id
        self._garden_name = garden_name
        self._hass = hass
        self._attr_name = f"{garden_name} Light"
        self._attr_unique_id = f"rise_garden_{garden_id}_light"

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

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        garden = self._get_garden_data()
        if garden:
            light_level = garden.get("light_level")
            return light_level is not None and light_level > 0
        return False

    @property
    def brightness(self) -> int | None:
        """Return the brightness (0-255)."""
        garden = self._get_garden_data()
        if garden:
            light_level = garden.get("light_level")
            if light_level is not None:
                # Convert 0-100 to 0-255
                return int(light_level * 2.55)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        garden = self._get_garden_data()
        return garden is not None and garden.get("is_online", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        # Convert 0-255 to 0-100
        level = int(brightness / 2.55)
        level = max(1, min(100, level))  # Ensure 1-100 range

        _LOGGER.debug("Setting light level to %s for garden %s", level, self._garden_id)

        success = await self._hass.async_add_executor_job(
            self._api.set_light_level, self._garden_id, level
        )

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set light level for garden %s", self._garden_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off light for garden %s", self._garden_id)

        success = await self._hass.async_add_executor_job(
            self._api.set_light_level, self._garden_id, 0
        )

        if success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to turn off light for garden %s", self._garden_id)
