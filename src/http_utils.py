import abc
import asyncio
import logging
import os
import random
import time
import typing

import aiohttp
import requests
from aiohttp import client_exceptions
from requests import JSONDecodeError

from src import exceptions
from src.config import config

log = logging.getLogger(__name__)


class AbstractProxyProvider(abc.ABC):
    @abc.abstractmethod
    def get_proxy(self) -> str:
        ...


class RedisProxyProvider(AbstractProxyProvider):
    URL = "http://localhost:5010/get?type=http"

    def get_proxy(self) -> str:
        json_data = requests.get(self.URL).json()
        return f'http://{json_data["proxy"]}'


class ListProxyProvider(AbstractProxyProvider):
    def _load_proxies(self) -> None:
        with open(os.path.join(config.root_dir, "proxies.csv"), "r") as proxies_file:
            for line in proxies_file:
                split = line.split(",")
                proxy = f"http://{split[0]}:{split[1]}"
                self._proxies.append(proxy)

    def __init__(self) -> None:
        self._proxies: list[str] = []
        self._load_proxies()

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
        except (
                exceptions.InvalidHttpResponseError,
                client_exceptions.ClientError) as e:
            log.warning(e)
            retries += 1
    raise exceptions.InvalidHttpResponseError()


class UserAgentProvider(abc.ABC):
    @abc.abstractmethod
    def get_user_agent(self) -> str:
        ...


class FileUserAgentProvider(UserAgentProvider):
    @staticmethod
    def _load_user_agents_from_file() -> list[str]:
        with open(
                f"{config.root_dir}/resources/user_agents.txt", "r"
        ) as user_agents_file:
            return [line.strip("\n") for line in user_agents_file]

    def __init__(self) -> None:
        self._headers = self._load_user_agents_from_file()
        self._random = random.Random()

    def get_user_agent(self) -> str:
        if not self._headers:
            self._load_user_agents_from_file()
        random_num = self._random.randint(0, len(self._headers) - 1)
        return self._headers[random_num]


def _randomize_headers(headers, user_agent_provider: UserAgentProvider):
    headers["user-agent"] = user_agent_provider.get_user_agent()
    return headers


async def sync_request_with_proxy(
        url: str,
        proxy_provider: AbstractProxyProvider,
        headers: dict[str, str] | None = None,
        max_retries: int = 5,
        randomize_headers: bool = False,
        user_agent_provider: UserAgentProvider = FileUserAgentProvider()
) -> typing.Any:
    if not headers:
        headers = {}
    if randomize_headers:
        headers = _randomize_headers(headers, user_agent_provider)
    retries = 0
    while retries < max_retries:
        proxy = proxy_provider.get_proxy()
        print(f"UA: {headers['user-agent']}, proxy: {proxy}")
        try:
            response = requests.get(url, headers=headers, proxies={"proxy": proxy})
            if response.status_code != 200:
                retries += 1
            return response.json()
        except (exceptions.InvalidHttpResponseError, JSONDecodeError) as e:
            log.warning(e)
            retries += 1
    raise exceptions.InvalidHttpResponseError()


if __name__ == "__main__":
    list_proxy_provider = RedisProxyProvider()
    counter = 0
    while counter < 20:
        while True:
            try:
                result = asyncio.run(
                    sync_request_with_proxy("https://api.debank.com/token/cache_balance_list?user_addr=0x7a16ff8270133f063aab6c9977183d9e72835428",
                                            RedisProxyProvider(), randomize_headers=True))

                print(result)
                counter += 1
                time.sleep(5)
                break
            except Exception as e:
                print(e, e.__class__.__name__)


