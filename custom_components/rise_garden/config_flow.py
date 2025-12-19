"""Config flow for Rise Gardens integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import RiseGardensAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class RiseGardenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rise Gardens."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = RiseGardensAPI(
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            # Test authentication
            if await self.hass.async_add_executor_job(api.authenticate):
                # Get gardens to use as title
                gardens = await self.hass.async_add_executor_job(api.get_gardens_list)
                garden_names = []
                if gardens:
                    for garden in gardens.get("gardens", []):
                        garden_names.append(garden.get("name", "Unknown"))

                title = f"Rise Gardens ({', '.join(garden_names)})" if garden_names else "Rise Gardens"

                # Check if already configured
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
            else:
                errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
