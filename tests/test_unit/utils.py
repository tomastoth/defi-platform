from datetime import datetime
from unittest import mock

import dotenv
import pytest
from defi_common.database import db, models
from defi_common.dbconfig import db_config
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data
from tests.test_unit.fixtures import model_address  # noqa


def create_aggregated_update(
        value_usd: float, amount: float, price: float, value_pct: float,
        symbol: str = "ETH"
) -> data.AddressUpdate:
    return data.AddressUpdate(
        value_usd=value_usd,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol=symbol,
                amount=amount,
                price=price,
                timestamp=101,
                value_pct=value_pct,
                value_usd=value_usd,
            )
        ],
    )


def create_aggregated_usd_asset(
        symbol: str,
        amount: float,
        price: float,
        value_usd: float,
) -> data.AggregatedUsdAsset:
    return data.AggregatedUsdAsset(
        symbol=symbol,
        amount=amount,
        price=price,
        value_usd=value_usd,
    )


def create_aggregated_asset(
        symbol: str,
        amount: float,
        price: float,
        value_pct: float,
        value_usd: float,
        timestamp: int = 101,
) -> data.AggregatedAsset:
    return data.AggregatedAsset(
        symbol=symbol,
        amount=amount,
        price=price,
        timestamp=timestamp,
        value_pct=value_pct,
        value_usd=value_usd,
    )


@pytest.mark.asyncio
async def test_database_session() -> orm.sessionmaker:
    dotenv.load_dotenv()
    engine = sql_asyncio.create_async_engine(db_config.test_db_url, echo=True)
    async with engine.begin() as conn:
        db.Base.metadata.bind = conn
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)
    async_session = orm.sessionmaker(
        engine, class_=sql_asyncio.AsyncSession, expire_on_commit=False
    )
    return async_session


def mock_finding_address(model_address: models.Address) -> mock.AsyncMock:
    session = mock.AsyncMock()
    find_mock = mock.MagicMock()
    session.execute.return_value = find_mock
    find_mock.scalars.return_value.first.return_value = model_address
    return session


def create_datetime(
        year: int = 2022,
        month: int = 1,
        day: int = 1,
        hour: int = 1,
        minute: int = 1,
        second: int = 1,
) -> datetime:
    return datetime(
        year=year, month=month, day=day, hour=hour, minute=minute, second=second
    )
