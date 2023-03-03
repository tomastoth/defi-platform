from typing import Optional

from defi_common.database.models import Blockchain
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def find_blockchain(name: str, session: AsyncSession) -> Blockchain | None:
    sel = select(Blockchain).where(Blockchain.name == name)
    exec = await session.execute(sel)
    return exec.scalars().first()
