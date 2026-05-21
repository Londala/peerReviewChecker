import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "network: marks tests that make real network calls (deselect with -m 'not network')")
