"""Support for MyWeblog sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from pyMyweblog import MyWebLogClient

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, OBJECTS_UPDATE_INTERVAL, BOOKINGS_UPDATE_INTERVAL
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

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
        async with MyWebLogClient(username, password, app_token) as client:
            result = await client.getObjects()
            return result.get('Object', [])

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
        async def async_update_bookings(airplane_id=airplane["id"]):
            async with MyWebLogClient(username, password, app_token) as client:
                result = await client.getBookings(airplane_id)
                # Extract the 'Booking' list for this airplane
                return result.get('Booking', [])
        bookings_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"myweblog_airplane_{airplane['id']}_bookings",
            update_method=async_update_bookings,
            update_interval=BOOKINGS_UPDATE_INTERVAL,
        )
        await bookings_coordinator.async_config_entry_first_refresh()
        sensors.append(MyWebLogAirplaneSensor(objects_coordinator, bookings_coordinator, airplane))
    async_add_entities(sensors, True)


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
        async with MyWebLogClient(username, password, app_token) as client:
            result = await client.getObjects()
            return result.get('Object', [])

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
        async def async_update_bookings(airplane_id=airplane["id"]):
            async with MyWebLogClient(username, password, app_token) as client:
                result = await client.getBookings(airplane_id)
                return result.get('Booking', [])
        bookings_coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"myweblog_airplane_{airplane['id']}_bookings",
            update_method=async_update_bookings,
            update_interval=BOOKINGS_UPDATE_INTERVAL,
        )
        await bookings_coordinator.async_config_entry_first_refresh()
        for key, description in SENSOR_TYPES.items():
            sensors.append(
                MyWebLogAirplaneSensor(
                    objects_coordinator,
                    bookings_coordinator,
                    airplane,
                    description
                )
            )
    async_add_entities(sensors, True)

class MyWebLogAirplaneSensor(SensorEntity):
    def __init__(self, objects_coordinator, bookings_coordinator, airplane, description: SensorEntityDescription):
        self.entity_description = description
        self._objects_coordinator = objects_coordinator
        self._bookings_coordinator = bookings_coordinator
        self._airplane_id = airplane["id"]
        self._airplane_regnr = airplane["regnr"]
        self._airplane_title = airplane.get("title", airplane["regnr"])
        self._attr_name = f"{self._airplane_regnr} {description.name}"
        self._attr_unique_id = f"myweblog_{self._airplane_regnr.lower().replace('-', '_')}_{description.key}"
        self._attr_device_class = description.device_class
        self._attr_icon = description.icon
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, self._airplane_regnr)},
            name = self._airplane_regnr,
            manufacturer = "myWebLog",
            model = self._airplane_title,
        )

    @property
    def state(self) -> StateType:
        obj = self._get_airplane_obj()
        if not obj:
            return None
        key = self.entity_description.key
        if key == "next_booking":
            import time
            now_ts = time.time()
            bookings = self._get_airplane_bookings()
            future_bookings = [b for b in bookings if b.get("bStart", 0) > now_ts]
            if not future_bookings:
                return None
            next_booking = min(future_bookings, key=lambda b: b.get("bStart", float("inf")), default=None)
            if not next_booking or not next_booking.get("bStartLTObj"):
                return None
            try:
                lt_obj = next_booking["bStartLTObj"]
                dt_str = lt_obj.get("date")
                tz_str = lt_obj.get("timezone")
                if not dt_str or not tz_str:
                    return None
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                import pytz
                tz = pytz.timezone(tz_str)
                dt = tz.localize(dt)
                return dt.isoformat()
            except Exception:
                return None
        elif key == "yellow_tags":
            return sum(1 for r in obj.get("activeRemarks", []) if r.get("category") == 2)
        elif key == "red_tags":
            return sum(1 for r in obj.get("activeRemarks", []) if r.get("category") == 1)
        elif key == "days_to_go":
            return obj.get("maintTimeDate", {}).get("daysToGoValue", 0)
        elif key == "hours_to_go":
            return obj.get("maintTimeDate", {}).get("hoursToGoValue", 0)
        elif key == "airborne":
            # Prefer flightData.total.airborne if available
            try:
                return obj["flightData"]["total"]["airborne"]
            except (KeyError, TypeError):
                return obj.get("ftData", {}).get("airborne", 0)
        elif key == "block":
            # Prefer flightData.total.block if available
            try:
                return obj["flightData"]["total"]["block"]
            except (KeyError, TypeError):
                return obj.get("ftData", {}).get("block", 0)
        elif key == "tachometer":
            # Prefer flightData.total.tachometer if available
            try:
                return obj["flightData"]["total"]["tachoMeter"]
            except (KeyError, TypeError):
                return obj.get("ftData", {}).get("tachometer", 0)
        elif key == "tach_time":
            # Prefer flightData.total.tachtime if available
            try:
                return obj["flightData"]["total"]["tachtime"]
            except (KeyError, TypeError):
                return obj.get("ftData", {}).get("tachtime", 0)
        elif key == "landings":
            # Prefer flightData.total.landings if available
            try:
                return obj["flightData"]["total"]["landings"]
            except (KeyError, TypeError):
                return obj.get("ftData", {}).get("landings", 0)
        elif key == "model":
            return obj.get("model")
        elif key == "club":
            return obj.get("clubname")
        return None

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

