# myWebLog Home Assistant Integration

This is a custom Home Assistant integration for [myWebLog](https://www.myweblog.se), allowing you to monitor and manage your club's airplanes directly from Home Assistant.

## Features
- **Multi-Airplane Support:** Select and monitor multiple airplanes during setup.
- **Booking Awareness:** Each airplane sensor shows the date/time of the next booking (as a timestamp).
- **Maintenance & Flight Data:** Exposes maintenance, remarks, and flight data as sensor attributes.
- **Localization:** Handles local timezones for bookings.

## Installation
1. Copy this repository into your Home Assistant `custom_components` directory:
   ```
   custom_components/
     myweblog/
       __init__.py
       sensor.py
       config_flow.py
       const.py
       ...
   ```
2. Restart Home Assistant.
3. Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).

## Configuration
- Enter your myWebLog username and password during setup.
- Select one or more airplanes to monitor.

## Sensors
For each selected airplane, a sensor will be created:
- **Entity ID:** `sensor.<regnr>` (e.g., `sensor.se_lop`)
- **State:** The date/time of the next booking (ISO 8601, local timezone, or `None` if no future bookings)
- **Attributes:**
  - `Model`: Airplane model
  - `Club`: Club name
  - `Yellow tags`: Count of yellow remarks
  - `Red tags`: Count of red remarks
  - `Days to go`: Days to next maintenance
  - `Hours to go`: Hours to next maintenance
  - `Airborne`, `Block`, `Tachometer`, `Tach time`, `Landings`: Flight/technical data

## Options & Customization
- To change selected airplanes after setup, remove and re-add the integration (options flow coming soon).
- All API credentials and tokens are stored securely in your Home Assistant config.

## Requirements
- Home Assistant 2023.6 or newer recommended
- Python package: `pyMyweblog` (automatically installed)

## License
See [LICENSE](LICENSE).

## Credits
- Integration by [Your Name/Club]
- Powered by [pyMyweblog](https://github.com/faanskit/pyMyweblog)

## Issues & Feedback
Please report issues or feature requests on [GitHub](https://github.com/faanskit/ha-myweblog/issues).
