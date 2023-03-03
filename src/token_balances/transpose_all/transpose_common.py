import asyncio
import pickle
import sys
from datetime import datetime
from enum import Enum
from typing import Coroutine

import aiohttp

from src.token_balances.transpose_all.contract_info import get_decimals
from src.token_balances.transpose_all.data import TraderExport, TradesInfo, Swap, SingleTrade
from src.token_balances.transpose_all.trader_backtest import TraderBacktest

API_KEY = "It5KmD2OXHC38oteuGlOsocL8XZrwb6m"
url = "https://api.transpose.io/sql"
other_token = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
other_token_decimals = 18
blacklisted_token_addresses = [
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "0xdac17f958d2ee523a2206206994597c13d831ec7",
    "0x6b175474e89094c44da98b954eedeac495271d0f"
]
blacklisted_token_addresses = [address.lower() for address in blacklisted_token_addresses]
headers = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY,
}


class TransposeBlockchain(Enum):
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    ETHEREUM = "ethereum"


def calculate_weighted_avg_price(prices, sizes):
    weighted_sum = sum(price * size for price, size in zip(prices, sizes))
    total_weight = sum(sizes)
    return weighted_sum / total_weight


async def get_first_traders_of_token(coin_address: str, limit: int = 100,
                                     blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM):
    traders_query = (
        f"WITH my_cte AS (SELECT origin_address, timestamp FROM {blockchain.value}.dex_swaps "
        f"WHERE to_token_address = '{coin_address}' "
        f"AND from_token_address = '{other_token}' "
        f"ORDER BY timestamp asc "
        f"LIMIT ({limit * 2})) "
        f"SELECT DISTINCT origin_address FROM my_cte LIMIT({limit});"
    )
    results = await _send_transpose_request(traders_query)
    trader_addresses = []
    for result in results:
        trader_addresses.append(result["origin_address"])
    return trader_addresses


def _format_timestamp_for_transpose(timestamp: datetime) -> str:
    return timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')


async def query_users_number_of_trades(trader_address, blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM):
    query = (
        f"SELECT COUNT(*) FROM {blockchain.value}.dex_swaps WHERE origin_address = '{trader_address}';"
    )
    results = await _send_transpose_request(query)
    return results[0]["count"]


async def query_users_traded_pairs(trader_address, limit=100, min_timestamp: datetime = datetime.min,
                                   blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM):
    query = (
        f"SELECT DISTINCT contract_address FROM ("
        f"SELECT contract_address, timestamp  FROM {blockchain.value}.dex_swaps "
        f"WHERE origin_address = '{trader_address}' "
        f"AND timestamp > '{_format_timestamp_for_transpose(min_timestamp)}' "
        f"ORDER BY timestamp desc "
        f"LIMIT {limit}) as addresses;"
    )
    results = await _send_transpose_request(query)
    return list(set((result["contract_address"] for result in results)))


async def _calculate_sell_trades(pair_address, trader_address,
                                 blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM) -> TradesInfo | None:
    sell_query = (
        f"SELECT * FROM {blockchain.value}.dex_swaps "
        f"WHERE contract_address = '{pair_address}' "
        f"AND origin_address = '{trader_address}' "
        f"AND to_token_address = '{other_token}' "
        f"ORDER BY timestamp asc "
    )
    trades = await _fetch_trades_from_query(sell_query, _calculate_sell_price, _calculate_sell_size, False)
    sell_prices = [trade.price for trade in trades]
    sell_sizes = [trade.size_eth for trade in trades]
    if not sell_prices:
        return None
    return _create_trades_info(sell_prices, sell_sizes, trades)


async def _calculate_buy_trades(pair_address, trader_address,
                                blockchain: TransposeBlockchain = TransposeBlockchain) -> TradesInfo | None:
    buy_query = (
        f"SELECT * FROM {blockchain.value}.dex_swaps "
        f"WHERE contract_address = '{pair_address}' "
        f"AND origin_address = '{trader_address}' "
        f"AND from_token_address = '{other_token}' "
        f"ORDER BY timestamp asc "
    )
    trades = await _fetch_trades_from_query(buy_query, _calculate_buy_price, _calculate_buy_size, True)
    buy_prices = [trade.price for trade in trades]
    buy_sizes = [trade.size_eth for trade in trades]
    if not buy_prices:
        return None
    return _create_trades_info(buy_prices, buy_sizes, trades)


def _create_trades_info(prices: list[float], sizes: list[float], trades: list[SingleTrade]):
    avg_price = calculate_weighted_avg_price(prices, sizes)
    number_of_trades = len(sizes)
    sum_size = sum(sizes)
    average_size = sum_size / number_of_trades
    return TradesInfo(
        average_price=avg_price,
        number_of_trades=number_of_trades,
        traded_eth=sum_size,
        average_eth=average_size,
        trades=trades
    )


async def _fetch_trades_from_query(query, calculate_price, calculate_size, is_buy: bool):
    results = await _send_transpose_request(query)
    trades = []
    for result in results:
        swap = Swap.from_dict(result)
        price = calculate_price(swap)
        size = calculate_size(swap)
        size_coin = size / price
        if is_buy:
            other_token_addr = result["to_token_address"]
        else:
            other_token_addr = result["from_token_address"]
        if other_token_addr.lower() in blacklisted_token_addresses:
            continue
        trade = SingleTrade(
            timestamp=swap.timestamp,
            size_coin=size_coin,
            size_eth=size,
            price=price,
            symbol=other_token_addr,
            is_buy=is_buy,
            coin_address=other_token_addr
        )
        trades.append(trade)
    return trades


async def _send_transpose_request(query):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json={"sql": query}) as resp:
            if resp.status != 200:
                raise Exception("Bad data", resp.reason)
            json_resp = await resp.json()
            results = json_resp["results"]
            return results


def _calculate_buy_price(swap: Swap):
    token_decimals = get_decimals(swap.to_token_address)
    quantity_out = swap.quantity_out / 10 ** other_token_decimals
    quantity_in = swap.quantity_in / 10 ** token_decimals
    buy_price = quantity_in / quantity_out
    return buy_price


def _calculate_sell_price(swap: Swap):
    token_decimals = get_decimals(swap.from_token_address)
    quantity_in = swap.quantity_in / 10 ** other_token_decimals
    quantity_out = swap.quantity_out / 10 ** token_decimals
    sell_price = quantity_out / quantity_in
    return sell_price


def _calculate_sell_size(swap):
    return swap.quantity_out / 10 ** other_token_decimals


def _calculate_buy_size(swap):
    return swap.quantity_in / 10 ** other_token_decimals


async def _export_per_coin(pair_address: str, trader: str,
                           blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM) -> TraderExport | None:
    try:
        all_trades = []
        buy_trades_info = await _calculate_buy_trades(pair_address, trader, blockchain)
        sell_trades_info = await _calculate_sell_trades(pair_address, trader, blockchain)
        if buy_trades_info:
            all_trades.extend(buy_trades_info.trades)
        if sell_trades_info:
            all_trades.extend(sell_trades_info.trades)
        if not buy_trades_info or not sell_trades_info:
            return None
        number_of_trades = buy_trades_info.number_of_trades + sell_trades_info.number_of_trades
        volume_eth = buy_trades_info.traded_eth + sell_trades_info.traded_eth
        average_eth = (buy_trades_info.average_eth + sell_trades_info.average_eth) / 2.0
        return TraderExport(
            number_of_trades=number_of_trades,
            traded_eth=volume_eth,
            average_eth_size=average_eth,
            trades=all_trades,
            sum_profit=0
        )
    except Exception as e:
        print(e)


async def get_traders_of_token(pair, limit=10, blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM):
    traders = await get_first_traders_of_token(pair, limit, blockchain)
    results = []
    for trader in traders:
        try:
            buy_price = _calculate_buy_trades(pair, trader, blockchain)
            sell_price = _calculate_sell_trades(pair, trader, blockchain)
            if not buy_price or not sell_price:
                continue
            sell_buy_ratio = sell_price / buy_price
            results.append((trader, sell_buy_ratio))
        except Exception as e:
            print(e)
            continue
    sorted_data = sorted(results, key=lambda x: x[1], reverse=True)
    return [result[0] for result in sorted_data]


async def throttle_fetch_pair_infos(single_coin_tasks: list[Coroutine]) -> list[TraderExport | None]:
    max_running_tasks = 1
    current_running_tasks = []
    results = []
    for task in single_coin_tasks:
        if len(current_running_tasks) < max_running_tasks:
            current_running_tasks.append(task)
        else:
            results.extend(await asyncio.gather(*current_running_tasks))
            current_running_tasks = []
            current_running_tasks.append(task)
    return results


async def fetch_trader(trader: str, min_timestamp: datetime = datetime.min,
                       limit_pairs: int = 100,
                       blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM) -> TraderExport | None:
    pairs = await query_users_traded_pairs(trader, min_timestamp=min_timestamp, limit=limit_pairs,
                                           blockchain=blockchain)
    all_trades = []
    number_of_trades = 0
    sum_traded_eth = 0
    for pair in pairs:
        single_coin_info = await _export_per_coin(pair, trader, blockchain)
        if single_coin_info:
            number_of_trades += single_coin_info.number_of_trades
            sum_traded_eth += single_coin_info.traded_eth
            all_trades.extend(single_coin_info.trades)
    if not number_of_trades:
        return None
    avg_traded_eth = sum_traded_eth / number_of_trades
    all_trades = sorted(all_trades, key=lambda x: x.timestamp)
    backtest = TraderBacktest()
    for trade in all_trades:
        backtest.on_trade(trade)
    sum_profit = backtest.get_profit()
    profit_trades = backtest.get_all_trades()
    return TraderExport(
        number_of_trades=number_of_trades,
        traded_eth=sum_traded_eth,
        average_eth_size=avg_traded_eth,
        trades=profit_trades,
        sum_profit=sum_profit
    )


async def backtest_trader(trader_address: str, min_timestamp: datetime,
                          blockchain: TransposeBlockchain = TransposeBlockchain.ETHEREUM):
    trader_info = await fetch_trader(trader_address, min_timestamp, limit_pairs=500, blockchain=blockchain)
    with open("./trades.pkl", "wb") as file:
        pickle.dump(trader_info, file)
    trader_backtest = TraderBacktest()
    for trade in trader_info.trades:
        trader_backtest.on_trade(trade)
    sys.exit()


async def main():
    other_token_eth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    max_user_trades = 3000
    min_user_trades = 20
    min_timestamp = datetime(year=2022, month=1, day=1, hour=1, minute=1, second=1)
    running_blockchain = TransposeBlockchain.ETHEREUM
    traders = await get_first_traders_of_token(
        "0x8b0fde007458ee153bd0f66cd448af5fb3d99b43",
        40,
        running_blockchain
    )
    # traders = ["0xea0F38B9f3Fa58fa6a42b6A592BfB00CAfa77f26"
    #            # "0xEd458354E77BD79f2A1db28c15f612E750463897",
    #            # "0x75A292e7DE2981184D8bD026b9e1d77A013365f9"
    #            ]
    trader_infos = []
    for trader in traders:
        number_of_trades = await query_users_number_of_trades(trader, running_blockchain)
        if number_of_trades > max_user_trades or number_of_trades < min_user_trades:
            print(f"skipping {trader}, number of trades: {number_of_trades} > {max_user_trades}")
            continue
        trader_info = await fetch_trader(trader, min_timestamp, blockchain=running_blockchain)
        if not trader_info:
            print(f"skipping {trader}, no trader info")
            continue
        trader_infos.append((trader, trader_info, trader_info.sum_profit))
        # print(trader_info.trades)
        print(
            f"{trader}, profit: {trader_info.sum_profit}, number of trades: {trader_info.number_of_trades},"
            f"volume eth: {trader_info.traded_eth}, avg eth: {trader_info.average_eth_size}")
    sorted_traders = sorted(trader_infos, key=lambda x: x[2], reverse=True)
    print("------------------------------------------------------------")
    for trader_data in sorted_traders:
        print(trader_data)


if __name__ == "__main__":
    asyncio.run(main())
