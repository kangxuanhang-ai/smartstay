import asyncio
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import init_db
from app.core.seed import seed_default_users, seed_default_rooms


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def biz_token(client):
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "qiantai", "password": "123456"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def guest_token(client):
    resp = await client.post(
        "/api/auth/login",
        json={"id_card": "100000000000000101", "password": "123456"},
    )
    return resp.json()["access_token"]
