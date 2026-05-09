import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_db: mark test as requiring a built LanceDB index")
