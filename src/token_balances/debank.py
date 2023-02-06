import typing

from defi_common import data, exceptions, enums
from defi_common.exceptions import DebankDataInvalidError, DebankUnknownBlockchainError

from src import http_utils
from src.token_balances.aggregated_assets import AggregatedAssetProvider, log, sort_by_value_usd, calc_sum_usd_value, \
    add_pct_value


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
        sorted_aggregated_assets = sort_by_value_usd(aggregated_assets)
        return sorted_aggregated_assets

    async def async_get_assets_for_address(
            self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        aggregated_usd_assets = await self._async_get_aggregated_usd_assets(
            address=address
        )
        if not aggregated_usd_assets:
            return None
        acc_sum_value_usd = calc_sum_usd_value(
            aggregated_usd_assets=aggregated_usd_assets
        )
        aggregated_assets = add_pct_value(
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
