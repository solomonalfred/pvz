import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from source.db.models import User, PVZTable, Reception, Product
from source.shemas.endpoint_shemas import (
    Registration,
    PVZUnit,
    ProductUnit,
    PVZList,
    DummyUser
)
from source.db.db_types import ReceptionStatus, RoleType
from source.utils.hasher import PasswordManager


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

hashed = PasswordManager()

async def create_user(session: AsyncSession, registration: Registration) -> User:
    logger.info("Создание пользователя с email=%s, роль=%s", registration.email, registration.role)
    hashed_password = hashed.hash_password(registration.password)
    new_user = User(
        email=registration.email,
        password=hashed_password,
        role=registration.role
    )
    try:
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        logger.info("Пользователь создан, id=%s", new_user.id)
        return new_user
    except Exception as e:
        logger.exception("Ошибка при создании пользователя: %s", e)
        raise

async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    logger.debug("Получение пользователя по email=%s", email)
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    logger.debug("Найден пользователь: %s", user)
    return user

async def create_pvz(session: AsyncSession, pvz_unit: PVZUnit) -> PVZTable:
    logger.info("Создание ПВЗ с городом=%s", pvz_unit.city)
    new_pvz = PVZTable(city=pvz_unit.city)
    try:
        session.add(new_pvz)
        await session.commit()
        await session.refresh(new_pvz)
        logger.info("ПВЗ создано, id=%s", new_pvz.id)
        return new_pvz
    except Exception as e:
        logger.exception("Ошибка при создании ПВЗ: %s", e)
        raise

async def create_reception_for_pvz(session: AsyncSession, pvz_id: UUID) -> Reception:
    logger.info("Создание приёмки для ПВЗ id=%s", pvz_id)
    new_reception = Reception(pvzId=pvz_id, status=ReceptionStatus.in_progress)
    try:
        session.add(new_reception)
        await session.commit()
        await session.refresh(new_reception)
        logger.info("Приёмка создана, id=%s для ПВЗ id=%s", new_reception.id, pvz_id)
        return new_reception
    except Exception as e:
        logger.exception("Ошибка при создании приёмки: %s", e)
        raise

async def create_product_for_reception(
    session: AsyncSession,
    reception_id: UUID,
    product_unit: ProductUnit
) -> Product:
    logger.info("Добавление товара в приёмку id=%s, тип=%s", reception_id, product_unit.type)
    new_product = Product(receptionId=reception_id, type=product_unit.type)
    try:
        session.add(new_product)
        await session.commit()
        await session.refresh(new_product)
        logger.info("Товар добавлен, id=%s в приёмке id=%s", new_product.id, reception_id)
        return new_product
    except Exception as e:
        logger.exception("Ошибка при добавлении товара: %s", e)
        raise

async def get_last_reception_by_pvz(
    session: AsyncSession, pvz_id: UUID
) -> Optional[Reception]:
    logger.debug("Запрос последней приёмки для ПВЗ id=%s", pvz_id)
    result = await session.execute(
        select(Reception)
        .where(Reception.pvzId == pvz_id)
        .order_by(Reception.dateTime.desc())
    )
    last_reception = result.scalars().first()
    logger.debug("Последняя приёмка: %s", last_reception)
    return last_reception

async def get_pvz_by_reception_id(
    session: AsyncSession, reception_id: UUID
) -> Optional[PVZTable]:
    logger.debug("Получение ПВЗ по id приёмки=%s", reception_id)
    result = await session.execute(
        select(PVZTable)
        .join(Reception, PVZTable.id == Reception.pvzId)
        .where(Reception.id == reception_id)
    )
    pvz = result.scalars().first()
    logger.debug("Найдено ПВЗ: %s", pvz)
    return pvz

async def close_reception_for_pvz(session: AsyncSession, pvz_id: UUID) -> Reception:
    logger.info("Закрытие приёмки для ПВЗ id=%s", pvz_id)
    new_reception = Reception(pvzId=pvz_id, status=ReceptionStatus.close)
    try:
        session.add(new_reception)
        await session.commit()
        await session.refresh(new_reception)
        logger.info("Приёмка закрыта, id=%s для ПВЗ id=%s", new_reception.id, pvz_id)
        return new_reception
    except Exception as e:
        logger.exception("Ошибка при закрытии приёмки: %s", e)
        raise

async def delete_last_product_for_reception(
    session: AsyncSession, reception_id: UUID
) -> Optional[Product]:
    logger.info("Удаление последнего товара для приёмки id=%s", reception_id)
    result = await session.execute(
        select(Product)
        .where(Product.receptionId == reception_id)
        .order_by(Product.dateTime.desc())
    )
    last_product = result.scalars().first()
    if last_product:
        try:
            await session.delete(last_product)
            await session.commit()
            logger.info("Товар удалён, id=%s", last_product.id)
        except Exception as e:
            logger.exception("Ошибка при удалении товара: %s", e)
            raise
    else:
        logger.info("Товаров для удаления не найдено в приёмке id=%s", reception_id)
    return last_product

async def get_pvz_receptions_products(
    session: AsyncSession, query_params: PVZList
) -> List[Dict[str, Any]]:
    logger.info(
        "Получение приёмо-товаров ПВЗ за период %s - %s, страница=%s, размер страницы=%s",
        query_params.start_date, query_params.end_date,
        query_params.page, query_params.limit
    )
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
            pvz_group.setdefault(pvz_id, []).append({
                "reception": rec.id,
                "product": prod.id
            })
    result_list = [{"pvz": k, "receptions": v} for k, v in pvz_group.items()]
    logger.info("Найдено групп ПВЗ: %s", len(result_list))
    return result_list

async def get_or_create_dummy_user(
    session: AsyncSession, dummy: DummyUser
) -> User:
    email = (
        "dummy_moderator@example.com"
        if dummy.role == RoleType.moderator
        else "dummy_employee@example.com"
    )
    logger.info("Получение или создание тестового пользователя роль=%s, email=%s", dummy.role, email)
    result = await session.execute(
        select(User).where(User.email == email, User.role == dummy.role)
    )
    user = result.scalars().first()
    if user:
        logger.debug("Найден тестовый пользователь id=%s", user.id)
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
    chosen = dummy_moderator if dummy.role == RoleType.moderator else dummy_employee
    logger.info("Возвращен тестовый пользователь id=%s", chosen.id)
    return chosen