from unittest.mock import patch, AsyncMock
from homeassistant.config_entries import ConfigEntryState  # type: ignore[import]
from homeassistant.core import HomeAssistant  # type: ignore[import]
from homeassistant.helpers import entity_registry as er  # type: ignore[import]
from custom_components.myweblog.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry  # type: ignore[import]


async def test_setup_unload_entry(hass: HomeAssistant) -> None:
    """Test setup and unload of a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [{"id": "1", "regnr": "SE-ABC", "title": "SE-ABC"}],
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


async def test_entity_cleanup_on_reload(hass: HomeAssistant) -> None:
    """Testar att entiteter tas bort när ett flygplan väljs bort."""
    # 1. Setup med två flygplan
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "token123",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC"},
                {"id": "2", "regnr": "SE-LOP", "title": "SE-LOP"},
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.sensor.MyWebLogClient") as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        # Returnera data för båda planen så att sensorer skapas
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC"},
                    {"ID": "2", "regnr": "SE-LOP"},
                ]
            }
        )
        instance.getBookings = AsyncMock(return_value={"Booking": []})

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        ent_reg = er.async_get(hass)
        # Vi kollar en specifik sensor som vi vet skapas (t.ex. next_booking)
        assert ent_reg.async_is_registered("sensor.se_abc_next_booking")
        assert ent_reg.async_is_registered("sensor.se_lop_next_booking")

        # 2. Uppdatera Options: Ta bort SE-LOP
        new_data = {
            "username": "test_user",
            "password": "test_password",
            "app_token": "token123",
            "airplanes": [{"id": "1", "regnr": "SE-ABC", "title": "SE-ABC"}],
        }

        hass.config_entries.async_update_entry(entry, data=new_data)
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

        # 3. Verifiera att SE-LOP nu är borta, men SE-ABC är kvar
        assert ent_reg.async_is_registered("sensor.se_abc_next_booking")
        assert not ent_reg.async_is_registered("sensor.se_lop_next_booking")

        # Stoppa timers för att slippa "lingering timer" errors
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
