from datetime import datetime

import sqlalchemy
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums, exceptions, time_utils
from src.database import models
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
    return found.scalars().first()  # type: ignore


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


def convert_address_model(address_model: models.Address) -> data.Address:
    return data.Address(
        address=address_model.address,
        blockchain_type=enums.BlockchainType(address_model.blockchain_type),
    )


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
