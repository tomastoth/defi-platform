from defi_common.database.mongo.beanie_com import create_beanie

_beanie_initialized = False


async def init_mongo():
    if not _beanie_initialized:
        __beanie_initialized = True
        await create_beanie()
