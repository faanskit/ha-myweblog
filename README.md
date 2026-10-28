# myWebLog Home Assistant Integration

![Quality Scale: Gold](https://img.shields.io/badge/Quality%20Scale-Gold-yellow.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

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
```bash
git clone https://github.com/faanskit/ha-myweblog.git
```

#### 4. Create a symlink from the `custom_components` directory to the repository:
```bash
cd /config/custom_components
ln -s ../github_repos/ha-myweblog/custom_components/myweblog
```
This will link the myweblog integration into Home Assistant as if it were installed directly.

#### 5. Restart Home Assistant.
#### 6. Add the "myWebLog" integration via the Home Assistant UI (Configuration → Devices & Services → Add Integration).

## Configuration

### Migration from v0.x to v1.0.0 (OAuth 2.1)

With `v1.0.0`, myWebLog transitions from legacy username/password authentication (Mobile API v3/v4) to modern OAuth 2.1 with PKCE (Mobile API v5).

Existing users upgrading from v0.x will experience a seamless migration:

1. **Automatic Schema Migration:**
   When Home Assistant boots with the updated integration, existing config entries are automatically migrated to version 2. Legacy passwords and stored app tokens are securely purged from Home Assistant storage.
2. **Re-authentication Prompt:**
   Because API v5 requires OAuth 2.1 credentials, Home Assistant will prompt for re-authentication with an alert on the myWebLog integration card under **Settings → Devices & Services**.
3. **One-Click Re-authentication:**
   - Click **Reconfigure** / **Re-authenticate** on the myWebLog card.
   - Confirm the prompt to open the secure myWebLog authorization page.
   - Log in with your myWebLog account credentials in your browser and authorize Home Assistant.
   - You are redirected back to Home Assistant automatically.
4. **Zero Configuration Lost:**
   - All previously selected airplanes are automatically preserved.
   - All entity IDs (sensor.<regnr>_*), unique IDs, historical data/statistics, and Lovelace dashboards remain 100% intact and continue updating immediately without any manual entity renaming.

### OAuth 2.1 Authentication (New Installations)
The integration uses standard Home Assistant OAuth 2.1 with PKCE.

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for and select **myWebLog**.
3. You will be redirected to the secure MyWebLog login page (`myweblog.se`).
4. Log in and authorize Home Assistant.
5. You are redirected back to Home Assistant and prompted to choose which airplanes to monitor.
6. Click **Submit** to finalize the setup.

> **Credentials & Development:**
> - By default, the integration connects using the pre-configured MyWebLog client ID (15) as a public client (no secret required, secured via PKCE).
> - If you operate a dedicated client ID / secret, you can optionally configure it via Home Assistant's **Application Credentials** (Settings → Devices & Services → ⋮ Menu → Application Credentials) or environment variables (MYWEBLOG_CLIENT_ID, MYWEBLOG_CLIENT_SECRET).

### Managing Monitored Airplanes (Options Flow)
You can modify your monitored airplanes at any time without reinstalling:
1. In Home Assistant, navigate to **Settings → Devices & Services → myWebLog**.
2. Click **Configure**.
3. Select or deselect airplanes and save. Entities for removed airplanes are automatically cleaned up from the registry.

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
  - `sensor.<regnr>_tach_time` (Tach time, h)
  - `sensor.<regnr>_landings` (Total landings)
  - `sensor.<regnr>_model` (Airplane model)
  - `sensor.<regnr>_club` (Club name)

- **Diagnostic Sensors** (Integration-level):
  - `sensor.myweblog_diagnostics_last_update_objects` (Last successful update timestamp)
  - `sensor.myweblog_diagnostics_update_interval_objects` (Update interval in seconds)
  - `sensor.myweblog_diagnostics_configured_airplanes` (Number of configured airplanes)

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
      {{ 0 < time_diff <= 60 }}
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

### Adding or Removing Airplanes

You can modify which airplanes are monitored without removing and re-adding the integration:

1. Go to **Configuration** → **Devices & Services** in Home Assistant.
2. Find the **myWebLog** integration and click on it.
3. Click the **Configure** button (or the three-dot menu → **Configure**).
4. Select or deselect airplanes from the list.
5. Click **Submit** to save your changes.

The integration will automatically reload with your updated airplane selection.

### Re-authentication

If your credentials expire or become invalid, the integration will automatically prompt you to re-authenticate:

1. A notification will appear in Home Assistant indicating that re-authentication is required.
2. Click the notification or go to **Configuration** → **Devices & Services** → **myWebLog**.
3. Enter your updated credentials.
4. The integration will automatically reload with the new credentials.

### Additional Notes
- All API credentials and tokens are stored securely in your Home Assistant config.
- You can add or update translations by editing the `en.json`, `sv.json`, or other language files in the `translations` directory.
- Sensor state_class and device_class can be customized for advanced Home Assistant statistics and energy dashboard support.

## Requirements
- Home Assistant 2023.6 or newer recommended
- Python package: `pyMyweblog` (automatically installed)

## Logging & Troubleshooting
This integration includes detailed logging for setup, configuration, data fetching, and sensor updates. Logs can help you troubleshoot connection issues, API errors, and integration behavior.

**How to enable debug logging:**
Add the following to your `configuration.yaml` to see detailed logs for this integration and the supporting `pyMyweblog` package:

```yaml
logger:
  default: info
  logs:
    custom_components.myweblog: debug
    pyMyweblog: debug
```

- Sensor creation, data updates, config flow steps, and errors are all logged.
- Check the Home Assistant logs if you experience issues with authentication, data updates, or sensor creation.

## License
See [LICENSE](LICENSE).

## Development & Testing

### Running Tests
To run the test suite, you need to install the development requirements first. It is recommended to use a virtual environment.

1. Install testing dependencies:
```bash
   pip install pytest-homeassistant-custom-component pytest-cov
   ```

2. Run the tests using `pytest`:
```bash
   pytest
   ```

   Or run with verbose output:
```bash
   pytest -v
   ```

**NOTE**
You may have to patch your `PYTHONPATH` to run this (Windows PowerShell):
```powershell
$env:PYTHONPATH = "$PWD"; pytest
```

### Running Tests with Coverage

To run the test suite with coverage reporting:

1. Install coverage dependencies (if not already installed):
```bash
   pip install pytest-cov
   ```

2. Run tests with coverage:
```bash
   pytest --cov=custom_components/myweblog --cov-report=term-missing
   ```

   This will show:
   - Coverage percentage for each file
   - Missing line numbers for uncovered code

3. Generate HTML coverage report:
```bash
   pytest --cov=custom_components/myweblog --cov-report=html
   ```

   This creates an `htmlcov` directory with an interactive HTML report. Open `htmlcov/index.html` in your browser to view detailed coverage information.

4. Generate both terminal and HTML reports:
```bash
   pytest --cov=custom_components/myweblog --cov-report=term-missing --cov-report=html
   ```

**Current Coverage:**
- `config_flow.py`: 100% coverage
- `sensor.py`: 91% coverage
- Overall: 95% coverage

The test suite covers configuration flow, sensor setup, error handling, options flow, re-authentication, and diagnostic sensors. We aim for high coverage to ensure reliability across Home Assistant updates.

## Contributing

### 1. Honor Home Assistant Integration Quality level
The integration is a GOLD level integration. This means contributors must ensure the following standards are maintained:
- **Extensive Documentation**: Provide comprehensive, user-friendly documentation including setup, features, troubleshooting, and examples.
- **Full Test Coverage**: Maintain automated tests covering the entire integration codebase (currently 95%+ coverage).
- **Robust Error Handling**: Implement proper error recovery, automatic re-authentication, and graceful handling of offline devices/services.
- **Reconfigurability**: Ensure the integration can be reconfigured and adjusted via the Home Assistant UI.
- **Translations**: Support multiple languages with complete translations for all user-facing strings.
- **Coding Standards**: Adhere to Home Assistant's Python Style Guide, with code formatted using Black and linted with Flake8.
- **Active Maintenance**: Have active code owners who maintain and update the integration.

### 2. Contribute with Code Style
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

### 3. Follow Git Flow for Development
If you're developing features or fixes:
- Create a separate branch for each feature or bugfix:
```bash
  git checkout -b feature/new-feature
  git checkout -b fix/something-broken
  ```
- Ensure all tests pass and linting checks succeed before submitting.
- Push your branch and submit a pull request (PR) to main when ready.
- PRs will be automatically validated with linting, HACS validation, and Home Assistant fest checks.

We appreciate your help in shaping the future of this integration!

## Credits
- Integration by [Marcus Karlsson](https://github.com/faanskit)
- Powered by [pyMyweblog](https://github.com/faanskit/pyMyweblog)

## Issues & Feedback
Please report issues or feature requests on [GitHub](https://github.com/faanskit/ha-myweblog/issues).
