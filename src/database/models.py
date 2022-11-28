from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, orm

from src.database import db


class Address(db.Base):  # type: ignore
    __tablename__ = "address"
    id = Column(Integer, primary_key=True)  # noqa
    time_created = Column(DateTime(), default=datetime.now())
    time_updated = Column(DateTime(), default=datetime.now())
    address = Column(String)
    blockchain_type = Column(String)
    address_updates = orm.relationship(
        "AggregatedBalanceUpdate", back_populates="address"
    )
    performance_results = orm.relationship(
        "PerformanceRunResult", back_populates="address"
    )
    address_performance_ranks = orm.relationship(
        "AddressPerformanceRank", back_populates="address"
    )

    def __repr__(self) -> str:
        return f"address: {self.address}, blockchain_type: {self.blockchain_type}"


class AggregatedBalanceUpdate(db.Base):  # type: ignore
    __tablename__ = "address_updates"
    id = Column(Integer, primary_key=True)  # noqa
    time_created = Column(DateTime(), default=datetime.now())
    time_updated = Column(DateTime(), default=datetime.now())
    value_usd = Column(Float, nullable=False)
    timestamp = Column(sqlalchemy.BigInteger, nullable=False)
    time = Column(DateTime, nullable=False)
    symbol = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value_pct = Column(Float, nullable=False)
    address = orm.relationship(Address, back_populates="address_updates")
    address_id = Column(Integer, ForeignKey("address.id"))

    def __repr__(self) -> str:
        return (
            f"symbol: {self.symbol}, value_usd: {self.value_usd}, price: {self.price} "
            f"time: {self.timestamp} address: {self.address}"
        )


class PerformanceRunResult(db.Base):  # type: ignore
    __tablename__ = "performance_run_results"
    id = Column(Integer, primary_key=True)  # noqa
    time_created = Column(DateTime(), default=datetime.now())
    time_updated = Column(DateTime(), default=datetime.now())
    performance = Column(Float, nullable=False)
    start_time = Column(DateTime(), nullable=False)
    end_time = Column(DateTime(), nullable=False)
    address = orm.relationship(Address, back_populates="performance_results")
    address_id = Column(Integer, ForeignKey("address.id"))


class AddressPerformanceRank(db.Base):  # type: ignore
    __tablename__ = "address_performance_rank"
    id = Column(Integer, primary_key=True)  # noqa
    time_created = Column(DateTime(), default=datetime.now())
    time_updated = Column(DateTime(), default=datetime.now())
    performance = Column(Float, nullable=False)
    time = Column(DateTime(), nullable=False)
    address = orm.relationship(Address, back_populates="address_performance_ranks")
    address_id = Column(Integer, ForeignKey("address.id"))
    ranking_type = Column(String, nullable=False)
    rank = Column(Integer, sqlalchemy.CheckConstraint("rank > 0"))
