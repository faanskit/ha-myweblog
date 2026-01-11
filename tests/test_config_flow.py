"""Test MyWeblog config flow."""
from unittest.mock import patch, AsyncMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.myweblog.const import DOMAIN


async def test_flow_user_init(hass: HomeAssistant) -> None:
    """Test the initial step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") == data_entry_flow.FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_flow_user_success(hass: HomeAssistant) -> None:
    """Test a successful config flow."""
    with patch(
        "custom_components.myweblog.config_flow.MyWebLogClient"
    ) as mock_client, patch(
        "custom_components.myweblog.sensor.MyWebLogClient"
    ) as mock_sensor_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.obtainAppToken = AsyncMock(return_value="fake_token")
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"},
                    {"ID": "2", "regnr": "SE-DEF", "model": "Piper PA-28"},
                ]
            }
        )

        sensor_instance = mock_sensor_client.return_value.__aenter__.return_value
        sensor_instance.getObjects = AsyncMock(
            return_value={
                "Object": [{"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"}]
            }
        )
        sensor_instance.getBookings = AsyncMock(return_value={"Booking": []})

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"username": "test_user", "password": "test_password"},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("step_id") == "select_airplane"

        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"airplanes": ["SE-ABC"]},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result.get("title") == "MyWeblog (test_user - 1 plane)"
        assert result.get("data") == {
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        }


async def test_flow_user_invalid_auth(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials."""
    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception(
            "Invalid credentials"
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"username": "test_user", "password": "test_password"},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "invalid_auth"}


async def test_flow_user_invalid_auth_real(hass: HomeAssistant) -> None:
    """Test config flow with invalid credentials (distinguished)."""
    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception(
            "Invalid credentials"
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"username": "test_user", "password": "test_password"},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "invalid_auth"}


async def test_reauth_flow(hass: HomeAssistant) -> None:
    """Test re-authentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "old_user",
            "password": "old_password",
            "app_token": "old_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
        title="MyWeblog (old_user - 1 plane)",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myweblog.config_flow.MyWebLogClient"
    ) as mock_client, patch(
        "custom_components.myweblog.sensor.MyWebLogClient"
    ) as mock_sensor_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.obtainAppToken = AsyncMock(return_value="new_token")
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"},
                ]
            }
        )

        sensor_instance = mock_sensor_client.return_value.__aenter__.return_value
        sensor_instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"},
                ]
            }
        )
        sensor_instance.getBookings = AsyncMock(return_value={"Booking": []})

        # First call should show the form (don't pass data - it will be available via context)
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("step_id") == "reauth"

        # Configure with new credentials
        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"username": "new_user", "password": "new_password"},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.ABORT
        assert result.get("reason") == "reauth_successful"

        # Wait for reload to complete
        await hass.async_block_till_done()

        # Check that entry was updated
        updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
        assert updated_entry is not None
        assert updated_entry.data["username"] == "new_user"
        assert updated_entry.data["password"] == "new_password"
        assert updated_entry.data["app_token"] == "new_token"


async def test_reauth_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test re-authentication flow with invalid credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "old_user",
            "password": "old_password",
            "app_token": "old_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
        title="MyWeblog (old_user - 1 plane)",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception(
            "Invalid credentials"
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )

        result = await hass.config_entries.flow.async_configure(
            result.get("flow_id"),
            {"username": "new_user", "password": "wrong_password"},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "invalid_auth"}
