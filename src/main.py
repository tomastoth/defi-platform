import asyncio
import logging

from apscheduler.schedulers import asyncio as asyncio_scheduler
from apscheduler.triggers import cron
from sqlalchemy.ext import asyncio as sql_asyncio

from src import addresses, runner
from src.database import db


def run_executor(
    session: sql_asyncio.AsyncSession, event_loop: asyncio.AbstractEventLoop
) -> None:
    event_loop.run_until_complete(runner.async_update_all_addresses(session))
    scheduler = asyncio_scheduler.AsyncIOScheduler(event_loop=event_loop)
    scheduler.add_job(
        runner.async_update_all_addresses,
        kwargs={"session": session},
        trigger=cron.CronTrigger.from_crontab("*/15 * * * *"),
        minute=5,
        second=0,
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
    run_executor(session, event_loop)