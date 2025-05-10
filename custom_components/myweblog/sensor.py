"""Support for MyWeblog sensors."""

from __future__ import annotations

from datetime import datetime
import logging
import time
from zoneinfo import ZoneInfo

from pyMyweblog import MyWebLogClient

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import BOOKINGS_UPDATE_INTERVAL, DOMAIN, OBJECTS_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "next_booking": SensorEntityDescription(
        key="next_booking",
        name="Next Booking",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:calendar-clock",
        translation_key="next_booking",
    ),
    "yellow_tags": SensorEntityDescription(
        key="yellow_tags",
        name="Yellow Tags",
        icon="mdi:tag-outline",
        translation_key="yellow_tags",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "red_tags": SensorEntityDescription(
        key="red_tags",
        name="Red Tags",
        icon="mdi:tag",
        translation_key="red_tags",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "days_to_go": SensorEntityDescription(
        key="days_to_go",
        name="Days to Go (Maintenance)",
        icon="mdi:calendar-range",
        translation_key="days_to_go",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="d",
    ),
    "hours_to_go": SensorEntityDescription(
        key="hours_to_go",
        name="Hours to Go (Maintenance)",
        icon="mdi:clock-outline",
        translation_key="hours_to_go",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="h",
    ),
    "airborne": SensorEntityDescription(
        key="airborne",
        name="Airborne",
        icon="mdi:airplane",
        translation_key="airborne",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="h",
    ),
    "block": SensorEntityDescription(
        key="block",
        name="Block",
        icon="mdi:car-brake-hold",
        translation_key="block",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="h",
    ),
    "tachometer": SensorEntityDescription(
        key="tachometer",
        name="Tachometer",
        icon="mdi:counter",
        translation_key="tachometer",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="h",
    ),
    "tach_time": SensorEntityDescription(
        key="tach_time",
        name="Tach Time",
        icon="mdi:timer-outline",
        translation_key="tach_time",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        unit_of_measurement="h",
    ),
    "landings": SensorEntityDescription(
        key="landings",
        name="Landings",
        icon="mdi:airplane-landing",
        translation_key="landings",
        state_class=SensorStateClass.TOTAL,
    ),
    "model": SensorEntityDescription(
        key="model",
        name="Model",
        icon="mdi:alpha-m-circle-outline",
        translation_key="model",
    ),
    "club": SensorEntityDescription(
        key="club",
        name="Club",
        icon="mdi:account-group",
        translation_key="club",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up myWebLog sensors from a config entry."""
    username = config_entry.data.get("username")
    password = config_entry.data.get("password")
    app_token = config_entry.data.get("app_token")
    airplanes = config_entry.data.get("airplanes", [])

    async def async_update_objects():
        _LOGGER.debug("Fetching objects for username=%s", username)
        try:
            async with MyWebLogClient(username, password, app_token) as client:
                result = await client.getObjects()
                _LOGGER.debug("Fetched objects: %s", result)
                return result.get("Object", [])
        except (ValueError, KeyError, TypeError) as e:
            _LOGGER.error("Error fetching objects: %s", e)
            return []

    objects_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="myweblog_airplanes_objects",
        update_method=async_update_objects,
        update_interval=OBJECTS_UPDATE_INTERVAL,
    )
    await objects_coordinator.async_config_entry_first_refresh()

    sensors = []
    for airplane in airplanes:
        _LOGGER.info("Creating sensor for airplane_id=%s", airplane["id"])

        async def async_update_bookings(airplane_id=airplane["id"]):
            _LOGGER.debug("Fetching bookings for airplane_id=%s", airplane_id)
            try:
                async with MyWebLogClient(username, password, app_token) as client:
                    result = await client.getBookings(airplane_id)
                    _LOGGER.debug("Fetched bookings: %s", result)
                    return result.get("Booking", [])
            except (ValueError, KeyError, TypeError) as e:
                _LOGGER.error(
                    "Error fetching bookings for airplane_id=%s: %s", airplane_id, e
                )
                return []

        bookings_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"myweblog_airplane_{airplane['id']}_bookings",
            update_method=async_update_bookings,
            update_interval=BOOKINGS_UPDATE_INTERVAL,
        )
        await bookings_coordinator.async_config_entry_first_refresh()
        sensors.extend(
            MyWebLogAirplaneSensor(
                objects_coordinator, bookings_coordinator, airplane, description
            )
            for description in SENSOR_TYPES.values()
        )
    async_add_entities(sensors, True)


class MyWebLogAirplaneSensor(SensorEntity):
    """Sensor entity for a specific metric of a myWebLog airplane."""

    def __init__(
        self,
        objects_coordinator,
        bookings_coordinator,
        airplane,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        self.entity_description = description
        self._objects_coordinator = objects_coordinator
        self._bookings_coordinator = bookings_coordinator
        self._airplane_id = airplane["id"]
        self._airplane_regnr = airplane["regnr"]
        self._airplane_title = airplane.get("title", airplane["regnr"])
        self._attr_unique_id = f"myweblog_{self._airplane_regnr.lower().replace('-', '_')}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._airplane_regnr)},
            name=self._airplane_regnr,
            manufacturer="myWebLog",
            model=self._airplane_title,
        )
        self._next_booking_obj = None
        _LOGGER.debug(
            "Created sensor: regnr=%s, key=%s, unique_id=%s",
            self._airplane_regnr,
            description.key,
            self._attr_unique_id,
        )

    def _get_yellow_tags(self, obj):
        return len(
            [r for r in obj.get("activeRemarks", []) if r.get("remarkCategory") == "1"]
        )

    def _get_red_tags(self, obj):
        return len(
            [r for r in obj.get("activeRemarks", []) if r.get("remarkCategory") == "2"]
        )

    def _get_days_to_go(self, obj):
        return obj.get("maintTimeDate", {}).get("daysToGoValue", 0)

    def _get_hours_to_go(self, obj):
        value = obj.get("maintTimeDate", {}).get("hoursToGoValue", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return round(value, 2)

    def _get_airborne(self, obj):
        try:
            value = obj["flightData"]["total"]["airborne"]
        except (KeyError, TypeError):
            value = obj.get("ftData", {}).get("airborne", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return round(value, 2)

    def _get_block(self, obj):
        try:
            value = obj["flightData"]["total"]["block"]
        except (KeyError, TypeError):
            value = obj.get("ftData", {}).get("block", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return round(value, 2)

    def _get_tachometer(self, obj):
        try:
            value = obj["flightData"]["total"]["tachoMeter"]
        except (KeyError, TypeError):
            value = obj.get("ftData", {}).get("tachometer", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return round(value, 2)

    def _get_tach_time(self, obj):
        try:
            value = obj["flightData"]["total"]["tachtime"]
        except (KeyError, TypeError):
            value = obj.get("ftData", {}).get("tachtime", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return value
        return round(value, 2)

    def _get_landings(self, obj):
        try:
            return obj["flightData"]["total"]["landings"]
        except (KeyError, TypeError):
            return obj.get("ftData", {}).get("landings", 0)

    def _get_model(self, obj):
        return obj.get("model")

    def _get_club(self, obj):
        return obj.get("clubname")

    def _get_next_booking(self, obj):
        bookings = self._get_airplane_bookings()
        if not bookings:
            self._next_booking_obj = None
            return None
        now = time.time()
        future_bookings = [
            b for b in bookings if b.get("bStart") and b.get("bStart") > now
        ]
        next_booking = min(
            future_bookings,
            key=lambda b: b.get("bStart", float("inf")),
            default=None,
        )
        self._next_booking_obj = next_booking  # Save for attribute access
        if not next_booking or not next_booking.get("bStartLTObj"):
            return None
        try:
            lt_obj = next_booking["bStartLTObj"]
            dt_str = lt_obj.get("date")
            tz_str = lt_obj.get("timezone")
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=ZoneInfo(tz_str))
            return dt.isoformat()
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        obj = self._get_airplane_obj()
        if obj is None:
            _LOGGER.warning(
                "No airplane object found for regnr=%s", self._airplane_regnr
            )
            return None

        key = self.entity_description.key

        dispatch = {
            "yellow_tags": self._get_yellow_tags,
            "red_tags": self._get_red_tags,
            "days_to_go": self._get_days_to_go,
            "hours_to_go": self._get_hours_to_go,
            "airborne": self._get_airborne,
            "block": self._get_block,
            "tachometer": self._get_tachometer,
            "tach_time": self._get_tach_time,
            "landings": self._get_landings,
            "model": self._get_model,
            "club": self._get_club,
            "next_booking": self._get_next_booking,
        }

        if key in dispatch:
            value = dispatch[key](obj)
            _LOGGER.debug("Sensor %s (%s): state=%s", self._airplane_regnr, key, value)
            return value
        _LOGGER.warning(
            "Unknown sensor key: %s for regnr=%s", key, self._airplane_regnr
        )
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes for the sensor.

        Sets the 'icon_color' attribute dynamically for Home Assistant 2023.4+:
        - For 'red_tags' sensors: sets icon color to red if value > 0.
        - For 'yellow_tags' sensors: sets icon color to yellow if value > 0.
        This allows the icon color to reflect the sensor state in the UI.
        Adds booking owner fullname for next_booking sensor.
        """
        attrs = super().extra_state_attributes or {}
        key = self.entity_description.key
        state = self.state
        if key == "red_tags" and isinstance(state, int) and state > 0:
            attrs["icon_color"] = "red"
        elif key == "yellow_tags" and isinstance(state, int) and state > 0:
            attrs["icon_color"] = "yellow"
        if key == "next_booking":
            # Try to get the fullname and elev_fullname from the booking object
            fullname = None
            student_name = None
            next_booking_obj = getattr(self, "_next_booking_obj", None)
            if next_booking_obj:
                fullname = next_booking_obj.get("fullname")
                student_name = next_booking_obj.get("elev_fullname")
                # Calculate booking length in seconds if both bStart and bEnd are present
                booking_length = None
                b_start = next_booking_obj.get("bStart")
                b_end = next_booking_obj.get("bEnd")
                if isinstance(b_start, (int, float)) and isinstance(
                    b_end, (int, float)
                ):
                    total_minutes = int((b_end - b_start) / 60)
                    hours, minutes = divmod(total_minutes, 60)
                    if hours > 0:
                        booking_length = f"{hours} hr {minutes} min"
                    else:
                        booking_length = f"{minutes} min"
                attrs["booking_length"] = booking_length
            attrs["owner_name"] = fullname
            attrs["student_name"] = student_name
        return attrs

    def _get_airplane_obj(self):
        data = self._objects_coordinator.data
        if not data:
            return None
        return next((obj for obj in data if obj.get("ID") == self._airplane_id), None)

    def _get_airplane_bookings(self):
        data = self._bookings_coordinator.data
        if not data:
            return []
        return data
