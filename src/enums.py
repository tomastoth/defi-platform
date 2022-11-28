import enum


class Blockchain(str, enum.Enum):
    ETH = "Ethereum"
    AVAX = "Avax"
    DFK = "Dfk"
    BSC = "Bsc"
    FTM = "Fantom"
    MATIC = "Polygon"
    ARB = "Arbitrum"


class BlockchainType(str, enum.Enum):
    EVM = "EVM"


class AddressRankingType(str, enum.Enum):
    HOUR = "HOUR"
