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
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant import config_entries

from .const import BOOKINGS_UPDATE_INTERVAL, DOMAIN, OBJECTS_UPDATE_INTERVAL
from .config_flow import is_auth_error

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
        native_unit_of_measurement="d",
    ),
    "days_to_flight_stop": SensorEntityDescription(
        key="days_to_flight_stop",
        name="Days to Go (Flight Stop)",
        icon="mdi:calendar-alert",
        translation_key="days_to_flight_stop",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="d",
    ),
    "hours_to_go": SensorEntityDescription(
        key="hours_to_go",
        name="Hours to Go (Maintenance)",
        icon="mdi:clock-outline",
        translation_key="hours_to_go",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
    ),
    "hours_to_flight_stop": SensorEntityDescription(
        key="hours_to_flight_stop",
        name="Hours to Go (Flight Stop)",
        icon="mdi:clock-alert-outline",
        translation_key="hours_to_flight_stop",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
    ),
    "airborne": SensorEntityDescription(
        key="airborne",
        name="Airborne",
        icon="mdi:airplane",
        translation_key="airborne",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
    ),
    "block": SensorEntityDescription(
        key="block",
        name="Block",
        icon="mdi:car-brake-hold",
        translation_key="block",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
    ),
    "tachometer": SensorEntityDescription(
        key="tachometer",
        name="Tachometer",
        icon="mdi:counter",
        translation_key="tachometer",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
    ),
    "tach_time": SensorEntityDescription(
        key="tach_time",
        name="Tach Time",
        icon="mdi:timer-outline",
        translation_key="tach_time",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="h",
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
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "club": SensorEntityDescription(
        key="club",
        name="Club",
        icon="mdi:account-group",
        translation_key="club",
        entity_category=EntityCategory.DIAGNOSTIC,
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

    if (
        not isinstance(username, str)
        or not isinstance(password, str)
        or not isinstance(app_token, str)
    ):
        raise TypeError("Missing or invalid credentials for myWebLog integration")

    async def async_update_objects():
        _LOGGER.debug("Fetching objects for username=%s", username)
        try:
            async with MyWebLogClient(username, password, app_token) as client:
                result = await client.getObjects()
                _LOGGER.debug("Fetched objects: %s", result)
                return result.get("Object", [])
        except Exception as e:
            if is_auth_error(e):
                _LOGGER.warning(
                    "Authentication error detected, triggering re-authentication"
                )
                hass.async_create_task(
                    hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={
                            "source": config_entries.SOURCE_REAUTH,
                            "entry_id": config_entry.entry_id,
                        },
                        data=config_entry.data,
                    )
                )
                raise UpdateFailed(
                    "Authentication failed, please re-authenticate"
                ) from e
            raise UpdateFailed(f"Error fetching objects: {e}") from e

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
            except Exception as e:
                if is_auth_error(e):
                    _LOGGER.warning(
                        "Authentication error detected, triggering re-authentication"
                    )
                    hass.async_create_task(
                        hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={
                                "source": config_entries.SOURCE_REAUTH,
                                "entry_id": config_entry.entry_id,
                            },
                            data=config_entry.data,
                        )
                    )
                    raise UpdateFailed(
                        "Authentication failed, please re-authenticate"
                    ) from e
                raise UpdateFailed(
                    f"Error fetching bookings for airplane_id={airplane_id}: {e}"
                ) from e

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


class MyWebLogAirplaneSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for a specific metric of a myWebLog airplane."""

    def __init__(
        self,
        objects_coordinator,
        bookings_coordinator,
        airplane,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        # Initialize with the objects_coordinator as the main coordinator
        super().__init__(objects_coordinator)
        self.entity_description = description
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
        self._attr_should_poll = False  # We use coordinator for updates
        _LOGGER.debug(
            "Created sensor: regnr=%s, key=%s, unique_id=%s",
            self._airplane_regnr,
            description.key,
            self._attr_unique_id,
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Add listener for bookings coordinator updates
        self.async_on_remove(
            self._bookings_coordinator.async_add_listener(self._handle_bookings_update)
        )
        # Initial update
        self._handle_bookings_update()

    def _handle_bookings_update(self) -> None:
        """Handle updated data from the bookings coordinator."""
        # Force a state update when bookings change
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self._bookings_coordinator.data is not None
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

    def _get_days_to_flight_stop(self, obj):
        return obj.get("maintTimeDate", {}).get("flightStop_daysToGoValue", 0)

    def _get_hours_to_go(self, obj):
        return round(float(obj.get("maintTimeDate", {}).get("hoursToGoValue", 0)), 2)

    def _get_hours_to_flight_stop(self, obj):
        return round(
            float(obj.get("maintTimeDate", {}).get("flightStop_hoursToGoValue", 0)), 2
        )

    def _get_airborne(self, obj):
        try:
            value = obj["flightData"]["total"]["airborne"]
        except (KeyError, TypeError):
            value = obj.get("ftData", {}).get("airborne", 0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return obj.get("ftData", {}).get("landings", 0)
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
        bookings = self._bookings_coordinator.data or []
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
        if not self.available:
            return None

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
            "days_to_flight_stop": self._get_days_to_flight_stop,
            "hours_to_flight_stop": self._get_hours_to_flight_stop,
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
            return dispatch[key](obj)

        _LOGGER.warning(
            "Unknown sensor key: %s for regnr=%s", key, self._airplane_regnr
        )
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes for the sensor."""
        attrs = dict(super().extra_state_attributes or {})
        key = self.entity_description.key
        state = self.state

        # Set icon colors for tag sensors
        if key == "red_tags" and isinstance(state, int) and state > 0:
            attrs["icon_color"] = "red"
        elif key == "yellow_tags" and isinstance(state, int) and state > 0:
            attrs["icon_color"] = "yellow"

        # Add booking information for next_booking sensor
        if key == "next_booking":
            next_booking_obj = getattr(self, "_next_booking_obj", None)
            if next_booking_obj:
                # Add booking owner information
                fullname = next_booking_obj.get("fullname")
                student_name = next_booking_obj.get("extra_elev_fullname")

                if fullname:
                    attrs["booked_by"] = fullname
                if student_name and student_name.strip() not in ("", " "):
                    attrs["student_name"] = student_name.strip()

                # Calculate booking length
                b_start = next_booking_obj.get("bStart")
                b_end = next_booking_obj.get("bEnd")
                if isinstance(b_start, (int, float)) and isinstance(
                    b_end, (int, float)
                ):
                    total_seconds = b_end - b_start
                    total_minutes = int(total_seconds / 60)
                    minutes = total_minutes % 60
                    total_hours = total_minutes // 60
                    hours = total_hours % 24
                    days = total_hours // 24

                    # Format the duration string
                    parts = []
                    if days > 0:
                        parts.append(f"{days} day{'s' if days != 1 else ''}")
                    if hours > 0 or days > 0:  # Show hours if there are days or hours
                        parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
                    parts.append(f"{minutes} min")

                    attrs["booking_length"] = " ".join(parts)

        return attrs

    def _get_airplane_obj(self):
        if not self.coordinator.data:
            return None
        return next(
            (
                obj
                for obj in self.coordinator.data
                if isinstance(obj, dict) and obj.get("ID") == self._airplane_id
            ),
            None,
        )
