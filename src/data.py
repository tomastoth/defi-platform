from datetime import datetime

import pydantic

from src import enums


class UsdValue(pydantic.BaseModel):
    value_usd: float


class PctValue(pydantic.BaseModel):
    value_pct: float


class Address(pydantic.BaseModel):
    address: str
    blockchain_type: enums.BlockchainType = pydantic.Field(
        default=enums.BlockchainType.EVM
    )

    def __hash__(self):
        return hash(f"{self.address}_{self.blockchain_type}")


class AggregatedUsdAsset(UsdValue):
    symbol: str
    amount: float
    price: float


class AggregatedAsset(AggregatedUsdAsset, PctValue):
    timestamp: int


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


class AddressPerformanceRank(pydantic.BaseModel):
    address: Address
    ranking_type: enums.AddressRankingType
    time: datetime
    avg_performance: float
    rank: int
