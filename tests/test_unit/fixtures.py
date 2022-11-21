import pytest

from src import data


@pytest.fixture
def address() -> data.Address:
    return data.Address(address="0x123")
