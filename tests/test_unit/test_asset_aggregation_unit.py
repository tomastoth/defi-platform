from src import aggregated_assets, data
from tests.test_unit import utils


def test_aggregating_from_multiple_blockchains():
    """
                symbol = asset_json["symbol"]
            balance = float(asset_json["balance"])
            price = float(asset_json["price"])
    """
    assets_blockchain_1 = [
        utils.create_aggregated_usd_asset(
            symbol="TOM",
            amount=1.0,
            price=100.0,
            value_usd=100.0
        )
    ]

    assets_blockchain_2 = [
        utils.create_aggregated_usd_asset(
            symbol="TOM",
            amount=1.0,
            price=200.0,
            value_usd=200.0
        )
    ]

    all_aggregated_usd_assets = []
    all_aggregated_usd_assets.extend(assets_blockchain_1)
    all_aggregated_usd_assets.extend(assets_blockchain_2)
    aggregated_all: list[
        data.AggregatedUsdAsset] = aggregated_assets._aggregate_usd_assets(
        all_aggregated_usd_assets=all_aggregated_usd_assets)
    tom_coin = aggregated_all[0]
    assert tom_coin.value_usd == 300.0
    assert tom_coin.price == 150.0
    assert tom_coin.amount == 2.0
    assert tom_coin.symbol == "TOM"
