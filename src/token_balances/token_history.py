import asyncio
import math
from typing import Optional

import dotenv

dotenv.load_dotenv()
from abc import abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import pytz
from defi_common.enums import Blockchain
from transpose import Transpose

from src.moralis_utils import TokenInfoProvider, MoralisTokenInfoProvider, TokenInfo


@dataclass
class TokenBalance:
    amount: float
    time: datetime


@dataclass
class TransactionBalancesExport:
    start_time: datetime
    end_time: datetime
    token_balances: dict[TokenInfo, list[TokenBalance]]


@dataclass
class Transaction:
    token_info: TokenInfo
    amount_divided: float
    tx_time: datetime
    sender: str
    receiver: str
    is_receiver: bool

    @property
    def token_address(self):
        return self.token_info.address


class TimeType(Enum):
    HOUR = 0
    DAY = 1


class TransactionProvider(ABC):
    @abstractmethod
    def get_transactions(
            self, address: str, blockchain: Blockchain
    ) -> list[Transaction]:
        pass


class TransposeTransactionProvder(TransactionProvider):
    def __init__(self, token_decimals_provider: TokenInfoProvider):
        self._transpose = Transpose(api_key="hU9huB4anD8oHD0He9cKswXrXPY6idXX")
        self._token_decimals_provider = token_decimals_provider

    def _extract_transaction(
            self, transaction, wanted_address: str, blockchain: Blockchain = Blockchain.ETH
    ) -> Optional[Transaction]:
        contract_address = transaction.contract_address
        receiver = transaction.to
        amount = transaction.quantity
        token_info = self._token_decimals_provider.get_token_info(
            contract_address, blockchain
        )
        if not token_info:
            return None
        decimals = token_info.decimals
        amount_divded = amount / math.pow(10, decimals) if decimals > 0 else amount
        tx_time = datetime.fromisoformat(transaction.timestamp).replace(tzinfo=pytz.UTC)
        is_receiving = receiver.lower() == wanted_address.lower() if receiver else False
        return Transaction(
            token_info=token_info,
            tx_time=tx_time,
            receiver=receiver,
            sender=transaction["from"],
            is_receiver=is_receiving,
            amount_divided=amount_divded,
        )

    def get_transactions(
            self, address: str, blockchain: Blockchain
    ) -> list[Transaction]:
        all_transactions = []
        last_received_time = None
        while True:
            if not last_received_time:
                new_transactions = self._transpose.token.transfers_by_account(
                    address, limit=500
                )
            else:
                new_transactions = self._transpose.token.transfers_by_account(
                    address, transferred_after=last_received_time, limit=500
                )
            all_transactions.extend(new_transactions)
            if not new_transactions or len(new_transactions) == 1:
                break
            last_received_time = all_transactions[-1].timestamp
        extracted_transactions = []
        for tx in all_transactions:
            extracted_transaction = self._extract_transaction(tx, address, blockchain)
            if extracted_transaction:
                extracted_transactions.append(extracted_transaction)
        return extracted_transactions


def round_time(time_to_format: datetime, time_type: TimeType) -> datetime:
    match time_type:
        case TimeType.HOUR:
            return time_to_format.replace(minute=0, second=0)
        case TimeType.DAY:
            return time_to_format.replace(hour=0, minute=0, second=0)


def create_time_data(
        time_type: TimeType, start_time: datetime, end_time: datetime
) -> dict[datetime, dict[any, any]]:
    time_data = dict[datetime, dict[any, any]]()
    current_time = start_time
    time_data[current_time] = {}
    time_to_add = (
        timedelta(hours=1) if time_type == TimeType.HOUR else timedelta(days=1)
    )
    while current_time < end_time:
        current_time += time_to_add
        time_data[current_time] = {}
    return time_data


class TokenHistory:
    start_time = datetime(year=2500, month=1, day=1)  # can't use max
    end_time = datetime(year=2000, month=1, day=1)

    def __init__(self, transaction_provider: TransactionProvider):
        self._transaction_provider = transaction_provider

    def _calculate_historical_balances(
            self, all_transactions: list[Transaction], time_type: TimeType
    ) -> TransactionBalancesExport:
        token_states: dict[TokenInfo, list[TokenBalance]] = dict[
            TokenInfo, list[TokenBalance]
        ]()
        for transaction in all_transactions:
            token_info = transaction.token_info
            if transaction.tx_time.timestamp() < self.start_time.timestamp():
                self.start_time = transaction.tx_time
            else:
                if transaction.tx_time.timestamp() > self.end_time.timestamp():
                    self.end_time = transaction.tx_time
            if token_info not in token_states:
                token_states[token_info] = []
                first_token_balance = TokenBalance(
                    transaction.amount_divided,
                    transaction.tx_time,
                )
                token_states[token_info].append(first_token_balance)
                continue

            last_update = token_states[token_info][-1]
            if transaction.is_receiver:
                new_amount = last_update.amount + transaction.amount_divided
            else:
                new_amount = last_update.amount - transaction.amount_divided
                # assert int(new_amount) >= 0
            new_token_balance = TokenBalance(
                amount=new_amount,
                time=transaction.tx_time,
            )
            token_states[token_info].append(new_token_balance)
        rounded_start_time = round_time(self.start_time, time_type)
        rounded_end_time = round_time(self.end_time, time_type)
        return TransactionBalancesExport(
            rounded_start_time, rounded_end_time, token_states
        )

    def _backfill_balances(
            self, time_data: dict[datetime, dict[TokenInfo, float]]
    ) -> dict[datetime, dict[TokenInfo, float]]:
        last_balances = dict()
        for day, daily_data in time_data.items():
            for last_token, last_balance in last_balances.items():
                if last_token not in daily_data:
                    daily_data[last_token] = last_balance
            for token, amount in daily_data.items():
                last_balances[token] = amount
        return time_data

    def get_historical_balances(
            self, address: str, time_type: TimeType, blockchain: Blockchain = Blockchain.ETH
    ) -> dict[datetime, dict[TokenInfo, float]]:
        all_transactions = self._transaction_provider.get_transactions(
            address, blockchain=blockchain
        )
        token_balances_export = self._calculate_historical_balances(
            all_transactions, time_type
        )
        time_data = create_time_data(
            time_type, token_balances_export.start_time, token_balances_export.end_time
        )
        history = self.add_coin_balances_at_time(
            token_balances_export.token_balances, time_data, time_type
        )
        return self._backfill_balances(history)

    def add_coin_balances_at_time(
            self,
            token_balances: dict[TokenInfo, list[TokenBalance]],
            time_data: dict[datetime, dict[TokenInfo, float]],
            time_type: TimeType,
    ) -> dict[datetime, dict[TokenInfo, float]]:
        for symbol, balances in token_balances.items():
            balances.reverse()
            for balance in balances:
                rounded_time = round_time(balance.time, time_type)
                assert rounded_time in time_data
                coins_updates_at_time = time_data[rounded_time]
                if symbol not in coins_updates_at_time:
                    coins_updates_at_time[symbol] = balance.amount
        return time_data


async def main():
    moralis = MoralisTokenInfoProvider()
    transaction_provider = TransposeTransactionProvder(moralis)
    token_history = TokenHistory(transaction_provider)
    time_type = TimeType.DAY
    address = "0x7ec49f1e1a02708b1b82bc804e65abe9ed5ca1e3"
    blockchain = Blockchain.ETH
    transactions = transaction_provider.get_transactions(address, blockchain)
    match_transactions(transactions)
    # token_balances_export = token_history.get_historical_balances(
    #     address, time_type=time_type
    # )
    # print(token_balances_export)
    # async with async_session() as session:
    #     with session.no_autoflush:
    #         await save_address_historical_balances(
    #             address, blockchain, session, token_balances_export
    #         )


if __name__ == "__main__":
    asyncio.run(main())
