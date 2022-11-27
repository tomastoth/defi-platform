import abc
import logging
import random
import typing

import aiohttp
from aiohttp import client_exceptions

from src import exceptions
from src.config import config

log = logging.getLogger(__name__)


class AbstractProxyProvider(abc.ABC):
    @abc.abstractmethod
    def get_proxy(self) -> str:
        ...


class ListProxyProvider(AbstractProxyProvider):
    def __init__(self) -> None:
        self._proxies: list[str] = []

    def load_proxies(self) -> None:
        with open(f"{config.root_dir}/proxies.csv", "r") as proxies_file:
            for line in proxies_file:
                split = line.split(",")
                proxy = f"http://{split[0]}:{split[1]}"
                self._proxies.append(proxy)

    def get_proxy(self) -> str:
        rnd = random.Random()
        max_index = len(self._proxies) - 1
        return self._proxies[rnd.randint(0, max_index)]


async def async_request(
    url: str, headers: dict[str, str] | None = None, proxy: str | None = None
) -> typing.Any:
    if not headers:
        headers = {}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, proxy=proxy) as response:
            if response.status != 200:
                log.warning(f"Got response status {response.status}")
                raise exceptions.InvalidHttpResponseError()
            return await response.json()


async def async_request_with_proxy(
    url: str,
    proxy_provider: AbstractProxyProvider,
    headers: dict[str, str] | None = None,
    max_retries: int = 5,
) -> typing.Any:
    retries = 0
    while retries < max_retries:
        proxy = proxy_provider.get_proxy()
        try:
            return await async_request(url, headers, proxy)
        except (exceptions.InvalidHttpResponseError, client_exceptions.ClientError):
            retries += 1
    raise exceptions.InvalidHttpResponseError()


if __name__ == "__main__":
    list_proxy_provider = ListProxyProvider()
    list_proxy_provider.load_proxies()
    print(list_proxy_provider.get_proxy())
