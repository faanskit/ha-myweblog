import pytest


def disable_socket(*args, **kwargs):
    pass


def enable_socket(*args, **kwargs):
    pass


def socket_allow_hosts(*args, **kwargs):
    pass


@pytest.fixture(name="socket_enabled")
def socket_enabled_fixture():
    yield
