"""Config flow for MyWeblog integration with OAuth 2.1 + PKCE."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import aiohttp
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from pyMyweblog.auth import AbstractMyWebLogAuth
from pyMyweblog.client import MyWebLogClient
from pyMyweblog.exceptions import MyWebLogAuthError

from .application_credentials import async_register_default_implementation
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class _StaticTokenAuth(AbstractMyWebLogAuth):
    """Temporary token auth for config flow setup."""

    def __init__(self, websession: aiohttp.ClientSession, access_token: str) -> None:
        super().__init__(websession)
        self._access_token = access_token

    async def async_get_access_token(self) -> str:
        return self._access_token


def is_auth_error(err: Exception) -> bool:
    """Check if an exception indicates an authentication error."""
    if isinstance(err, MyWebLogAuthError):
        return True
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


def filter_airplanes(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter and format airplanes from objects list."""
    callsign_pattern = re.compile(r"^[A-Z0-9]{1,2}-[A-Z0-9]+$", re.IGNORECASE)
    airplanes = []
    for obj in objects:
        regnr = obj.get("registration") or obj.get("regnr") or ""
        cat_info = obj.get("category")
        cat_id = cat_info.get("id") if isinstance(cat_info, dict) else None
        plane_id = obj.get("id") or obj.get("ID")

        # In API v5, category 0 is Aircraft. Alternatively match callsign pattern.
        is_aircraft = (
            (cat_id == 0) if cat_id is not None else bool(callsign_pattern.match(regnr))
        )
        if is_aircraft and plane_id and regnr:
            model_info = obj.get("model") or {}
            model_str = (
                (
                    (model_info.get("name") or model_info.get("designator"))
                    if isinstance(model_info, dict)
                    else str(model_info)
                )
                or obj.get("comment")
                or ""
            )
            title = f"{regnr} ({model_str})" if model_str else regnr
            airplanes.append(
                {
                    "id": plane_id,
                    "regnr": regnr,
                    "title": title,
                }
            )
    return airplanes


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for MyWeblog with OAuth 2.1."""

    DOMAIN = DOMAIN
    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._oauth_data: dict[str, Any] = {}
        self._me: dict[str, Any] = {}
        self._airplanes: list[dict[str, Any]] = []

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to pass to authorize endpoint."""
        return {
            "cl": "se",
            "theme": "system",
        }

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step by registering default implementation and starting OAuth."""
        await async_register_default_implementation(self.hass)
        return await super().async_step_user(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauth dialog."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Handle creation of entry once OAuth flow completes."""
        token = data["token"]["access_token"]
        session = async_get_clientsession(self.hass)
        auth = _StaticTokenAuth(session, token)
        client = MyWebLogClient(auth=auth)

        try:
            me_resp = await client.get_me()
            me = me_resp.get("data", me_resp) if isinstance(me_resp, dict) else {}
            objects_resp = await client.get_objects()
            objects = (
                objects_resp.get("data", objects_resp.get("Object", []))
                if isinstance(objects_resp, dict)
                else []
            )
        except Exception as err:
            _LOGGER.error("Failed to fetch initial profile data: %s", err)
            if is_auth_error(err):
                return self.async_abort(reason="invalid_auth")
            return self.async_abort(reason="cannot_connect")

        user_id = str(me.get("id"))
        await self.async_set_unique_id(user_id)

        # Handle re-authentication
        if self.source == config_entries.SOURCE_REAUTH:
            reauth_entry = self._get_reauth_entry()
            if reauth_entry:
                if reauth_entry.unique_id is None:
                    self.hass.config_entries.async_update_entry(
                        reauth_entry, unique_id=user_id
                    )
                else:
                    self._abort_if_unique_id_mismatch(reason="account_mismatch")
                data["airplanes"] = reauth_entry.data.get("airplanes", [])
                data["user_id"] = me.get("id")
                data["username"] = me.get("username") or reauth_entry.data.get(
                    "username"
                )
                return self.async_update_reload_and_abort(
                    reauth_entry, data_updates=data
                )

        self._abort_if_unique_id_configured()

        airplanes = filter_airplanes(objects)
        if not airplanes:
            _LOGGER.warning("No airplanes found for account %s", user_id)

        self._oauth_data = data
        self._me = me
        self._airplanes = airplanes

        return await self.async_step_select_airplane()

    async def async_step_select_airplane(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle airplane selection step."""
        errors = {}

        if user_input is not None:
            selected_regnrs = set(user_input.get("airplanes", []))
            selected_planes = [
                plane for plane in self._airplanes if plane["regnr"] in selected_regnrs
            ]

            if not selected_planes:
                errors["base"] = "no_airplanes_selected"
            else:
                planes_count = len(selected_planes)
                name_info = self._me.get("name")
                if isinstance(name_info, dict):
                    full_name = name_info.get("full")
                else:
                    full_name = str(name_info or "")

                username = (
                    self._me.get("username")
                    or full_name
                    or str(self._me.get("id", "User"))
                )
                title = (
                    f"MyWeblog ({username} - {planes_count} "
                    f"{'plane' if planes_count == 1 else 'planes'})"
                )

                _LOGGER.info(
                    "Config flow: selected %d airplanes for %s",
                    planes_count,
                    username,
                )

                return self.async_create_entry(
                    title=title,
                    data={
                        **self._oauth_data,
                        "user_id": self._me.get("id"),
                        "username": self._me.get("username"),
                        "airplanes": selected_planes,
                    },
                )

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
        self._my_config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow initialization."""
        return await self.async_step_options(user_input)

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow for airplane selection."""
        errors = {}
        try:
            entry = self.config_entry
        except (AttributeError, ValueError):
            entry = self._my_config_entry

        current_airplanes = entry.data.get("airplanes", [])
        current_regnrs = {plane["regnr"] for plane in current_airplanes}

        # Try to fetch fresh objects from active client or runtime_data
        airplanes = current_airplanes
        try:
            runtime_data = getattr(entry, "runtime_data", None)
            if runtime_data and hasattr(runtime_data, "client"):
                objects_resp = await runtime_data.client.get_objects()
                objects = objects_resp.get("data", objects_resp.get("Object", []))
                fresh_airplanes = filter_airplanes(objects)
                if fresh_airplanes:
                    airplanes = fresh_airplanes
        except Exception as err:
            _LOGGER.warning("Could not refresh airplanes for options: %s", err)

        if user_input is not None:
            selected_regnrs = set(user_input.get("airplanes", []))
            selected_planes = [
                plane for plane in airplanes if plane["regnr"] in selected_regnrs
            ]

            if not selected_planes:
                errors["base"] = "no_airplanes_selected"
            else:
                planes_count = len(selected_planes)
                username = entry.data.get("username", "User")
                title = (
                    f"MyWeblog ({username} - {planes_count} "
                    f"{'plane' if planes_count == 1 else 'planes'})"
                )

                self.hass.config_entries.async_update_entry(
                    entry,
                    title=title,
                    data={
                        **entry.data,
                        "airplanes": selected_planes,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_create_entry(title="", data={})

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
