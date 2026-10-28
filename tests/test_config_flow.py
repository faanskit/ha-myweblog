"""Unit tests for MyWeblog config flow and options flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myweblog.const import DOMAIN, OAUTH2_AUTHORIZE
from pyMyweblog.exceptions import MyWebLogAuthError, MyWebLogError


async def _start_oauth_flow(hass: HomeAssistant) -> dict:
    """Helper to start OAuth flow and advance past pick_implementation if needed."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    if (
        result["type"] == data_entry_flow.FlowResultType.FORM
        and result["step_id"] == "pick_implementation"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"implementation": DOMAIN}
        )
    return result


async def _complete_external_step(
    hass: HomeAssistant, flow_id: str, state: str, code: str = "mock_code"
) -> dict:
    """Helper to send callback and advance past EXTERNAL_STEP_DONE to creation."""
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"state": state, "code": code}
    )
    assert result["type"] == data_entry_flow.FlowResultType.EXTERNAL_STEP_DONE
    # Calling async_configure without input invokes async_step_creation
    return await hass.config_entries.flow.async_configure(flow_id)


async def test_full_oauth_flow(hass: HomeAssistant) -> None:
    """Test full OAuth 2.1 flow including airplane selection and entry creation."""
    result = await _start_oauth_flow(hass)
    assert result["type"] == data_entry_flow.FlowResultType.EXTERNAL_STEP
    assert result["step_id"] == "auth"
    assert OAUTH2_AUTHORIZE in result["url"]
    assert "client_id=15" in result["url"]
    assert "code_challenge=" in result["url"]
    assert "code_challenge_method=S256" in result["url"]
    assert "theme=system" in result["url"]

    # Simulate callback
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(
            return_value={
                "access_token": "mock_at",
                "refresh_token": "mock_rt",
                "expires_in": 3600,
            }
        ),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(
            return_value={
                "data": {
                    "id": 66375,
                    "username": "368-12345",
                    "name": {"full": "Marcus Karlsson"},
                }
            }
        )
        client.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                        "category": {"id": 0},
                        "model": {"name": "Piper PA-28"},
                    },
                    {
                        "id": 5610,
                        "registration": "SE-JET",
                        "category": {"id": 0},
                        "model": {"name": "Cessna 172"},
                    },
                    {
                        "id": 5602,
                        "registration": "Tuggen",
                        "category": {"id": 1},
                    },
                ]
            }
        )

        result2 = await _complete_external_step(
            hass, result["flow_id"], state, "mock_auth_code"
        )

        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "select_airplane"

        # Select airplanes
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"airplanes": ["SE-DUM"]},
        )

        assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result3["title"] == "MyWeblog (368-12345 - 1 plane)"
        assert result3["data"]["token"]["access_token"] == "mock_at"
        assert len(result3["data"]["airplanes"]) == 1
        assert result3["data"]["airplanes"][0]["regnr"] == "SE-DUM"


async def test_oauth_flow_empty_selection_shows_error(hass: HomeAssistant) -> None:
    """Test that submitting an empty airplane selection shows validation error."""
    result = await _start_oauth_flow(hass)
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "mock_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(
            return_value={"data": {"id": 66375, "username": "368-12345"}}
        )
        client.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                        "category": {"id": 0},
                    }
                ]
            }
        )

        result2 = await _complete_external_step(hass, result["flow_id"], state)
        assert result2["step_id"] == "select_airplane"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"airplanes": []},
        )
        assert result3["type"] == data_entry_flow.FlowResultType.FORM
        assert result3["errors"] == {"base": "no_airplanes_selected"}


async def test_oauth_flow_api_auth_error_aborts(hass: HomeAssistant) -> None:
    """Test that auth error during initial profile fetch aborts the flow."""
    result = await _start_oauth_flow(hass)
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "mock_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(side_effect=MyWebLogAuthError("Invalid token"))

        result2 = await _complete_external_step(hass, result["flow_id"], state)
        assert result2["type"] == data_entry_flow.FlowResultType.ABORT
        assert result2["reason"] == "invalid_auth"


async def test_oauth_flow_connection_error_aborts(hass: HomeAssistant) -> None:
    """Test that connection error during initial fetch aborts with cannot_connect."""
    result = await _start_oauth_flow(hass)
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "mock_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(side_effect=MyWebLogError("Timeout"))

        result2 = await _complete_external_step(hass, result["flow_id"], state)
        assert result2["type"] == data_entry_flow.FlowResultType.ABORT
        assert result2["reason"] == "cannot_connect"


async def test_oauth_flow_already_configured(hass: HomeAssistant) -> None:
    """Test that configuring an account already registered aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="66375",
        data={"username": "existing_user"},
    )
    entry.add_to_hass(hass)

    result = await _start_oauth_flow(hass)
    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "mock_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(
            return_value={"data": {"id": 66375, "username": "368-12345"}}
        )
        client.get_objects = AsyncMock(return_value={"data": []})

        result2 = await _complete_external_step(hass, result["flow_id"], state)
        assert result2["type"] == data_entry_flow.FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Test successful re-authentication updates the token and preserves airplanes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "expired_at"},
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Aircraft)"}
            ],
            "username": "368-12345",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    if (
        result_confirm["type"] == data_entry_flow.FlowResultType.FORM
        and result_confirm["step_id"] == "pick_implementation"
    ):
        result_confirm = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"], {"implementation": DOMAIN}
        )

    assert result_confirm["type"] == data_entry_flow.FlowResultType.EXTERNAL_STEP

    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(
            return_value={
                "access_token": "new_refreshed_at",
                "refresh_token": "new_refreshed_rt",
                "expires_in": 3600,
            }
        ),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(
            return_value={"data": {"id": 66375, "username": "368-12345"}}
        )
        client.get_objects = AsyncMock(return_value={"data": []})

        result_oauth = await _complete_external_step(
            hass, result["flow_id"], state, "new_code"
        )

        assert result_oauth["type"] == data_entry_flow.FlowResultType.ABORT
        assert result_oauth["reason"] == "reauth_successful"
        assert entry.data["token"]["access_token"] == "new_refreshed_at"
        # Preserves existing airplane list
        assert len(entry.data["airplanes"]) == 1
        assert entry.data["airplanes"][0]["regnr"] == "SE-DUM"


async def test_reauth_flow_account_mismatch(hass: HomeAssistant) -> None:
    """Test that re-authenticating with a different user ID aborts with account_mismatch."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "expired_at"},
            "airplanes": [{"id": 5599, "regnr": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    if (
        result_confirm["type"] == data_entry_flow.FlowResultType.FORM
        and result_confirm["step_id"] == "pick_implementation"
    ):
        result_confirm = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"], {"implementation": DOMAIN}
        )

    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "other_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        # Returns different user ID (99999 instead of 66375)
        client.get_me = AsyncMock(
            return_value={"data": {"id": 99999, "username": "other_user"}}
        )
        client.get_objects = AsyncMock(return_value={"data": []})

        result_oauth = await _complete_external_step(
            hass, result["flow_id"], state, "new_code"
        )

        assert result_oauth["type"] == data_entry_flow.FlowResultType.ABORT
        assert result_oauth["reason"] == "account_mismatch"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow to reconfigure selected airplanes."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "username": "368-12345",
            "airplanes": [
                {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM (Piper PA-28)"}
            ],
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.myweblog.MyWebLogClient") as mock_client:
        instance = mock_client.return_value
        instance.get_objects = AsyncMock(
            return_value={
                "data": [
                    {
                        "id": 5599,
                        "registration": "SE-DUM",
                        "category": {"id": 0},
                        "model": {"name": "Piper PA-28"},
                    },
                    {
                        "id": 5610,
                        "registration": "SE-JET",
                        "category": {"id": 0},
                        "model": {"name": "Cessna 172"},
                    },
                ]
            }
        )
        instance.get_bookings = AsyncMock(return_value={"data": []})

        # Set up entry so runtime_data is populated with mock client
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Initialize options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "options"

        # Select both SE-DUM and SE-JET
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"airplanes": ["SE-DUM", "SE-JET"]},
        )

        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert len(entry.data["airplanes"]) == 2
        regs = [p["regnr"] for p in entry.data["airplanes"]]
        assert "SE-DUM" in regs
        assert "SE-JET" in regs


async def test_options_flow_empty_selection_shows_error(
    hass: HomeAssistant,
) -> None:
    """Test options flow shows validation error on empty selection."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="66375",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "valid_at"},
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"airplanes": []},
    )
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "no_airplanes_selected"}


async def test_reauth_migrated_v1_entry_without_unique_id(
    hass: HomeAssistant,
) -> None:
    """Test re-auth for a migrated v1 entry that had unique_id=None."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id=None,
        data={
            "username": "old_user",
            "airplanes": [{"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}],
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result_confirm = await hass.config_entries.flow.async_configure(
        result["flow_id"], {}
    )
    if (
        result_confirm["type"] == data_entry_flow.FlowResultType.FORM
        and result_confirm["step_id"] == "pick_implementation"
    ):
        result_confirm = await hass.config_entries.flow.async_configure(
            result_confirm["flow_id"], {"implementation": DOMAIN}
        )

    state = config_entry_oauth2_flow._encode_jwt(
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
        },
    )

    with patch(
        "custom_components.myweblog.application_credentials.MyWebLogOAuth2Implementation.async_resolve_external_data",
        AsyncMock(return_value={"access_token": "migrated_at", "expires_in": 3600}),
    ), patch("custom_components.myweblog.config_flow.MyWebLogClient") as mock_client:
        client = mock_client.return_value
        client.get_me = AsyncMock(
            return_value={"data": {"id": 66375, "username": "368-12345"}}
        )
        client.get_objects = AsyncMock(return_value={"data": []})

        result_oauth = await _complete_external_step(
            hass, result["flow_id"], state, "migrated_code"
        )

        assert result_oauth["type"] == data_entry_flow.FlowResultType.ABORT
        assert result_oauth["reason"] == "reauth_successful"
        assert entry.unique_id == "66375"
        assert entry.data["token"]["access_token"] == "migrated_at"
        assert entry.data["username"] == "368-12345"
        assert entry.data["airplanes"] == [
            {"id": 5599, "regnr": "SE-DUM", "title": "SE-DUM"}
        ]


async def test_oauth_implementation_pkce_public_and_confidential(
    hass: HomeAssistant,
) -> None:
    """Test MyWebLogOAuth2Implementation omits client_secret in Public Client mode."""
    from custom_components.myweblog.application_credentials import (
        MyWebLogOAuth2Implementation,
    )

    # 1. Public Client (Option 2: client_secret=None)
    pub_impl = MyWebLogOAuth2Implementation(
        hass=hass,
        domain=DOMAIN,
        client_id="15",
        client_secret=None,
    )
    assert pub_impl.client_secret is None
    auth_url = await pub_impl.async_generate_authorize_url("flow_123")
    assert "code_challenge=" in auth_url
    assert "theme=system" in auth_url

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(
        return_value={"access_token": "pub_at", "expires_in": 3600}
    )

    with patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = mock_get_session.return_value
        mock_session.post = AsyncMock(return_value=mock_resp)

        await pub_impl.async_resolve_external_data(
            {
                "code": "auth_code_1",
                "state": {
                    "flow_id": "flow_123",
                    "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
                },
            }
        )

        posted_data = mock_session.post.call_args.kwargs["data"]
        assert "client_secret" not in posted_data
        assert posted_data["client_id"] == "15"
        assert "code_verifier" in posted_data
        assert posted_data["device_name"] == "Home Assistant"

    # 2. Confidential Client (Option 1: with client_secret)
    conf_impl = MyWebLogOAuth2Implementation(
        hass=hass,
        domain=DOMAIN,
        client_id="15",
        client_secret="top_secret",
    )
    assert conf_impl.client_secret == "top_secret"
    await conf_impl.async_generate_authorize_url("flow_456")

    with patch(
        "homeassistant.helpers.config_entry_oauth2_flow.async_get_clientsession"
    ) as mock_get_session:
        mock_session = mock_get_session.return_value
        mock_session.post = AsyncMock(return_value=mock_resp)

        await conf_impl.async_resolve_external_data(
            {
                "code": "auth_code_2",
                "state": {
                    "flow_id": "flow_456",
                    "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
                },
            }
        )

        posted_data = mock_session.post.call_args.kwargs["data"]
        assert posted_data["client_secret"] == "top_secret"
        assert "code_verifier" in posted_data
