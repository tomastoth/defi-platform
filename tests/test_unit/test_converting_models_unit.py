from datetime import datetime

from src.database import models, services
from tests.test_unit.fixtures import model_address  # noqa


def test_converting_agg_update_model_to_data(model_address: models.Address) -> None:
    update_time = datetime(2022, 1, 1, 1, 1, 1)
    model = models.AggregatedBalanceUpdate(
        value_usd=100.0,
        timestamp=int(update_time.timestamp()),
        time=update_time,
        symbol="BTC",
        amount=1,
        price=100.0,
        value_pct=100.0,
        address=model_address,
        address_id=model_address.id,
    )
    converted = services.convert_aggregated_model(aggregated_balance_model=model)
    assert converted.price == 100.0
    assert converted.symbol == "BTC"
    assert converted.amount == 1
    assert converted.value_usd == 100.0
    assert converted.value_pct == 100.0
    assert converted.timestamp == model.timestamp
