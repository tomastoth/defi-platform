"""
Module used for different ways of adding / finding interesting addresses
"""
import abc
import logging

import sqlalchemy.ext.asyncio as sql_asyncio

from defi_common import data, enums, exceptions
from src import http_utils
from defi_common.database import services

"""
1. start with list of addresses
2. get addresses from debank list?
3. get addresses by scanning people interacting with specific contracts?
"""
log = logging.getLogger(__name__)


async def async_save_found_addresses(
    addresses: list[data.Address], session: sql_asyncio.AsyncSession
) -> None:
    for address in addresses:
        try:
            await services.async_save_address(address, session)
        except exceptions.AddressAlreadyExistsError:
            log.warning(f"could not save address: {address}, it already exists")


class AddressesFinder(abc.ABC):
    @abc.abstractmethod
    async def async_find_addresses(self) -> list[data.Address]:
        ...


class DebankAddressFinder(AddressesFinder):
    URL = "https://api.debank.com/social_ranking/list?"

    def __init__(self, pages_to_get: int = 5):
        self._pages_to_get = pages_to_get

    async def _async_get_debank_leaderboard(self, pages: int = 5) -> list[data.Address]:
        addresses: list[data.Address] = []
        for page in range(pages):
            url = f"{self.URL}/page_num={page}&page_count=50"
            leaderboard_result = await http_utils.async_request(url)
            if "data" not in leaderboard_result:
                raise exceptions.DebankDataMissingError()
            leaderboard_data = leaderboard_result["data"]
            social_ranking_list = leaderboard_data["social_ranking_list"]
            for user in social_ranking_list:
                address = user["id"]
                addresses.append(
                    data.Address(
                        address=address,
                        blockchain_type=enums.BlockchainType.EVM,
                    )
                )
        return addresses

    async def async_find_addresses(self) -> list[data.Address]:
        return await self._async_get_debank_leaderboard(self._pages_to_get)


async def async_save_addresses_from_all_providers(
    session: sql_asyncio.AsyncSession,
) -> None:
    """
    Supposed to be run after db reset
    :param session: db session
    """
    all_addresses: list[data.Address] = []
    debank_address_finder = DebankAddressFinder(5)
    debank_addresses = await debank_address_finder.async_find_addresses()
    all_addresses.extend(debank_addresses)
    limit_addressess = all_addresses[:20]  # limiting rn to not get 429 on debank
    await async_save_found_addresses(limit_addressess, session)
