import pytest
import sqlalchemy

from src import data, performance, runner, time_utils
from src.database import models
from tests.test_unit import utils
from tests.test_unit.fixtures import address  # noqa
from tests.test_unit.utils import test_database_session  # noqa


def test_performance_calculations_acceptance(address: data.Address) -> None:
    # we have old AddressUpdate
    old_addres_update = data.AddressUpdate(
        value_usd=100000.0,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=50.0,
                price=1000.0,
                timestamp=100,
                value_pct=50.0,
                value_usd=50000.0,
            ),
            data.AggregatedAsset(
                symbol="AAVE",
                amount=50.0,
                price=1000.0,
                timestamp=100,
                value_pct=50.0,
                value_usd=50000.0,
            ),
        ],
    )
    new_address_update = data.AddressUpdate(
        value_usd=200000.0,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=50.0,
                price=2000.0,
                timestamp=101,
                value_pct=50.0,
                value_usd=100000.0,
            ),
            data.AggregatedAsset(
                symbol="AAVE",
                amount=50.0,
                price=2000.0,
                timestamp=101,
                value_pct=50.0,
                value_usd=100000.0,
            ),
        ],
    )
    # we compare old to new to get account asset_performance

    performance_result = performance.calculate_performance(
        old_address_updates=old_addres_update.aggregated_assets,
        new_address_updates=new_address_update.aggregated_assets,
        start_time=time_utils.get_datetime_from_ts(0),
        end_time=time_utils.get_datetime_from_ts(1),
        address=address,
    )

    assert performance_result.performance

    # we compare addresses by peformance
    ...


class MockAssetProvider:
    def __init__(self) -> None:
        self.call_number = 1

    async def get_assets(
        self, address: models.Address, run_time: int
    ) -> data.AddressUpdate:
        price_multiplier_address_1 = (
            1 if self.call_number == 1 else 0.5
        )  # first address loses 50% of value
        price_multiplier_address_2 = (
            1 if self.call_number == 1 else 0.75
        )  # second address loses 25% of value
        amount = 1
        if address.address == "0x123":
            price = 1000.0 * price_multiplier_address_1
            return data.AddressUpdate(
                value_usd=price * amount,
                blockchain_wallet_assets=[],
                aggregated_assets=[
                    data.AggregatedAsset(
                        symbol="WETH",
                        amount=amount,
                        price=price,
                        value_pct=100.0,
                        value_usd=price * amount,
                        timestamp=run_time,
                    )
                ],
            )
        if address.address == "0x124":
            price = 100.0 * price_multiplier_address_2
            self.call_number += 1  # so next timestamp we call we get different prices
            return data.AddressUpdate(
                value_usd=price * amount,
                blockchain_wallet_assets=[],
                aggregated_assets=[
                    data.AggregatedAsset(
                        symbol="NEO",
                        amount=amount,
                        price=price,
                        value_pct=100.0,
                        value_usd=price * amount,
                        timestamp=run_time,
                    )
                ],
            )
        raise Exception("Should not happen")


@pytest.mark.asyncio
async def test_running_performance_for_all_addresses() -> None:
    async_session = await utils.test_database_session()
    async with async_session() as session:
        address_1 = models.Address(address="0x123", blockchain_type="EVM")
        address_2 = models.Address(address="0x124", blockchain_type="EVM")
        session.add_all([address_1, address_2])
        await session.commit()
        mock_asset_provider = MockAssetProvider()
        # run getting of update
        await runner.async_update_all_addresses(
            session, provide_assets=mock_asset_provider.get_assets  # type: ignore
        )
        await runner.async_update_all_addresses(
            session, provide_assets=mock_asset_provider.get_assets  # type: ignore
        )
        # run comparison of last update to second last update
        # runner should fetch last and second last update for each address

        # compare performances of all addresses
        performance_query = (
            sqlalchemy.select(models.PerformanceRunResult)
            .order_by(models.PerformanceRunResult.performance.desc())
            .limit(2)
        )
        performance_query_exec = await session.execute(performance_query)
        best_performance_results = performance_query_exec.scalars().all()
        best_performance_result: models.PerformanceRunResult = best_performance_results[
            0
        ]
        second_best_performance_result: models.PerformanceRunResult = (
            best_performance_results[1]
        )
        assert (
            best_performance_result.end_time == second_best_performance_result.end_time
        )
        assert (
            best_performance_result.performance
            > second_best_performance_result.performance
        )
        assert best_performance_result.start_time
        assert best_performance_result.end_time
        # ??? profit
