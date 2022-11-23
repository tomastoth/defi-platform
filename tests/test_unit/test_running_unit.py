from unittest import mock

import pytest

from src import data, runner
from src.database import models
from tests.test_unit import utils
from tests.test_unit.fixtures import model_address  # noqa


@pytest.mark.asyncio
async def test_running_all_addresses(model_address: models.Address) -> None:
    execute_mock = mock.MagicMock()
    execute_mock.scalars.return_value.all.return_value = [model_address]
    session = mock.AsyncMock()
    session.execute.return_value = execute_mock
    with mock.patch(
        "src.debank.Debank.async_get_assets_for_address"
    ) as get_assets_for_address:
        aggregated_asset = utils.create_aggregated_update(
            amount=100.0, price=1000.0, value_pct=100.0, value_usd=100000.0
        ).aggregated_assets[0]
        get_assets_for_address.return_value = data.AddressUpdate(
            value_usd=100000,
            blockchain_wallet_assets=[],
            aggregated_assets=[aggregated_asset],
        )
        with mock.patch("src.database.services.async_save_aggregated_update") as save:
            await runner.async_update_all_addresses(session=session)
            assert save.call_count == 1
