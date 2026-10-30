"""Support for MyWeblog sensors."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN

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
    ),
    "club": SensorEntityDescription(
        key="club",
        name="Club",
        icon="mdi:account-group",
        translation_key="club",
    ),
}


class MyWebLogDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor for MyWebLog integration health."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[Any],
        key: str,
        name: str,
        icon: str,
        static_value: int | None = None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._key = key
        self._static_value = static_value
        self._attr_unique_id = f"myweblog_diagnostic_{key}"
        self._attr_name = name
        self._attr_icon = icon
        if key == "last_update_objects":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "diagnostics")},
            name="MyWebLog Diagnostics",
            manufacturer="myWebLog",
        )

    @property
    def native_value(self) -> StateType | datetime:
        """Return the native value of the diagnostic sensor."""
        if self._key == "last_update_objects":
            ts = getattr(self.coordinator, "_last_update_success_timestamp", None)
            if ts is not None:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            return None
        if self._key == "update_interval_objects":
            interval = self.coordinator.update_interval
            if interval:
                return int(interval.total_seconds())
            return None
        if self._key == "airplane_count":
            return self._static_value
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up myWebLog sensors from a config entry."""
    ent_reg = er.async_get(hass)
    airplanes = config_entry.data.get("airplanes", [])
    current_regnrs = {
        p["regnr"].lower().replace("-", "_") for p in airplanes if p.get("regnr")
    }

    # Clean up obsolete entities if planes were unselected or sensor types removed
    existing_entities = er.async_entries_for_config_entry(
        ent_reg, config_entry.entry_id
    )

    valid_suffixes = tuple(f"_{k}" for k in SENSOR_TYPES.keys())
    for entity in existing_entities:
        if entity.unique_id.startswith("myweblog_diagnostic_"):
            continue

        is_current = any(
            entity.unique_id.startswith(f"myweblog_{reg}_") for reg in current_regnrs
        )
        is_valid_sensor = entity.unique_id.endswith(valid_suffixes)
        if not is_current or not is_valid_sensor:
            _LOGGER.info("Removing obsolete MyWebLog sensor: %s", entity.entity_id)
            ent_reg.async_remove(entity.entity_id)

    # Obtain coordinators from runtime_data if present
    runtime_data = getattr(config_entry, "runtime_data", None)
    if runtime_data is not None:
        objects_coordinator = runtime_data.objects_coordinator
        bookings_coordinators = runtime_data.bookings_coordinators
    else:
        # Fallback for test fixtures that mock config_entry directly without setup_entry
        from .__init__ import async_setup_entry as init_setup_entry

        await init_setup_entry(hass, config_entry)  # type: ignore[arg-type]
        runtime_data = getattr(config_entry, "runtime_data", None)
        objects_coordinator = runtime_data.objects_coordinator
        bookings_coordinators = runtime_data.bookings_coordinators

    sensors: list[SensorEntity] = []
    for airplane in airplanes:
        plane_id = str(airplane["id"])
        b_coord = bookings_coordinators.get(plane_id)
        if b_coord is None:
            # Fallback if plane ID was int
            b_coord = objects_coordinator

        for description in SENSOR_TYPES.values():
            sensors.append(
                MyWebLogAirplaneSensor(
                    objects_coordinator=objects_coordinator,
                    bookings_coordinator=b_coord,
                    airplane=airplane,
                    description=description,
                )
            )

    # Diagnostic sensors
    diagnostic_sensors = [
        MyWebLogDiagnosticSensor(
            objects_coordinator,
            "last_update_objects",
            "Last Update (Objects)",
            "mdi:clock-outline",
        ),
        MyWebLogDiagnosticSensor(
            objects_coordinator,
            "update_interval_objects",
            "Update Interval (Objects)",
            "mdi:timer",
        ),
        MyWebLogDiagnosticSensor(
            objects_coordinator,
            "airplane_count",
            "Configured Airplanes",
            "mdi:airplane",
            len(airplanes),
        ),
    ]
    sensors.extend(diagnostic_sensors)

    async_add_entities(sensors, True)


class MyWebLogAirplaneSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for a specific metric of a myWebLog airplane."""

    def __init__(
        self,
        objects_coordinator: DataUpdateCoordinator[Any],
        bookings_coordinator: DataUpdateCoordinator[Any],
        airplane: dict[str, Any],
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(objects_coordinator)
        self.entity_description = description
        self._bookings_coordinator = bookings_coordinator
        self._airplane_id = str(airplane["id"])
        self._airplane_regnr = airplane["regnr"]
        self._airplane_title = airplane.get("title", airplane["regnr"])
        self._attr_unique_id = (
            f"myweblog_{self._airplane_regnr.lower().replace('-', '_')}_"
            f"{description.key}"
        )
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._airplane_regnr)},
            name=self._airplane_regnr,
            manufacturer="myWebLog",
            model=self._airplane_title,
        )
        self._next_booking_obj: dict[str, Any] | None = None
        self._attr_should_poll = False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._bookings_coordinator.async_add_listener(self._handle_bookings_update)
        )
        self._handle_bookings_update()

    def _handle_bookings_update(self) -> None:
        """Handle updated data from the bookings coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self._bookings_coordinator.data is not None
        )

    def _get_yellow_tags(self, obj: dict[str, Any]) -> int:
        remarks = obj.get("active_remarks", obj.get("activeRemarks", []))
        return len(
            [
                r
                for r in remarks
                if str(r.get("category_id") or r.get("remarkCategory")) == "1"
            ]
        )

    def _get_red_tags(self, obj: dict[str, Any]) -> int:
        remarks = obj.get("active_remarks", obj.get("activeRemarks", []))
        return len(
            [
                r
                for r in remarks
                if str(r.get("category_id") or r.get("remarkCategory")) == "2"
            ]
        )

    def _get_days_to_go(self, obj: dict[str, Any]) -> int:
        rem = (obj.get("status") or {}).get("remaining_time") or {}
        val = rem.get("soft_days")
        if val is not None:
            return int(val)
        return int(obj.get("maintTimeDate", {}).get("daysToGoValue", 0))

    def _get_days_to_flight_stop(self, obj: dict[str, Any]) -> int:
        rem = (obj.get("status") or {}).get("remaining_time") or {}
        val = rem.get("hard_days")
        if val is not None:
            return int(val)
        return int(obj.get("maintTimeDate", {}).get("flightStop_daysToGoValue", 0))

    def _get_hours_to_go(self, obj: dict[str, Any]) -> float:
        rem = (obj.get("status") or {}).get("remaining_time") or {}
        for key in ("soft_airborne", "soft_tach", "soft_tachometer"):
            if rem.get(key) is not None:
                return round(float(rem[key]), 2)
        val = obj.get("maintTimeDate", {}).get("hoursToGoValue", 0)
        return round(float(val or 0), 2)

    def _get_hours_to_flight_stop(self, obj: dict[str, Any]) -> float:
        rem = (obj.get("status") or {}).get("remaining_time") or {}
        for key in ("hard_airborne", "hard_tach", "hard_tachometer"):
            if rem.get(key) is not None:
                return round(float(rem[key]), 2)
        val = obj.get("maintTimeDate", {}).get("flightStop_hoursToGoValue", 0)
        return round(float(val or 0), 2)

    def _get_airborne(self, obj: dict[str, Any]) -> float:
        ts = (obj.get("time_summary") or {}).get("total") or {}
        if ts.get("airborne") is not None:
            return round(float(ts["airborne"]), 2)
        try:
            return round(float(obj["flightData"]["total"]["airborne"]), 2)
        except (KeyError, TypeError, ValueError):
            val = obj.get("ftData", {}).get("airborne", 0)
            try:
                return round(float(val), 2)
            except (TypeError, ValueError):
                return 0.0

    def _get_block(self, obj: dict[str, Any]) -> float:
        ts = (obj.get("time_summary") or {}).get("total") or {}
        if ts.get("block") is not None:
            return round(float(ts["block"]), 2)
        try:
            return round(float(obj["flightData"]["total"]["block"]), 2)
        except (KeyError, TypeError, ValueError):
            val = obj.get("ftData", {}).get("block", 0)
            try:
                return round(float(val), 2)
            except (TypeError, ValueError):
                return 0.0

    def _get_tachometer(self, obj: dict[str, Any]) -> float:
        ts = (obj.get("time_summary") or {}).get("total") or {}
        for key in ("tachometer", "tachoMeter", "tach_meter", "meter"):
            if ts.get(key) is not None:
                try:
                    return round(float(ts[key]), 2)
                except (TypeError, ValueError):
                    pass
        try:
            return round(float(obj["flightData"]["total"]["tachoMeter"]), 2)
        except (KeyError, TypeError, ValueError):
            val = obj.get("ftData", {}).get("tachometer", 0)
            try:
                return round(float(val), 2)
            except (TypeError, ValueError):
                return 0.0

    def _get_tach_time(self, obj: dict[str, Any]) -> float:
        ts = (obj.get("time_summary") or {}).get("total") or {}
        if ts.get("tach") is not None:
            return round(float(ts["tach"]), 2)
        try:
            return round(float(obj["flightData"]["total"]["tachtime"]), 2)
        except (KeyError, TypeError, ValueError):
            val = obj.get("ftData", {}).get("tachtime", 0)
            try:
                return round(float(val), 2)
            except (TypeError, ValueError):
                return 0.0

    def _get_landings(self, obj: dict[str, Any]) -> int:
        ts = (obj.get("time_summary") or {}).get("total") or {}
        if ts.get("landings") is not None:
            return int(ts["landings"])
        try:
            return int(obj["flightData"]["total"]["landings"])
        except (KeyError, TypeError, ValueError):
            return int(obj.get("ftData", {}).get("landings", 0) or 0)

    def _get_model(self, obj: dict[str, Any]) -> str | None:
        model_info = obj.get("model")
        if isinstance(model_info, dict):
            return (
                model_info.get("name")
                or model_info.get("designator")
                or obj.get("comment")
            )
        return model_info

    def _get_club(self, obj: dict[str, Any]) -> str | None:
        org = obj.get("organization") or obj.get("club")
        if isinstance(org, dict):
            return org.get("name")
        return obj.get("clubname") or (str(org) if org else None)

    def _get_next_booking(self, obj: dict[str, Any]) -> StateType | datetime:
        bookings = self._bookings_coordinator.data or []
        if not bookings:
            self._next_booking_obj = None
            return None

        now = datetime.now(timezone.utc)
        future_bookings: list[tuple[datetime, dict[str, Any]]] = []

        for b in bookings:
            start_at_str = b.get("start_at") or b.get("start_time")
            if start_at_str:
                try:
                    clean_iso = start_at_str.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(clean_iso)
                    if dt > now and not b.get("is_passed", False):
                        future_bookings.append((dt, b))
                except Exception:
                    pass
            elif b.get("bStart"):
                b_start = b.get("bStart")
                if isinstance(b_start, (int, float)) and b_start > now.timestamp():
                    dt = datetime.fromtimestamp(b_start, tz=timezone.utc)
                    future_bookings.append((dt, b))

        if not future_bookings:
            self._next_booking_obj = None
            return None

        future_bookings.sort(key=lambda x: x[0])
        next_dt, next_booking = future_bookings[0]
        self._next_booking_obj = next_booking

        start_local = (
            next_booking.get("start_local")
            or next_booking.get("start_time")
            or next_booking.get("start_at")
        )
        if start_local:
            try:
                return datetime.fromisoformat(start_local)
            except Exception:
                pass

        lt_obj = next_booking.get("bStartLTObj")
        if lt_obj:
            try:
                dt_str = lt_obj.get("date")
                tz_str = lt_obj.get("timezone", "UTC")
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                return dt.replace(tzinfo=ZoneInfo(tz_str))
            except Exception:
                pass

        return next_dt

    @property
    def native_value(self) -> StateType | datetime:
        """Return the native value of the sensor."""
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

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for the sensor."""
        attrs = dict(super().extra_state_attributes or {})
        key = self.entity_description.key
        state_val = self.native_value

        if key == "red_tags" and isinstance(state_val, int) and state_val > 0:
            attrs["icon_color"] = "red"
        elif key == "yellow_tags" and isinstance(state_val, int) and state_val > 0:
            attrs["icon_color"] = "yellow"

        if key == "next_booking":
            b = self._next_booking_obj
            if b:
                user_info = b.get("user")
                if isinstance(user_info, dict):
                    name_obj = user_info.get("name")
                    if isinstance(name_obj, dict):
                        fullname = name_obj.get("full")
                    else:
                        fullname = (
                            name_obj
                            or user_info.get("full_name")
                            or user_info.get("username")
                        )
                else:
                    fullname = b.get("fullname") or b.get("calendar_name")

                student_info = b.get("student")
                if isinstance(student_info, dict):
                    student_name = student_info.get("name")
                else:
                    student_name = b.get("extra_elev_fullname")

                if fullname:
                    attrs["booked_by"] = fullname
                    attrs["user_name"] = fullname
                if student_name and student_name.strip() not in ("", " "):
                    attrs["student_name"] = student_name.strip()

                if b.get("id") or b.get("ID"):
                    attrs["booking_id"] = b.get("id") or b.get("ID")
                if b.get("comment") is not None:
                    attrs["comment"] = b.get("comment")

                # Calculate booking duration and local time slot
                start_iso = (
                    b.get("start_local") or b.get("start_at") or b.get("start_time")
                )
                end_iso = b.get("end_local") or b.get("end_at") or b.get("stop_time")
                if start_iso and end_iso:
                    try:
                        s_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                        e_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
                        attrs["start_time"] = start_iso
                        attrs["stop_time"] = end_iso
                        attrs["time_slot"] = (
                            f"{s_dt.strftime('%H:%M')} - {e_dt.strftime('%H:%M')}"
                        )
                        duration_secs = int((e_dt - s_dt).total_seconds())
                        total_minutes = duration_secs // 60
                        minutes = total_minutes % 60
                        total_hours = total_minutes // 60
                        hours = total_hours % 24
                        days = total_hours // 24
                        parts = []
                        if days > 0:
                            parts.append(f"{days} day{'s' if days != 1 else ''}")
                        if hours > 0 or days > 0:
                            parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
                        parts.append(f"{minutes} min")
                        attrs["booking_length"] = " ".join(parts)
                    except Exception:
                        pass
                else:
                    b_start = b.get("bStart")
                    b_end = b.get("bEnd")
                    if isinstance(b_start, (int, float)) and isinstance(
                        b_end, (int, float)
                    ):
                        duration_secs = int(b_end - b_start)
                        total_minutes = duration_secs // 60
                        minutes = total_minutes % 60
                        total_hours = total_minutes // 60
                        hours = total_hours % 24
                        days = total_hours // 24
                        parts = []
                        if days > 0:
                            parts.append(f"{days} day{'s' if days != 1 else ''}")
                        if hours > 0 or days > 0:
                            parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
                        parts.append(f"{minutes} min")
                        attrs["booking_length"] = " ".join(parts)

        return attrs

    def _get_airplane_obj(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return next(
            (
                obj
                for obj in self.coordinator.data
                if isinstance(obj, dict)
                and str(obj.get("id") or obj.get("ID")) == self._airplane_id
            ),
            None,
        )
