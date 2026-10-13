"""Config flow for the local Rise Garden integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import RiseGardenLocal, RiseLocalError
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


class RiseLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for local Rise Garden."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client = RiseGardenLocal(
                user_input[CONF_HOST], user_input.get(CONF_PORT, DEFAULT_PORT)
            )
            try:
                unit_id = await client.unit_id()
            except RiseLocalError:
                unit_id = None

            if unit_id:
                await self.async_set_unique_id(unit_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Rise Garden {unit_id} (local)",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
