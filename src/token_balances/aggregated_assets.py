import logging
from abc import ABC, abstractmethod

from defi_common import data, exceptions

from src import spec

log = logging.getLogger(__name__)


def add_pct_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset],
        sum_value_usd: float,
        run_time: int,
) -> list[data.AggregatedAsset]:
    """
    Adds percentage of owned value for each asset from sum value usd
    """
    aggregated_assets: list[data.AggregatedAsset] = []
    for aggregated_usd_asset in aggregated_usd_assets:
        asset_pct_value = (aggregated_usd_asset.value_usd / sum_value_usd) * 100.0
        aggregated_asset = data.AggregatedAsset(
            symbol=aggregated_usd_asset.symbol,
            amount=aggregated_usd_asset.amount,
            price=aggregated_usd_asset.price,
            value_usd=aggregated_usd_asset.value_usd,
            value_pct=asset_pct_value,
            timestamp=run_time,
        )
        aggregated_assets.append(aggregated_asset)
    return aggregated_assets


def sort_by_value_usd(
        value_usd_list: list[spec.UsdValue],
) -> list[spec.UsdValue]:
    value_usd_list.sort(key=lambda x: x.value_usd, reverse=True)
    return value_usd_list  # type ignore


def calc_sum_usd_value(
        aggregated_usd_assets: list[data.AggregatedUsdAsset],
) -> float:
    return sum([asset.value_usd for asset in aggregated_usd_assets])  # type: ignore


class AggregatedAssetProvider(ABC):
    @abstractmethod
    async def async_get_assets_for_address(
            self, address: data.Address, run_time: int
    ) -> data.AddressUpdate | None:
        pass


def _combine_aggregated_usd_assets(
        assets_to_combine: list[data.AggregatedUsdAsset],
) -> data.AggregatedUsdAsset:
    if not assets_to_combine:
        raise exceptions.InvalidParamError()
    sum_amount = 0.0
    sum_value_usd = 0.0
    sum_weighted_price = 0.0
    sum_weight = 0.0

    for asset in assets_to_combine:
        sum_amount += asset.amount
        sum_value_usd += asset.value_usd
        sum_weighted_price += asset.amount * asset.price
        sum_weight += asset.amount
    avg_price = sum_weighted_price / sum_weight
    symbol = assets_to_combine[0].symbol
    return data.AggregatedUsdAsset(
        symbol=symbol, price=avg_price, value_usd=sum_value_usd, amount=sum_amount
    )


def aggregate_usd_assets(
        all_aggregated_usd_assets: list[data.AggregatedUsdAsset],
) -> list[data.AggregatedUsdAsset]:
    aggregated_dict: dict[str, data.AggregatedUsdAsset] = {}
    for asset in all_aggregated_usd_assets:
        lower_asset_symbol = asset.symbol.lower()
        if lower_asset_symbol not in aggregated_dict:
            aggregated_dict[lower_asset_symbol] = asset
        else:
            found_agg_asset = aggregated_dict[lower_asset_symbol]
            combined_asset = _combine_aggregated_usd_assets([found_agg_asset, asset])
            aggregated_dict[lower_asset_symbol] = combined_asset

    return list(aggregated_dict.values())


