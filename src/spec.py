import typing

from defi_common import data


UsdValue = typing.TypeVar("UsdValue", bound=data.UsdValue)
AssetProvider = typing.Callable[
    [data.Address, int],
    typing.Coroutine[typing.Any, typing.Any, data.AddressUpdate | None],
]
