import logging
import typing

import aiohttp

from src import schemas, enums

log = logging.getLogger(__name__)


class DebankDataInvalid(Exception):
    pass


class DebankUnknownBlockchain(Exception):
    pass


class Debank:
    DEBANK_URL = "https://api.debank.com/"

    def __init__(self) -> None:
        pass

    async def async_get_assets_for_address(
        self, address: schemas.Address
    ) -> schemas.AddressUpdate:
        blockchain_assets = await self._async_get_blockchain_assets(address=address)
        return schemas.AddressUpdate(
            value_usd=0.0,
            assets_blockchain=blockchain_assets,
            assets_pct=[],
            assets_usd=[],
        )

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
        raise DebankUnknownBlockchain()

    @staticmethod
    async def _async_request(url: str) -> typing.Dict[str, typing.Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    @staticmethod
    def _extract_blockchain_asset(
        data: typing.Dict[str, typing.Any]
    ) -> typing.Optional[schemas.BlockchainAsset]:
        try:
            token_amount = float(data["amount"])
            blockchain = Debank._parse_debank_blockchain(data["chain"])
            token_symbol = data["symbol"]
            token_price = float(data["price"])
            value_usd = token_amount * token_price
        except DebankDataInvalid as e:
            log.warning(f"Can't extract debank data: {e}, data: {data}")
            return None
        except DebankUnknownBlockchain as e:
            log.warning(f"Can't extract debank blockchain: {e}, data: {data}")
            return None
        return schemas.BlockchainAsset(
            symbol=token_symbol,
            amount=token_amount,
            value_usd=value_usd,
            blockchain=blockchain,
            price=token_price,
        )

    @staticmethod
    async def _async_get_blockchain_assets(
        address: schemas.Address,
    ) -> typing.List[schemas.BlockchainAsset]:
        url = f"{Debank.DEBANK_URL}token/cache_balance_list?user_addr={address.address}"
        balances_json = await Debank._async_request(url)
        if "data" not in balances_json:
            raise DebankDataInvalid()
        balances: typing.List[schemas.BlockchainAsset] = []
        all_data = balances_json["data"]
        for data in all_data:
            blockchain_asset = Debank._extract_blockchain_asset(data)
            if blockchain_asset:
                balances.append(blockchain_asset)
        sorted_blockchain_assets = await Debank._sort_by_value_usd(balances)
        return sorted_blockchain_assets

    @staticmethod
    async def _sort_by_value_usd(
        value_usd_list: typing.List[schemas.UsdValue],
    ) -> typing.List[schemas.UsdValue]:
        value_usd_list.sort(key=lambda x: x.value_usd, reverse=True)
        return value_usd_list
