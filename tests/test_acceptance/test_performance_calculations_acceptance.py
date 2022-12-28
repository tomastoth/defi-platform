from datetime import datetime

import pytest
import sqlalchemy
from defi_common.database import models

import src  # noqa
from src import data, enums, performance, runner, time_utils
from src.database import services
from tests.test_unit import utils
from tests.test_unit.fixtures import address, model_address  # noqa


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
            session, provide_assets=mock_asset_provider.get_assets, sleep_time=0
        )
        await runner.async_update_all_addresses(
            session, provide_assets=mock_asset_provider.get_assets, sleep_time=0
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


def create_performance_updates(
    address: models.Address,
    end_date_1: datetime,
    end_date_2: datetime,
    start_date_1: datetime,
    start_date_2: datetime,
    performances: list[float],
) -> tuple[models.PerformanceRunResult, models.PerformanceRunResult]:
    perf_1 = models.PerformanceRunResult(
        performance=performances[0],
        start_time=start_date_1,
        end_time=end_date_1,
        address=address,
        address_id=address.id,
    )
    perf_2 = models.PerformanceRunResult(
        performance=performances[1],
        start_time=start_date_2,
        end_time=end_date_2,
        address=address,
        address_id=address.id,
    )
    return perf_1, perf_2
    # ??? profit


@pytest.mark.asyncio
async def test_address_ranking(
    address: data.Address, model_address: models.Address
) -> None:
    """
    - create different options to export performance comparison
        - for example 1 hour, 12 hours, 24 hours, 1 week
    - all will have start time and end time
    - for each, we select all PerformanceRunResult and average them
    - we do this for all addresses
    - after that we compare the averaged values
    - we sort addresses by these metrics
    - save the ranked_addresses ran
    """
    async_session = await utils.test_database_session()
    async with async_session() as session:
        performance_start_date_1 = utils.create_datetime(hour=1, minute=15)
        performance_end_date_1 = utils.create_datetime(hour=1, minute=30)
        performance_start_date_2 = utils.create_datetime(hour=1, minute=30)
        performance_end_date_2 = utils.create_datetime(hour=1, minute=45)
        time_now = utils.create_datetime(hour=2)
        address = models.Address(address="0x123", blockchain_type="EVM")
        address_2 = models.Address(address="0x124", blockchain_type="EVM")
        data_address = services.convert_address_model(address)
        data_address_2 = services.convert_address_model(address_2)
        address_2.address = "0x124"
        addr_1_performances = [1.0, 1.0]
        addr_2_performances = [0.5, 0.5]
        addr_1_perf_1, addr_1_perf_2 = create_performance_updates(
            address,
            performance_end_date_1,
            performance_end_date_2,
            performance_start_date_1,
            performance_start_date_2,
            addr_1_performances,
        )
        addr_2_perf_1, addr_2_perf_2 = create_performance_updates(
            address_2,
            performance_end_date_1,
            performance_end_date_2,
            performance_start_date_1,
            performance_start_date_2,
            addr_2_performances,
        )
        session.add_all([addr_1_perf_1, addr_1_perf_2, addr_2_perf_1, addr_2_perf_2])
        await session.commit()
        await runner.async_run_address_ranking(
            time_type=enums.RunTimeType.HOUR,
            session=session,
            current_time=time_now,
        )
        wanted_query_time = datetime(2022, 1, 1, 1, 0, 0)
        ranked_addresses: list[
            data.AddressPerformanceRank
        ] = await services.async_find_address_rankings(
            ranking_type=enums.RunTimeType.HOUR,
            time=wanted_query_time,
            session=session,
        )
        first_address_avg_perf = ranked_addresses[0]
        second_addres_avg_perf = ranked_addresses[1]
        assert first_address_avg_perf.address == data_address
        assert first_address_avg_perf.avg_performance == 1.0
        assert first_address_avg_perf.rank == 1
        assert first_address_avg_perf.time == wanted_query_time
        assert first_address_avg_perf.ranking_type == enums.RunTimeType.HOUR
        assert second_addres_avg_perf.address == data_address_2
        assert second_addres_avg_perf.avg_performance == 0.5
        assert second_addres_avg_perf.rank == 2
