from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from jose.exceptions import JWTClaimsError
from sqlalchemy.ext.asyncio import AsyncSession

from source.utils.hasher import PasswordManager
from source.config import get_settings
from source.shemas.endpoint_shemas import Credentials, Token
from source.db.models import User
from source.db.methods import get_user_by_email, get_async_session
from source.routers.auth.exception import credentials_exception

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
hashed = PasswordManager()
settings = get_settings()

async def authenticate_user(user_data: Credentials, db: AsyncSession) -> Optional[User]:
    user = await get_user_by_email(db, str(user_data.email))
    if not user:
        return None
    user = user
    if not hashed.verify_password(user_data.password, user.password):
        return None
    return user

async def generate_token(data: Dict[str, Any], expires_delta: timedelta = None) -> Token:
    access_to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_to_encode.update({"exp": expire})
    access_token = jwt.encode(
        access_to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )
    return Token(access_token=access_token)

async def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except (JWTError, ExpiredSignatureError, JWTClaimsError):
        return None

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_async_session),
):
    payload = await decode_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("data")
    if username is None:
        raise credentials_exception
    user = await get_user_by_email(db, username)
    if user is None:
        raise credentials_exception
    return user
