import sqlalchemy
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data, enums
from src.database import models


class AddressAlreadyExistsError(Exception):
    pass


class AddressNotCreatedError(Exception):
    pass


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
        time=update.time_ms,
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
