from datetime import timedelta, datetime

from defi_common.enums import Blockchain

from src.moralis_utils import TokenInfo
from src.token_balances.token_history import (
    create_time_data,
    TimeType,
    TokenHistory,
    TransactionProvider,
    Transaction,
)
from tests.test_unit.utils import create_datetime


def test_creating_hourly_data():
    start_time = create_datetime(year=2022, month=1, day=1, hour=0, minute=0, second=0)
    end_time = create_datetime(year=2022, month=1, day=1, hour=10, minute=0, second=0)
    time_data = create_time_data(
        time_type=TimeType.HOUR, start_time=start_time, end_time=end_time
    )
    after_start_time = start_time + timedelta(hours=1)
    assert after_start_time in time_data
    assert start_time in time_data
    assert end_time in time_data
    after_time = end_time + timedelta(minutes=1)
    before_time = end_time - timedelta(minutes=1)
    assert after_time not in time_data
    assert before_time not in time_data


def test_creating_daily_data():
    start_time = create_datetime(year=2022, month=1, day=1, hour=0, minute=0, second=0)
    end_time = create_datetime(year=2022, month=1, day=10, hour=0, minute=0, second=0)
    time_data = create_time_data(
        time_type=TimeType.DAY, start_time=start_time, end_time=end_time
    )
    after_start_time = start_time + timedelta(days=1)
    after_time = end_time + timedelta(minutes=1)
    before_time = start_time - timedelta(minutes=1)
    assert before_time not in time_data
    assert after_time not in time_data
    assert start_time in time_data
    assert after_start_time in time_data
    assert end_time in time_data


def test_backfilling_daily_data():
    """
    Tests backfilling of token balance for address
    """
    first_tx_time = datetime(2022, 1, 1)
    second_tx_time = first_tx_time + timedelta(days=2)
    token_info = TokenInfo(symbol="test", decimals=18, address="0x123")

    class TestTransactionProvider(TransactionProvider):
        def get_transactions(
            self, address: str, blockchain: Blockchain
        ) -> list[Transaction]:
            first_transaction = Transaction(
                token_info=token_info,
                amount_divided=1.0,
                tx_time=first_tx_time,
                sender="0xsender",
                receiver="0xreceiver",
                is_receiver=True,
            )
            second_transaction = Transaction(
                token_info=token_info,
                amount_divided=1.0,
                tx_time=second_tx_time,
                sender="0xsender",
                receiver="0xreceiver",
                is_receiver=True,
            )
            return [first_transaction, second_transaction]

    th = TokenHistory(TestTransactionProvider())
    time_data = th.get_historical_balances(
        address="0xreceiver", time_type=TimeType.DAY, blockchain=Blockchain.ETH
    )
    middle_date = first_tx_time + timedelta(days=1)
    assert time_data[first_tx_time].get(token_info) == 1
    assert time_data[middle_date].get(token_info) == 1
    assert time_data[second_tx_time].get(token_info) == 2
