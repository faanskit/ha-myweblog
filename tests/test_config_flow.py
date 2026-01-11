"""Test MyWeblog config flow."""
from unittest.mock import patch, AsyncMock

from homeassistant import config_entries, data_entry_flow  # type: ignore[import]
from homeassistant.core import HomeAssistant  # type: ignore[import]
from pytest_homeassistant_custom_component.common import MockConfigEntry  # type: ignore[import]
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


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow for modifying airplane selection."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
        title="MyWeblog (test_user - 1 plane)",
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
                    {"ID": "2", "regnr": "SE-DEF", "model": "Piper PA-28"},
                ]
            }
        )

        sensor_instance = mock_sensor_client.return_value.__aenter__.return_value
        sensor_instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"},
                    {"ID": "2", "regnr": "SE-DEF", "model": "Piper PA-28"},
                ]
            }
        )
        sensor_instance.getBookings = AsyncMock(return_value={"Booking": []})

        # Start options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("step_id") == "options"

        # Add another airplane
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            {"airplanes": ["SE-ABC", "SE-DEF"]},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

        # Verify entry was updated
        updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
        assert updated_entry is not None
        assert len(updated_entry.data["airplanes"]) == 2
        assert updated_entry.data["app_token"] == "new_token"


async def test_options_flow_remove_airplane(hass: HomeAssistant) -> None:
    """Test options flow for removing an airplane."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"},
                {"id": "2", "regnr": "SE-DEF", "title": "SE-DEF (Piper PA-28)"},
            ],
        },
        title="MyWeblog (test_user - 2 planes)",
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
                    {"ID": "2", "regnr": "SE-DEF", "model": "Piper PA-28"},
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

        # Start options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result.get("type") == data_entry_flow.FlowResultType.FORM

        # Remove one airplane
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            {"airplanes": ["SE-ABC"]},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()

        # Verify entry was updated
        updated_entry = hass.config_entries.async_get_entry(entry.entry_id)
        assert updated_entry is not None
        assert len(updated_entry.data["airplanes"]) == 1
        assert updated_entry.data["airplanes"][0]["regnr"] == "SE-ABC"


async def test_options_flow_no_selection(hass: HomeAssistant) -> None:
    """Test options flow with no airplanes selected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
        title="MyWeblog (test_user - 1 plane)",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.obtainAppToken = AsyncMock(return_value="new_token")
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "SE-ABC", "model": "Cessna 172"},
                ]
            }
        )

        # Start options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result.get("type") == data_entry_flow.FlowResultType.FORM

        # Try to submit with no selection
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            {"airplanes": []},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "no_airplanes_selected"}


async def test_options_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test options flow with invalid credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "fake_token",
            "airplanes": [
                {"id": "1", "regnr": "SE-ABC", "title": "SE-ABC (Cessna 172)"}
            ],
        },
        title="MyWeblog (test_user - 1 plane)",
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception(
            "Invalid credentials"
        )

        # Start options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result.get("type") == data_entry_flow.FlowResultType.FORM

        # Try to submit - should fail with auth error
        result = await hass.config_entries.options.async_configure(
            result.get("flow_id"),
            {"airplanes": ["SE-ABC"]},
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "invalid_auth"}


async def test_is_auth_error(hass: HomeAssistant) -> None:
    """Test is_auth_error helper with various error messages."""
    from custom_components.myweblog.config_flow import is_auth_error

    # Test various auth error patterns
    assert is_auth_error(Exception("Invalid credentials")) is True
    assert is_auth_error(Exception("ogiltigt lösenord")) is True
    assert is_auth_error(Exception("Unauthorized access")) is True
    assert is_auth_error(Exception("Forbidden")) is True
    assert is_auth_error(Exception("401 error")) is True
    assert is_auth_error(Exception("403 forbidden")) is True
    assert is_auth_error(Exception("Authentication failed")) is True

    # Test non-auth errors
    assert is_auth_error(Exception("Connection timeout")) is False
    assert is_auth_error(Exception("Network error")) is False
    assert is_auth_error(Exception("Server error 500")) is False


async def test_validate_credentials_connection_error(hass: HomeAssistant) -> None:
    """Test validate_credentials with connection errors."""
    from custom_components.myweblog.config_flow import (
        validate_credentials,
        CannotConnect,
    )

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        mock_client.return_value.__aenter__.side_effect = Exception(
            "Connection timeout"
        )

        try:
            await validate_credentials(hass, "test_user", "test_password")
            assert False, "Should have raised CannotConnect"
        except CannotConnect:
            pass  # Expected
        except Exception:
            assert False, "Should have raised CannotConnect, not other exception"


async def test_validate_credentials_no_airplanes(hass: HomeAssistant) -> None:
    """Test validate_credentials with no airplanes found."""
    from custom_components.myweblog.config_flow import validate_credentials

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.obtainAppToken = AsyncMock(return_value="token")
        instance.getObjects = AsyncMock(return_value={"Object": []})  # No airplanes

        airplanes, token = await validate_credentials(
            hass, "test_user", "test_password"
        )
        assert airplanes == []
        assert token == "token"


async def test_validate_credentials_invalid_callsign(hass: HomeAssistant) -> None:
    """Test validate_credentials with invalid callsign patterns."""
    from custom_components.myweblog.config_flow import validate_credentials

    with patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        instance = mock_client.return_value.__aenter__.return_value
        instance.obtainAppToken = AsyncMock(return_value="token")
        # Object with invalid callsign (doesn't match pattern)
        instance.getObjects = AsyncMock(
            return_value={
                "Object": [
                    {"ID": "1", "regnr": "INVALID", "model": "Test"}  # Invalid pattern
                ]
            }
        )

        airplanes, token = await validate_credentials(
            hass, "test_user", "test_password"
        )
        # Invalid callsigns should be filtered out
        assert airplanes == []
        assert token == "token"


async def test_flow_user_cannot_connect(hass: HomeAssistant) -> None:
    """Test config flow with CannotConnect error."""
    from custom_components.myweblog.config_flow import CannotConnect

    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = CannotConnect()

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "test_user", "password": "test_password"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "cannot_connect"}


async def test_flow_user_generic_exception(hass: HomeAssistant) -> None:
    """Test config flow with generic exception."""
    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = ValueError("Unexpected error")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "test_user", "password": "test_password"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "unknown"}


async def test_reauth_cannot_connect(hass: HomeAssistant) -> None:
    """Test reauth flow with CannotConnect error."""
    from custom_components.myweblog.config_flow import CannotConnect

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "token",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = CannotConnect()

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "test_user", "password": "test_password"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "cannot_connect"}


async def test_reauth_generic_exception(hass: HomeAssistant) -> None:
    """Test reauth flow with generic exception."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "token",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = ValueError("Unexpected error")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"username": "test_user", "password": "test_password"}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "unknown"}


async def test_options_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test options flow with CannotConnect error."""
    from custom_components.myweblog.config_flow import CannotConnect

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "token",
            "airplanes": [{"id": "1", "regnr": "SE-ABC", "title": "SE-ABC"}],
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = CannotConnect()

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"airplanes": ["SE-ABC"]}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "cannot_connect"}


async def test_options_flow_generic_exception(hass: HomeAssistant) -> None:
    """Test options flow with generic exception."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "test_user",
            "password": "test_password",
            "app_token": "token",
            "airplanes": [{"id": "1", "regnr": "SE-ABC", "title": "SE-ABC"}],
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myweblog.config_flow.validate_credentials"
    ) as mock_validate:
        mock_validate.side_effect = ValueError("Unexpected error")

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"airplanes": ["SE-ABC"]}
        )

        assert result.get("type") == data_entry_flow.FlowResultType.FORM
        assert result.get("errors") == {"base": "unknown"}
