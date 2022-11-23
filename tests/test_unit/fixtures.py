import pytest

from src import data
from src.database import models


@pytest.fixture
def address() -> data.Address:
    return data.Address(address="0x123")


@pytest.fixture
def model_address() -> models.Address:
    return models.Address(address="0x123", blockchain_type="EVM")
