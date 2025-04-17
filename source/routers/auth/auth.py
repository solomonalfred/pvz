import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from source.constants.routers import RouterInfo, Endpoints
from source.shemas.endpoint_shemas import Token, Registration, Credentials, DummyUser
from source.db.engine import get_async_session
from source.db.methods import (
    get_user_by_email,
    create_user,
    get_or_create_dummy_user
)
from source.routers.auth.services import (
    generate_token,
    authenticate_user
)
from source.routers.auth.exception import credentials_exception


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix=RouterInfo.prefix,
    tags=[RouterInfo.auth_tags]
)

@router.post(
    path=Endpoints.DUMMY,
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Получение тестового токена"
)
async def dummy_login(
    dummy: DummyUser,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Получен запрос на тестовый логин с ролью=%s", dummy.role)
    try:
        user = await get_or_create_dummy_user(db, dummy)
        logger.info("Найден или создан тестовый пользователь id=%s, role=%s", user.id, user.role)
        token = await generate_token({"data": user.email, "role": user.role})
        logger.info("Сгенерирован тестовый токен для user_id=%s", user.id)
        return token
    except Exception as e:
        logger.exception("Ошибка при получении тестового токена: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос"
        )

@router.post(
    path=Endpoints.REGISTRATION,
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя"
)
async def registration(
    user_data: Registration,
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    logger.info("Запрос на регистрацию пользователя email=%s, role=%s", user_data.email, user_data.role)
    try:
        existing = await get_user_by_email(db, str(user_data.email))
    except Exception as e:
        logger.exception("Ошибка при проверке существующего пользователя: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос"
        )
    if existing:
        logger.warning("Попытка регистрации уже существующего пользователя email=%s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует"
        )
    try:
        new_user = await create_user(db, user_data)
        logger.info("Пользователь зарегистрирован id=%s", new_user.id)
    except Exception as e:
        logger.exception("Ошибка при создании пользователя: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос"
        )
    token = await generate_token({"data": user_data.email, "role": user_data.role})
    logger.info("Сгенерирован токен для нового пользователя id=%s", new_user.id)
    return token

@router.post(
    path=Endpoints.LOGIN,
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Авторизация пользователя"
)
async def login(
    user_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_session),
) -> Any:
    logger.info("Запрос на авторизацию пользователя username=%s", user_data.username)
    try:
        user = await authenticate_user(
            Credentials(email=user_data.username, password=user_data.password),
            db
        )
        if not user:
            logger.warning("Неверные учетные данные для username=%s", user_data.username)
            raise credentials_exception
        token = await generate_token({"data": user.email, "role": user.role})
        logger.info("Успешная авторизация user_id=%s", user.id)
        return token
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ошибка при авторизации пользователя: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные"
        )
