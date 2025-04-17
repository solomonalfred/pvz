from datetime import datetime
from uuid import UUID
from typing import Annotated, Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
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
    current_user: Annotated[User, Depends(get_current_user)],
    pvz_data: PVZUnit,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    user_role = current_user.role
    if user_role != RoleType.moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    try:
        await create_pvz(db, pvz_data)
        PVZ_CREATED.inc()
        return {"description": "ПВЗ создан"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос",
        )

@router.post(
    path=Endpoints.RECEPTIONS,
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Создание новой приемки товаров (только для сотрудников ПВЗ)"
)
async def create_reception(
    current_user: Annotated[User, Depends(get_current_user)],
    pvz_id: UUID,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    user_role = current_user.role
    if user_role != RoleType.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if last_rec is not None and last_rec.status == ReceptionStatus.in_progress:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный запрос или есть незакрытая приемка",
            )
        await create_reception_for_pvz(db, pvz_id)
        RECEPTION_CREATED.inc()
        return {"description": "Приемка создана"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос или есть незакрытая приемка",
        )

@router.post(
    path=Endpoints.PRODUCTS,
    response_model=ResponseMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление товара в текущую приемку (только для сотрудников ПВЗ)"
)
async def create_product(
    current_user: Annotated[User, Depends(get_current_user)],
    product: ProductUnit,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    user_role = current_user.role
    if user_role != RoleType.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    try:
        last_rec = await get_last_reception_by_pvz(db, product.pvzId)
        if last_rec is None or last_rec.status == ReceptionStatus.close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный запрос или нет активной приемки",
            )
        await create_product_for_reception(db, last_rec.id, product)
        PRODUCT_ADDED.inc()
        return {"description": "Товар добавлен"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос или нет активной приемки",
        )

@router.post(
    path=Endpoints.CLOSE_LAST_REC,
    response_model=ResponseMessage,
    status_code=status.HTTP_200_OK,
    summary="Закрытие последней открытой приемки товаров в рамках ПВЗ"
)
async def close_reception(
    current_user: Annotated[User, Depends(get_current_user)],
    pvz_id: UUID,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    user_role = current_user.role
    if user_role != RoleType.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if last_rec is None or last_rec.status == ReceptionStatus.close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный запрос или приемка уже закрыта",
            )
        await close_reception_for_pvz(db, pvz_id)
        return {"description": "Приемка закрыта"}
    except Exception as e:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if last_rec.status == ReceptionStatus.close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный запрос или приемка уже закрыта",
            )

@router.post(
    path=Endpoints.DELETE_PRODUCT,
    response_model=ResponseMessage,
    status_code=status.HTTP_200_OK,
    summary="Удаление последнего добавленного товара из текущей приемки (LIFO, только для сотрудников ПВЗ)"
)
async def delete_last_product(
    current_user: Annotated[User, Depends(get_current_user)],
    pvz_id: UUID,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    user_role = current_user.role
    if user_role != RoleType.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )
    try:
        last_rec = await get_last_reception_by_pvz(db, pvz_id)
        if last_rec is None or last_rec.status == ReceptionStatus.close:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный запрос, нет активной приемки или нет товаров для удаления",
            )
        resp = await delete_last_product_for_reception(db, last_rec.id)
        if resp:
            return {"description": "Товар удален"}
        return {"description": "Не осталось товаров на этой приёмке"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос, нет активной приемки или нет товаров для удаления",
        )


@router.get(
    path=Endpoints.PVZ_END,  # например, "/pvz"
    status_code=status.HTTP_200_OK,
    summary="Получение списка ПВЗ с фильтрацией по дате приемки и пагинацией"
)
async def pvz_list(
        start_date: str = Query(..., description="Дата начала в формате dd.MM.YYYYHH:MM:SS"),
        end_date: str = Query(..., description="Дата окончания в формате dd.MM.YYYYHH:MM:SS"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(1, ge=1, le=30, description="Количество элементов на странице"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session)
) -> List[Dict[str, Any]]:
    try:
        start_date_parsed = datetime.strptime(start_date, "%d.%m.%Y%H:%M:%S")
        end_date_parsed = datetime.strptime(end_date, "%d.%m.%Y%H:%M:%S")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Ожидается dd.MM.YYYYHH:MM:SS"
        )
    pvz_data = PVZList(
        start_date=start_date_parsed,
        end_date=end_date_parsed,
        page=page,
        limit=limit
    )
    try:
        result_list = await get_pvz_receptions_products(db, pvz_data)
        return result_list
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос",
        )
