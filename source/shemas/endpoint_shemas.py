from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from source.db.db_types import RoleType, ProductType, CityType


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DummyUser(BaseModel):
    role: RoleType

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class Registration(Credentials, DummyUser):
    pass

class PVZUnit(BaseModel):
    city: CityType

class PVZList(BaseModel):
    start_date: datetime
    end_date: datetime
    page: int = Field(1, ge=1)
    limit: int = Field(1, ge=1, le=30)

class PVZID(BaseModel):
    pvzId: UUID

class ProductUnit(PVZID):
    type: ProductType

class ResponseMessage(BaseModel):
    description: str
