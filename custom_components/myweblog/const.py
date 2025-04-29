"""Constants for the MyWeblog integration."""

from datetime import timedelta

DOMAIN = "myweblog"

DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

OBJECTS_UPDATE_INTERVAL = timedelta(hours=1)
BOOKINGS_UPDATE_INTERVAL = timedelta(minutes=15)
