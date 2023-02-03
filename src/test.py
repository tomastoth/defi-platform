import asyncio

import sqlalchemy
from src.config import config # noqa
from defi_common.database import db
from defi_common.database.models import AggregatedBalanceUpdate, Address
from sqlalchemy import desc

from src.main import init_db


async def main():
    await init_db()
    async with db.async_session() as ses:
        kkt = sqlalchemy.select(AggregatedBalanceUpdate,Address) \
            .order_by(desc(AggregatedBalanceUpdate.timestamp)) \
            .limit(20)
        exec = (await ses.execute(kkt)).scalars().all()
        breakpoint()


if __name__ == '__main__':
    asyncio.run(main())
