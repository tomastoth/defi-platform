from datetime import datetime
from unittest import mock

import pytest
from defi_common.database import models

from src import data, runner
from tests.test_unit import utils
from tests.test_unit.fixtures import address, model_address  # noqa


async def get_assets(address: data.Address, run_time: int) -> data.AddressUpdate:
    aggregated_asset = utils.create_aggregated_update(
        amount=100.0, price=1000.0, value_pct=100.0, value_usd=100000.0
    ).aggregated_assets[0]
    return data.AddressUpdate(
        value_usd=100000,
        aggregated_assets=[aggregated_asset],
    )


@pytest.mark.asyncio
async def test_running_saving_aggregated_asset(
    address: data.Address, model_address: models.Address
) -> None:
    with mock.patch("src.database.services.async_find_all_addresses") as find_addresses:
        find_addresses.return_value = [model_address]
        with mock.patch(
            "src.database.services.convert_address_model"
        ) as convert_address:
            convert_address.return_value = address
            execute_mock = mock.MagicMock()
            session = mock.AsyncMock()
            session.execute.return_value = execute_mock
            with mock.patch(
                "src.database.services.async_save_aggregated_update"
            ) as save:
                await runner.async_run_single_address(
                    session=session,
                    provide_assets=get_assets,
                    address=address,
                    run_time_dt=datetime.now(),
                    performances=[],
                    run_time=100,
                )
                assert save.call_count == 1
