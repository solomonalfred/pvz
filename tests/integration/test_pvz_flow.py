import pytest
from httpx import AsyncClient
from uuid import UUID

from source.app import app
from source.constants.routers import RouterInfo, Endpoints
from source.db.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session, monkeypatch):
    async def _get_test_session():
        yield db_session

    monkeypatch.setattr(
        "source.db.engine.get_async_session",
        lambda: _get_test_session()
    )

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.anyio
async def test_full_pvz_lifecycle(client: AsyncClient):
    dummy_url = f"{RouterInfo.prefix}{Endpoints.DUMMY}"
    resp = await client.post(dummy_url, json={"role": "moderator"})
    assert resp.status_code == 200
    token_mod = resp.json()["access_token"]
    headers_mod = {"Authorization": f"Bearer {token_mod}"}

    resp = await client.post(
        Endpoints.PVZ_END,
        json={"city": "Москва"},
        headers=headers_mod
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "ПВЗ создан"

    start = "01.01.202000:00:00"
    end   = "01.01.203000:00:00"
    list_url = f"{Endpoints.PVZ_END}?start_date={start}&end_date={end}&page=1&limit=10"
    resp = await client.get(list_url, headers=headers_mod)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 3
    pvz_id = UUID(data[0]["pvz"])

    resp_emp = await client.post(dummy_url, json={"role": "employee"})
    assert resp_emp.status_code == 200
    token_emp = resp_emp.json()["access_token"]
    headers_emp = {"Authorization": f"Bearer {token_emp}"}

    rec_url = f"{Endpoints.RECEPTIONS}?pvz_id={pvz_id}"
    resp = await client.post(rec_url, headers=headers_emp)
    assert resp.status_code == 201 or resp.status_code == 400

    for _ in range(50):
        resp = await client.post(
            Endpoints.PRODUCTS,
            json={"pvzId": str(pvz_id), "type": "электроника"},
            headers=headers_emp
        )
        assert resp.status_code == 201

    close_url = f"{Endpoints.CLOSE_LAST_REC}?pvz_id={pvz_id}"
    resp = await client.post(close_url, headers=headers_emp)
    assert resp.status_code == 200
    assert resp.json()["description"] == "Приемка закрыта"
