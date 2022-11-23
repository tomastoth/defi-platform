from sqlalchemy.ext import asyncio as sql_asyncio

from src import debank, spec
from src.database import services


async def async_update_all_addresses(
    session: sql_asyncio.AsyncSession, provide_assets: spec.AssetProvider | None = None
) -> None:
    addresses_models = await services.async_find_all_addresses(session)
    addresses = [
        services.convert_address_model(address_model)
        for address_model in addresses_models
    ]
    debank_client = debank.Debank()
    if not provide_assets:
        provide_assets = debank_client.async_get_assets_for_address
    address_updates = [await provide_assets(address) for address in addresses]
    for i, address_update in enumerate(address_updates):
        address = addresses[i]
        for aggregated_asset in address_update.aggregated_assets:
            await services.async_save_aggregated_update(
                aggregated_asset, address, session
            )
