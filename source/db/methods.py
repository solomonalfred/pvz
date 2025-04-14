from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from source.db.models import User, PVZTable, Reception, Product
from source.shemas.endpoint_shemas import Registration, PVZUnit, ProductUnit
from source.db.db_types import ReceptionStatus
from source.db.engine import get_async_session
from source.utils.hasher import PasswordManager


hashed = PasswordManager()

async def create_user(session: AsyncSession,
                      registration: Registration) -> User:
    hashed_password = hashed.hash_password(registration.password)
    new_user = User(
        email=registration.email,
        password=hashed_password,
        role=registration.role
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    return user

async def create_pvz(session: AsyncSession, pvz_unit: PVZUnit) -> PVZTable:
    new_pvz = PVZTable(
        city=pvz_unit.city
    )
    session.add(new_pvz)
    await session.commit()
    await session.refresh(new_pvz)
    return new_pvz

async def create_reception_for_pvz(session: AsyncSession, pvz_id: int) -> Reception:
    new_reception = Reception(
        pvzId=pvz_id,
        status=ReceptionStatus.in_progress
    )
    session.add(new_reception)
    await session.commit()
    await session.refresh(new_reception)
    return new_reception

async def create_product_for_reception(session: AsyncSession, reception_id: int, product_unit: ProductUnit) -> Product:
    new_product = Product(
        receptionId=reception_id,
        type=product_unit.type
    )
    session.add(new_product)
    await session.commit()
    await session.refresh(new_product)
    return new_product

async def get_last_reception_by_pvz(session: AsyncSession, pvz_id: int) -> Optional[Reception]:
    result = await session.execute(
        select(Reception)
        .where(Reception.pvzId == pvz_id)
        .order_by(Reception.dateTime.desc())
    )
    last_reception = result.scalars().first()
    return last_reception


async def get_pvz_by_reception_id(session: AsyncSession, reception_id: int) -> Optional[PVZTable]:
    result = await session.execute(
        select(PVZTable)
        .join(Reception, PVZTable.id == Reception.pvzId)
        .where(Reception.id == reception_id)
    )
    pvz = result.scalars().first()
    return pvz

async def close_reception_for_pvz(session: AsyncSession, pvz_id: int) -> Reception:
    new_reception = Reception(
        pvzId=pvz_id,
        status=ReceptionStatus.close
    )
    session.add(new_reception)
    await session.commit()
    await session.refresh(new_reception)
    return new_reception

async def delete_last_product_for_reception(session: AsyncSession, reception_id: int) -> Optional[Product]:
    result = await session.execute(
        select(Product)
        .where(Product.receptionId == reception_id)
        .order_by(Product.dateTime.desc())
    )
    last_product = result.scalars().first()
    if last_product:
        await session.delete(last_product)
        await session.commit()
    return last_product
