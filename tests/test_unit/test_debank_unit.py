import json

import pytest

from src import debank, enums
from src import schemas


# BALANCE TO TEST FOR JSON WAS ~3609


@pytest.fixture
def address():
    return schemas.Address(address="0x91826f730bfe0db68f27400cb5587fb64d42867f")


@pytest.mark.asyncio
async def test_requesting_user_portfolio(address):
    db = debank.Debank()
    await db.async_get_assets_for_address(address=address)


@pytest.mark.asyncio
async def test_parsing_balance_of_address(address):
    db = debank.Debank()
    db._async_request = return_mock_balance_data
    asset_balance = await db.async_get_assets_for_address(address)
    eth_on_ftm = asset_balance.assets_blockchain[0]
    assert eth_on_ftm.value_usd == pytest.approx(356, rel=1e1)
    assert eth_on_ftm.blockchain == enums.Blockchain.FTM


async def return_mock_balance_data():
    return json.load(open("../test_data/debank_balances.json"))
