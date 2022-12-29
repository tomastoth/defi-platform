import pytest

from src import coin_changes
from tests.test_unit import utils

@pytest.mark.asyncio
async def test_coin_changes():
    wotk = utils.create_aggregated_asset(
        symbol="WOTK",
        amount=50.0,
        price=1.0,
        value_pct=50.0,
        value_usd=50.0
    )
    beth = utils.create_aggregated_asset(
        symbol="BETH",
        amount=50.0,
        price=1.0,
        value_pct=50.0,
        value_usd=50.0
    )
    first_updates = [
        wotk,
        beth
    ]
    wotk2 = wotk.copy()
    wotk2.value_pct = 100.0
    second_updates = [
        wotk2
    ]
    coin_changes_dict = {}
    await coin_changes.async_extract_coin_changes(
        coin_changes_dict,
        first_updates,
        second_updates
    )
    assert coin_changes_dict["WOTK"] == 50.0
    assert coin_changes_dict["BETH"] == -50.0

