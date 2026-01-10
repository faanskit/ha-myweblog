from unittest.mock import patch, AsyncMock
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from custom_components.myweblog.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_unload_entry(hass: HomeAssistant) -> None:
    """Test setup and unload of a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.sensor.MyWebLogClient") as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.getObjects = AsyncMock(return_value={"Object": []})
        instance.getBookings = AsyncMock(return_value={"Booking": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state == ConfigEntryState.NOT_LOADED
