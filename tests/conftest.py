"""Fixtures for testing MyWeblog integration."""
import pytest  # type: ignore[import]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
