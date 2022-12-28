import src  # noqa
import asyncio
import logging
import time

from apscheduler.schedulers import asyncio as asyncio_scheduler
from apscheduler.triggers import cron
from defi_common.database import db
from sqlalchemy.ext import asyncio as sql_asyncio

from src import addresses, enums, runner


async def async_run_executor() -> None:
    scheduler = asyncio_scheduler.AsyncIOScheduler()
    session = db.get_session()
    async with db.async_session() as session:
        scheduler.add_job(
            runner.async_update_all_addresses,
            kwargs={"session": session},
            trigger=cron.CronTrigger.from_crontab("*/15 * * * *"),
        )
    async with db.async_session() as session:
        scheduler.add_job(
            runner.async_run_address_ranking,
            kwargs={"session": session, "time_type": enums.RunTimeType.HOUR},
            trigger=cron.CronTrigger.from_crontab("1 * * * *"),
        )
    async with db.async_session() as session:
        scheduler.add_job(
            runner.async_run_coin_change_ranking,
            kwargs={"session": session, "time_type": enums.RunTimeType.HOUR},
            trigger=cron.CronTrigger.from_crontab("1 * * * *"),
        )
    async with db.async_session() as session:
        scheduler.add_job(
            runner.async_run_address_ranking,
            kwargs={"session": session, "time_type": enums.RunTimeType.DAY},
            trigger=cron.CronTrigger.from_crontab("1 0 * * *"),
        )
    scheduler.start()
    # block main thread forever to let schedulers run
    while True:
        time.sleep(10)


async def init_db() -> None:
    await db.init_models()
    session = db.async_session()
    await addresses.async_save_addresses_from_all_providers(session)


def setup_logging() -> None:
    logging.basicConfig(
        format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
        level=logging.INFO,
    )


async def run_updating(session: sql_asyncio.AsyncSession) -> None:
    await runner.async_update_all_addresses(session)


if __name__ == "__main__":
    setup_logging()
    event_loop = asyncio.new_event_loop()
    event_loop.run_until_complete(init_db())
    event_loop.run_until_complete(async_run_executor())
