# type: ignore
import pytest

from src import enums, models
from src.debank import Debank


@pytest.mark.skip(reason="not yet implemented")
def test_extracting_data_from_debank_for_single_address():
    debank = Debank()
    address = models.Address(address="0x123", blockchain_type=enums.BlockchainType.EVM)
    address_balances = await debank.async_get_assets_for_address(address=address)
    assert address_balances.value_usd
    coin_highest_value_usd = address_balances.assets_usd[0]
    assert coin_highest_value_usd.value_usd
    assert coin_highest_value_usd.amount
    assert coin_highest_value_usd.symbol
    coin_highest_value_pct = address_balances.assets_pct[0]
    assert coin_highest_value_pct.symbol
    assert coin_highest_value_pct.value_pct
