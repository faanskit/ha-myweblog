"""Unit tests for MyWeblog integration lifecycle and setup."""

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myweblog import async_migrate_entry
from custom_components.myweblog.const import DOMAIN
from pyMyweblog.exceptions import MyWebLogAuthError, MyWebLogMaintenanceError


async def test_setup_unload_entry(hass: HomeAssistant) -> None:
    """Test successful setup and unload of a v2 OAuth2 config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "mock_at", "refresh_token": "mock_rt"},
            "username": "368-12345",
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Aircraft)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                        "model": {"name": "Piper PA-28"},
                        "time_summary": {
                            "total": {
                                "airborne": 1004.58,
                                "block": 1006.92,
                                "tach": 1006.0,
                                "landings": 137,
                            }
                        },
                    }
                ]
            }
        )
        instance.get_bookings = AsyncMock(return_value={"data": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED
        assert entry.runtime_data is not None
        assert entry.runtime_data.client is not None
        assert entry.runtime_data.objects_coordinator is not None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.NOT_LOADED


async def test_migrate_entry_v1_to_v2(hass: HomeAssistant) -> None:
    """Test migration from version 1 (password/app_token) to version 2 (OAuth2)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "username": "old_user",
            "password": "legacy_password",
            "app_token": "legacy_token",
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert "password" not in entry.data
    assert "app_token" not in entry.data
    assert entry.data["username"] == "old_user"


async def test_setup_entry_missing_token_auth_failed(
    hass: HomeAssistant,
) -> None:
    """Test that entry without OAuth token triggers ConfigEntryAuthFailed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "username": "migrated_user",
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_setup_entry_auth_error_triggers_reauth(
    hass: HomeAssistant,
) -> None:
    """Test that 401 Unauthorized raises ConfigEntryAuthFailed."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "expired_at"},
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(side_effect=MyWebLogAuthError("Token expired"))

        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_setup_entry_maintenance_triggers_retry(
    hass: HomeAssistant,
) -> None:
    """Test that 503 Maintenance raises UpdateFailed leading to SETUP_RETRY."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(
            side_effect=MyWebLogMaintenanceError(
                "Closed for maintenance", code=10060, retry_after=60
            )
        )

        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_entity_cleanup_on_reload(hass: HomeAssistant) -> None:
    """Test that entities are removed from registry when airplane is unselected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_tok"},
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"},
                {"id": 5610, "regnr": "SE-JET", "title": "SE-JET"},
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {"id": 5599, "registration": "SE-DUM"},
                    {"id": 5610, "registration": "SE-JET"},
                ]
            }
        )
        instance.get_bookings = AsyncMock(return_value={"data": []})

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        ent_reg = er.async_get(hass)
        assert ent_reg.async_is_registered("sensor.se_dum_next_booking")
        assert ent_reg.async_is_registered("sensor.se_jet_next_booking")

        # Update entry to remove SE-JET
        new_data = dict(entry.data)
        new_data["airplanes"] = [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}]
        hass.config_entries.async_update_entry(entry, data=new_data)
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        assert ent_reg.async_is_registered("sensor.se_dum_next_booking")
        assert not ent_reg.async_is_registered("sensor.se_jet_next_booking")

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_auth_401_forces_token_refresh_and_retries(
    hass: HomeAssistant,
) -> None:
    """Test that a 401 response forces an OAuth2 token refresh and retries once."""
    import time
    from unittest.mock import MagicMock
    from custom_components.myweblog.api import AsyncConfigEntryAuth
    from pyMyweblog.auth import AbstractMyWebLogAuth

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "stale_token",
                "refresh_token": "valid_rt",
                "expires_in": 3600,
                "expires_at": time.time() + 1800,
            },
        },
    )
    entry.add_to_hass(hass)

    oauth_session = MagicMock()
    oauth_session.hass = hass
    oauth_session.config_entry = entry
    type(oauth_session).token = property(lambda self: entry.data["token"])

    refresh_calls = 0

    async def mock_ensure_valid() -> None:
        nonlocal refresh_calls
        if entry.data["token"].get("expires_at", 0) == 0:
            refresh_calls += 1
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "token": {
                        "access_token": "fresh_token",
                        "refresh_token": "fresh_rt",
                        "expires_in": 3600,
                        "expires_at": time.time() + 3600,
                    },
                },
            )

    oauth_session.async_ensure_token_valid = AsyncMock(side_effect=mock_ensure_valid)

    auth = AsyncConfigEntryAuth(MagicMock(), oauth_session)

    seen_tokens: list[str] = []

    async def mock_super_request(
        self_obj: Any, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        tok = await self_obj.async_get_access_token()
        seen_tokens.append(tok)
        if tok == "stale_token":
            raise MyWebLogAuthError("HTTP 401 Unauthorized", status=401)
        return {"data": [{"id": 335}]}

    with patch.object(AbstractMyWebLogAuth, "request", new=mock_super_request):
        res = await auth.request("GET", "/bookings", headers={"X-Custom": "1"})

    assert res == {"data": [{"id": 335}]}
    assert refresh_calls == 1
    assert seen_tokens == ["stale_token", "fresh_token"]
    assert entry.data["token"]["access_token"] == "fresh_token"


async def test_auth_401_concurrent_requests_refresh_only_once(
    hass: HomeAssistant,
) -> None:
    """Test that concurrent 401 responses only trigger a single token refresh."""
    import asyncio
    import time
    from unittest.mock import MagicMock
    from custom_components.myweblog.api import AsyncConfigEntryAuth
    from pyMyweblog.auth import AbstractMyWebLogAuth

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_implementation": DOMAIN,
            "token": {
                "access_token": "stale_token",
                "refresh_token": "valid_rt",
                "expires_in": 3600,
                "expires_at": time.time() + 1800,
            },
        },
    )
    entry.add_to_hass(hass)

    oauth_session = MagicMock()
    oauth_session.hass = hass
    oauth_session.config_entry = entry
    type(oauth_session).token = property(lambda self: entry.data["token"])

    refresh_calls = 0

    async def mock_ensure_valid() -> None:
        nonlocal refresh_calls
        if entry.data["token"].get("expires_at", 0) == 0:
            refresh_calls += 1
            await asyncio.sleep(0.01)
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "token": {
                        "access_token": f"fresh_token_{refresh_calls}",
                        "refresh_token": "fresh_rt",
                        "expires_in": 3600,
                        "expires_at": time.time() + 3600,
                    },
                },
            )

    oauth_session.async_ensure_token_valid = AsyncMock(side_effect=mock_ensure_valid)
    auth = AsyncConfigEntryAuth(MagicMock(), oauth_session)

    async def mock_super_request(
        self_obj: Any, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        tok = await self_obj.async_get_access_token()
        if tok == "stale_token":
            # Stagger failures so task 2 & 3 fail after task 1 has already refreshed
            if "335" in path:
                await asyncio.sleep(0.03)
            elif "538" in path:
                await asyncio.sleep(0.05)
            raise MyWebLogAuthError("HTTP 401 Unauthorized", status=401)
        return {"path": path, "token": tok}

    with patch.object(AbstractMyWebLogAuth, "request", new=mock_super_request):
        results = await asyncio.gather(
            auth.request("GET", "/bookings?object_id=3748"),
            auth.request("GET", "/bookings?object_id=335"),
            auth.request("GET", "/bookings?object_id=538"),
        )

    assert refresh_calls == 1
    assert all(r["token"] == "fresh_token_1" for r in results)


async def test_setup_unload_entry_main_api(hass: HomeAssistant) -> None:
    """Test successful setup and unload of a Main API config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="main_368_test_id",
        data={
            "auth_type": "main",
            "client_id": "test_id",
            "client_secret": "test_secret",
            "user_id": "368",
            "username": "Drönarklubb Sydost (Main API)",
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Aircraft)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.api_mode = "main"
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                        "model": {"name": "Piper PA-28"},
                        "time_summary": {
                            "total": {
                                "airborne": 100.0,
                                "block": 105.0,
                                "tach": 102.0,
                                "landings": 20,
                            }
                        },
                    }
                ]
            }
        )
        instance.get_bookings = AsyncMock(return_value={"data": []})
        instance.get_flight_logs = AsyncMock(return_value={"data": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED
        assert entry.runtime_data is not None
        assert entry.runtime_data.client is not None
        assert entry.runtime_data.client.api_mode == "main"
        assert entry.runtime_data.oauth_session is None
        assert entry.runtime_data.objects_coordinator is not None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.NOT_LOADED


async def test_setup_entry_main_api_missing_credentials(
    hass: HomeAssistant,
) -> None:
    """Test that Main API entry without credentials fails setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "auth_type": "main",
            "client_id": "only_id",
        },
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_setup_entry_main_api_forbidden_flightlogs(
    hass: HomeAssistant,
) -> None:
    """Test that HTTP 403 Forbidden on flight logs is handled gracefully."""
    from pyMyweblog.exceptions import MyWebLogForbiddenError

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="main_368_test_id",
        data={
            "auth_type": "main",
            "client_id": "test_id",
            "client_secret": "test_secret",
            "user_id": "368",
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.api_mode = "main"
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                    }
                ]
            }
        )
        instance.get_bookings = AsyncMock(return_value={"data": []})
        instance.get_flight_logs = AsyncMock(
            side_effect=MyWebLogForbiddenError("403 Forbidden", status=403)
        )

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED


async def test_setup_entry_main_api_forbidden_bookings(
    hass: HomeAssistant,
) -> None:
    """Test that HTTP 403 Forbidden on bookings is handled gracefully without crashing setup."""
    from pyMyweblog.exceptions import MyWebLogForbiddenError

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="main_368_test_id",
        data={
            "auth_type": "main",
            "client_id": "test_id",
            "client_secret": "test_secret",
            "user_id": "368",
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.api_mode = "main"
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                    }
                ]
            }
        )
        instance.get_bookings = AsyncMock(
            side_effect=MyWebLogForbiddenError("403 Forbidden", status=403)
        )
        instance.get_flight_logs = AsyncMock(return_value={"data": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED
        # Bookings coordinator returns empty list gracefully
        b_coord = entry.runtime_data.bookings_coordinators.get("5599")
        assert b_coord is not None
        assert b_coord.data == []
