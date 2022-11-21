import pytest

from src import data, performance_calculations
from tests.test_unit.fixtures import address  # noqa


def create_update(
    value_usd: float, amount: float, price: float, value_pct: float
) -> data.AddressUpdate:
    return data.AddressUpdate(
        value_usd=value_usd,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=amount,
                price=price,
                time_ms=101,
                value_pct=value_pct,
                value_usd=value_pct,
            )
        ],
    )


@pytest.mark.parametrize(
    "old_value_usd,new_value_usd,performance",
    [(100.0, 200.0, 100.0), (100.0, 50.0, -50.0), (100.0, 0.0, -100.0)],
)
def test_asset_gaining_in_value(
    old_value_usd: float,
    new_value_usd: float,
    performance: float,
    address: data.Address,
) -> None:
    old_update = create_update(
        value_usd=old_value_usd, amount=1, price=old_value_usd, value_pct=100.0
    )
    new_update = create_update(
        value_usd=new_value_usd, amount=1, price=new_value_usd, value_pct=100.0
    )
    performance_result = performance_calculations.calculate_performance(
        old_address_updates=old_update.aggregated_assets,
        new_address_updates=new_update.aggregated_assets,
    )
    assert performance_result.performance == pytest.approx(performance)
