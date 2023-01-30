from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from transpose import Transpose


@dataclass
class TokenBalance:
    address: str
    amount: float
    time: datetime


class TokenHistory:
    def __init__(self):
        self._transpose = Transpose(api_key="hU9huB4anD8oHD0He9cKswXrXPY6idXX")

    def get_historical_balances(self, address: str) -> Dict[str, List[TokenBalance]]:
        all_transactions = []
        last_received_time = None
        while True:
            if not last_received_time:
                new_transactions = self._transpose.token.transfers_by_account(address, limit=500)
            else:
                new_transactions = self._transpose.token.transfers_by_account(address,
                                                                              transferred_after=last_received_time,
                                                                              limit=500)
            all_transactions.extend(new_transactions)
            if not new_transactions or len(new_transactions) == 1:
                break
            last_received_time = all_transactions[-1].timestamp
        token_states = dict()
        for transaction in all_transactions:
            contract_address = transaction.contract_address
            receiver = transaction.to
            amount = transaction.quantity
            tx_time = transaction.timestamp
            is_receiving = receiver.lower() == address.lower() if receiver else False
            if contract_address not in token_states:
                token_states[contract_address] = []
                first_token_balance = TokenBalance(contract_address, amount, tx_time)
                token_states[contract_address].append(first_token_balance)
                continue

            last_update = token_states[contract_address][-1]
            if is_receiving:
                new_amount = last_update.amount + amount
            else:
                new_amount = last_update.amount - amount
                assert new_amount >= 0
            new_token_balance = TokenBalance(address=contract_address, amount=new_amount,time=tx_time)
            token_states[contract_address].append(new_token_balance)
        return token_states


if __name__ == '__main__':
    token_history = TokenHistory()
    print(token_history.get_historical_balances(address="0xfe8f318c45996556098b715b08d398e09f4cf95d"))
