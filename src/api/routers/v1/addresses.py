import time
from datetime import datetime

from defi_common.data import Address
from defi_common.database.db import get_session
from defi_common.enums import Blockchain
from defi_common.time_utils import get_time_now
from fastapi import APIRouter

from src.aggregated_assets import async_provide_aggregated_assets

router = APIRouter(prefix="/addresses")


@router.get("/{address}")
async def get_address_info(address: str):
    address_data = Address(address=address)
    aggregated_assets = await async_provide_aggregated_assets(address=address_data,
                                          run_timestamp=get_time_now())

    return {"address": aggregated_assets}
