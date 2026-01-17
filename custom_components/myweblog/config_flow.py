"""Config flow for MyWeblog integration."""

from __future__ import annotations

import logging
import re
from typing import Any

from pyMyweblog import MyWebLogClient
import voluptuous as vol  # type: ignore[import]

from homeassistant import config_entries  # type: ignore[import]
from homeassistant.core import HomeAssistant  # type: ignore[import]
from homeassistant.data_entry_flow import FlowResult  # type: ignore[import]
from homeassistant.exceptions import HomeAssistantError  # type: ignore[import]
from homeassistant.helpers import config_validation as cv  # type: ignore[import]

from .const import APP_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


def is_auth_error(err: Exception) -> bool:
    """Check if an exception indicates an authentication error."""
    err_str = str(err).lower()
    return (
        "ogiltigt" in err_str
        or "invalid" in err_str
        or "auth" in err_str
        or "unauthorized" in err_str
        or "forbidden" in err_str
        or "401" in err_str
        or "403" in err_str
    )


async def validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> tuple[list[dict[str, Any]], str]:
    """Validate the user credentials and return (airplanes, app_token)."""
    _LOGGER.debug("Validating credentials for username=%s", username)
    try:
        async with MyWebLogClient(username, password) as client:
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
            _LOGGER.info(
                "Validated credentials for %s, found %d airplanes",
                username,
                len(airplanes),
            )
            return airplanes, app_token or ""

    except Exception as err:
        _LOGGER.error("Credential validation failed for username=%s: %s", username, err)
        if is_auth_error(err):
            raise InvalidAuth from err
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[misc]
    """Handle a config flow for MyWeblog."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username = None
        self._password = None
        self._airplanes = []
        self._app_token = None

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication."""
        _LOGGER.debug("Starting re-authentication flow")
        errors = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                airplanes, app_token = await validate_credentials(
                    self.hass, user_input["username"], user_input["password"]
                )
                _LOGGER.info(
                    "Re-authentication successful for %s", user_input["username"]
                )

                # Update the config entry with new credentials
                if entry is not None:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            "username": user_input["username"],
                            "password": user_input["password"],
                            "app_token": app_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            except CannotConnect:
                _LOGGER.error("Re-auth: cannot connect")
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                _LOGGER.error("Re-auth: invalid credentials")
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Re-auth: unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"username": entry.title if entry else "Unknown"},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step for username/password."""
        _LOGGER.debug("Starting config flow: step_user")
        errors = {}

        if user_input is not None:
            try:
                self._airplanes, self._app_token = await validate_credentials(
                    self.hass, user_input["username"], user_input["password"]
                )
                self._username = user_input["username"]
                self._password = user_input["password"]
                _LOGGER.info(
                    "Config flow: credentials validated for %s", self._username
                )
                return await self.async_step_select_airplane()
            except CannotConnect:
                _LOGGER.error(
                    "Config flow: cannot connect for username=%s",
                    user_input.get("username"),
                )
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                _LOGGER.error(
                    "Config flow: invalid auth for username=%s",
                    user_input.get("username"),
                )
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Config flow: unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_airplane(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the airplane selection step."""
        _LOGGER.debug("Starting config flow: step_select_airplane")
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

            _LOGGER.info(
                "Config flow: selected %d airplanes for user %s",
                planes_count,
                self._username,
            )

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

    def _get_reauth_entry(self) -> config_entries.ConfigEntry | None:
        """Get the config entry being re-authenticated."""
        return self.hass.config_entries.async_get_entry(self.context["entry_id"])


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for MyWeblog."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self.config_entry_data = config_entry.data

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow initialization."""
        _LOGGER.debug("Starting options flow")
        return await self.async_step_options(user_input)

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow for airplane selection."""
        _LOGGER.debug("Starting options flow: step_options")
        errors = {}
        entry = self.config_entry

        username = entry.data.get("username")
        password = entry.data.get("password")
        current_airplanes = entry.data.get("airplanes", [])
        current_regnrs = {plane["regnr"] for plane in current_airplanes}

        if user_input is not None:
            try:
                # Fetch available airplanes from API
                airplanes, app_token = await validate_credentials(
                    self.hass, username, password
                )

                # Find selected airplanes
                selected_regnrs = set(user_input.get("airplanes", []))
                selected_planes = [
                    plane for plane in airplanes if plane["regnr"] in selected_regnrs
                ]

                if not selected_planes:
                    errors["base"] = "no_airplanes_selected"
                else:
                    # Update the config entry
                    planes_data = [
                        {
                            "id": plane["id"],
                            "regnr": plane["regnr"],
                            "title": plane["title"],
                        }
                        for plane in selected_planes
                    ]

                    planes_count = len(planes_data)
                    title = f"MyWeblog ({username} - {planes_count} {'plane' if planes_count == 1 else 'planes'})"

                    _LOGGER.info(
                        "Options flow: updating to %d airplanes for user %s",
                        planes_count,
                        username,
                    )

                    self.hass.config_entries.async_update_entry(
                        entry,
                        title=title,
                        data={
                            **entry.data,
                            "airplanes": planes_data,
                            "app_token": app_token,
                        },
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_create_entry(title="", data={})
            except CannotConnect:
                _LOGGER.error("Options flow: cannot connect")
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                _LOGGER.error("Options flow: invalid credentials")
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Options flow: unexpected exception")
                errors["base"] = "unknown"

        # Fetch available airplanes for the form
        try:
            airplanes, _ = await validate_credentials(self.hass, username, password)
        except Exception as err:
            _LOGGER.error("Options flow: failed to fetch airplanes: %s", err)
            # Use current airplanes if we can't fetch new ones
            airplanes = current_airplanes

        # Create mapping of registration numbers to plane data
        airplane_titles = {plane["regnr"]: plane["title"] for plane in airplanes}

        schema = vol.Schema(
            {
                vol.Required(
                    "airplanes", default=list(current_regnrs)
                ): cv.multi_select(airplane_titles)
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=schema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
