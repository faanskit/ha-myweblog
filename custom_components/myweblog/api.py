"""API client authentication bridge for Home Assistant OAuth2Session."""

from __future__ import annotations

import aiohttp
from homeassistant.helpers import config_entry_oauth2_flow

from pyMyweblog.auth import AbstractMyWebLogAuth


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

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing automatically if expired."""
        if "expires_at" in self._oauth_session.token:
            await self._oauth_session.async_ensure_token_valid()
        return str(self._oauth_session.token["access_token"])
