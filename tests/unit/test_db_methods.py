# tests/unit/test_db_methods.py
import pytest
import asyncio
from uuid import UUID

import pytest_asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession
)
from sqlalchemy.orm import sessionmaker

from source.db.models import Base, User, PVZTable, Reception, Product
from source.db.methods import (
    create_user,
    get_user_by_email,
    create_pvz,
    create_reception_for_pvz,
    create_product_for_reception,
    get_last_reception_by_pvz,
    get_pvz_by_reception_id,
    close_reception_for_pvz,
    delete_last_product_for_reception,
    get_pvz_receptions_products,
    get_or_create_dummy_user
)
from source.shemas.endpoint_shemas import (
    Registration,
    PVZUnit,
    ProductUnit,
    PVZList,
    DummyUser
)
from source.db.db_types import ReceptionStatus, RoleType

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def session(engine):
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as s:
        yield s
        await s.rollback()

@pytest.mark.asyncio
async def test_create_and_get_user(session):
    reg = Registration(email="u@example.com", password="secret", role=RoleType.employee)
    user = await create_user(session, reg)
    assert isinstance(user.id, UUID)
    assert user.email == "u@example.com"
    fetched = await get_user_by_email(session, "u@example.com")
    assert fetched.id == user.id

@pytest.mark.asyncio
async def test_create_pvz_and_read(session):
    pvz = await create_pvz(session, PVZUnit(city="Москва"))
    assert isinstance(pvz.id, UUID)
    assert pvz.city.value == "Москва"

@pytest.mark.asyncio
async def test_create_and_get_reception(session):
    pvz = await create_pvz(session, PVZUnit(city="Москва"))
    rec = await create_reception_for_pvz(session, pvz.id)
    assert rec.pvzId == pvz.id
    assert rec.status == ReceptionStatus.in_progress
    last = await get_last_reception_by_pvz(session, pvz.id)
    assert last.id == rec.id

@pytest.mark.asyncio
async def test_create_and_delete_product(session):
    pvz = await create_pvz(session, PVZUnit(city="Москва"))
    rec = await create_reception_for_pvz(session, pvz.id)
    prod_unit = ProductUnit(pvzId=pvz.id, type="электроника")
    prod = await create_product_for_reception(session, rec.id, prod_unit)
    assert prod.receptionId == rec.id
    deleted = await delete_last_product_for_reception(session, rec.id)
    assert deleted.id == prod.id
    none = await delete_last_product_for_reception(session, rec.id)
    assert none is None

@pytest.mark.asyncio
async def test_get_pvz_by_reception_id(session):
    pvz = await create_pvz(session, PVZUnit(city="Москва"))
    rec = await create_reception_for_pvz(session, pvz.id)
    fetched = await get_pvz_by_reception_id(session, rec.id)
    assert fetched.id == pvz.id

@pytest.mark.asyncio
async def test_close_reception(session):
    pvz = await create_pvz(session, PVZUnit(city="Москва"))
    close_rec = await close_reception_for_pvz(session, pvz.id)
    assert close_rec.status == ReceptionStatus.close
    last = await get_last_reception_by_pvz(session, pvz.id)
    assert last.id == close_rec.id

@pytest.mark.asyncio
async def test_get_pvz_receptions_products(session):
    pvz1 = await create_pvz(session, PVZUnit(city="Москва"))
    pvz2 = await create_pvz(session, PVZUnit(city="Москва"))
    rec1 = await create_reception_for_pvz(session, pvz1.id)
    for _ in range(3):
        await create_product_for_reception(session, rec1.id, ProductUnit(pvzId=pvz1.id, type="электроника"))
    rec2 = await create_reception_for_pvz(session, pvz2.id)
    await close_reception_for_pvz(session, pvz2.id)
    now = datetime.utcnow()
    params = PVZList(
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
        page=1,
        limit=10
    )
    result = await get_pvz_receptions_products(session, params)
    assert isinstance(result, list) and len(result) == 1
    entry = result[0]
    assert entry["pvz"] == pvz1.id
    assert len(entry["receptions"]) == 3

@pytest.mark.asyncio
async def test_get_or_create_dummy_user(session):
    dummy_mod = DummyUser(role=RoleType.moderator)
    user_mod = await get_or_create_dummy_user(session, dummy_mod)
    assert user_mod.role == RoleType.moderator
    again = await get_or_create_dummy_user(session, dummy_mod)
    assert again.id == user_mod.id
    dummy_emp = DummyUser(role=RoleType.employee)
    user_emp = await get_or_create_dummy_user(session, dummy_emp)
    assert user_emp.role == RoleType.employee
