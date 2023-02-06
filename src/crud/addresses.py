from datetime import datetime

from defi_common.data import Address as AddressModel
from defi_common.database.models import Blockchain, TokenBalance
from defi_common.database.services import async_save_address, async_find_address
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud.tokens import find_token, save_token
from src.moralis_utils import TokenInfo


async def create_address(address: str, session: AsyncSession) -> None:
    address_data = AddressModel(address=address)
    await async_save_address(address_data, session)


async def save_address_historical_balances(
    address: str,
    blockchain: Blockchain,
    session: AsyncSession,
    time_data: dict[datetime, dict[TokenInfo, float]],
) -> None:
    address = AddressModel(address=address)
    address_model = await async_find_address(address, session)
    if not address_model:
        await create_address(address.address, session)
        address_model = await async_find_address(address, session)

    token_infos_to_model_ids = dict[TokenInfo, int]()
    for date, token_balances in time_data.items():
        for token_info, balance in token_balances.items():
            if token_info not in token_infos_to_model_ids:
                token_model = await find_token(address.address, blockchain, session)
                if not token_model:
                    token_model = await save_token(token_info, blockchain, session)
                token_infos_to_model_ids[token_info] = token_model.id
            token_id = token_infos_to_model_ids[token_info]
            date = date.replace(tzinfo=None)
            token_balance = TokenBalance(
                time=date,
                address_id=address_model.id,
                token_id=token_id,
                amount=balance,
            )
            session.add(token_balance)
    await session.commit()
