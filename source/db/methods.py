from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from source.db.models import User, PVZTable, Reception, Product
from source.shemas.endpoint_shemas import Registration, PVZUnit, ProductUnit, PVZList, DummyUser
from source.db.db_types import ReceptionStatus, RoleType
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

async def create_reception_for_pvz(session: AsyncSession, pvz_id: UUID) -> Reception:
    new_reception = Reception(
        pvzId=pvz_id,
        status=ReceptionStatus.in_progress
    )
    session.add(new_reception)
    await session.commit()
    await session.refresh(new_reception)
    return new_reception

async def create_product_for_reception(session: AsyncSession, reception_id: UUID, product_unit: ProductUnit) -> Product:
    new_product = Product(
        receptionId=reception_id,
        type=product_unit.type
    )
    session.add(new_product)
    await session.commit()
    await session.refresh(new_product)
    return new_product

async def get_last_reception_by_pvz(session: AsyncSession, pvz_id: UUID) -> Optional[Reception]:
    result = await session.execute(
        select(Reception)
        .where(Reception.pvzId == pvz_id)
        .order_by(Reception.dateTime.desc())
    )
    last_reception = result.scalars().first()
    return last_reception


async def get_pvz_by_reception_id(session: AsyncSession, reception_id: UUID) -> Optional[PVZTable]:
    result = await session.execute(
        select(PVZTable)
        .join(Reception, PVZTable.id == Reception.pvzId)
        .where(Reception.id == reception_id)
    )
    pvz = result.scalars().first()
    return pvz

async def close_reception_for_pvz(session: AsyncSession, pvz_id: UUID) -> Reception:
    new_reception = Reception(
        pvzId=pvz_id,
        status=ReceptionStatus.close
    )
    session.add(new_reception)
    await session.commit()
    await session.refresh(new_reception)
    return new_reception

async def delete_last_product_for_reception(session: AsyncSession, reception_id: UUID) -> Optional[Product]:
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




async def get_pvz_receptions_products(
    session: AsyncSession, query_params: PVZList
) -> List[Dict[str, Any]]:
    offset_val = (query_params.page - 1) * query_params.limit
    stmt = (
        select(Reception)
        .options(selectinload(Reception.products))
        .where(
            Reception.status == ReceptionStatus.in_progress,
            Reception.dateTime >= query_params.start_date,
            Reception.dateTime <= query_params.end_date,
        )
        .order_by(Reception.dateTime.desc())
        .offset(offset_val)
        .limit(query_params.limit)
    )
    result = await session.execute(stmt)
    receptions = result.scalars().unique().all()
    pvz_group: Dict[UUID, List[Dict[str, UUID]]] = {}
    for rec in receptions:
        pvz_id: UUID = rec.pvzId
        if not rec.products:
            continue
        for prod in rec.products:
            if pvz_id not in pvz_group:
                pvz_group[pvz_id] = []
            pvz_group[pvz_id].append({
                "reception": rec.id,
                "product": prod.id
            })
    result_list = [
        {"pvz": pvz_id, "receptions": rec_list} for pvz_id, rec_list in pvz_group.items()
    ]
    return result_list


async def get_or_create_dummy_user(session: AsyncSession, dummy: DummyUser) -> User:
    email = "dummy_employee@example.com"
    if dummy.role == RoleType.moderator:
        email = "dummy_moderator@example.com"
    result = await session.execute(
        select(User).where(User.email == email, User.role == dummy.role)
    )
    user = result.scalars().first()
    if user:
        return user
    dummy_employee = User(
        email="dummy_employee@example.com",
        password="*******",
        role=RoleType.employee
    )
    dummy_moderator = User(
        email="dummy_moderator@example.com",
        password="*******",
        role=RoleType.moderator
    )
    session.add_all([dummy_employee, dummy_moderator])
    await session.commit()
    await session.refresh(dummy_employee)
    await session.refresh(dummy_moderator)
    if dummy.role == RoleType.employee:
        return dummy_employee
    else:
        return dummy_moderator
