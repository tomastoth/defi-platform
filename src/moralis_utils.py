from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Optional

from defi_common.enums import Blockchain
from moralis import evm_api

from src.config import config

BAD_DOMAINS = [".io", ".net", ".xyz", ".co"]


def _convert_moralis_blockchain(blockchain: Blockchain) -> str:
    match blockchain:
        case Blockchain.ETH:
            return "eth"


@dataclass
class TokenInfo:
    symbol: str
    decimals: int
    address: str

    def __hash__(self) -> int:
        return hash(f"{self.symbol}, {self.decimals}, {self.address}")


class TokenInfoProvider(ABC):
    def __init__(self):
        self._cached_token_info: dict[str, TokenInfo] = dict()

    @abstractmethod
    def _get_token_info(
        self, contract_address: str, blockchain: Blockchain
    ) -> TokenInfo:
        pass

    def get_token_info(
        self, contract_address: str, blockchain: Blockchain
    ) -> Optional[TokenInfo]:
        key = f"{contract_address}_{blockchain}"
        if key not in self._cached_token_info:
            token_info = self._get_token_info(contract_address, blockchain)
            if token_info:
                self._cached_token_info[key] = token_info
        try:
            return self._cached_token_info[key]
        except KeyError:
            return None


class MoralisError(Exception):
    pass


class MoralisTokenInfoProvider(TokenInfoProvider):
    def __init__(self):
        super().__init__()

    def _get_token_info(
        self, contract_address: str, blockchain: Blockchain
    ) -> Optional[TokenInfo]:
        moralis_chain = _convert_moralis_blockchain(blockchain)
        params = {"addresses": [contract_address], "chain": moralis_chain}
        result = evm_api.token.get_token_metadata(
            api_key=config.moralis_key, params=params
        )
        if not result:
            raise MoralisError("Could not get contract decimals")
        token_info = result[0]
        symbol = token_info["symbol"]
        try:
            decimals = int(token_info["decimals"])
        except TypeError:
            return None
        if any(bad_domain in symbol for bad_domain in BAD_DOMAINS):
            return None
        return TokenInfo(symbol=symbol, decimals=decimals, address=contract_address)
