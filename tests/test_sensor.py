"""Unit tests for MyWeblog sensors."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myweblog.const import DOMAIN

MOCK_OBJECTS_DATA = {
    "data": [
        {
            "id": 5599,
            "registration": "SE-DUM",
            "category": {"id": 0, "name": "Aircraft"},
            "model": {"id": 1, "name": "Piper PA-28"},
            "club": {"id": 368, "name": "Drönarklubb Sydost"},
            "active_remarks": [
                {"id": 1, "category_id": 1, "comment": "Tach bulb flickering"},
                {"id": 2, "category_id": 1, "comment": "Left step loose"},
                {"id": 3, "category_id": 2, "comment": "Pitot heat inoperative"},
            ],
            "status": {
                "remaining_time": {
                    "soft_days": 10,
                    "hard_days": 5,
                    "soft_airborne": 20.5,
                    "hard_airborne": 15.2,
                }
            },
            "time_summary": {
                "total": {
                    "airborne": 1004.58,
                    "block": 1006.92,
                    "tachometer": 7054.1,
                    "tach": 4256.6,
                    "landings": 137,
                }
            },
        },
        {
            "id": 5610,
            "registration": "SE-JET",
            "category": {"id": 0, "name": "Aircraft"},
            "model": {"id": 2, "name": "Cessna 172"},
            "club": {"id": 368, "name": "Drönarklubb Sydost"},
            "active_remarks": [],
            "status": {"remaining_time": {}},
            "time_summary": {
                "total": {
                    "airborne": 8001.0,
                    "block": 8001.5,
                    "tachometer": 8500.0,
                    "tach": 8001.3,
                    "landings": 802,
                }
            },
        },
    ]
}

MOCK_BOOKINGS_DATA = {
    "data": [
        {
            "id": 2149212,
            "object_id": 5599,
            "start_at": "2099-10-28T10:00:00Z",
            "end_at": "2099-10-28T12:00:00Z",
            "start_local": "2099-10-28T11:00:00+01:00",
            "end_local": "2099-10-28T13:00:00+01:00",
            "user": {
                "id": 66375,
                "name": {"full": "Marcus Karlsson"},
            },
            "comment": "Flight to Visby",
        }
    ]
}


async def test_airplane_sensors(hass: HomeAssistant) -> None:
    """Test all aircraft sensors and attributes for configured airplane."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "username": "368-12345",
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Piper PA-28)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(return_value=MOCK_OBJECTS_DATA)
        instance.get_bookings = AsyncMock(return_value=MOCK_BOOKINGS_DATA)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check total time sensors
        airborne = hass.states.get("sensor.se_dum_airborne")
        assert airborne is not None
        assert airborne.state == "1004.58"
        assert airborne.attributes["unit_of_measurement"] == "h"
        assert airborne.attributes["device_class"] == SensorDeviceClass.DURATION

        block = hass.states.get("sensor.se_dum_block")
        assert block is not None
        assert block.state == "1006.92"
        assert block.attributes["unit_of_measurement"] == "h"

        tachometer = hass.states.get("sensor.se_dum_tachometer")
        assert tachometer is not None
        assert tachometer.state == "7054.1"
        assert tachometer.attributes["unit_of_measurement"] == "h"

        tach_time = hass.states.get("sensor.se_dum_tach_time")
        assert tach_time is not None
        assert tach_time.state == "4256.6"
        assert tach_time.attributes["unit_of_measurement"] == "h"

        landings = hass.states.get("sensor.se_dum_landings")
        assert landings is not None
        assert landings.state == "137"

        # Check metadata sensors
        model = hass.states.get("sensor.se_dum_model")
        assert model is not None
        assert model.state == "Piper PA-28"

        club = hass.states.get("sensor.se_dum_club")
        assert club is not None
        assert club.state == "Drönarklubb Sydost"

        # Check remark tags
        yellow = hass.states.get("sensor.se_dum_yellow_tags")
        assert yellow is not None
        assert yellow.state == "2"

        red = hass.states.get("sensor.se_dum_red_tags")
        assert red is not None
        assert red.state == "1"

        # Check maintenance remaining time sensors
        days_maint = hass.states.get("sensor.se_dum_days_to_go_maintenance")
        assert days_maint is not None
        assert days_maint.state == "10"
        assert days_maint.attributes["unit_of_measurement"] == "d"

        days_stop = hass.states.get("sensor.se_dum_days_to_go_flight_stop")
        assert days_stop is not None
        assert days_stop.state == "5"
        assert days_stop.attributes["unit_of_measurement"] == "d"

        hours_maint = hass.states.get("sensor.se_dum_hours_to_go_maintenance")
        assert hours_maint is not None
        assert hours_maint.state == "20.5"
        assert hours_maint.attributes["unit_of_measurement"] == "h"

        hours_stop = hass.states.get("sensor.se_dum_hours_to_go_flight_stop")
        assert hours_stop is not None
        assert hours_stop.state == "15.2"
        assert hours_stop.attributes["unit_of_measurement"] == "h"

        # Check next booking sensor
        next_booking = hass.states.get("sensor.se_dum_next_booking")
        assert next_booking is not None
        assert "2099-10-28" in next_booking.state
        assert next_booking.attributes["user_name"] == "Marcus Karlsson"
        assert next_booking.attributes["booking_id"] == 2149212
        assert next_booking.attributes["comment"] == "Flight to Visby"
        assert next_booking.attributes["time_slot"] == "11:00 - 13:00"
        assert next_booking.attributes["booking_length"] == "2 hrs 0 min"

        # Check diagnostic sensors
        diag_airplanes = hass.states.get(
            "sensor.myweblog_diagnostics_configured_airplanes"
        )
        assert diag_airplanes is not None
        assert diag_airplanes.state == "1"

        diag_interval = hass.states.get(
            "sensor.myweblog_diagnostics_update_interval_objects"
        )
        assert diag_interval is not None
        assert int(diag_interval.state) > 0

        diag_last_update = hass.states.get(
            "sensor.myweblog_diagnostics_last_update_objects"
        )
        assert diag_last_update is not None

        # Verify device registry
        ent_reg = er.async_get(hass)
        entry_reg = ent_reg.async_get("sensor.se_dum_airborne")
        assert entry_reg is not None
        assert entry_reg.unique_id == "myweblog_se_dum_airborne"

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_sensors_multiple_airplanes(hass: HomeAssistant) -> None:
    """Test setup of multiple airplanes and their respective sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"},
                {"id": 5610, "regnr": "SE-JET", "title": "SE-JET"},
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(return_value=MOCK_OBJECTS_DATA)
        instance.get_bookings = AsyncMock(return_value={"data": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Both airplanes have airborne sensors
        assert hass.states.get("sensor.se_dum_airborne") is not None
        assert hass.states.get("sensor.se_dum_airborne").state == "1004.58"

        assert hass.states.get("sensor.se_jet_airborne") is not None
        assert hass.states.get("sensor.se_jet_airborne").state == "8001.0"

        # Diagnostic airplane count is 2
        diag_count = hass.states.get("sensor.myweblog_diagnostics_configured_airplanes")
        assert diag_count is not None
        assert diag_count.state == "2"

        # When no bookings exist, next_booking state is None / unknown
        se_jet_booking = hass.states.get("sensor.se_jet_next_booking")
        assert se_jet_booking is not None
        assert se_jet_booking.state in ("unknown", "unavailable", "None")

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_sensors_legacy_fallback_keys(hass: HomeAssistant) -> None:
    """Test that legacy dictionary keys (ftData, maintTimeDate) still parse correctly."""
    legacy_objects = {
        "Object": [
            {
                "ID": "5599",
                "regnr": "SE-DUM",
                "model": "Piper PA-28",
                "clubname": "Drönarklubb Sydost",
                "activeRemarks": [
                    {"remarkCategory": "1", "comment": "Yellow remark"},
                    {"remarkCategory": "2", "comment": "Red remark"},
                ],
                "maintTimeDate": {
                    "daysToGoValue": 14,
                    "flightStop_daysToGoValue": 7,
                    "hoursToGoValue": 35.0,
                    "flightStop_hoursToGoValue": 25.0,
                },
                "ftData": {
                    "airborne": 500.25,
                    "block": 505.5,
                    "tachometer": 508.5,
                    "tachtime": 503.0,
                    "landings": 80,
                },
            }
        ]
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(return_value=legacy_objects)
        instance.get_bookings = AsyncMock(return_value={"Booking": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert hass.states.get("sensor.se_dum_airborne").state == "500.25"
        assert hass.states.get("sensor.se_dum_block").state == "505.5"
        assert hass.states.get("sensor.se_dum_tachometer").state == "508.5"
        assert hass.states.get("sensor.se_dum_tach_time").state == "503.0"
        assert hass.states.get("sensor.se_dum_landings").state == "80"
        assert hass.states.get("sensor.se_dum_yellow_tags").state == "1"
        assert hass.states.get("sensor.se_dum_red_tags").state == "1"
        assert hass.states.get("sensor.se_dum_days_to_go_maintenance").state == "14"
        assert hass.states.get("sensor.se_dum_days_to_go_flight_stop").state == "7"
        assert hass.states.get("sensor.se_dum_hours_to_go_maintenance").state == "35.0"
        assert hass.states.get("sensor.se_dum_hours_to_go_flight_stop").state == "25.0"

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_obsolete_sensors_cleaned_up(hass: HomeAssistant) -> None:
    """Test that obsolete or unselected sensors are removed on setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Piper PA-28)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    ent_reg = er.async_get(hass)
    obsolete_entity = ent_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="myweblog_se_dum_obsolete_metric",
        config_entry=entry,
    )
    assert ent_reg.async_get(obsolete_entity.entity_id) is not None

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(return_value=MOCK_OBJECTS_DATA)
        instance.get_bookings = AsyncMock(return_value={"data": []})

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Obsolete entity should be cleaned up from registry
        assert ent_reg.async_get(obsolete_entity.entity_id) is None

        # Both tachometer and tach_time should exist
        assert hass.states.get("sensor.se_dum_tachometer") is not None
        assert hass.states.get("sensor.se_dum_tach_time") is not None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
