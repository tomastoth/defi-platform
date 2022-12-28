import asyncio
import logging

from apscheduler.schedulers import asyncio as asyncio_scheduler
from apscheduler.triggers import cron
from defi_common.database import db
from sqlalchemy.ext import asyncio as sql_asyncio

import src  # noqa
from src import addresses, enums, runner


async def async_run_executor(event_loop: asyncio.AbstractEventLoop) -> None:
    scheduler = asyncio_scheduler.AsyncIOScheduler(event_loop=event_loop)
    session = await db.get_session().__anext__()
    scheduler.add_job(
        runner.async_update_all_addresses,
        kwargs={"session": session},
        trigger=cron.CronTrigger.from_crontab("*/15 * * * *"),
    )
    session = await db.get_session().__anext__()
    scheduler.add_job(
        runner.async_run_address_ranking,
        kwargs={"session": session, "time_type": enums.RunTimeType.HOUR},
        trigger=cron.CronTrigger.from_crontab("1 * * * *"),
    )
    session = await db.get_session().__anext__()
    scheduler.add_job(
        runner.async_run_coin_change_ranking,
        kwargs={"session": session, "time_type": enums.RunTimeType.HOUR},
        trigger=cron.CronTrigger.from_crontab("1 * * * *"),
    )
    session = await db.get_session().__anext__()
    scheduler.add_job(
        runner.async_run_address_ranking,
        kwargs={"session": session, "time_type": enums.RunTimeType.DAY},
        trigger=cron.CronTrigger.from_crontab("1 0 * * *"),
    )
    scheduler.start()
    event_loop.run_forever()


async def init_db() -> sql_asyncio.AsyncSession:
    await db.init_models()
    session = db.async_session()
    await addresses.async_save_addresses_from_all_providers(session)
    return session


def setup_logging() -> None:
    logging.basicConfig(
        format="[%(levelname)s] %(message)s (%(filename)s, %(funcName)s(), line %(lineno)d)",
        level=logging.INFO,
    )


async def run_updating(session: sql_asyncio.AsyncSession) -> None:
    await runner.async_update_all_addresses(session)


if __name__ == "__main__":
    setup_logging()
    event_loop = asyncio.get_event_loop()
    session = event_loop.run_until_complete(init_db())
    event_loop.run_until_complete(async_run_executor(session, event_loop))
