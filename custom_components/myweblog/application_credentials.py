"""Application credentials and OAuth2 PKCE implementation for MyWebLog."""

from __future__ import annotations

import os
from typing import Any

from homeassistant.components.application_credentials import (
    AuthImplementation,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from yarl import URL

from pyMyweblog.auth import generate_pkce_pair

from .const import DEFAULT_CLIENT_ID, DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN


class MyWebLogOAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """MyWebLog OAuth 2.1 implementation supporting PKCE and Public/Confidential clients."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        client_id: str,
        client_secret: str | None = None,
        authorize_url: str = OAUTH2_AUTHORIZE,
        token_url: str = OAUTH2_TOKEN,
        name: str = "MyWebLog",
    ) -> None:
        """Initialize MyWebLog OAuth2 implementation."""
        super().__init__(
            hass=hass,
            domain=domain,
            client_id=client_id,
            client_secret=client_secret or "",
            authorize_url=authorize_url,
            token_url=token_url,
        )
        self._name = name
        self._raw_client_secret = client_secret.strip() if client_secret else None
        self.client_secret = self._raw_client_secret  # type: ignore[assignment]
        self._pkce_verifiers: dict[str, str] = {}

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return self._name

    @property
    def redirect_uri(self) -> str:
        """Return the redirect uri, defaulting to My Home Assistant OAuth redirect."""
        try:
            return super().redirect_uri
        except RuntimeError:
            return "https://my.home-assistant.io/redirect/oauth"

    async def async_generate_authorize_url(self, flow_id: str) -> str:
        """Generate authorize URL with PKCE S256 code challenge."""
        code_verifier, code_challenge = generate_pkce_pair()
        self._pkce_verifiers[flow_id] = code_verifier

        base_url = await super().async_generate_authorize_url(flow_id)
        return str(
            URL(base_url).update_query(
                {
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                    "cl": "se",
                }
            )
        )

    async def async_resolve_external_data(self, external_data: Any) -> dict[str, Any]:
        """Resolve authorization code to tokens with PKCE code_verifier."""
        flow_id = (
            external_data.get("state", {}).get("flow_id")
            if isinstance(external_data.get("state"), dict)
            else None
        )
        code_verifier = self._pkce_verifiers.pop(flow_id, None) if flow_id else None

        req_data: dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": external_data["code"],
            "redirect_uri": external_data["state"]["redirect_uri"],
            "device_name": "Home Assistant",
        }
        if code_verifier:
            req_data["code_verifier"] = code_verifier

        return await self._token_request(req_data)

    async def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Send a token request ensuring correct client_secret handling."""
        data["client_id"] = self.client_id
        if self._raw_client_secret:
            data["client_secret"] = self._raw_client_secret
        else:
            data.pop("client_secret", None)

        return await super()._token_request(data)


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> AuthImplementation:
    """Return implementation for application credentials (Option 1)."""
    return MyWebLogOAuth2Implementation(
        hass=hass,
        domain=auth_domain,
        client_id=credential.client_id,
        client_secret=credential.client_secret,
        name="MyWebLog Credentials",
    )


async def async_register_default_implementation(hass: HomeAssistant) -> None:
    """Register the built-in default Public Client implementation (Option 2 / Dev)."""
    implementations = await config_entry_oauth2_flow.async_get_implementations(
        hass, DOMAIN
    )
    if DOMAIN in implementations:
        return

    client_id = os.getenv("MYWEBLOG_CLIENT_ID", DEFAULT_CLIENT_ID)
    client_secret = os.getenv("MYWEBLOG_CLIENT_SECRET")

    config_entry_oauth2_flow.async_register_implementation(
        hass,
        DOMAIN,
        MyWebLogOAuth2Implementation(
            hass=hass,
            domain=DOMAIN,
            client_id=client_id,
            client_secret=client_secret,
            name="MyWebLog Default",
        ),
    )
