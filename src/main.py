import asyncio
import logging
import src  # noqa
from apscheduler.schedulers import asyncio as asyncio_scheduler
from apscheduler.triggers import cron
from defi_common.database import db
from sqlalchemy.ext import asyncio as sql_asyncio

from src import addresses, enums, runner


def run_executor(event_loop: asyncio.AbstractEventLoop) -> None:
    scheduler = asyncio_scheduler.AsyncIOScheduler(event_loop=event_loop)
    scheduler.add_job(
        runner.async_update_all_addresses,
        kwargs={"session_maker": db.async_session},
        trigger=cron.CronTrigger.from_crontab("*/2 * * * *"),
    )
    scheduler.add_job(
        runner.async_run_address_ranking,
        kwargs={"session_maker": db.async_session, "time_type": enums.RunTimeType.HOUR},
        trigger=cron.CronTrigger.from_crontab("1 * * * *"),
    )
    scheduler.add_job(
        runner.async_run_coin_change_ranking,
        kwargs={"session_maker": db.async_session, "time_type": enums.RunTimeType.HOUR},
        trigger=cron.CronTrigger.from_crontab("1 * * * *"),
    )
    scheduler.add_job(
        runner.async_run_address_ranking,
        kwargs={"session_maker": db.async_session, "time_type": enums.RunTimeType.DAY},
        trigger=cron.CronTrigger.from_crontab("1 0 * * *"),
    )
    scheduler.start()
    event_loop.run_forever()


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
    run_executor(event_loop)
