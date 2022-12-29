class AddressAlreadyExistsError(Exception):
    pass


class AddressNotCreatedError(Exception):
    pass


class AddressNotFoundError(Exception):
    pass


class DebankDataMissingError(Exception):
    pass


class InvalidHttpResponseError(Exception):
    pass


class UnknownEnumError(Exception):
    pass


class DebankDataInvalidError(Exception):
    pass


class DebankUnknownBlockchainError(Exception):
    pass


class CovalentUnknownBlockchainError(Exception):
    pass


class NansenPortfolioUnknownBlockchainError(Exception):
    pass

class InvalidParamError(Exception):
    pass