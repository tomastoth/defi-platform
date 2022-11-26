from datetime import datetime

from src import data, math_utils


def _add_assets_to_dict(
    assets: list[data.AggregatedAsset],
) -> dict[str, data.AggregatedAsset]:
    asset_dict = {}
    for asset in assets:
        symbol_lowercase = asset.symbol.lower()
        asset_dict[symbol_lowercase] = asset
    return asset_dict


def calculate_performance(
    old_address_updates: list[data.AggregatedAsset],
    new_address_updates: list[data.AggregatedAsset],
    start_time: datetime,
    address: data.Address,
    end_time: datetime = datetime.now(),
) -> data.PerformanceResult:
    old_assets_dict = _add_assets_to_dict(old_address_updates)
    new_assets_dict = _add_assets_to_dict(new_address_updates)
    performance = 0.0
    for old_asset_symbol, old_asset in old_assets_dict.items():
        if old_asset_symbol in new_assets_dict:
            new_asset = new_assets_dict[old_asset_symbol]
            asset_price_change_pct = math_utils.calc_percentage_diff(
                new_asset.price, old_asset.price
            )
            old_asset_pct_held = old_asset.value_pct / 100.0
            performance_gain = asset_price_change_pct * old_asset_pct_held
            performance += performance_gain
    performance_result = data.PerformanceResult(
        performance=performance,
        start_time=start_time,
        end_time=end_time,
        address=address,
    )
    return performance_result
