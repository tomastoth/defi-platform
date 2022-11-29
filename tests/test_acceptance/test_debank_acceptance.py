# type: ignore
import json
import os
from unittest import mock

import pytest

from src import data, enums
from src.config import config
from src.debank import Debank


# @pytest.mark.skip(reason="not yet implemented")
@pytest.mark.asyncio
async def test_extracting_data_from_debank_for_single_address():
    debank = Debank()
    address = data.Address(address="0x123", blockchain_type=enums.BlockchainType.EVM)
    with mock.patch(
        "src.debank.Debank.async_get_blockchain_assets"
    ) as get_blockchain_assets:
        get_blockchain_assets.return_value = []
        with mock.patch("src.http_utils.async_request") as async_request:
            async_request.return_value = json.load(
                open(
                    os.path.join(config.test_data_dir,"debank_integrated_aggregated_balances.json")
                )
            )
            address_update = await debank.async_get_assets_for_address(
                address=address, run_time=100
            )
    coin_highest_value_usd = address_update.aggregated_assets[0]
    assert coin_highest_value_usd.value_usd == 100000.0
    assert coin_highest_value_usd.amount == 100.0
    assert coin_highest_value_usd.symbol == "ETH"
    assert address_update.value_usd == 100000.0
