"""Unit tests for MyWeblog integration lifecycle and setup."""

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
