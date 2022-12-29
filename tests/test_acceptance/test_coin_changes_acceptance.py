from datetime import datetime

import pytest
import sqlalchemy.ext.asyncio as sql_async

from src import coin_changes, data, enums
from src.database import services
from tests.test_unit import utils

"""
Test getting aggregated assets for all addresses

- From these updates we need to aggregate coin changes % wise
- Average this for all users
- End data should look like this:
[
1. ETH -> +20%
2. BTC -> +15%
3. USDT -> -15%
]
"""


async def save_agg_update(
    updates: list[data.AggregatedAsset],
    user: data.Address,
    session: sql_async.AsyncSession,
) -> None:
    [
        await services.async_save_aggregated_update(update, user, session)
        for update in updates
    ]


@pytest.mark.asyncio
async def test_coin_changes() -> None:
    # old data to which we can compare for 2 users
    user1 = data.Address(address="0x123")
    user2 = data.Address(address="0x124")
    start_ts = 1671462000
    end_ts = 1671465600
    user_1_agg_assets_1 = [
        utils.create_aggregated_asset(
            value_usd=100.0,
            amount=1.0,
            price=100.0,
            value_pct=49.9,
            symbol="SPEX",
            timestamp=start_ts,
        ),
        utils.create_aggregated_asset(
            value_usd=100.0,
            amount=1.0,
            price=100.0,
            value_pct=50.0,
            symbol="KETO",
            timestamp=start_ts,
        ),
    ]

    user_2_agg_assets_1 = [
        utils.create_aggregated_asset(
            value_usd=100.0,
            amount=1.0,
            price=100.0,
            value_pct=50.1,
            symbol="LEL",
            timestamp=start_ts,
        ),
        utils.create_aggregated_asset(
            value_usd=100.0,
            amount=1.0,
            price=100.0,
            value_pct=50.0,
            symbol="ROT",
            timestamp=start_ts,
        ),
    ]
    user_1_agg_assets_2 = [
        utils.create_aggregated_asset(
            value_usd=200.0,
            amount=1.0,
            price=200.0,
            value_pct=100.0,
            symbol="SPEX",
            timestamp=end_ts,
        ),
    ]
    user_2_agg_assets_2 = [
        utils.create_aggregated_asset(
            value_usd=200.0,
            amount=1.0,
            price=200.0,
            value_pct=100.0,
            symbol="ROT",
            timestamp=end_ts,
        ),
    ]
    async_session = await utils.test_database_session()
    async with async_session() as session:
        await save_agg_update(user_1_agg_assets_1, user1, session)
        await save_agg_update(user_2_agg_assets_1, user2, session)

        # new data which we compare to old data for 2 users
        await save_agg_update(user_1_agg_assets_2, user1, session)
        await save_agg_update(user_2_agg_assets_2, user2, session)
        """
        when comparing we would normally compare full hour, here we have
        timestamp1 = 101, timestamp 2 = 102
        """
        # calculate result averaged
        end_dt = datetime.fromtimestamp(end_ts)
        await coin_changes.async_run_coin_ranking(
            time_type=enums.RunTimeType.HOUR, session=session, current_time=end_dt
        )
        result: list[
            data.AssetOwnedChange
        ] = await services.async_find_coin_ranking_by_time(
            at_time=end_dt, session=session
        )
        spex = result[0]
        assert spex.symbol == "SPEX"
        assert spex.pct_change == pytest.approx(25.05, abs=1e-2)
        rot = result[1]
        assert rot.symbol == "ROT"
        assert rot.pct_change == pytest.approx(25.0)
        negative_symbol = result[2]
        assert negative_symbol.pct_change == pytest.approx(-25.0)
