from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from source.constants.routers import RouterInfo, Endpoints
from source.shemas.endpoint_shemas import Token, Registration, Credentials, DummyUser
from source.db.engine import get_async_session
from source.db.methods import (
    get_user_by_email,
    create_user
)
from source.routers.auth.services import (
    generate_token,
    authenticate_user
)
from source.routers.auth.exception import credentials_exception


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
    user: DummyUser
) -> Any:
    ...

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
    try:
        user = await get_user_by_email(db, str(user_data.email))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос",
        )
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует",
        )
    try:
        await create_user(db, user_data)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный запрос",
        )
    token = await generate_token({"data": user_data.email, "role": user_data.role})
    return token

@router.post(
    path=Endpoints.LOGIN,
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Авторизация пользователя",
)
async def login(
    user_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_session),
) -> Any:
    try:
        user = await authenticate_user(
            Credentials(email=user_data.username, password=user_data.password),
            db
        )
        if not user:
            raise credentials_exception
        tokens = await generate_token({"data": user.email, "role": user.role})
        return tokens
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
        )
