from typing import Optional

from defi_common.database.models import Token
from defi_common.enums import Blockchain
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.blockchains import find_blockchain
from src.moralis_utils import TokenInfo


async def find_token(
    address: str, blockchain: Blockchain, session: AsyncSession
) -> Token | None:
    blockchain = await find_blockchain(name=blockchain.value, session=session)
    sel = select(Token).where(
        Token.address == address, Token.blockchain_id == blockchain.id
    )
    exec = await session.execute(sel)
    return exec.scalars().first()


async def save_token(
    token_info: TokenInfo, blockchain: Blockchain, session: AsyncSession
) -> Token:
    blockchain_model = await find_blockchain(name=blockchain.value, session=session)
    token_model = Token(
        symbol=token_info.symbol,
        address=token_info.address,
        blockchain_id=blockchain_model.id,
        blockchain=blockchain_model,
        decimals=token_info.decimals,
    )

    session.add(token_model)
    await session.commit()
    return token_model
