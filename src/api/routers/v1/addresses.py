from defi_common import time_utils
from defi_common.data import Address
from defi_common.enums import Blockchain
from fastapi import APIRouter

from src.token_balances.zapper import ZapperAssetProvider

router = APIRouter(prefix="/addresses")
zapper = ZapperAssetProvider()

@router.get("/{address}/historical")
async def get_historical_balances(
        address: str,
        blockchain: Blockchain,
        token_address: str,
        start_time: str,
        end_time: str,
):
    pass


@router.get("/{address}")
async def get_address(address: str):
    address_data = Address(address=address)
    return await zapper.async_get_assets_for_address(address_data,time_utils.get_time_now())