"""Constants for the MyWeblog integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "myweblog"

OAUTH2_AUTHORIZE = "https://api.myweblog.se/mobile/v5/oauth/authorize"
OAUTH2_TOKEN = "https://api.myweblog.se/mobile/v5/oauth/token"
DEFAULT_CLIENT_ID = "15"

DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

OBJECTS_UPDATE_INTERVAL = timedelta(hours=1)
BOOKINGS_UPDATE_INTERVAL = timedelta(minutes=15)
