import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "eval: mark test as part of the LLM evaluation harness")
