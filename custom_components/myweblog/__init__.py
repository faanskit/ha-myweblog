"""MyWeblog integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pyMyweblog.client import MyWebLogClient
from pyMyweblog.exceptions import (
    MyWebLogAuthError,
    MyWebLogError,
    MyWebLogMaintenanceError,
    MyWebLogRateLimitError,
)

from .api import AsyncConfigEntryAuth
from .application_credentials import async_register_default_implementation
from .const import (
    BOOKINGS_UPDATE_INTERVAL,
    OBJECTS_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class MyWebLogData:
    """Runtime data stored in entry.runtime_data."""

    client: MyWebLogClient
    oauth_session: config_entry_oauth2_flow.OAuth2Session
    objects_coordinator: DataUpdateCoordinator[list[dict[str, Any]]]
    bookings_coordinators: dict[str, DataUpdateCoordinator[list[dict[str, Any]]]]


type MyWebLogConfigEntry = ConfigEntry[MyWebLogData]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry from version 1 to version 2 (OAuth 2.1)."""
    _LOGGER.debug(
        "Migrating MyWebLog entry %s from version %s",
        config_entry.entry_id,
        config_entry.version,
    )

    if config_entry.version == 1:
        new_data = dict(config_entry.data)
        # Remove legacy credentials
        new_data.pop("password", None)
        new_data.pop("app_token", None)

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2,
        )
        _LOGGER.info("Migrated MyWebLog entry %s to version 2", config_entry.entry_id)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: MyWebLogConfigEntry) -> bool:
    """Set up MyWeblog from a config entry."""
    await async_register_default_implementation(hass)

    if "token" not in entry.data:
        raise ConfigEntryAuthFailed("No OAuth token found. Re-authentication required.")

    try:
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
    except Exception as err:
        raise ConfigEntryAuthFailed(f"Cannot find OAuth implementation: {err}") from err

    session = async_get_clientsession(hass)
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    auth = AsyncConfigEntryAuth(session, oauth_session)
    client = MyWebLogClient(auth=auth)

    # 1. Objects coordinator
    async def async_update_objects() -> list[dict[str, Any]]:
        _LOGGER.debug(
            "Fetching objects for MyWebLog account %s", entry.data.get("username")
        )
        try:
            res = await client.get_objects()
            data = res.get("data", res.get("Object", []))
            return data if isinstance(data, list) else []
        except MyWebLogAuthError as err:
            raise ConfigEntryAuthFailed(
                "Authentication expired, please re-authenticate"
            ) from err
        except aiohttp.ClientResponseError as err:
            if err.status in (400, 401):
                raise ConfigEntryAuthFailed(
                    "Authentication expired, please re-authenticate"
                ) from err
            raise UpdateFailed(f"HTTP error fetching objects: {err}") from err
        except (
            MyWebLogMaintenanceError,
            MyWebLogRateLimitError,
            aiohttp.ClientError,
            MyWebLogError,
        ) as err:
            raise UpdateFailed(f"Error fetching objects: {err}") from err

    objects_coordinator = DataUpdateCoordinator[list[dict[str, Any]]](
        hass,
        _LOGGER,
        name=f"myweblog_{entry.entry_id}_objects",
        update_method=async_update_objects,
        update_interval=OBJECTS_UPDATE_INTERVAL,
    )
    # Track last successful update timestamp
    objects_coordinator._last_update_success_timestamp = None  # type: ignore[attr-defined]

    def update_timestamp() -> None:
        if objects_coordinator.last_exception is None:
            objects_coordinator._last_update_success_timestamp = time.time()  # type: ignore[attr-defined]

    objects_coordinator.async_add_listener(update_timestamp)
    await objects_coordinator.async_config_entry_first_refresh()
    if objects_coordinator.last_exception is None:
        objects_coordinator._last_update_success_timestamp = time.time()  # type: ignore[attr-defined]

    # 2. Bookings coordinators for each airplane
    airplanes = entry.data.get("airplanes", [])
    bookings_coordinators: dict[str, DataUpdateCoordinator[list[dict[str, Any]]]] = {}

    for airplane in airplanes:
        plane_id = str(airplane["id"])

        async def make_update_bookings(
            p_id: str,
        ) -> Any:
            async def async_update_bookings() -> list[dict[str, Any]]:
                _LOGGER.debug("Fetching bookings for airplane %s", p_id)
                try:
                    res = await client.get_bookings(object_id=p_id)
                    data = res.get("data", res.get("Booking", []))
                    return data if isinstance(data, list) else []
                except MyWebLogAuthError as err:
                    raise ConfigEntryAuthFailed(
                        "Authentication expired, please re-authenticate"
                    ) from err
                except aiohttp.ClientResponseError as err:
                    if err.status in (400, 401):
                        raise ConfigEntryAuthFailed(
                            "Authentication expired, please re-authenticate"
                        ) from err
                    raise UpdateFailed(
                        f"HTTP error fetching bookings for {p_id}: {err}"
                    ) from err
                except (
                    MyWebLogMaintenanceError,
                    MyWebLogRateLimitError,
                    aiohttp.ClientError,
                    MyWebLogError,
                ) as err:
                    raise UpdateFailed(
                        f"Error fetching bookings for {p_id}: {err}"
                    ) from err

            return async_update_bookings

        update_method = await make_update_bookings(plane_id)
        b_coord = DataUpdateCoordinator[list[dict[str, Any]]](
            hass,
            _LOGGER,
            name=f"myweblog_{plane_id}_bookings",
            update_method=update_method,
            update_interval=BOOKINGS_UPDATE_INTERVAL,
        )
        await b_coord.async_config_entry_first_refresh()
        bookings_coordinators[plane_id] = b_coord

    entry.runtime_data = MyWebLogData(
        client=client,
        oauth_session=oauth_session,
        objects_coordinator=objects_coordinator,
        bookings_coordinators=bookings_coordinators,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyWebLogConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
