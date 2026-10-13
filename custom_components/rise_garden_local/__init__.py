"""The local (LAN) Rise Garden integration.

Talks directly to the controller on the local network (TCP port 1000) with no
cloud dependency. See api.py for the protocol.
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api import RiseGardenLocal, RiseLocalError
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import RiseLocalCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_COMMAND = "send_command"
SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("command"): cv.string,
        vol.Optional("multiline", default=False): cv.boolean,
    }
)

SERVICE_SET_LIGHT_SCHEDULE = "set_light_schedule"
SET_LIGHT_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("steps"): vol.All(
            cv.ensure_list,
            vol.Length(min=1),
            [
                vol.Schema(
                    {
                        vol.Required("start_utc"): cv.string,
                        vol.Required("duration_s"): vol.All(vol.Coerce(int), vol.Range(min=1)),
                        vol.Optional("level", default=100): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
                    }
                )
            ],
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    client = RiseGardenLocal(entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT))
    coordinator = RiseLocalCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SEND_COMMAND)
            hass.services.async_remove(DOMAIN, SERVICE_SET_LIGHT_SCHEDULE)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register the raw command service (discovery / power users)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    def _first_entry() -> dict:
        # Use the first configured controller.
        entries = list(hass.data.get(DOMAIN, {}).values())
        if not entries:
            raise HomeAssistantError("No Rise Garden controller configured")
        return entries[0]

    async def _send_command(call: ServiceCall) -> dict:
        client: RiseGardenLocal = _first_entry()["client"]
        try:
            reply = await client.raw(call.data["command"], multiline=call.data["multiline"])
        except RiseLocalError as err:
            raise HomeAssistantError(str(err)) from err
        return {"reply": reply}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_COMMAND,
        _send_command,
        schema=SEND_COMMAND_SCHEMA,
        supports_response=True,
    )

    async def _set_light_schedule(call: ServiceCall) -> None:
        store = _first_entry()
        try:
            await store["client"].set_light_schedule(call.data["steps"])
        except (RiseLocalError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await store["coordinator"].async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LIGHT_SCHEDULE,
        _set_light_schedule,
        schema=SET_LIGHT_SCHEDULE_SCHEMA,
    )
