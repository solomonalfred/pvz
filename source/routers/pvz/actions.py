import logging
from datetime import datetime
from uuid import UUID
from typing import Any, List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import Counter

from source.constants.routers import RouterInfo, Endpoints
from source.db.db_types import RoleType, ReceptionStatus
from source.shemas.endpoint_shemas import ResponseMessage, PVZUnit, ProductUnit, PVZList
from source.db.models import User
from source.routers.auth.services import get_current_user, get_async_session
from source.db.methods import (
    create_pvz,
    create_reception_for_pvz,
    get_last_reception_by_pvz,
    create_product_for_reception,
    get_pvz_by_reception_id,
    close_reception_for_pvz,
    delete_last_product_for_reception,
    get_pvz_receptions_products
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PVZ_CREATED = Counter('pvz_created_total', 'Количество созданных ПВЗ')
RECEPTION_CREATED = Counter('receptions_created_total', 'Количество созданных приёмок')
PRODUCT_ADDED = Counter('products_added_total', 'Количество добавленных товаров')

router = APIRouter(
    prefix=RouterInfo.prefix,
    tags=[RouterInfo.pvz_tags]
)

@router.post(
    path=Endpoints.PVZ_END,
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    summary='Создание ПВЗ (только для модераторов)'
)
async def create_pvz_(
    pvz_data: PVZUnit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на создание ПВЗ от пользователя id=%s, роль=%s", current_user.id, current_user.role)
    if current_user.role != RoleType.moderator:
        logger.warning("Доступ запрещен для пользователя id=%s при создании ПВЗ", current_user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    try:
        new_pvz = await create_pvz(db, pvz_data)
        PVZ_CREATED.inc()
        logger.info("ПВЗ создано id=%s, город=%s", new_pvz.id, pvz_data.city)
        return {"description": "ПВЗ создан"}
    except Exception as e:
        logger.exception("Ошибка при создании ПВЗ: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")

@router.post(
    path=Endpoints.RECEPTIONS,
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Создание новой приемки товаров (только для сотрудников ПВЗ)"
)
async def create_reception(
    current_user: User = Depends(get_current_user),
    pvz_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на создание приёмки ПВЗ id=%s от пользователя id=%s", pvz_id, current_user.id)
    if current_user.role != RoleType.employee:
        logger.warning("Доступ запрещен для пользователя id=%s при создании приёмки", current_user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if last_rec and last_rec.status == ReceptionStatus.in_progress:
            logger.warning("Незакрытая приёмка уже существует для ПВЗ id=%s", pvz_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Есть незакрытая приемка")
        new_rec = await create_reception_for_pvz(db, pvz_id)
        RECEPTION_CREATED.inc()
        logger.info("Приёмка создана id=%s для ПВЗ id=%s", new_rec.id, pvz_id)
        return {"description": "Приемка создана"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при создании приёмки: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")

@router.post(
    path=Endpoints.PRODUCTS,
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление товара в текущую приемку (только для сотрудников ПВЗ)"
)
async def create_product(
    product: ProductUnit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на добавление товара в приемку %s от пользователя id=%s", product.pvzId, current_user.id)
    if current_user.role != RoleType.employee:
        logger.warning("Доступ запрещен для пользователя id=%s при добавлении товара", current_user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    try:
        last_rec = await get_last_reception_by_pvz(db, product.pvzId)
        if not last_rec or last_rec.status == ReceptionStatus.close:
            logger.warning("Нет активной приемки для ПВЗ id=%s", product.pvzId)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет активной приемки")
        new_prod = await create_product_for_reception(db, last_rec.id, product)
        PRODUCT_ADDED.inc()
        logger.info("Товар добавлен id=%s в приёмку id=%s", new_prod.id, last_rec.id)
        return {"description": "Товар добавлен"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при добавлении товара: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")

@router.post(
    path=Endpoints.CLOSE_LAST_REC,
    response_model=ResponseMessage,
    status_code=status.HTTP_200_OK,
    summary="Закрытие последней открытой приемки товаров в рамках ПВЗ"
)
async def close_reception(
    current_user: User = Depends(get_current_user),
    pvz_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на закрытие приёмки для ПВЗ id=%s от пользователя id=%s", pvz_id, current_user.id)
    if current_user.role != RoleType.employee:
        logger.warning("Доступ запрещен для пользователя id=%s при закрытии приёмки", current_user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if not last_rec or last_rec.status == ReceptionStatus.close:
            logger.warning("Нет открытой приёмки для закрытия ПВЗ id=%s", pvz_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Приемка уже закрыта или не существует")
        closed = await close_reception_for_pvz(db, pvz_id)
        logger.info("Приемка закрыта id=%s", closed.id)
        return {"description": "Приемка закрыта"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при закрытии приёмки: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")

@router.post(
    path=Endpoints.DELETE_PRODUCT,
    response_model=ResponseMessage,
    status_code=status.HTTP_200_OK,
    summary="Удаление последнего добавленного товара из текущей приемки (LIFO)"
)
async def delete_last_product(
    current_user: User = Depends(get_current_user),
    pvz_id: UUID = Query(...),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на удаление товара из приёмки ПВЗ id=%s от пользователя id=%s", pvz_id, current_user.id)
    if current_user.role != RoleType.employee:
        logger.warning("Доступ запрещен для пользователя id=%s при удалении товара", current_user.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if not last_rec or last_rec.status == ReceptionStatus.close:
            logger.warning("Нет активной приемки или товаров для удаления в ПВЗ id=%s", pvz_id)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет активной приемки или товаров для удаления")
        deleted = await delete_last_product_for_reception(db, last_rec.id)
        if deleted:
            logger.info("Товар удален id=%s", deleted.id)
            return {"description": "Товар удален"}
        logger.info("Товары для удаления не найдены в приёмке id=%s", last_rec.id)
        return {"description": "Не осталось товаров"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при удалении товара: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")

@router.get(
    path=Endpoints.PVZ_END,
    status_code=status.HTTP_200_OK,
    summary="Получение списка ПВЗ с фильтрацией по дате и пагинацией"
)
async def pvz_list(
    start_date: str = Query(..., description="Дата начала dd.MM.YYYYHH:MM:SS"),
    end_date: str = Query(..., description="Дата окончания dd.MM.YYYYHH:MM:SS"),
    page: int = Query(1, ge=1),
    limit: int = Query(1, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    logger.info("Получен запрос списка ПВЗ от пользователя id=%s, период %s - %s, страница=%s, лимит=%s", current_user.id, start_date, end_date, page, limit)
    try:
        start_dt = datetime.strptime(start_date, "%d.%m.%Y%H:%M:%S")
        end_dt = datetime.strptime(end_date, "%d.%m.%Y%H:%M:%S")
    except ValueError:
        logger.warning("Неверный формат даты: start=%s, end=%s", start_date, end_date)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный формат даты. Ожидается dd.MM.YYYYHH:MM:SS")
    try:
        result_list = await get_pvz_receptions_products(db, PVZList(start_date=start_dt, end_date=end_dt, page=page, limit=limit))
        logger.info("Возвращено групп ПВЗ: %s", len(result_list))
        return result_list
    except Exception as e:
        logger.exception("Ошибка при получении списка ПВЗ: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный запрос")
