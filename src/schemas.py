import pydantic

from src import enums


class UsdValue(pydantic.BaseModel):
    value_usd: float


class Address(pydantic.BaseModel):
    address: str


class AggregatedAssetUsd(UsdValue):
    symbol: str
    amount: float


class BlockchainAsset(AggregatedAssetUsd):
    symbol: str
    amount: float
    blockchain: enums.Blockchain
    price: float


class AssetPct(pydantic.BaseModel):
    symbol: str
    value_pct: float


class AddressUpdate(UsdValue):
    assets_blockchain: list[BlockchainAsset]
    assets_pct: list[AssetPct]
    assets_usd: list[AggregatedAssetUsd]
