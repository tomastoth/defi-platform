from datetime import datetime

import pydantic

from src import enums, time_utils


class UsdValue(pydantic.BaseModel):
    value_usd: float


class PctValue(pydantic.BaseModel):
    value_pct: float


class Address(pydantic.BaseModel):
    address: str
    blockchain_type: enums.BlockchainType = pydantic.Field(
        default=enums.BlockchainType.EVM
    )


class AggregatedUsdAsset(UsdValue):
    symbol: str
    amount: float
    price: float


class AggregatedAsset(AggregatedUsdAsset, PctValue):
    timestamp: int = pydantic.Field(default=time_utils.get_time_now())


class BlockchainAsset(UsdValue):
    symbol: str
    amount: float
    blockchain: enums.Blockchain
    price: float


class AddressUpdate(UsdValue):
    blockchain_wallet_assets: list[BlockchainAsset]
    aggregated_assets: list[AggregatedAsset]


class PerformanceResult(pydantic.BaseModel):
    performance: float
    end_time: datetime
    start_time: datetime
    address: Address
