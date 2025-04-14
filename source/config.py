from functools import lru_cache

from dotenv import load_dotenv
from pydantic import (
    EmailStr,
    FieldValidationInfo,
    PostgresDsn,
    SecretStr,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    load_dotenv()

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASS: SecretStr
    DB_NAME: str

    PORT: int

    CREATE_ADMIN: bool = True
    ADMIN_LOGIN: str
    ADMIN_PASSWORD: SecretStr
    ADMIN_EMAIL: EmailStr

    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DB_URI: str | None = None

    @field_validator("DB_URI")
    @classmethod
    def validate_db_uri(cls, value: str | None, info: FieldValidationInfo):
        if isinstance(value, str):
            return value
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data["DB_USER"],
                password=info.data["DB_PASS"].get_secret_value(),
                host=info.data["DB_HOST"],
                port=info.data["DB_PORT"],
                path=info.data["DB_NAME"],
            )
        )

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()

if __name__ == "__main__":
    settings = get_settings()
    print(settings.DB_URI)
