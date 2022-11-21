from src import data, performance_calculations


def test_performance_calculations_acceptance() -> None:
    # we have old AddressUpdate
    old_addres_update = data.AddressUpdate(
        value_usd=100000.0,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=50.0,
                price=1000.0,
                time_ms=100,
                value_pct=50.0,
                value_usd=50000.0,
            ),
            data.AggregatedAsset(
                symbol="AAVE",
                amount=50.0,
                price=1000.0,
                time_ms=100,
                value_pct=50.0,
                value_usd=50000.0,
            ),
        ],
    )
    new_address_update = data.AddressUpdate(
        value_usd=200000.0,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=50.0,
                price=2000.0,
                time_ms=101,
                value_pct=50.0,
                value_usd=100000.0,
            ),
            data.AggregatedAsset(
                symbol="AAVE",
                amount=50.0,
                price=2000.0,
                time_ms=101,
                value_pct=50.0,
                value_usd=100000.0,
            ),
        ],
    )
    # we compare old to new to get account performance

    performance_result = performance_calculations.calculate_performance(
        old_address_updates=old_addres_update.aggregated_assets,
        new_address_updates=new_address_update.aggregated_assets,
    )

    assert performance_result.performance

    # we compare addresses by peformance
    ...
