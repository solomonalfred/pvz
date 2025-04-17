import asyncio
import grpc
from sqlalchemy import select
import pvz_pb2
import pvz_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from typing_extensions import AsyncGenerator
import sqlalchemy as sql
from contextlib import asynccontextmanager
from enum import StrEnum, auto
from typing import Annotated
from sqlalchemy import Column, ForeignKey, String, Enum, DateTime, func
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

# from source.config import get_settings
from config import get_settings


class RoleType(StrEnum):
    employee = auto()
    moderator = auto()

class ReceptionStatus(StrEnum):
    in_progress = auto()
    close = auto()

class ProductType(StrEnum):
    electonic = "электроника"
    clothes = "одежда"
    shoes = "обувь"

class CityType(StrEnum):
    moscow = "Москва"
    spb = "Санкт-Петербург"
    kazan = "Казань"


class SessionManager:
    def __init__(self):
        settings = get_settings()
        self.async_engine = create_async_engine(url=settings.DB_URI, echo=False)

        self.async_session = sessionmaker(self.async_engine, expire_on_commit=False, class_=AsyncSession)

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
        return cls.instance

    def get_session(self) -> Session | AsyncSession:
        return self.async_session()

    async def get_table_names(self):
        async with self.async_engine.connect() as conn:
            tables = await conn.run_sync(lambda sync_conn: sql.inspect(sync_conn).get_table_name())
            return tables

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = SessionManager().get_session()

    async with async_session:
        try:
            yield async_session
            await async_session.commit()
        except SQLAlchemyError as exc:
            await async_session.rollback()
            raise exc
        finally:
            await async_session.close()

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

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

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
    pvzId: uuid.UUID = Column(PG_UUID(as_uuid=True), ForeignKey('pvztable.id'), nullable=False)
    status: Annotated[str, 64] = Column(
        Enum(ReceptionStatus, name="reception_status_enum"),
        nullable=False,
        default=ReceptionStatus.in_progress
    )
    pvz = relationship("PVZTable", back_populates="receptions")
    products = relationship("Product", back_populates="reception", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "product"

    dateTime: Annotated[DateTime, None] = Column(DateTime, nullable=False, default=func.now())
    type: Annotated[str, 64] = Column(Enum(ProductType, name="product_type_enum"), nullable=False)
    receptionId: uuid.UUID = Column(PG_UUID(as_uuid=True), ForeignKey('reception.id'), nullable=False)
    reception = relationship("Reception", back_populates="products")

class PVZService(pvz_pb2_grpc.PVZServiceServicer):
    async def GetPVZList(self, request, context):
        async with get_async_session() as session:
            stmt = select(PVZTable)
            result = await session.execute(stmt)
            pvz_objs = result.scalars().all()

            pvz_messages = []
            for obj in pvz_objs:
                ts = Timestamp()
                ts.FromDatetime(obj.registrationDate)
                pvz_messages.append(
                    pvz_pb2.PVZ(
                        id=str(obj.id),
                        registration_date=ts,
                        city=obj.city.value
                    )
                )

            return pvz_pb2.GetPVZListResponse(pvzs=pvz_messages)

async def serve() -> None:
    server = grpc.aio.server()
    pvz_pb2_grpc.add_PVZServiceServicer_to_server(PVZService(), server)
    listen_addr = "[::]:3000"
    server.add_insecure_port(listen_addr)
    print(f"gRPC сервер запущен на {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
