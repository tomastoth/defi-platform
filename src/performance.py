from datetime import datetime, timedelta

from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums, exceptions, math_utils
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
    match address_ranking_type:  # noqa
        case enums.AddressRankingType.HOUR:
            end_time = wanted_time.replace(minute=1, second=1)
            start_time = end_time - timedelta(hours=1)
            return start_time, end_time
        case enums.AddressRankingType.DAY:
            wanted_day = wanted_time - timedelta(days=1)
            end_time = wanted_day.replace(hour=23, minute=59, second=59)
            start_time = wanted_day.replace(hour=0, minute=0, second=1)
            return start_time, end_time


def _get_saving_time_for_ranking(
    address_ranking_type: enums.AddressRankingType, current_time: datetime
) -> datetime:
    match address_ranking_type:
        case enums.AddressRankingType.HOUR:
            hour_back = current_time - timedelta(hours=1)
            zeroed = hour_back.replace(minute=0, second=0)
            return zeroed
    raise exceptions.UnknownEnumError()


async def _async_create_address_ranks(
    query_time: datetime,
    ranking_type: enums.AddressRankingType,
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
    ranking_type: enums.AddressRankingType,
    session: sql_asyncio.AsyncSession,
    run_time: datetime = datetime.now(),
) -> None:
    start_time, end_time = _get_times_for_comparison(ranking_type, run_time)
    performance_dict = await _async_calculate_avg_performances(
        start_time, end_time, session
    )
    sorted_rank_dict: dict[data.Address, float] = dict(
        sorted(performance_dict.items(), key=lambda item: item[1], reverse=True)
    )
    query_time = _get_saving_time_for_ranking(ranking_type, run_time)
    address_ranks = await _async_create_address_ranks(
        query_time, ranking_type, sorted_rank_dict
    )
    await services.async_save_address_ranks(address_ranks, session)
