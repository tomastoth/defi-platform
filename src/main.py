import asyncio

from src import data, debank, runner
from src.database import db, services


async def main() -> None:
    await db.init_models()
    async with db.async_session() as session:
        add = data.Address(address="0x91826f730bfe0db68f27400cb5587fb64d42867f")
        await services.async_save_address(add, session)
        await runner.async_update_all_addresses(session)


async def init_debank():
    dbnk = debank.Debank()
    add = data.Address(address="0x91826f730bfe0db68f27400cb5587fb64d42867f")
    acc_overview = await dbnk.async_get_assets_for_address(address=add)
    for agg_asset in acc_overview.aggregated_assets:
        print(agg_asset)


if __name__ == "__main__":
    asyncio.run(main())
