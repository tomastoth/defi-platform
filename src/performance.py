import typing
from datetime import datetime, timedelta

from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums, math_utils
from src.database import services


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


def _get_times_for_comparison(
    address_ranking_type: enums.AddressRankingType, wanted_time: datetime
) -> tuple[datetime, datetime]:
    match address_ranking_type:
        case enums.AddressRankingType.HOUR:
            end_time = wanted_time.replace(minute=1, second=1)
            start_time = end_time - timedelta(hours=1)
            return start_time, end_time


async def async_save_address_ranking(
    averaging_type: enums.AddressRankingType,
    session: sql_asyncio.AsyncSession,
    addresses: list[data.Address],
    time_now: datetime = datetime.now(),
) -> None:
    start_time, end_time = _get_times_for_comparison(averaging_type, time_now)
    performance_dict: dict[data.Address, float] = {}
    for address in addresses:
        performance_results: list[
            data.PerformanceResult
        ] = await services.async_find_performance_results(
            address=address,
            start_datetime=start_time,
            end_datetime=end_time,
            session=session,
        )
        sum_performances = sum(
            performance.performance for performance in performance_results
        )
        avg_performance = sum_performances / float(len(performance_results))
        performance_dict[address] = avg_performance

    sorted_rank_dict: dict[data.Address, float] = dict(
        sorted(performance_dict.items(), key=lambda item: item[1], reverse=True)
    )
    address_ranks: list[data.AddressPerformanceRank] = []
    for index, (address, avg_performance) in enumerate(sorted_rank_dict.items()):
        rank = index + 1
        address_ranks.append(
            data.AddressPerformanceRank(
                address=address,
                ranking_type=averaging_type,
                time=time_now,
                avg_performance=avg_performance,
                rank=rank,
            )
        )
    await services.async_save_address_ranks(address_ranks, session)
