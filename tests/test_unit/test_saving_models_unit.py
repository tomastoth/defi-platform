from unittest import mock

import pytest

from src import data
from src.database import models, services
from tests.test_unit import utils
from tests.test_unit.fixtures import model_address  # noqa


@pytest.fixture
def address() -> data.Address:
    return data.Address(address="0x123")


@pytest.mark.asyncio
async def test_saving_aggregated_model() -> None:
    update_to_save = utils.create_aggregated_update(
        value_usd=1000.0, amount=1.0, price=1000.0, value_pct=100.0
    ).aggregated_assets[0]
    address_to_save = data.Address(address="0x123")
    mock_session = mock.AsyncMock()
    mock_add: mock.AsyncMock = mock_session.add
    execute_query = mock.MagicMock()
    mock_session.execute.return_value = execute_query
    execute_query.scalars.return_value.first.return_value = models.Address(address="0x123", blockchain_type="EVM")
    await services.async_save_aggregated_update(update_to_save, address_to_save, mock_session)
    created_model: models.AggregatedBalanceUpdate = mock_add.call_args[0][0]
    assert created_model.symbol == update_to_save.symbol
    assert created_model.price == update_to_save.price
    assert created_model.value_usd == update_to_save.value_usd
    assert created_model.value_pct == update_to_save.value_pct
    assert created_model.time == update_to_save.time_ms
    assert created_model.amount == update_to_save.amount
    address_model: models.Address = created_model.address
    assert address_model.address == "0x123"


@pytest.mark.asyncio
async def test_creating_new_address(address: data.Address) -> None:
    session_mock = mock.AsyncMock()
    add_mock: mock.AsyncMock = session_mock.add
    with mock.patch("src.database.services.async_find_address") as find_address:
        find_address.return_value = None
        await services.async_save_address(address=address, session=session_mock)
    address_model: models.Address = add_mock.call_args[0][0]
    assert address_model.address == "0x123"
    assert address_model.blockchain_type == "EVM"


@pytest.mark.asyncio
async def test_throwing_when_address_already_exists(address: models.Address) -> None:
    session_mock = mock.AsyncMock()
    with mock.patch("src.database.services.async_find_address") as find_address:
        find_address.return_value = mock.MagicMock()
        with pytest.raises(services.AddressAlreadyExistsError):
            await services.async_save_address(address, session_mock)


@pytest.mark.asyncio
async def test_finding_all_addresses(model_address: models.Address) -> None:
    addresses_data = [model_address]
    session_mock = mock.AsyncMock()
    execute_mock = mock.MagicMock()
    execute_mock.scalars.return_value.all.return_value = addresses_data
    session_mock.execute.return_value = execute_mock
    addresses: list[models.Address] = await services.async_find_all_addresses(session=session_mock)
    expected_address = addresses[0]
    assert expected_address.address == "0x123"
    assert expected_address.blockchain_type == "EVM"
