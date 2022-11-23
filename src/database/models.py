import sqlalchemy
from sqlalchemy import Column, Float, ForeignKey, String, orm

from src.database import db


class Address(db.Base):  # type: ignore
    __tablename__ = "address"
    id = Column(sqlalchemy.Integer, primary_key=True)  # noqa
    address = Column(String)
    blockchain_type = Column(String)
    address_updates = orm.relationship(
        "AggregatedBalanceUpdate", back_populates="address"
    )

    def __repr__(self) -> str:
        return f"address: {self.address}, blockchain_type: {self.blockchain_type}"


class AggregatedBalanceUpdate(db.Base):  # type: ignore
    __tablename__ = "address_updates"
    id = Column(sqlalchemy.Integer, primary_key=True)  # noqa
    value_usd = Column(Float)
    time = Column(sqlalchemy.BigInteger)
    symbol = Column(String)
    amount = Column(Float)
    price = Column(Float)
    value_pct = Column(Float)
    address = orm.relationship(Address, back_populates="address_updates")
    address_id = Column(sqlalchemy.Integer, ForeignKey("address.id"))

    def __repr__(self) -> str:
        return (
            f"symbol: {self.symbol}, value_usd: {self.value_usd}, price: {self.price} "
            f"time: {self.time} address: {self.address}"
        )
