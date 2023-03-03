import asyncio
from enum import Enum

from defi_common import data, time_utils
from defi_common.data import AggregatedUsdAsset, Address, AddressUpdate

from src import http_utils
from src.config import config
from src.token_balances.aggregated_assets import AggregatedAssetProvider, calc_sum_usd_value, add_pct_value, \
    sort_by_value_usd, _combine_aggregated_usd_assets, aggregate_usd_assets

MIN_USD_VALUE = 5

class ZapperAssetProvider(AggregatedAssetProvider):
    ZAPPER_URL = "https://api.zapper.xyz/v2"

    def __init__(self):
        self._zapper_api_key = config.zapper_key

    async def _get_staked_assets_for_address(self, address: data.Address) -> list[AggregatedUsdAsset]:
        url = f"{self.ZAPPER_URL}/balances/apps?addresses%5B%5D={address.address}"
        headers = self._create_zapper_headers()
        result = await http_utils.async_request(url, headers=headers)
        all_assets = []
        for app_data in result:
            app_name = app_data["appName"]
            blockchain = app_data["network"]
            products = app_data["products"]
            for product in products:
                product_type = product["label"]
                assets = product["assets"]
                for asset in assets:
                    tokens = asset["tokens"]
                    for token in tokens:
                        value_usd = token["balanceUSD"]
                        if value_usd < MIN_USD_VALUE:
                            continue
                        asset = AggregatedUsdAsset(
                            symbol=token["symbol"],
                            amount=token["balance"],
                            price=token["price"],
                            value_usd=token["balanceUSD"]
                        )
                        all_assets.append(asset)
        return all_assets

    async def async_get_assets_for_address(
            self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        wallet_assets = await self._get_wallet_tokens(address)
        pool_assets = await self._get_staked_assets_for_address(address)
        all_assets = wallet_assets.copy()
        all_assets.extend(pool_assets)
        usd_value = calc_sum_usd_value(all_assets)
        combined_assets = aggregate_usd_assets(all_assets)
        aggregated_pct_assets = add_pct_value(combined_assets, usd_value, run_time)
        sorted_assets = sort_by_value_usd(aggregated_pct_assets)
        return AddressUpdate(aggregated_assets=sorted_assets, value_usd=usd_value)

    async def _get_wallet_tokens(self, address):
        url = f"{self.ZAPPER_URL}/balances/tokens?addresses%5B%5D={address.address}"
        headers = self._create_zapper_headers()
        result = await http_utils.async_request(url, headers=headers)
        all_tokens_data = result[address.address]
        blockchain_to_assets = dict[str, list[AggregatedUsdAsset]]()
        all_assets = []
        if not all_tokens_data:
            return []
        for token_data in all_tokens_data:
            token = token_data["token"]
            balance_usd = token["balanceUSD"]
            if balance_usd < MIN_USD_VALUE:
                continue
            blockchain = token_data["network"]
            symbol = token["symbol"]
            price = token["price"]
            balance = token["balance"]
            asset = AggregatedUsdAsset(symbol=symbol, amount=balance, price=price, value_usd=balance_usd)
            if blockchain not in blockchain_to_assets:
                blockchain_to_assets[blockchain] = []
            blockchain_to_assets[blockchain].append(asset)
            all_assets.append(asset)
        return all_assets

    def _create_zapper_headers(self):
        headers = {
            "accept": "*/*",
            "Authorization": f"Basic {self._zapper_api_key}"
        }
        return headers


async def async_provide_aggregated_assets(
        address: data.Address, run_timestamp: int
) -> data.AddressUpdate | None:
    zapper_asset_provider = ZapperAssetProvider()
    return await zapper_asset_provider.async_get_assets_for_address(
        address, run_timestamp
    )
