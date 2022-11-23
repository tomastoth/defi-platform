from src import data


def create_aggregated_update(
    value_usd: float, amount: float, price: float, value_pct: float
) -> data.AddressUpdate:
    return data.AddressUpdate(
        value_usd=value_usd,
        blockchain_wallet_assets=[],
        aggregated_assets=[
            data.AggregatedAsset(
                symbol="ETH",
                amount=amount,
                price=price,
                time_ms=101,
                value_pct=value_pct,
                value_usd=value_pct,
            )
        ],
    )
