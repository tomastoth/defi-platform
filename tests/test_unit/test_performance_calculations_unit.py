from datetime import datetime

import pytest

from src import data, enums, performance, time_utils
from tests.test_unit import utils
from tests.test_unit.fixtures import address, model_address  # noqa


@pytest.mark.parametrize(
    "old_value_usd,new_value_usd,asset_performance",
    [(100.0, 200.0, 100.0), (100.0, 50.0, -50.0), (100.0, 0.0, -100.0)],
)
def test_asset_gaining_in_value(
    old_value_usd: float,
    new_value_usd: float,
    asset_performance: float,
    address: data.Address,
) -> None:
    old_update = utils.create_aggregated_update(
        value_usd=old_value_usd, amount=1, price=old_value_usd, value_pct=100.0
    )
    new_update = utils.create_aggregated_update(
        value_usd=new_value_usd, amount=1, price=new_value_usd, value_pct=100.0
    )
    performance_result = performance.calculate_performance(
        old_address_updates=old_update.aggregated_assets,
        new_address_updates=new_update.aggregated_assets,
        start_time=time_utils.get_datetime_from_ts(0),
        end_time=time_utils.get_datetime_from_ts(1),
        address=address,
    )
    assert performance_result.performance == pytest.approx(asset_performance)


def test_extracting_dates_from_hourly_ranking_type() -> None:
    mock_time = utils.create_datetime(hour=2, minute=0, second=11)
    start_time, end_time = performance._get_times_for_comparison(
        enums.AddressRankingType.HOUR, wanted_time=mock_time
    )
    assert start_time == utils.create_datetime()
    assert end_time == utils.create_datetime(hour=2)


def test_extracting_dates_from_daily_ranking_type() -> None:
    mock_time = utils.create_datetime(day=2, hour=0, minute=0, second=1)
    start_time, end_time = performance._get_times_for_comparison(
        enums.AddressRankingType.DAY, wanted_time=mock_time
    )
    assert start_time == utils.create_datetime(hour=0, minute=0, second=1)
    assert end_time == utils.create_datetime(hour=23, minute=59, second=59)


def test_extracting_saving_time_for_ranking() -> None:
    mock_time = datetime(year=2022, month=1, day=1, hour=2, minute=0, second=1)
    saving_time = performance._get_saving_time_for_ranking(
        address_ranking_type=enums.AddressRankingType.HOUR, current_time=mock_time
    )
    assert saving_time == datetime(
        year=2022, month=1, day=1, hour=1, minute=0, second=0
    )
