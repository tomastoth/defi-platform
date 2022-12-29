import asyncio
from datetime import datetime


from defi_common.database import db
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums, math_utils
from src.database import services
from src.enums import RunTimeType
from src.time_utils import get_saving_time_for_ranking, get_times_for_comparison
import logging

log = logging.getLogger(__name__)


def _add_assets_to_dict(
    assets: list[data.AggregatedAsset],
) -> dict[str, data.AggregatedAsset]:
    asset_dict = {}
    for asset in assets:
        symbol_lowercase = asset.symbol.lower()
        asset_dict[symbol_lowercase] = asset
    return asset_dict


def calculate_performance(
    old_address_updates: list[data.AggregatedAsset],
    new_address_updates: list[data.AggregatedAsset],
    start_time: datetime,
    address: data.Address,
    end_time: datetime = datetime.now(),
) -> data.PerformanceResult:
    old_assets_dict = _add_assets_to_dict(old_address_updates)
    new_assets_dict = _add_assets_to_dict(new_address_updates)
    performance = 0.0
    for old_asset_symbol, old_asset in old_assets_dict.items():
        if old_asset_symbol in new_assets_dict:
            new_asset = new_assets_dict[old_asset_symbol]
            asset_price_change_pct = math_utils.calc_percentage_diff(
                new_asset.price, old_asset.price
            )
            old_asset_pct_held = old_asset.value_pct / 100.0
            performance_gain = asset_price_change_pct * old_asset_pct_held
            performance += performance_gain
    performance_result = data.PerformanceResult(
        performance=performance,
        start_time=start_time,
        end_time=end_time,
        address=address,
    )
    return performance_result


async def _async_create_address_ranks(
    query_time: datetime,
    ranking_type: enums.RunTimeType,
    sorted_rank_dict: dict[data.Address, float],
) -> list[data.AddressPerformanceRank]:
    address_ranks: list[data.AddressPerformanceRank] = []
    for index, (address, avg_performance) in enumerate(sorted_rank_dict.items()):
        rank = index + 1
        address_ranks.append(
            data.AddressPerformanceRank(
                address=address,
                ranking_type=ranking_type,
                time=query_time,
                avg_performance=avg_performance,
                rank=rank,
            )
        )
    return address_ranks


async def _async_calculate_avg_performances(
    start_time: datetime, end_time: datetime, session: sql_asyncio.AsyncSession
) -> dict[data.Address, float]:
    performance_dict: dict[data.Address, float] = {}
    addresses: list[data.Address] = await services.async_find_all_converted_addresses(
        session
    )
    for address in addresses:
        performance_results: list[
            data.PerformanceResult
        ] = await services.async_find_performance_results(
            address=address,
            start_datetime=start_time,
            end_datetime=end_time,
            session=session,
        )
        if len(performance_results):
            sum_performances = sum(
                performance.performance for performance in performance_results
            )
            avg_performance = sum_performances / float(len(performance_results))
            performance_dict[address] = avg_performance
    return performance_dict


async def async_save_address_ranking(
    ranking_type: enums.RunTimeType,
    session: sql_asyncio.AsyncSession,
    run_time: datetime = datetime.now(),
) -> None:
    start_time, end_time = get_times_for_comparison(ranking_type, run_time)
    log.info(
        f"Address ranking, run_time: {run_time}, start_time: {start_time},"
        f"end_time: {end_time}"
    )
    performance_dict = await _async_calculate_avg_performances(
        start_time, end_time, session
    )
    log.info(f"address running perf dict len: {len(performance_dict)}")
    sorted_rank_dict = dict(
        sorted(performance_dict.items(), key=lambda item: item[1], reverse=True)
    )
    log.info(f"address running sorted perf dict len: {len(sorted_rank_dict)}")
    query_time = get_saving_time_for_ranking(ranking_type, run_time)
    address_ranks = await _async_create_address_ranks(
        query_time, ranking_type, sorted_rank_dict
    )
    log.info(f"address running address ranks len: {len(address_ranks)}")
    await services.async_save_address_ranks(address_ranks, session)
    log.info("Saved address ranks")


async def main():
    async with db.async_session() as session:
        await async_save_address_ranking(RunTimeType.HOUR, session)


if __name__ == "__main__":
    asyncio.run(main())
