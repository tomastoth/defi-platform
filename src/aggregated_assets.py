import asyncio
import logging
import typing
from abc import ABC, abstractmethod
from datetime import datetime

from src import http_utils, spec
from defi_common import data, enums, exceptions, time_utils
from defi_common.exceptions import DebankDataInvalidError, DebankUnknownBlockchainError

log = logging.getLogger(__name__)


def _add_pct_value(
    aggregated_usd_assets: list[data.AggregatedUsdAsset],
    sum_value_usd: float,
    run_time: int,
) -> list[data.AggregatedAsset]:
    """
    Adds percentage of owned value for each asset from sum value usd
    """
    aggregated_assets: list[data.AggregatedAsset] = []
    for aggregated_usd_asset in aggregated_usd_assets:
        asset_pct_value = (aggregated_usd_asset.value_usd / sum_value_usd) * 100.0
        aggregated_asset = data.AggregatedAsset(
            symbol=aggregated_usd_asset.symbol,
            amount=aggregated_usd_asset.amount,
            price=aggregated_usd_asset.price,
            value_usd=aggregated_usd_asset.value_usd,
            value_pct=asset_pct_value,
            timestamp=run_time,
        )
        aggregated_assets.append(aggregated_asset)
    return aggregated_assets


def _sort_by_value_usd(
    value_usd_list: list[spec.UsdValue],
) -> list[spec.UsdValue]:
    value_usd_list.sort(key=lambda x: x.value_usd, reverse=True)
    return value_usd_list  # type ignore


def _calc_sum_usd_value(
    aggregated_usd_assets: list[data.AggregatedUsdAsset],
) -> float:
    return sum([asset.value_usd for asset in aggregated_usd_assets])  # type: ignore


class AggregatedAssetProvider(ABC):
    @abstractmethod
    async def async_get_assets_for_address(
        self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        pass


def _combine_aggregated_usd_assets(
    assets_to_combine: list[data.AggregatedUsdAsset],
) -> data.AggregatedUsdAsset:
    if not assets_to_combine:
        raise exceptions.InvalidParamError()
    sum_amount = 0.0
    sum_value_usd = 0.0
    sum_weighted_price = 0.0
    sum_weight = 0.0

    for asset in assets_to_combine:
        sum_amount += asset.amount
        sum_value_usd += asset.value_usd
        sum_weighted_price += asset.amount * asset.price
        sum_weight += asset.amount
    avg_price = sum_weighted_price / sum_weight
    symbol = assets_to_combine[0].symbol
    return data.AggregatedUsdAsset(
        symbol=symbol, price=avg_price, value_usd=sum_value_usd, amount=sum_amount
    )


def _aggregate_usd_assets(
    all_aggregated_usd_assets: list[data.AggregatedUsdAsset],
) -> list[data.AggregatedUsdAsset]:
    aggregated_dict: dict[str, data.AggregatedUsdAsset] = {}
    for asset in all_aggregated_usd_assets:
        lower_asset_symbol = asset.symbol.lower()
        if lower_asset_symbol not in aggregated_dict:
            aggregated_dict[lower_asset_symbol] = asset
        else:
            found_agg_asset = aggregated_dict[lower_asset_symbol]
            combined_asset = _combine_aggregated_usd_assets([found_agg_asset, asset])
            aggregated_dict[lower_asset_symbol] = combined_asset

    return list(aggregated_dict.values())


class NansenPortfolioAssetProvider(AggregatedAssetProvider):
    BASE_URL = "https://api-dev.nansen.ai/portfolio/wallet"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        'Accept-Encoding': 'gzip, deflate, br',
        'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImQwNWI0MDljNmYyMmM0MDNlMWY5MWY5ODY3YWM0OTJhOTA2MTk1NTgiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vZDUtbmFuc2VuLXByb2QiLCJhdWQiOiJkNS1uYW5zZW4tcHJvZCIsImF1dGhfdGltZSI6MTY3MzQ1ODcyNCwidXNlcl9pZCI6InZjdWZnMWVjbTdYWllObThldjdsbm1wWE1lMjIiLCJzdWIiOiJ2Y3VmZzFlY203WFpZTm04ZXY3bG5tcFhNZTIyIiwiaWF0IjoxNjc1NDMwNjkxLCJleHAiOjE2NzU0MzQyOTEsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.OpzQJitABsYTHbnA0f3JQfnUMNqR509TzSUn7yU76oBI1vm__iotGO8ALaZ9Wu9QaYtSfn39bF5eeaypx7wcwv4SsPGHutMrwFu-j5D-VuW6-DndEp08bareKiMFgCcosSAFSzNDI-J32In5n0G0jvn9i0XK-eK-753eHc0oWvMBkudBZkfpZhVOflET7udf-1UCWWmC-kdexlY74JxvDRpk7Mqb7Cxmv3clVgQuygLHhclcuTz0bQBHVJpz1EqA7wVsnn1c3oxi1NuIRAVULs3hxqbLhxPv-geH8JK9lVWpnhGmgjdlwEsbBnpwFCyINWxAKfh4xQo74jZFdv6VYA',
        "passcode": "A63uGa8775Ne89wwqADwKYGeyceXAxmHL",
        'ape-secret': 'U2FsdGVkX1+2gaugZSJ5NytjYJSj4FbqCzG3XdiRLwu1zEsNgnXtQ/L7xkQXN8HTdIslfTb7v8aIDlUZDTCd9jHiOUCqhgeFsllx1jcZQ3Hfvk+Hnh5Yw0v28/1UQyBkyKwU0wihK75Jx7F+x+3iXw==',
        "Origin": "https://portfolio.nansen.ai",
        "Connection": "keep-alive",
        "Referer": "https://portfolio.nansen.ai/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        # Requests doesn't support trailers
        'TE': 'trailers',
    }

    def __init__(self) -> None:
        self._blockchains_to_run = [
            enums.Blockchain.ETH,
            enums.Blockchain.AVAX,
            enums.Blockchain.MATIC,
            enums.Blockchain.OPTIMISM,
            enums.Blockchain.ARB,
        ]

    def _extract_aggregated_assets(
        self, resp_json: list[dict[str, typing.Any]], blockchain: enums.Blockchain
    ) -> list[data.AggregatedUsdAsset]:
        aggregated_assets = []
        for asset_json in resp_json:
            symbol = asset_json["symbol"]
            balance = float(asset_json["balance"])
            price = float(asset_json["price"])
            value_usd = balance * price
            asset = data.AggregatedUsdAsset(
                symbol=symbol,
                amount=balance,
                blockchain=blockchain,
                price=price,
                value_usd=value_usd,
            )
            aggregated_assets.append(asset)
        return aggregated_assets

    def _get_formatted_blockchain(self, blockchain: enums.Blockchain) -> str:
        match blockchain:
            case blockchain.ETH:
                return "eth"
            case blockchain.MATIC:
                return "matic2"
            case blockchain.OPTIMISM:
                return "optimism"
            case blockchain.BSC:
                return "bsc"
            case blockchain.ARB:
                return "arbitrum"
            case blockchain.AVAX:
                return "avax"

        raise exceptions.NansenPortfolioUnknownBlockchainError()

    async def _extract_single_blockchain_aggregated_assets(
        self, address: data.Address, blockchain: enums.Blockchain
    ) -> list[data.AggregatedUsdAsset]:
        address_str = address.address
        blockchain_str = self._get_formatted_blockchain(blockchain)
        url = f"{self.BASE_URL}/{blockchain_str}/{address_str}"
        print(url)
        try:
            resp_json = await http_utils.async_request(url, self.headers)
        except exceptions.InvalidHttpResponseError as e:
            log.warning(f"Can't request agg assets, add: {address.address}")
            return []
        if not resp_json:
            return []
        return self._extract_aggregated_assets(resp_json, blockchain)

    def _create_single_address_update(
        self, all_aggregated_assets: list[data.AggregatedUsdAsset], run_time: int
    ) -> data.AddressUpdate:
        sum_usd_value = _calc_sum_usd_value(all_aggregated_assets)
        aggregated_assets_pct = _add_pct_value(
            all_aggregated_assets, sum_usd_value, run_time
        )
        aggregated_assets_pct_sorted = _sort_by_value_usd(aggregated_assets_pct)
        return data.AddressUpdate(
            aggregated_assets=aggregated_assets_pct_sorted, value_usd=sum_usd_value
        )

    async def async_get_assets_for_address(
        self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        all_aggregated_usd_assets = []
        for blockchain in self._blockchains_to_run:
            blockchain_aggregated_usd_assets = (
                await self._extract_single_blockchain_aggregated_assets(
                    address, blockchain
                )
            )
            all_aggregated_usd_assets.extend(blockchain_aggregated_usd_assets)
        summed_averaged_assets = _aggregate_usd_assets(all_aggregated_usd_assets)
        return self._create_single_address_update(summed_averaged_assets, run_time)


class Debank(AggregatedAssetProvider):
    DEBANK_URL = "http://api.debank.com/"
    HEADERS = {
        "authority": "api.debank.com",
        "accept": "*/*",
        "accept-language": "en",
        "cache-control": "no-cache",
        "dnt": "1",
        "origin": "https://debank.com",
        "pragma": "no-cache",
        "referer": "https://debank.com/",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "source": "web",
        "Connection": "keep-alive",
        "x-api-ver": "v2",
    }

    def __init__(
        self,
        proxy_provider: http_utils.ProxyProvider = http_utils.RedisProxyProvider(),
        user_agent_provider: http_utils.UserAgentProvider = http_utils.FileUserAgentProvider(),
    ):
        self._proxy_provider = proxy_provider
        self._user_agent_provider = user_agent_provider

    def _adjust_headers(self) -> dict[str, typing.Any]:
        headers = Debank.HEADERS.copy()
        headers["user-agent"] = self._user_agent_provider.get_user_agent()
        return headers

    async def _async_get_aggregated_usd_assets(
        self,
        address: data.Address,
    ) -> list[data.AggregatedUsdAsset]:
        url = f"{Debank.DEBANK_URL}asset/classify?user_addr={address.address}"
        log.info(f"before getting url {url}")
        headers = self._adjust_headers()
        try:
            overall_assets_json = await http_utils.sync_request_with_proxy(
                url,
                proxy_provider=self._proxy_provider,
                headers=headers,
                randomize_headers=True,
            )
        except exceptions.InvalidHttpResponseError as e:
            log.warning(
                f"Could not receive data for address {address.address}, skipping update, e: {e}"
            )
            return []
        log.info(f"after getting url {url}")
        if "data" not in overall_assets_json:
            raise DebankDataInvalidError()
        wallet_data = overall_assets_json["data"]
        coin_list = wallet_data["coin_list"]
        aggregated_assets = []
        for coin in coin_list:
            aggregated_usd_asset = Debank._extract_aggregated_usd_asset(coin)
            if aggregated_usd_asset.value_usd > 0:
                aggregated_assets.append(aggregated_usd_asset)
        sorted_aggregated_assets = _sort_by_value_usd(aggregated_assets)
        return sorted_aggregated_assets

    async def async_get_assets_for_address(
        self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        aggregated_usd_assets = await self._async_get_aggregated_usd_assets(
            address=address
        )
        if not aggregated_usd_assets:
            return None
        acc_sum_value_usd = _calc_sum_usd_value(
            aggregated_usd_assets=aggregated_usd_assets
        )
        aggregated_assets = _add_pct_value(
            aggregated_usd_assets=aggregated_usd_assets,
            sum_value_usd=acc_sum_value_usd,
            run_time=run_time,
        )
        return data.AddressUpdate(
            value_usd=acc_sum_value_usd,
            aggregated_assets=aggregated_assets,
        )

    @staticmethod
    def _extract_aggregated_usd_asset(
        coin: dict[str, typing.Any]
    ) -> data.AggregatedUsdAsset:
        token_amount = coin["amount"]
        symbol = coin["symbol"]
        price = coin["price"]
        value_usd = token_amount * price
        aggregated_usd_asset = data.AggregatedUsdAsset(
            symbol=symbol, amount=token_amount, price=price, value_usd=value_usd
        )
        return aggregated_usd_asset

    @staticmethod
    def _parse_debank_blockchain(blockchain: str) -> enums.Blockchain:
        match blockchain:
            case "eth":
                return enums.Blockchain.ETH
            case "ftm":
                return enums.Blockchain.FTM
            case "bsc":
                return enums.Blockchain.BSC
            case "arb":
                return enums.Blockchain.ARB
            case "matic":
                return enums.Blockchain.MATIC
        raise DebankUnknownBlockchainError()


async def async_provide_aggregated_assets(
    address: data.Address, run_timestamp: int
) -> data.AddressUpdate | None:
    nansen_portfolio_price_provider = NansenPortfolioAssetProvider()
    return await nansen_portfolio_price_provider.async_get_assets_for_address(
        address, run_timestamp
    )
