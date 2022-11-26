import time
from datetime import datetime


def get_time_now() -> int:
    return int(time.time())


def get_datetime_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts)
