import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext import asyncio as sql_asyncio
from sqlalchemy.orm import sessionmaker

import src  # noqa
import src.token_balances.nasnen_portfolio
from src import (
    coin_changes,
    performance,
    spec,
)
from src.token_balances import aggregated_assets, zapper
from defi_common.database import services
from defi_common import data, enums, time_utils

log = logging.getLogger(__name__)


async def async_calculate_address_performance(
    address: data.Address,
    last_aggregated_time: float,
    last_aggregated_updates: list[data.AggregatedAsset],
    new_aggregated_updates: list[data.AggregatedAsset],
    performances: list[data.PerformanceResult],
    current_datetime: datetime,
) -> None:
    performance_result = performance.calculate_performance(
        old_address_updates=last_aggregated_updates,
        new_address_updates=new_aggregated_updates,
        start_time=time_utils.get_datetime_from_ts(last_aggregated_time),
        end_time=current_datetime,
        address=address,
    )
    performances.append(performance_result)


async def async_save_aggregated_assets_for_address(
    address: data.Address,
    session: sql_asyncio.AsyncSession,
    new_aggregated_updates: list[data.AggregatedAsset],
) -> None:
    for aggregated_asset in new_aggregated_updates:
        await services.async_save_aggregated_update(aggregated_asset, address, session)


async def async_run_single_address(
    address: data.Address,
    performances: list[data.PerformanceResult],
    run_time_dt: datetime,
    session: sql_asyncio.AsyncSession,
    provide_assets: spec.AssetProvider,
    current_time: int,
) -> None:
    log.info(f"Updating address: {address.address}")
    last_aggregated_updates: list[
        data.AggregatedAsset
    ] = await services.async_find_address_last_aggregated_updates(address, session)
    address_update = await provide_assets(address, current_time)
    if not address_update:
        log.warning(
            f"Could not fetch last agg updates for address: {address}, skipping update"
        )
        return
    new_aggregated_updates = address_update.aggregated_assets
    await async_save_aggregated_assets_for_address(
        address=address, new_aggregated_updates=new_aggregated_updates, session=session
    )
    if not last_aggregated_updates:
        log.warning(
            f"Could not find last agg updates for address: {address}, skipping performance"
        )
        return

    last_aggregated_time = last_aggregated_updates[0].timestamp
    await async_calculate_address_performance(
        address,
        last_aggregated_time,
        last_aggregated_updates,
        new_aggregated_updates,
        performances,
        run_time_dt,
    )


async def async_update_all_addresses(
    session_maker: sessionmaker,
    provide_assets: spec.AssetProvider = zapper.async_provide_aggregated_assets,
    sleep_time: int = 15,
) -> None:
    async with session_maker() as session:
        run_time = time_utils.get_time_now()
        run_time_dt = time_utils.get_datetime_from_ts(run_time)
        addresses_models = await services.async_find_all_addresses(session)
        addresses = [
            services.convert_address_model(address_model)
            for address_model in addresses_models
        ]
        performances: list[data.PerformanceResult] = []
        for address in addresses:
            await async_run_single_address(
                address=address,
                performances=performances,
                provide_assets=provide_assets,
                run_time_dt=run_time_dt,
                session=session,
                current_time=run_time,
            )

            await asyncio.sleep(sleep_time)
        [
            await services.async_save_performance_result(single_performance, session)
            for single_performance in performances
        ]


async def async_run_address_ranking(
    time_type: enums.RunTimeType,
    session_maker: sessionmaker,
    current_time: datetime | None = None,
) -> None:
    if not current_time:
        current_time = datetime.now()
    async with session_maker() as session:
        await performance.async_save_address_ranking(
            ranking_type=time_type,
            session=session,
            run_time=current_time,
        )


async def async_run_coin_change_ranking(
    time_type: enums.RunTimeType,
    session_maker: sessionmaker,
    current_time: datetime | None = None,
) -> None:
    if not current_time:
        current_time = datetime.now()
    async with session_maker() as session:
        await coin_changes.async_run_coin_ranking(time_type, current_time, session)
