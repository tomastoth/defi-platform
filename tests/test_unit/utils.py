import pytest
from sqlalchemy import orm
from sqlalchemy.ext import asyncio as sql_asyncio

from src import data
from src.config import config
from src.database import db


def create_aggregated_update(
    value_usd: float, amount: float, price: float, value_pct: float
) -> data.AddressUpdate:
    return data.AddressUpdate(
        value_usd=value_usd,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=amount,
                price=price,
                time_ms=101,
                value_pct=value_pct,
                value_usd=value_pct,
            )
        ],
    )


@pytest.mark.asyncio
async def test_database_session():
    engine = sql_asyncio.create_async_engine(config.test_db_url, echo=True)
    async with engine.begin() as conn:
        db.Base.metadata.bind = conn
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)
    async_session = orm.sessionmaker(
        engine, class_=sql_asyncio.AsyncSession, expire_on_commit=False
    )
    return async_session
