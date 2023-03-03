from datetime import datetime, timedelta

import pytest

from src.token_balances.transpose_all.data import SingleTrade
from src.token_balances.transpose_all.trader_backtest import TraderBacktest


@pytest.fixture
def trader_backtest() -> TraderBacktest:
    return TraderBacktest()


def create_single_trade(size_coin: float, price: float, size_eth: float, timestamp: datetime, symbol: str = "XYZ",
                        coin_address: str = "0x123", is_buy: bool = True) -> SingleTrade:
    return SingleTrade(
        timestamp=timestamp.isoformat(),
        size_coin=size_coin,
        size_eth=size_eth,
        price=price,
        symbol=symbol,
        is_buy=is_buy,
        coin_address=coin_address
    )


def test_trader_backtest_buys(trader_backtest):
    backtest_start_time = datetime(2023, 1, 1, 1, 1, 1)
    first_buy = create_single_trade(
        size_coin=10.0,
        price=1.0,
        size_eth=0.1,
        symbol="XYZ",
        coin_address="0x123",
        is_buy=True,
        timestamp=backtest_start_time
    )
    second_buy = create_single_trade(
        size_coin=10.0,
        price=2.0,
        size_eth=0.2,
        symbol="XYZ",
        coin_address="0x123",
        is_buy=True,
        timestamp=backtest_start_time + timedelta(minutes=2)
    )
    trader_backtest.on_trade(first_buy)
    assert trader_backtest.get_current_avg_price_of_coin(first_buy.coin_address) == 1.0
    assert trader_backtest.get_current_size_of_coin(first_buy.coin_address) == 10.0
    trader_backtest.on_trade(second_buy)
    assert trader_backtest.get_current_avg_price_of_coin(first_buy.coin_address) == 1.5
    assert trader_backtest.get_current_size_of_coin(first_buy.coin_address) == 20.0
    first_sell = create_single_trade(
        size_coin=10.0,
        price=3.0,
        size_eth=0.2,
        symbol="XYZ",
        coin_address="0x123",
        is_buy=False,
        timestamp=backtest_start_time + timedelta(minutes=4)
    )
    trader_backtest.on_trade(first_sell)
    assert trader_backtest.get_profit() == 15.0
    assert trader_backtest.get_current_size_of_coin(first_buy.coin_address) == 10
