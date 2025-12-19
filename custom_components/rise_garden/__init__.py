"""Rise Gardens integration for Home Assistant."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RiseGardensAPI
from .const import (
    DOMAIN,
    UPDATE_INTERVAL,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

CONF_REFRESH_TOKEN = "refresh_token"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rise Gardens from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]

    api = RiseGardensAPI(username, password)

    # Set up callback to persist refresh token when rotated
    def on_token_refresh(new_refresh_token: str) -> None:
        """Handle refresh token rotation by persisting new token."""
        _LOGGER.debug("Persisting rotated refresh token")
        new_data = {**entry.data, CONF_REFRESH_TOKEN: new_refresh_token}
        hass.config_entries.async_update_entry(entry, data=new_data)

    api.set_token_refresh_callback(on_token_refresh)

    # Try to restore session from stored refresh token
    stored_refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
    auth_success = False

    if stored_refresh_token:
        _LOGGER.debug("Attempting to restore session with stored refresh token")
        api.refresh_token = stored_refresh_token
        auth_success = await hass.async_add_executor_job(api.refresh_access_token)

    if not auth_success:
        _LOGGER.debug("Fresh authentication required")
        auth_success = await hass.async_add_executor_job(api.authenticate)

    if not auth_success:
        _LOGGER.error("Failed to authenticate with Rise Gardens")
        return False

    # Store refresh token after successful auth
    if api.refresh_token and api.refresh_token != stored_refresh_token:
        new_data = {**entry.data, CONF_REFRESH_TOKEN: api.refresh_token}
        hass.config_entries.async_update_entry(entry, data=new_data)

    async def async_update_data():
        """Fetch data from Rise Gardens API."""
        try:
            gardens_list = await hass.async_add_executor_job(api.get_gardens_list)
            device_data = await hass.async_add_executor_job(api.get_gardens_device_data)

            if gardens_list is None:
                # API methods already handle token refresh internally
                # If we still get None, there's a real connectivity issue
                raise UpdateFailed("Failed to fetch gardens list - API returned None")

            return {
                "gardens_list": gardens_list,
                "device_data": device_data or {},
            }
        except UpdateFailed:
            raise
        except Exception as ex:
            raise UpdateFailed(f"Error communicating with Rise Gardens API: {ex}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
