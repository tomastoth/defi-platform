import pytest

import src.token_balances.debank
from src.token_balances import aggregated_assets
from defi_common import data
from tests.test_unit.fixtures import address  # noqa


@pytest.mark.asyncio
@pytest.mark.skip(reason="live execution, would call debank")
async def test_requesting_user_portfolio(address: data.Address) -> None:
    db = src.token_balances.debank.Debank()
    await db.async_get_assets_for_address(address=address, run_time=100)


def test_calculating_pct_of_aggregated_assets() -> None:
    agg_asset_1 = data.AggregatedUsdAsset(
        symbol="asset1", amount=1.0, price=1.0, value_usd=1.0
    )
    agg_asset_2 = data.AggregatedUsdAsset(
        symbol="asset2", amount=1.0, price=1.0, value_usd=1.0
    )
    aggregated_usd_assets = [agg_asset_1, agg_asset_2]
    agg_asets = aggregated_assets.add_pct_value(
        aggregated_usd_assets=aggregated_usd_assets, sum_value_usd=2.0, run_time=100
    )
    aggregated_pct_asset1: data.AggregatedAsset = agg_asets[0]
    assert aggregated_pct_asset1.value_pct == 50.0
    aggregated_pct_asset2: data.AggregatedAsset = agg_asets[1]
    assert aggregated_pct_asset2.value_pct == 50.0
