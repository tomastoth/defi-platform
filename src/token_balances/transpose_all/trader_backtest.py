"""
1. Receives a list of SingleTrades, sorted by time,
    these trades can be both buy / sell trades
2. for each time T, we need to know, which coins we are currently holding, how much,
    and what is the average purchase price, this can be only done when there is the same opposite coin (ETH/USDC)
3. when there is SELL, we calculate profit from the trade in the other currency (ETH/USDC),
4. when there is new purchase of coin we are currently holding, we need to recalculate it's weighted price
"""
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from defi_common.enums import Blockchain

from src.api.core.logger import logger
from src.token_balances.transpose_all.data import SingleTrade, ProfitTrade


@dataclass
class CoinBalance:
    symbol: str
    address: str
    blockchain: Blockchain
    avg_buy_price: float
    size_held: float
    timestamp: int

    def add_new_buy(self, size_coin: float, price: float, timestamp: datetime):
        purchase_weights = {self.avg_buy_price: self.size_held}
        if price not in purchase_weights:
            purchase_weights[price] = 0
        purchase_weights[price] += size_coin
        self.avg_buy_price = self._calculate_avg_buy_price(purchase_weights)
        self.size_held += size_coin
        logger.debug(
            f"Coin: {self.symbol}, new buy, price: {price}, amt: {size_coin},"
            f" new balance: {self.size_held}, new avg_price: {self.avg_buy_price}, time: {timestamp}")

    def subtract_size(self, size_coin: float):
        if size_coin > self.size_held:
            logger.info("Would sell more than we have, probably bought more with other coin!, trimming to amt we owned")
            size_coin = self.size_held
        self.size_held -= size_coin

    def calculate_profit(self, sell_price: float, size_coin: float) -> float:
        value_spend_buying = size_coin * self.avg_buy_price
        value_paid_selling = size_coin * sell_price
        profit = value_paid_selling - value_spend_buying  # TODO we need to account fees somehow
        return profit

    def _calculate_avg_buy_price(self, purchase_weights: dict[float, float]) -> float:
        sum_weighted_price = sum({price * size for price, size in purchase_weights.items()})
        sum_weights = sum(size for size in purchase_weights.values())
        return sum_weighted_price / sum_weights


class SingleTradeReceiver(ABC):
    @abstractmethod
    def on_trade(self, single_trade: SingleTrade) -> None:
        pass


class TradesKeeper(ABC):

    @abstractmethod
    def get_all_trades(self) -> list[ProfitTrade]:
        pass


class CurrentPositionProvider(ABC):
    @abstractmethod
    def get_current_size_of_coin(self, address: str) -> float:
        pass

    @abstractmethod
    def get_current_avg_price_of_coin(self, address: str) -> float:
        pass


class ProfitProvider(ABC):
    @abstractmethod
    def get_profit(self) -> float:
        pass


class TraderBacktest(SingleTradeReceiver, CurrentPositionProvider, ProfitProvider, TradesKeeper):

    def __init__(self, running_blockchain: Blockchain = Blockchain.ETH):
        self._curent_balances: dict[str, CoinBalance] = dict()
        self._blockchain = running_blockchain
        self._sum_profit = 0
        self._trades = []
        # self._coin_states: dict[datetime, dict[str, CoinBalance]] = dict()

    def on_trade(self, single_trade: SingleTrade) -> None:
        coin_address = single_trade.coin_address
        symbol = single_trade.symbol
        timestamp = datetime.fromisoformat(single_trade.timestamp)
        price = single_trade.price
        size = single_trade.size_coin
        if single_trade.is_buy:
            if coin_address in self._curent_balances:
                self._curent_balances[coin_address].add_new_buy(size, price, single_trade.timestamp)
            else:
                self.add_new_bought_coin(coin_address, single_trade, symbol, timestamp)
                logger.debug(
                    f"Coin: {symbol}, new buy, price: {price}, amt: {size},"
                    f" new balance: {size}, new avg_price: {price}, time: {single_trade.timestamp}")
            self._trades.append(ProfitTrade(**single_trade.__dict__))
        else:
            if coin_address in self._curent_balances:
                current_coin = self._curent_balances[coin_address]
                profit = current_coin.calculate_profit(price, size)
                self._sum_profit += profit
                current_coin.subtract_size(size)
                logger.info(
                    f"Coin: {current_coin.symbol}, new sell, price:{price:.8f}, amt: {size:.8f}, profit: {profit:.8f},"
                    f" sum_profit: {self._sum_profit:.8f} new balance: {current_coin.size_held:.8f}, time: {single_trade.timestamp}")
                self._trades.append(
                    ProfitTrade(profit=profit,**single_trade.__dict__)
                )
            else:
                logger.info(f"received sell trade, don't have it in bought coins, {single_trade}")
                # if we are selling it for ETH, but didn't buy for ETH, we can't calculate profit

    def add_new_bought_coin(self, coin_address, single_trade, symbol, timestamp):
        new_coin = CoinBalance(
            symbol=symbol,
            address=coin_address,
            blockchain=self._blockchain,
            avg_buy_price=single_trade.price,
            size_held=single_trade.size_coin,
            timestamp=int(timestamp.timestamp())
        )
        self._curent_balances[coin_address] = new_coin

    def get_current_avg_price_of_coin(self, address: str) -> float:
        if address not in self._curent_balances:
            return 0
        return self._curent_balances[address].avg_buy_price

    def get_current_size_of_coin(self, address: str) -> float:
        if address not in self._curent_balances:
            return 0
        return self._curent_balances[address].size_held

    def get_profit(self) -> float:
        return self._sum_profit

    def get_all_trades(self) -> list[ProfitTrade]:
        return self._trades


if __name__ == '__main__':
    with open("./trades.pkl", "rb") as file:
        trader_info = pickle.load(file)
        trader_backtest = TraderBacktest()
        for trade in trader_info.trades:
            trader_backtest.on_trade(trade)
