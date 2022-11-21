import logging
import typing

import aiohttp

from src import data, enums, spec

log = logging.getLogger(__name__)


class DebankDataInvalid(Exception):
    pass


class DebankUnknownBlockchain(Exception):
    pass


class Debank:
    DEBANK_URL = "https://api.debank.com/"

    @staticmethod
    async def _async_get_blockchain_assets(
        address: data.Address,
    ) -> typing.List[data.BlockchainAsset]:
        url = f"{Debank.DEBANK_URL}token/cache_balance_list?user_addr={address.address}"
        balances_json = await Debank._async_request(url)
        if "data" not in balances_json:
            raise DebankDataInvalid()
        balances: typing.List[data.BlockchainAsset] = []
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
        overall_assets_json = await Debank._async_request(url)
        if "data" not in overall_assets_json:
            raise DebankDataInvalid()
        wallet_data = overall_assets_json["data"]
        coin_list = wallet_data["coin_list"]
        aggregated_assets = []
        for coin in coin_list:
            aggregated_usd_asset = Debank._extract_aggregated_usd_asset(coin)
            aggregated_assets.append(aggregated_usd_asset)
        sorted_aggregated_assets = Debank._sort_by_value_usd(aggregated_assets)
        return sorted_aggregated_assets

    @staticmethod
    def _add_pct_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset], sum_value_usd: float
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
            )
            aggregated_assets.append(aggregated_asset)
        return aggregated_assets

    async def async_get_assets_for_address(
        self, address: data.Address
    ) -> data.AddressUpdate:
        blockchain_assets = await self._async_get_blockchain_assets(address=address)
        aggregated_usd_assets = await self._async_get_aggregated_usd_assets(
            address=address
        )
        acc_sum_value_usd = Debank._calc_sum_usd_value(
            aggregated_usd_assets=aggregated_usd_assets
        )
        aggregated_assets = self._add_pct_value(
            aggregated_usd_assets=aggregated_usd_assets, sum_value_usd=acc_sum_value_usd
        )
        return data.AddressUpdate(
            value_usd=acc_sum_value_usd,
            blockchain_wallet_assets=blockchain_assets,
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
    async def _async_request(url: str) -> typing.Any:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

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
        value_usd_list: typing.List[spec.UsdValue],
    ) -> typing.List[spec.UsdValue]:
        value_usd_list.sort(key=lambda x: x.value_usd, reverse=True)
        return value_usd_list

    @staticmethod
    def _calc_sum_usd_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset],
    ) -> float:
        return sum([asset.value_usd for asset in aggregated_usd_assets])
