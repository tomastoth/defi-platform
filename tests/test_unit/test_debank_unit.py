import json
import unittest.mock

import pytest

from src import config, data, debank, enums
from tests.test_unit.fixtures import address  # noqa


@pytest.mark.asyncio
@pytest.mark.skip(reason="live execution, would call debank")
async def test_requesting_user_portfolio(address: data.Address) -> None:
    db = debank.Debank()
    await db.async_get_assets_for_address(address=address)


@pytest.mark.asyncio
async def test_parsing_protocol_on_blockchain_balance_of_address(
    address: data.Address,
) -> None:
    db = debank.Debank()
    with unittest.mock.patch("src.debank.Debank._async_request") as async_request:
        async_request.return_value = json.load(
            open(f"{config.config.test_data_dir}\\debank_balances.json")
        )
        blockchain_assets = await db._async_get_blockchain_assets(address)
    eth_on_ftm = blockchain_assets[0]
    assert eth_on_ftm.value_usd == pytest.approx(356, rel=1e1)
    assert eth_on_ftm.blockchain == enums.Blockchain.FTM


def test_calculating_pct_of_aggregated_assets() -> None:
    db = debank.Debank()
    agg_asset_1 = data.AggregatedUsdAsset(
        symbol="asset1", amount=1.0, price=1.0, value_usd=1.0
    )
    agg_asset_2 = data.AggregatedUsdAsset(
        symbol="asset2", amount=1.0, price=1.0, value_usd=1.0
    )
    aggregated_usd_assets = [agg_asset_1, agg_asset_2]
    aggregated_assets = db._add_pct_value(
        aggregated_usd_assets=aggregated_usd_assets, sum_value_usd=2.0
    )
    aggregated_pct_asset1: data.AggregatedAsset = aggregated_assets[0]
    assert aggregated_pct_asset1.value_pct == 50.0
    aggregated_pct_asset2: data.AggregatedAsset = aggregated_assets[1]
    assert aggregated_pct_asset2.value_pct == 50.0
