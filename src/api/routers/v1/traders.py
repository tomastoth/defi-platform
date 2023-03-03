from datetime import datetime

from defi_common.database.mongo.models import Trade, TraderUpdate
from fastapi import APIRouter, Depends

from src.api.core.dependencies import init_mongo
from src.token_balances.transpose_all.transpose_common import fetch_trader
from src.token_balances.zapper import ZapperAssetProvider

router = APIRouter(prefix="/traders")
zapper = ZapperAssetProvider()

min_timestamp_to_fetch = datetime(year=2022, month=5, day=1, hour=1, minute=1, second=1)


@router.get("/{address}")
async def get_trader_info(address: str, _=Depends(init_mongo)):
    found_trader_update = await TraderUpdate.find_one(TraderUpdate.trader_address == address)
    if found_trader_update:
        return found_trader_update
    trader_info = await fetch_trader(address, min_timestamp_to_fetch)
    trades = []
    if not trader_info:
        return {"message": "Not found!"}
    for trade in trader_info.trades:
        trade_model = Trade(
            timestamp=trade.timestamp,
            coin_symbol=trade.symbol,
            is_buy=trade.is_buy,
            size_eth=trade.size_eth,
            price=trade.price,
            profit=trade.profit,
            trader_address=address
        )
        trades.append(trade_model)
    trader_update = TraderUpdate(
        number_of_trades=trader_info.number_of_trades,
        traded_eth=trader_info.traded_eth,
        average_trade_size=trader_info.average_eth_size,
        trader_address=address,
        trades=trades,
        sum_profit=trader_info.sum_profit
    )
    await trader_update.save()
    return trader_info.__dict__
