import logging
from datetime import datetime

import sqlalchemy.ext.asyncio as sql_asyncio
from defi_common.database import services

import src  # noqa
from defi_common import data, enums, time_utils
from defi_common.data import AssetOwnedChange
from defi_common.time_utils import get_times_for_comparison

log = logging.getLogger(__name__)


def _agg_update_list_to_dict(
    updates: list[data.AggregatedAsset],
) -> dict[str, data.AggregatedAsset]:
    result = {}
    for update in updates:
        result[update.symbol] = update
    return result


def _add_sum_value_to_dict(
    symbol: str, value: float, dict_to_edit: dict[str, float]
) -> None:
    if symbol not in dict_to_edit:
        dict_to_edit[symbol] = 0
    dict_to_edit[symbol] += value


async def _async_fetch_aggregated_updates(
    address: data.Address,
    end_time: datetime,
    session: sql_asyncio.AsyncSession,
    start_time: datetime,
) -> tuple[list[data.AggregatedAsset], list[data.AggregatedAsset]]:
    first_updates = await services.async_find_aggregated_updates(
        address, start_time, session
    )
    second_updates = await services.async_find_aggregated_updates(
        address, end_time, session
    )
    return first_updates, second_updates


def _create_asset_owned_changes(
    sorted_coin_changes: dict[str, float],
    end_time: datetime,
    run_time_type: enums.RunTimeType,
) -> list[data.AssetOwnedChange]:
    result: list[data.AssetOwnedChange] = []
    for i, (symbol, sorted_coin_change) in enumerate(sorted_coin_changes.items()):
        rank = i + 1
        result.append(
            AssetOwnedChange(
                time=end_time,
                rank=rank,
                symbol=symbol,
                pct_change=sorted_coin_change,
                run_type=run_time_type,
            )
        )
    return result


def _calculate_sorted_averaged_coin_changes(
    addresses: list[data.Address], coin_change_sums: dict[str, float]
) -> dict[str, float]:
    coin_changes_avged: dict[str, float] = {}
    for symbol, coin_change_sum in coin_change_sums.items():
        coin_changes_avged[symbol] = coin_change_sum / len(addresses)
    sorted_coin_changes: dict[str, float] = dict(
        sorted(coin_changes_avged.items(), key=lambda x: x[1], reverse=True)
    )
    return sorted_coin_changes


async def async_extract_coin_changes(
    coin_change_sums: dict[str, float],
    first_updates: list[data.AggregatedAsset],
    second_updates: list[data.AggregatedAsset],
) -> None:
    first_updates_dict = _agg_update_list_to_dict(first_updates)
    second_updates_dict = _agg_update_list_to_dict(second_updates)
    for symbol, update in first_updates_dict.items():
        first_pct = update.value_pct
        if symbol in second_updates_dict.keys():
            second_pct = second_updates_dict[symbol].value_pct
            pct_diff = second_pct - first_pct
            _add_sum_value_to_dict(symbol, pct_diff, coin_change_sums)
        else:
            negative_first_pct = -1.0 * first_pct
            _add_sum_value_to_dict(symbol, negative_first_pct, coin_change_sums)
    for symbol, _update in second_updates_dict.items():
        if symbol not in first_updates_dict.keys():
            second_pct = _update.value_pct
            _add_sum_value_to_dict(symbol, second_pct, coin_change_sums)


async def async_calculate_averaged_coin_changes(
    start_time: datetime,
    end_time: datetime,
    run_time_type: enums.RunTimeType,
    session: sql_asyncio.AsyncSession,
    addresses: list[data.Address] | None = None,
) -> list[data.AssetOwnedChange]:
    if not addresses:
        addresses = await services.async_find_all_converted_addresses(session)
    coin_change_sums: dict[str, float] = {}
    if not addresses:
        log.warning("Received empty addresses in async_calculate_average_coin_changes")
        return []
    for address in addresses:
        first_updates, second_updates = await _async_fetch_aggregated_updates(
            address, end_time, session, start_time
        )
        log.info(
            f"Coin changes, time now: {time_utils.get_time_now()}, start_time: {start_time},"
            f"end time: {end_time}"
        )
        if not first_updates or not second_updates:
            log.warning(
                f"address {address} has no first or second updates, skipping calculating coin change"
            )
            continue
        await async_extract_coin_changes(
            coin_change_sums, first_updates, second_updates
        )

    sorted_coin_changes = _calculate_sorted_averaged_coin_changes(
        addresses, coin_change_sums
    )
    return _create_asset_owned_changes(sorted_coin_changes, end_time, run_time_type)


async def async_run_coin_ranking(
    time_type: enums.RunTimeType,
    current_time: datetime,
    session: sql_asyncio.AsyncSession,
) -> None:
    start_dt, end_dt = get_times_for_comparison(time_type, current_time)
    coin_changes = await async_calculate_averaged_coin_changes(
        start_time=start_dt, end_time=end_dt, run_time_type=time_type, session=session
    )
    log.info(f"coin ranking, coin changes len: {len(coin_changes)}")
    await services.async_save_coin_changes(
        coin_changes, save_time=current_time, run_time_type=time_type, session=session
    )
    log.info(f"Saved coin ranking")
