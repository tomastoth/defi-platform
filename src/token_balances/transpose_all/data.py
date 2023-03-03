import inspect
from dataclasses import dataclass


@dataclass
class TraderExport:
    number_of_trades: int
    traded_eth: float
    average_eth_size: float
    trades: list["ProfitTrade"]
    sum_profit: float

    def __str__(self) -> str:
        return f"avg_profi: {self.sum_profit}, trades: {self.number_of_trades}, traded_eth: {self.traded_eth}," \
               f"avg_eth_size: {self.average_eth_size}"

    def __repr__(self) -> str:
        return self.__str__()


@dataclass
class TradesInfo:
    average_price: float
    number_of_trades: int
    traded_eth: float
    average_eth: float
    trades: list["SingleTrade"]


@dataclass
class Swap:
    from_token_address: str
    to_token_address: str
    quantity_in: int
    quantity_out: int
    timestamp: int

    @classmethod
    def from_dict(cls, env):
        return cls(
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )


@dataclass
class SingleTrade:
    timestamp: str
    size_coin: float
    size_eth: float
    price: float
    symbol: str
    is_buy: bool
    coin_address: str | None = None


@dataclass
class ProfitTrade(SingleTrade):
    profit: float | None = None
