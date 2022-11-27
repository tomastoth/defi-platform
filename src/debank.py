import logging
import time
import typing

from src import data, enums, exceptions, http_utils, spec

log = logging.getLogger(__name__)


class DebankDataInvalid(Exception):
    pass


class DebankUnknownBlockchain(Exception):
    pass


class Debank:
    DEBANK_URL = "https://api.debank.com/"
    HEADERS = {
        "authority": "api.debank.com",
        "accept": "*/*",
        "accept-language": "en",
        "account": '{"random_at":1669564020,"random_id":"4cb9e160803a45d394015cedd00d5fef","user_addr":null}',
        "cache-control": "no-cache",
        "dnt": "1",
        "origin": "https://debank.com",
        "pragma": "no-cache",
        "referer": "https://debank.com/",
        "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "source": "web",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
        "x-api-nonce": "n_t2eUxoa3cTlI6oUGZPu9FVfd0rxxcE2ctP4Gu4S8",
        "x-api-sign": "1bd86b3509314cce80e9758290223caec62ee3bb66893defc81c576445ca36ab",
        "x-api-ts": "1669564022",
        "x-api-ver": "v2",
    }
    PROXY_PROVIDER = http_utils.ListProxyProvider()
    PROXY_PROVIDER.load_proxies()

    @staticmethod
    async def async_get_blockchain_assets(
        address: data.Address,
    ) -> list[data.BlockchainAsset]:
        url = f"{Debank.DEBANK_URL}token/cache_balance_list?user_addr={address.address}"
        balances_json = await http_utils.async_request(url, headers=Debank.HEADERS)
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
        sorted_blockchain_wallet_assets = Debank._sort_by_value_usd(balances)
        return sorted_blockchain_wallet_assets

    @staticmethod
    async def _async_get_aggregated_usd_assets(
        address: data.Address,
    ) -> list[data.AggregatedUsdAsset]:
        url = f"{Debank.DEBANK_URL}/asset/classify?user_addr={address.address}"
        try:
            adjusted_headers = Debank._adjust_headers()
            overall_assets_json = await http_utils.async_request(
                url,
                headers=adjusted_headers,
            )
        except exceptions.InvalidHttpResponseError:
            log.warning(
                f"Could not receive data for address {address.address}, skipping update"
            )
            return []
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
    def _adjust_headers() -> dict[str, str]:
        headers = Debank.HEADERS.copy()
        headers["x-api-ts"] = str(int(time.time()))
        return headers

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
