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
For each selected airplane, **multiple sensors** are created—one for each metric:

- **Entity IDs:**
  - `sensor.<regnr>_next_booking` (Next booking timestamp)
  - `sensor.<regnr>_yellow_tags` (Yellow remarks count)
  - `sensor.<regnr>_red_tags` (Red remarks count)
  - `sensor.<regnr>_days_to_go` (Days to next maintenance)
  - `sensor.<regnr>_hours_to_go` (Hours to next maintenance)
  - `sensor.<regnr>_airborne` (Total airborne time, h)
  - `sensor.<regnr>_block` (Total block time, h)
  - `sensor.<regnr>_tachometer` (Tachometer total, h)
  - `sensor.<regnr>_tach_time` (Tach time, h)
  - `sensor.<regnr>_landings` (Total landings)
  - `sensor.<regnr>_model` (Airplane model)
  - `sensor.<regnr>_club` (Club name)

- **State:**
  - Each sensor's state reflects the current value for that metric (e.g., hours, count, timestamp, or string).
  - Numeric sensors use appropriate `state_class` and `device_class` for Home Assistant statistics and dashboards.

- **Localization:**
  - All sensor names and descriptions support translation (English and Swedish included by default).

- **Efficient API Usage:**
  - All sensors for an airplane share data via Home Assistant's DataUpdateCoordinator, minimizing API calls.
  - Data is fetched once per update interval and shared across all sensors for each airplane.

- **Grouping:**
  - In the Home Assistant UI, sensors are grouped by airplane, making it easy to monitor all metrics for each aircraft on a single card.

## Options & Customization
- To change selected airplanes after setup, remove and re-add the integration (options flow coming soon).
- All API credentials and tokens are stored securely in your Home Assistant config.
- You can add or update translations by editing the `en.json`, `sv.json`, or other language files in the `translations` directory.
- Sensor state_class and device_class can be customized for advanced Home Assistant statistics and energy dashboard support.

## Requirements
- Home Assistant 2023.6 or newer recommended
- Python package: `pyMyweblog` (automatically installed)

## License
See [LICENSE](LICENSE).

## Credits
- Integration by [Marcus Karlsson](https://github.com/faanskit)
- Powered by [pyMyweblog](https://github.com/faanskit/pyMyweblog)

## Issues & Feedback
Please report issues or feature requests on [GitHub](https://github.com/faanskit/ha-myweblog/issues).
