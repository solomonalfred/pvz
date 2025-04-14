from typing import Annotated, Optional
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Enum, DateTime, func
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import relationship

from source.db.db_types import RoleType, ReceptionStatus, ProductType, CityType

MetaStr = Annotated[str, 255]
DetailedInfoStr = Annotated[str, 2000]
ends, tab = "\n", "\t"

@as_declarative()
class Base:
    __table_args__ = {"extend_existing": True}

    type_annotation_map = {MetaStr: String(255), DetailedInfoStr: String(2000)}

    def __repr__(self):
        columns = []
        for column in self.__table__.columns.keys():
            columns.append(f"{column}={getattr(self, column)}")
        return f"[{self.__class__.__name__}]{ends}{tab}{f',{ends + tab}'.join(columns)}"

    id = Column(Integer, primary_key=True, index=True)

class User(Base):
    __tablename__ = "user"

    password: Annotated[str, 255] = Column(String(255), nullable=False)
    email: Annotated[str, 255] = Column(String(255), nullable=False)
    role: Annotated[str, 64] = Column(Enum(RoleType, name="role_enum"), nullable=False, default=RoleType.employee)

class PVZTable(Base):
    __tablename__ = "pvztable"

    registrationDate: Annotated[DateTime, None] = Column(DateTime, nullable=False, default=func.now())
    city: Annotated[str, 64] = Column(Enum(CityType, name="city_enum"), nullable=False)
    receptions = relationship("Reception", back_populates="pvz", cascade="all, delete-orphan")

class Reception(Base):
    __tablename__ = "reception"

    dateTime: Annotated[DateTime, None] = Column(DateTime, nullable=False, default=func.now())
    pvzId: int = Column(Integer, ForeignKey('pvztable.id'), nullable=False)
    status: Annotated[str, 64] = Column(Enum(ReceptionStatus, name="reception_status_enum"),
                                        nullable=False, default=ReceptionStatus.in_progress)
    pvz = relationship("PVZTable", back_populates="receptions")
    products = relationship("Product", back_populates="reception", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "product"

    dateTime: Annotated[DateTime, None] = Column(DateTime, nullable=False, default=func.now())
    type: Annotated[str, 64] = Column(Enum(ProductType, name="product_type_enum"),
                                      nullable=False)
    receptionId: int = Column(Integer, ForeignKey('reception.id'), nullable=False)
    reception = relationship("Reception", back_populates="products")
