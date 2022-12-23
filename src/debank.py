import asyncio
import logging
import time
import typing

from playwright.async_api import async_playwright

from src import data, enums, exceptions, http_utils, spec

log = logging.getLogger(__name__)


class DebankDataInvalid(Exception):
    pass


class DebankUnknownBlockchain(Exception):
    pass


class Debank:
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

    @classmethod
    async def async_get_blockchain_assets(
        cls, address: data.Address
    ) -> list[data.BlockchainAsset]:
        async with async_playwright() as p:
            url = f"{Debank.DEBANK_URL}token/cache_balance_list?user_addr={address.address}"
            browser = await p.chromium.launch()
            page = await browser.new_page()
            response = await page.goto(url)
            balances_json = await response.json()
            balances = Debank.extract_wallet_assets_from_request(balances_json)
            await browser.close()
            return balances

    @staticmethod
    def extract_wallet_assets_from_request(
        balances_json: dict[str, typing.Any]
    ) -> list[spec.UsdValue]:
        if "data" not in balances_json:
            raise DebankDataInvalid()
        balances: list[data.BlockchainAsset] = []
        all_data = balances_json["data"]
        for single_data in all_data:
            blockchain_wallet_asset = Debank._extract_blockchain_wallet_asset(
                single_data
            )
            if blockchain_wallet_asset:
                balances.append(blockchain_wallet_asset)
        return Debank._sort_by_value_usd(balances)

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
            raise DebankDataInvalid()
        wallet_data = overall_assets_json["data"]
        coin_list = wallet_data["coin_list"]
        aggregated_assets = []
        for coin in coin_list:
            aggregated_usd_asset = Debank._extract_aggregated_usd_asset(coin)
            if aggregated_usd_asset.value_usd > 0:
                aggregated_assets.append(aggregated_usd_asset)
        sorted_aggregated_assets = Debank._sort_by_value_usd(aggregated_assets)
        return sorted_aggregated_assets

    @staticmethod
    def _add_pct_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset],
        sum_value_usd: float,
        run_time: int,
    ) -> list[data.AggregatedAsset]:
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

    async def async_get_assets_for_address(
        self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        aggregated_usd_assets = await self._async_get_aggregated_usd_assets(
            address=address
        )
        if not aggregated_usd_assets:
            return None
        acc_sum_value_usd = Debank._calc_sum_usd_value(
            aggregated_usd_assets=aggregated_usd_assets
        )
        aggregated_assets = self._add_pct_value(
            aggregated_usd_assets=aggregated_usd_assets,
            sum_value_usd=acc_sum_value_usd,
            run_time=run_time,
        )
        return data.AddressUpdate(
            value_usd=acc_sum_value_usd,
            blockchain_wallet_assets=[],
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
        match blockchain:  # noqa: E999
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
        raise DebankUnknownBlockchain()

    @staticmethod
    def _extract_blockchain_wallet_asset(
        wallet_data: typing.Dict[str, typing.Any]
    ) -> typing.Optional[data.BlockchainAsset]:
        try:
            token_amount = float(wallet_data["amount"])
            blockchain = Debank._parse_debank_blockchain(wallet_data["chain"])
            token_symbol = wallet_data["symbol"]
            token_price = float(wallet_data["price"])
            value_usd = token_amount * token_price
        except DebankDataInvalid as e:
            log.warning(
                f"Can't extract debank wallet_data: {e}, wallet_data: {wallet_data}"
            )
            return None
        except DebankUnknownBlockchain as e:
            log.warning(
                f"Can't extract debank blockchain: {e}, wallet_data: {wallet_data}"
            )
            return None
        return data.BlockchainAsset(
            symbol=token_symbol,
            amount=token_amount,
            value_usd=value_usd,
            blockchain=blockchain,
            price=token_price,
        )

    @staticmethod
    def _sort_by_value_usd(
        value_usd_list: list[spec.UsdValue],
    ) -> list[spec.UsdValue]:
        value_usd_list.sort(key=lambda x: x.value_usd, reverse=True)
        return value_usd_list

    @staticmethod
    def _calc_sum_usd_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset],
    ) -> float:
        return sum([asset.value_usd for asset in aggregated_usd_assets])


async def async_provide_aggregated_assets(
    address: data.Address, run_timestamp: int
) -> data.AddressUpdate | None:
    debank = Debank()
    return await debank.async_get_assets_for_address(address, run_timestamp)


if __name__ == "__main__":
    dbnk = Debank()
    counter = 0
    while counter < 10:
        result = asyncio.run(
            dbnk._async_get_aggregated_usd_assets(
                address=data.Address(
                    address="0xeee7fa9f2148e9499d6d857dc09e29864203b138"
                )
            )
        )
        print(result)
        time.sleep(5)
        counter += 1
