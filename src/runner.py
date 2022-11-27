import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, debank, performance, spec, time_utils
from src.database import services

log = logging.getLogger(__name__)


async def async_calculate_address_performance(
    address: data.Address,
    last_aggregated_time: float,
    last_aggregated_updates: list[data.AggregatedAsset],
    new_aggregated_updates: list[data.AggregatedAsset],
    performances: list[data.PerformanceResult],
    run_time_dt: datetime,
) -> None:
    performance_result = performance.calculate_performance(
        old_address_updates=last_aggregated_updates,
        new_address_updates=new_aggregated_updates,
        start_time=time_utils.get_datetime_from_ts(last_aggregated_time),
        end_time=run_time_dt,
        address=address,
    )
    performances.append(performance_result)


async def async_save_aggregated_assets_for_address(
    address: data.Address,
    new_aggregated_updates: list[data.AggregatedAsset],
    session: sql_asyncio.AsyncSession,
) -> None:
    for aggregated_asset in new_aggregated_updates:
        await services.async_save_aggregated_update(aggregated_asset, address, session)


async def async_run_single_address(
    address: data.Address,
    performances: list[data.PerformanceResult],
    run_time_dt: datetime,
    session: sql_asyncio.AsyncSession,
    provide_assets: spec.AssetProvider,
    run_time: int,
) -> None:
    log.info(f"Updating address: {address.address}")
    last_aggregated_updates: list[
        data.AggregatedAsset
    ] = await services.async_find_address_last_aggregated_updates(address, session)
    address_update = await provide_assets(address, run_time)
    if not address_update:
        log.warning(
            f"Could not fetch last agg updates for address: {address}, skipping update"
        )
        return
    new_aggregated_updates = address_update.aggregated_assets
    await async_save_aggregated_assets_for_address(
        address, new_aggregated_updates, session
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
    session: sql_asyncio.AsyncSession,
    provide_assets: spec.AssetProvider = debank.async_provide_aggregated_assets,
) -> None:
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
            run_time=run_time,
        )

        await asyncio.sleep(15)
    [
        await services.async_save_performance_result(single_performance, session)  # type: ignore
        for single_performance in performances
    ]
