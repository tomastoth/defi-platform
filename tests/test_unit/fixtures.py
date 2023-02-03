import pytest
from defi_common.database import models

from defi_common import data


@pytest.fixture
def address() -> data.Address:
    return data.Address(address="0x123")


@pytest.fixture
def model_address() -> models.Address:
    return models.Address(address="0x123", blockchain_type="EVM")
