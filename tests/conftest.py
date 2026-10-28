"""Fixtures for testing MyWeblog integration."""

import asyncio
import sys
import threading
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Filter out Windows safe shutdown loop thread from pytest-homeassistant thread leak checks
    _orig_enumerate = threading.enumerate

    def _safe_enumerate():
        return [t for t in _orig_enumerate() if "_run_safe_shutdown_loop" not in t.name]

    threading.enumerate = _safe_enumerate


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    if sys.platform == "win32":
        loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
    else:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield
