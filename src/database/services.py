from datetime import datetime

import sqlalchemy
from defi_common.database import models
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums, exceptions, time_utils
from src.exceptions import AddressAlreadyExistsError, AddressNotCreatedError


async def async_find_address(
    address: data.Address, session: sql_asyncio.AsyncSession
) -> models.Address | None:
    lower_address = address.address.lower()
    query = sqlalchemy.select(models.Address).where(
        models.Address.address == lower_address,
        models.Address.blockchain_type == str(address.blockchain_type.value),
    )
    found = await session.execute(query)
    return found.scalars().first()


async def async_save_address(
    address: data.Address, session: sql_asyncio.AsyncSession
) -> None:
    address_model = models.Address(
        address=address.address, blockchain_type=str(address.blockchain_type.value)
    )
    existing_address = await async_find_address(address, session)
    if existing_address:
        raise AddressAlreadyExistsError()
    session.add(address_model)
    await session.commit()


async def async_save_aggregated_update(
    update: data.AggregatedAsset,
    address: data.Address,
    session: sql_asyncio.AsyncSession,
) -> None:
    existing_address = await async_find_address(address, session)
    if not existing_address:
        await async_save_address(address, session)
        existing_address = await async_find_address(address, session)
    if not existing_address:
        raise AddressNotCreatedError()
    update_model = models.AggregatedBalanceUpdate(
        symbol=update.symbol,
        amount=update.amount,
        price=update.price,
        value_usd=update.value_usd,
        value_pct=update.value_pct,
        timestamp=update.timestamp,
        time=time_utils.get_datetime_from_ts(update.timestamp),
        address=existing_address,
        address_id=existing_address.id,
    )
    session.add(update_model)
    await session.commit()


async def async_find_all_addresses(
    session: sql_asyncio.AsyncSession,
) -> list[models.Address]:
    query = sqlalchemy.select(models.Address)
    execute = await session.execute(query)
    return execute.scalars().all()  # type: ignore


def convert_address_model(address_model: models.Address) -> data.Address:
    return data.Address(
        address=address_model.address,
        blockchain_type=enums.BlockchainType(address_model.blockchain_type),
    )


async def async_find_all_converted_addresses(
    session: sql_asyncio.AsyncSession,
) -> list[data.Address]:
    return [
        convert_address_model(address)
        for address in await async_find_all_addresses(session)
    ]


def convert_aggregated_model(
    aggregated_balance_model: models.AggregatedBalanceUpdate,
) -> data.AggregatedAsset:
    return data.AggregatedAsset(
        symbol=aggregated_balance_model.symbol,
        value_pct=aggregated_balance_model.value_pct,
        value_usd=aggregated_balance_model.value_usd,
        amount=aggregated_balance_model.amount,
        price=aggregated_balance_model.price,
        timestamp=aggregated_balance_model.timestamp,
    )


async def async_find_address_last_aggregated_updates(
    address: data.Address, session: sql_asyncio.AsyncSession
) -> list[data.AggregatedAsset]:
    address_model = await async_find_address(address, session)
    if not address_model:
        raise exceptions.AddressNotFoundError()
    last_update_query = (
        sqlalchemy.select(models.AggregatedBalanceUpdate)
        .where(models.AggregatedBalanceUpdate.address_id == address_model.id)
        .order_by(models.AggregatedBalanceUpdate.timestamp.desc())
        .limit(1)
    )
    last_update_exec = await session.execute(last_update_query)
    last_update: models.AggregatedBalanceUpdate = last_update_exec.scalars().first()
    if not last_update:
        return []
    last_update_time = last_update.timestamp
    all_last_time_query = sqlalchemy.select(models.AggregatedBalanceUpdate).where(
        models.AggregatedBalanceUpdate.timestamp == last_update_time,
        models.AggregatedBalanceUpdate.address_id == address_model.id,
    )
    all_last_time_exec = await session.execute(all_last_time_query)
    unconverted = all_last_time_exec.scalars().all()
    return [convert_aggregated_model(model) for model in unconverted]


async def async_find_aggregated_updates(
    address: data.Address, at_time: datetime, session: sql_asyncio.AsyncSession
) -> list[data.AggregatedAsset]:
    address_model = await async_find_address(address, session)
    if not address_model:
        raise exceptions.AddressNotFoundError()
    update_time_closest_to_wanted_time_query = (
        sqlalchemy.select(models.AggregatedBalanceUpdate)
        .where(models.AggregatedBalanceUpdate.timestamp <= at_time.timestamp())
        .order_by(models.AggregatedBalanceUpdate.timestamp.desc())
        .limit(1)
    )

    time_exec = await session.execute(update_time_closest_to_wanted_time_query)
    time_update = time_exec.scalars().first()
    if not time_update:
        return []
    wanted_time = time_update.timestamp
    updates_query = sqlalchemy.select(models.AggregatedBalanceUpdate).where(
        models.AggregatedBalanceUpdate.address_id == address_model.id,
        models.AggregatedBalanceUpdate.timestamp == wanted_time,
    )
    updates_exec = await session.execute(updates_query)
    return [convert_aggregated_model(model) for model in updates_exec.scalars().all()]


async def async_save_performance_result(
    performance_data: data.PerformanceResult, session: sql_asyncio.AsyncSession
) -> None:
    address_model = await async_find_address(performance_data.address, session)
    performance_model = models.PerformanceRunResult(
        time_created=datetime.now(),
        time_updated=datetime.now(),
        start_time=performance_data.start_time,
        end_time=performance_data.end_time,
        address=address_model,
        performance=performance_data.performance,
    )
    session.add(performance_model)
    await session.commit()


def convert_performance_model(
    performance_model: models.PerformanceRunResult,
) -> data.PerformanceResult:
    address = convert_address_model(performance_model.address)
    return data.PerformanceResult(
        performance=performance_model.performance,
        end_time=performance_model.end_time,
        start_time=performance_model.start_time,
        address=address,
    )


async def async_find_performance_results(
    address: data.Address,
    start_datetime: datetime,
    end_datetime: datetime,
    session: sql_asyncio.AsyncSession,
) -> list[data.PerformanceResult]:
    model_address = await async_find_address(address, session)
    if not model_address:
        raise exceptions.AddressNotFoundError()
    query = sqlalchemy.select(models.PerformanceRunResult).where(
        models.PerformanceRunResult.address_id == model_address.id,
        models.PerformanceRunResult.start_time >= start_datetime,
        models.PerformanceRunResult.end_time <= end_datetime,
    )
    exec_stmt = await session.execute(query)

    performance_models = exec_stmt.scalars().all()
    return [
        convert_performance_model(performance_model)
        for performance_model in performance_models
    ]


def convert_address_rank_model(
    rank_model: models.AddressPerformanceRank,
) -> data.AddressPerformanceRank:
    return data.AddressPerformanceRank(
        address=convert_address_model(rank_model.address),
        ranking_type=enums.RunTimeType(rank_model.ranking_type),
        time=rank_model.time,
        avg_performance=rank_model.performance,
        rank=rank_model.rank,
    )


async def async_find_address_rankings(
    ranking_type: enums.RunTimeType,
    time: datetime,
    session: sql_asyncio.AsyncSession,
) -> list[data.AddressPerformanceRank]:
    query = sqlalchemy.select(models.AddressPerformanceRank).where(
        models.AddressPerformanceRank.time == time,
        models.AddressPerformanceRank.ranking_type == ranking_type.value,
    )
    query_exec = await session.execute(query)
    rank_models = query_exec.scalars().all()
    return [convert_address_rank_model(rank_model) for rank_model in rank_models]


async def async_convert_address_rank_to_model(
    address_rank: data.AddressPerformanceRank, session: sql_asyncio.AsyncSession
) -> models.AddressPerformanceRank:
    model_address = await async_find_address(address_rank.address, session)
    if not model_address:
        raise exceptions.AddressNotFoundError()
    return models.AddressPerformanceRank(
        performance=address_rank.avg_performance,
        time=address_rank.time,
        address=model_address,
        address_id=model_address.id,
        ranking_type=str(address_rank.ranking_type.value),
        rank=address_rank.rank,
    )


async def async_save_address_ranks(
    address_ranks: list[data.AddressPerformanceRank], session: sql_asyncio.AsyncSession
) -> None:
    rank_models = [
        await async_convert_address_rank_to_model(address_rank, session)
        for address_rank in address_ranks
    ]
    session.add_all(rank_models)
    await session.commit()


async def async_save_coin_changes(
    coin_changes_list: list[data.AssetOwnedChange],
    save_time: datetime,
    run_time_type: enums.RunTimeType,
    session: sql_asyncio.AsyncSession,
) -> None:
    to_save: list[models.CoinChangeRank] = []
    for coin_change in coin_changes_list:
        coin_change_rank = models.CoinChangeRank(
            rank=coin_change.rank,
            time=save_time,
            pct_change=coin_change.pct_change,
            ranking_type=run_time_type.value,
            symbol=coin_change.symbol,
        )
        to_save.append(coin_change_rank)
    session.add_all(to_save)
    await session.commit()


def convert_coin_change_model(model: models.CoinChangeRank) -> data.AssetOwnedChange:
    return data.AssetOwnedChange(
        rank=model.rank,
        symbol=model.symbol,
        pct_change=model.pct_change,
        run_type=enums.RunTimeType(model.ranking_type),
        time=model.time,
    )


async def async_find_coin_ranking_by_time(
    at_time: datetime, session: sql_asyncio.AsyncSession
) -> list[data.AssetOwnedChange]:
    query = sqlalchemy.select(models.CoinChangeRank).where(
        models.CoinChangeRank.time == at_time
    )
    coin_change_exec = await session.execute(query)
    coin_rank_models = coin_change_exec.scalars().all()
    return [convert_coin_change_model(model) for model in coin_rank_models]
