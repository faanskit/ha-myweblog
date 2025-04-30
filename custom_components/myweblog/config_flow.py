"""Config flow for MyWeblog integration."""

from __future__ import annotations

import logging
import re
from typing import Any

from pyMyweblog import MyWebLogClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, APP_SECRET

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_credentials(hass: HomeAssistant, username: str, password: str):
    """Validate the user credentials and return (airplanes, app_token)."""
    try:
        async with MyWebLogClient(username, password, app_token=None) as client:
            app_token = await client.obtainAppToken(APP_SECRET)
            result = await client.getObjects()

            # Filter out non-planes and extract required data
            airplanes = []

            callsign_pattern = re.compile(r"^[A-Z0-9]{1,2}-[A-Z0-9]+$", re.IGNORECASE)
            for obj in result.get("Object", []):
                regnr = obj.get("regnr", "")
                plane_id = obj.get("ID")
                if callsign_pattern.match(regnr) and plane_id:
                    airplanes.append(
                        {
                            "id": plane_id,
                            "regnr": regnr,
                            "title": f"{regnr} ({obj.get('model', '')})",
                        }
                    )
            return airplanes, app_token

    except Exception as err:
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyWeblog."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username = None
        self._password = None
        self._airplanes = []
        self._app_token = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step for username/password."""
        errors = {}

        if user_input is not None:
            try:
                self._airplanes, self._app_token = await validate_credentials(
                    self.hass, user_input["username"], user_input["password"]
                )
                self._username = user_input["username"]
                self._password = user_input["password"]
                return await self.async_step_select_airplane()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_airplane(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the airplane selection step."""
        errors = {}

        if user_input is not None:
            # Find all selected airplanes' data
            selected_planes = [
                plane
                for plane in self._airplanes
                if plane["regnr"] in user_input["airplanes"]
            ]

            # Create a summary title with the number of planes
            planes_count = len(selected_planes)
            title = f"MyWeblog ({self._username} - {planes_count} {'plane' if planes_count == 1 else 'planes'})"

            # Store the planes data as a list
            planes_data = [
                {"id": plane["id"], "regnr": plane["regnr"], "title": plane["title"]}
                for plane in selected_planes
            ]

            return self.async_create_entry(
                title=title,
                data={
                    "username": self._username,
                    "password": self._password,
                    "app_token": self._app_token,
                    "airplanes": planes_data,
                },
            )

        # Create a mapping of registration numbers to plane data
        airplane_titles = {plane["regnr"]: plane["title"] for plane in self._airplanes}

        schema = vol.Schema(
            {vol.Required("airplanes"): cv.multi_select(airplane_titles)}
        )

        return self.async_show_form(
            step_id="select_airplane", data_schema=schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
