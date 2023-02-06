import typing

from defi_common import enums, data, exceptions

from src import http_utils
from src.token_balances.aggregated_assets import AggregatedAssetProvider, log, calc_sum_usd_value, add_pct_value, \
    sort_by_value_usd, aggregate_usd_assets


class NansenPortfolioAssetProvider(AggregatedAssetProvider):
    BASE_URL = "https://api-dev.nansen.ai/portfolio/wallet"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImQwNWI0MDljNmYyMmM0MDNlMWY5MWY5ODY3YWM0OTJhOTA2MTk1NTgiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vZDUtbmFuc2VuLXByb2QiLCJhdWQiOiJkNS1uYW5zZW4tcHJvZCIsImF1dGhfdGltZSI6MTY3MzQ1ODcyNCwidXNlcl9pZCI6InZjdWZnMWVjbTdYWllObThldjdsbm1wWE1lMjIiLCJzdWIiOiJ2Y3VmZzFlY203WFpZTm04ZXY3bG5tcFhNZTIyIiwiaWF0IjoxNjc1NDMwNjkxLCJleHAiOjE2NzU0MzQyOTEsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnt9LCJzaWduX2luX3Byb3ZpZGVyIjoiY3VzdG9tIn19.OpzQJitABsYTHbnA0f3JQfnUMNqR509TzSUn7yU76oBI1vm__iotGO8ALaZ9Wu9QaYtSfn39bF5eeaypx7wcwv4SsPGHutMrwFu-j5D-VuW6-DndEp08bareKiMFgCcosSAFSzNDI-J32In5n0G0jvn9i0XK-eK-753eHc0oWvMBkudBZkfpZhVOflET7udf-1UCWWmC-kdexlY74JxvDRpk7Mqb7Cxmv3clVgQuygLHhclcuTz0bQBHVJpz1EqA7wVsnn1c3oxi1NuIRAVULs3hxqbLhxPv-geH8JK9lVWpnhGmgjdlwEsbBnpwFCyINWxAKfh4xQo74jZFdv6VYA",
        "passcode": "A63uGa8775Ne89wwqADwKYGeyceXAxmHL",
        "ape-secret": "U2FsdGVkX1+2gaugZSJ5NytjYJSj4FbqCzG3XdiRLwu1zEsNgnXtQ/L7xkQXN8HTdIslfTb7v8aIDlUZDTCd9jHiOUCqhgeFsllx1jcZQ3Hfvk+Hnh5Yw0v28/1UQyBkyKwU0wihK75Jx7F+x+3iXw==",
        "Origin": "https://portfolio.nansen.ai",
        "Connection": "keep-alive",
        "Referer": "https://portfolio.nansen.ai/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        # Requests doesn't support trailers
        "TE": "trailers",
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
        sum_usd_value = calc_sum_usd_value(all_aggregated_assets)
        aggregated_assets_pct = add_pct_value(
            all_aggregated_assets, sum_usd_value, run_time
        )
        aggregated_assets_pct_sorted = sort_by_value_usd(aggregated_assets_pct)
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
        summed_averaged_assets = aggregate_usd_assets(all_aggregated_usd_assets)
        return self._create_single_address_update(summed_averaged_assets, run_time)


