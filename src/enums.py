import enum


class Blockchain(str, enum.Enum):

    ETH = "Ethereum"
    AVAX = "Avax"
    DFK = "Dfk"
    BSC = "Bsc"
    FTM = "Fantom"
    MATIC = "Polygon"
    ARB = "Arbitrum"
    OPTIMISM = "Optimism"
    APTOS = "Aptos"


class BlockchainType(str, enum.Enum):
    EVM = "EVM"


class RunTimeType(str, enum.Enum):
    HOUR = "HOUR"
    DAY = "DAY"
