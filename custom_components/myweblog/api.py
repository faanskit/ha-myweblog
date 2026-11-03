"""API client authentication bridge for Home Assistant OAuth2Session."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.helpers import config_entry_oauth2_flow

from pyMyweblog.auth import AbstractMyWebLogAuth
from pyMyweblog.exceptions import MyWebLogAuthError

_LOGGER = logging.getLogger(__name__)


class AsyncConfigEntryAuth(AbstractMyWebLogAuth):
    """Provide pyMyweblog authentication tied to a Home Assistant OAuth2Session."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize the auth provider."""
        super().__init__(websession)
        self._oauth_session = oauth_session
        self._force_refresh_lock = asyncio.Lock()

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing automatically if expired."""
        async with self._force_refresh_lock:
            if "expires_at" in self._oauth_session.token:
                await self._oauth_session.async_ensure_token_valid()
            return str(self._oauth_session.token["access_token"])

    async def _async_force_token_refresh(self, failed_token: str | None) -> None:
        """Force an OAuth2 token refresh if the token has not already been updated."""
        async with self._force_refresh_lock:
            current_token = self._oauth_session.token.get("access_token")
            if failed_token is not None and current_token != failed_token:
                _LOGGER.debug(
                    "Access token already refreshed by another task; skipping duplicate refresh"
                )
                return

            _LOGGER.info(
                "Received 401 Unauthorized from MyWebLog API; refreshing token and retrying"
            )
            config_entry = getattr(self._oauth_session, "config_entry", None)
            hass = getattr(self._oauth_session, "hass", None)
            if (
                config_entry is not None
                and hass is not None
                and isinstance(getattr(config_entry, "data", None), dict)
                and "token" in config_entry.data
            ):
                expired_token = {**self._oauth_session.token, "expires_at": 0}
                hass.config_entries.async_update_entry(
                    config_entry,
                    data={**config_entry.data, "token": expired_token},
                )
            elif isinstance(self._oauth_session.token, dict):
                self._oauth_session.token["expires_at"] = 0

            await self._oauth_session.async_ensure_token_valid()

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Execute an HTTP request, refreshing the token and retrying once on 401."""
        req_kwargs = dict(kwargs)
        if "headers" in req_kwargs and req_kwargs["headers"] is not None:
            req_kwargs["headers"] = dict(req_kwargs["headers"])

        used_token = await self.async_get_access_token()
        try:
            return await super().request(method, path, **req_kwargs)
        except MyWebLogAuthError:
            await self._async_force_token_refresh(used_token)
            return await super().request(method, path, **kwargs)
