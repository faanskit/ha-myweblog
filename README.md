# myWebLog Home Assistant Integration

This is a custom Home Assistant integration for [myWebLog](https://www.myweblog.se), allowing you to monitor and manage your club's airplanes directly from Home Assistant.

## Features
- **Multi-Airplane Support:** Select and monitor multiple airplanes during setup.
- **Booking Awareness:** Each airplane sensor shows the date/time of the next booking (as a timestamp).
- **Maintenance & Flight Data:** Exposes maintenance, remarks, and flight data as individual sensors.
- **Localization:** Handles local timezones for bookings and supports translations.
- **Automation Ready:** Sensor state changes (e.g., next booking) can be used to trigger automations—ideal for use cases like pre-heating an airplane before a scheduled flight.
- **Efficient & Grouped:** Sensors are grouped by airplane and share API calls for efficient operation.

## Installation
### Option 1: HACS (Recommended)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=faanskit&repository=ha-myweblog&category=integration)

**Pre-requisites:**
- HACS installed

This integration is not (currently) in the default HACS store, please add it as a custom repository:
1. Go to HACS in your Home Assistant sidebar.
2. Click the three-dot menu (⋮) in the top right and select "Custom repositories".
3. Enter `https://github.com/faanskit/ha-myweblog` as the repository URL and select "Integration" as the category.
4. Find "myWebLog" in HACS > Integrations and click "Download".
5. Restart Home Assistant.
6. **Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).**

### Option 2: Git installation

1. Make sure you have git installed on your machine.
2. Navigate to your Home Assistant configuration directory (commonly `~/.homeassistant` or `/config`).
3. If it doesn't exist, create a `custom_components` directory:
   ```bash
   mkdir -p custom_components
   ```
4. Change into the `custom_components` directory:
   ```bash
   cd custom_components
   ```
5. Clone the repository:
   ```bash
   git clone https://github.com/faanskit/ha-myweblog.git myweblog
   ```
   This will create a `myweblog` directory with all integration files inside.
6. Restart Home Assistant.
7. **Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).**

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

## Example: Automate Pre-Flight Heater

You can use the `next_booking` sensor to automate actions before a scheduled flight. For example, to start a heater one hour before the next booking:

```yaml
automation:
  - alias: "Preheat Before Next Booking"
    trigger:
      - platform: state
        entity_id: sensor.se_mbi_next_booking  # Replace with your airplane's sensor
    condition:
      - condition: template
        value_template: >
          {{ (as_timestamp(states('sensor.se_mbi_next_booking')) - as_timestamp(now())) <= 3600 }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.heater  # Replace with your heater switch
```

- This automation will trigger whenever the next booking changes (including when a new booking is added that is sooner than the previous one).
- The condition ensures the heater only turns on if the booking is within an hour.
- Adjust `sensor.se_mbi_next_booking` and `switch.heater` to match your actual entity IDs.

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
