import enum


class Blockchain(str, enum.Enum):
    ETH = "Ethereum"
    AVAX = "Avax"
    DFK = "Dfk"
    BSC = "Bsc"
    FTM = "Fantom"
    MATIC = "Polygon"
    ARB = "Arbitrum"
