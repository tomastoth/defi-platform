from datetime import datetime
from unittest import mock

import pytest
from defi_common.database import models
from defi_common import exceptions, data
from defi_common.database import services
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
    mock_add: mock.AsyncMock = mock.MagicMock()
    mock_session.add = mock_add
    execute_query = mock.MagicMock()
    mock_session.execute.return_value = execute_query
    execute_query.scalars.return_value.first.return_value = models.Address(
        address="0x123", blockchain_type="EVM"
    )
    await services.async_save_aggregated_update(
        update_to_save, address_to_save, mock_session
    )
    created_model: models.AggregatedBalanceUpdate = mock_add.call_args[0][0]
    assert created_model.symbol == update_to_save.symbol
    assert created_model.price == update_to_save.price
    assert created_model.value_usd == update_to_save.value_usd
    assert created_model.value_pct == update_to_save.value_pct
    assert created_model.timestamp == update_to_save.timestamp
    assert created_model.amount == update_to_save.amount
    address_model: models.Address = created_model.address
    assert address_model.address == "0x123"


@pytest.mark.asyncio
async def test_creating_new_address(address: data.Address) -> None:
    session_mock = mock.AsyncMock()
    add_mock: mock.AsyncMock = mock.MagicMock()
    session_mock.add = add_mock
    with mock.patch("defi_common.database.services.async_find_address") as find_address:
        find_address.return_value = None
        await services.async_save_address(address=address, session=session_mock)
    address_model: models.Address = add_mock.call_args[0][0]
    assert address_model.address == "0x123"
    assert address_model.blockchain_type == "EVM"


@pytest.mark.asyncio
async def test_throwing_when_address_already_exists(address: models.Address) -> None:
    session_mock = mock.AsyncMock()
    with mock.patch("defi_common.database.services.async_find_address") as find_address:
        find_address.return_value = mock.MagicMock()
        with pytest.raises(exceptions.AddressAlreadyExistsError):
            await services.async_save_address(address, session_mock)


@pytest.mark.asyncio
async def test_finding_all_addresses(model_address: models.Address) -> None:
    addresses_data = [model_address]
    session_mock = mock.AsyncMock()
    execute_mock = mock.MagicMock()
    execute_mock.scalars.return_value.all.return_value = addresses_data
    session_mock.execute.return_value = execute_mock
    addresses: list[models.Address] = await services.async_find_all_addresses(
        session=session_mock
    )
    expected_address = addresses[0]
    assert expected_address.address == "0x123"
    assert expected_address.blockchain_type == "EVM"


@pytest.mark.asyncio
async def test_saving_performance_result(
    address: data.Address, model_address: models.Address
) -> None:
    mock_service = utils.mock_finding_address(model_address)
    add_mock = mock.MagicMock()
    mock_service.add = add_mock
    perf_data = data.PerformanceResult(
        performance=10.0,
        start_time=datetime(2022, 1, 1, 1, 1, 1),
        end_time=datetime(2022, 1, 1, 1, 5, 1),
        address=address,
    )
    await services.async_save_performance_result(perf_data, mock_service)
    created_perf_model: models.PerformanceRunResult = add_mock.call_args[0][0]
    assert created_perf_model.address.id == model_address.id
    assert created_perf_model.performance == perf_data.performance
    assert created_perf_model.start_time == perf_data.start_time
    assert created_perf_model.end_time == perf_data.end_time
    assert created_perf_model.address_id == model_address.id
    assert created_perf_model.time_created
    assert created_perf_model.time_updated
