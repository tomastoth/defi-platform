import time
from datetime import datetime, timedelta

from src import enums, exceptions


def get_time_now() -> int:
    return int(time.time())


def get_datetime_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts)


def get_times_for_comparison(
    time_type: enums.RunTimeType, wanted_time: datetime
) -> tuple[datetime, datetime]:
    match time_type:  # noqa
        case enums.RunTimeType.HOUR:
            end_time = wanted_time.replace(minute=1, second=1)
            start_time = end_time - timedelta(hours=1)
            return start_time, end_time
        case enums.RunTimeType.DAY:
            wanted_day = wanted_time - timedelta(days=1)
            end_time = wanted_day.replace(hour=23, minute=59, second=59)
            start_time = wanted_day.replace(hour=0, minute=0, second=1)
            return start_time, end_time


def get_saving_time_for_ranking(
    address_ranking_type: enums.RunTimeType, current_time: datetime
) -> datetime:
    match address_ranking_type:
        case enums.RunTimeType.HOUR:
            hour_back = current_time - timedelta(hours=1)
            zeroed = hour_back.replace(minute=0, second=0)
            return zeroed
    raise exceptions.UnknownEnumError()
