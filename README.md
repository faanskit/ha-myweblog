# myWebLog Home Assistant Integration

This is a custom Home Assistant integration for [myWebLog](https://www.myweblog.se), allowing you to monitor and manage your club's airplanes directly from Home Assistant.

## 🚧 Beta Phase Instructions

This integration is currently in **beta**. We welcome early adopters, testers, and contributors!

### 1. Install via Option 3
As the integration is not yet available via the default HACS store, please install using [Option 3: Git-based Installation](#option-3-git-based-installation-with-symlink-advanced--dev-use).

### 2. Report Bugs
If you encounter any issues or unexpected behavior:
- Please report them via [GitHub Issues](https://github.com/faanskit/ha-myweblog/issues).
- Include relevant logs and reproduction steps when possible.

### 3. Contribute with Code Style
When contributing:
- Format your code using **Black**:
  ```bash
  black .
  ``` 
- Check your code style using Flake8:
  ```bash
  flake8
  ```
- Follow [Home Assistant's Python Style Guide](https://developers.home-assistant.io/docs/development/python_style_guide/) for consistency. This includes naming conventions, async/await usage, docstrings, and structure.


### 4. Follow Git Flow for Development
If you're developing features or fixes:
- Create a separate branch for each feature or bugfix:
  ```bash
  git checkout -b fix/something-broken
  ```
- Push your branch and submit a pull request (PR) to main when ready.

We appreciate your help in shaping the future of this integration!

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

### Option 2: HACS Custom Repository
**Pre-requisites:**
- HACS installed

This integration is not (currently) in the default HACS store, please add it as a custom repository:
1. Go to HACS in your Home Assistant sidebar.
2. Click the three-dot menu (⋮) in the top right and select "Custom repositories".
3. Enter `https://github.com/faanskit/ha-myweblog` as the repository URL and select "Integration" as the category.
4. Find "myWebLog" in HACS > Integrations and click "Download".
5. Restart Home Assistant.
6. **Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).**

### Option 3: Git-based Installation with Symlink (Developer-Friendly)

> 🧪 Use this method if you want to keep integration code in a separate folder (e.g., for development, testing, or easy updates via `git pull`).

#### 1. Open a terminal and go to your Home Assistant config directory:
```bash
cd /config
``` 
#### 2. Create a directory to hold GitHub repositories (if it doesn't already exist):
```bash
mkdir -p github_repos
```
#### 3. Clone the repository into that folder:
When the repo is public, run:

```bash
git clone https://github.com/faanskit/ha-myweblog.git
```
During the beta phase, and the repo is private, use your GitHub username and a [personal access token (PAT)](https://github.com/settings/tokens) like this:

```bash
git clone https://<your-username>:<your-token>@github.com/faanskit/ha-myweblog.git
```
Example:

```bash
git clone https://mygithubuser:ghp_xxXyYzZzz123TOKENHERE@github.com/faanskit/ha-myweblog.git
```

🔐 Create your token [here](https://github.com/settings/tokens).

✅ Make sure it has the repo scope if accessing a private repository.


#### 4. Create a symlink from the `custom_components` directory to the repository:
```bash
cd /config/custom_components
ln -s ../github_repos/ha-myweblog/custom_components/myweblog
```
This will link the myweblog integration into Home Assistant as if it were installed directly.

#### 5. Restart Home Assistant.
#### 6. Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).

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

## Displaying Icon Colors in Lovelace

To reflect the `icon_color` attribute (red for `red_tags`, yellow for `yellow_tags`) in the frontend, use a Lovelace card with the following configuration:

```yaml
type: entity
entity: sensor.<your_sensor_entity_id>
icon: mdi:alert  # Optional, if not set in the sensor
style: |
  :host {
    --paper-item-icon-color: {{ state_attr('sensor.<your_sensor_entity_id>', 'icon_color') | default('gray') }};
  }
```

Replace `<your_sensor_entity_id>` with your actual sensor entity ID (e.g., `sensor.airplane_red_tags`).

This approach uses a custom style to dynamically set the icon color based on the `icon_color` attribute. If the attribute is not set, the icon will default to gray.

## Example: Automate Pre-Flight Heater

You can use the `next_booking` sensor to automate actions before a scheduled flight. For example, to start a heater one hour before the next booking:

```yaml
alias: Turn on heater 60 minutes before booking
description: This automation turns on the heater 1 hour before the next booking starts.
trigger:
  - platform: time_pattern
    minutes: "/5"  # Runs every 5 minutes
condition:
  - condition: template
    value_template: >-
      {% set booking_time = as_timestamp(states('sensor.next_booking')) %}
      {% set current_time = as_timestamp(now()) %}
      {% set time_diff = booking_time - current_time %}
      {% set window = 300 %}  # 5 minutes in seconds
      {{ time_diff > 0 and time_diff <= 3600 and time_diff >= (3600 - window) }}
action:
  - service: switch.turn_on
    target:
      entity_id: switch.heater
mode: single
```
**Trigger**: Runs every 5 minutes.

**Condition**: Checks if the next booking is approximately 60 minutes away (within ±5 minutes).

**Action**: Turns on the heater (replace switch.heater with your actual switch entity).

```yaml
alias: Turn off heater after 60 minutes
description: Turns off the heater if it has been on for 60 minutes.
trigger:
  - platform: state
    entity_id: switch.heater
    to: "on"
    for:
      hours: 1
condition: []
action:
  - service: switch.turn_off
    target:
      entity_id: switch.heater
mode: single
```
**Trigger**: Fires when the switch has been in the on state for 1 hour.

**Action**: Turns off the heater.

## Options & Customization
- To change selected airplanes after setup, remove and re-add the integration (options flow coming soon).
- All API credentials and tokens are stored securely in your Home Assistant config.
- You can add or update translations by editing the `en.json`, `sv.json`, or other language files in the `translations` directory.
- Sensor state_class and device_class can be customized for advanced Home Assistant statistics and energy dashboard support.

## Requirements
- Home Assistant 2023.6 or newer recommended
- Python package: `pyMyweblog` (automatically installed)

## Logging & Troubleshooting
This integration includes detailed logging for setup, configuration, data fetching, and sensor updates. Logs can help you troubleshoot connection issues, API errors, and integration behavior.

**How to enable debug logging:**
Add the following to your `configuration.yaml` to see detailed logs for this integration:

```yaml
logger:
  default: info
  logs:
    custom_components.myweblog: debug
```

- Sensor creation, data updates, config flow steps, and errors are all logged.
- Check the Home Assistant logs if you experience issues with authentication, data updates, or sensor creation.

## License
See [LICENSE](LICENSE).

## Credits
- Integration by [Marcus Karlsson](https://github.com/faanskit)
- Powered by [pyMyweblog](https://github.com/faanskit/pyMyweblog)

## Issues & Feedback
Please report issues or feature requests on [GitHub](https://github.com/faanskit/ha-myweblog/issues).
