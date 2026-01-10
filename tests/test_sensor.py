from unittest.mock import patch, AsyncMock
from homeassistant.core import HomeAssistant
from custom_components.myweblog.const import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_sensors(hass: HomeAssistant) -> None:
    """Test MyWeblog sensors."""
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
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {
                        "ID": "1",
                        "regnr": "SE-ABC",
                        "model": "Cessna 172",
                        "clubname": "Test Club",
                        "activeRemarks": [],
                        "maintTimeDate": {
                            "daysToGoValue": 10,
                            "flightStop_daysToGoValue": 5,
                            "hoursToGoValue": 20.5,
                            "flightStop_hoursToGoValue": 15.2,
                        },
                        "flightData": {
                            "total": {
                                "airborne": 100.1,
                                "block": 110.2,
                                "tachoMeter": 120.3,
                                "tachtime": 130.4,
                                "landings": 50,
                            }
                        },
                    }
                ]
            }
        )
        instance.getBookings = AsyncMock(return_value={"Booking": []})

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check sensors
        state = hass.states.get("sensor.se_abc_airborne")
        assert state is not None
        assert state.state == "100.1"
        assert state.attributes["unit_of_measurement"] == "h"

        state = hass.states.get("sensor.se_abc_model")
        assert state is not None
        assert state.state == "Cessna 172"

        state = hass.states.get("sensor.se_abc_red_tags")
        assert state is not None
        assert state.state == "0"
