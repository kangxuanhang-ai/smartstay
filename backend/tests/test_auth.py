import pytest


@pytest.mark.asyncio
async def test_biz_login_success(client):
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "qiantai", "password": "123456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_biz_login_wrong_password(client):
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "qiantai", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_biz_login_invalid_role(client):
    """Manager should not be able to login via C端 endpoint"""
    resp = await client.post(
        "/api/auth/login",
        json={"id_card": "dianzhang", "password": "123456"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_guest_login_success(client):
    resp = await client.post(
        "/api/auth/login",
        json={"id_card": "100000000000000101", "password": "123456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_me_endpoint(client, biz_token):
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {biz_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "front_desk"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_change_password(client):
    """Test change password with a dedicated test user to avoid affecting shared fixtures."""
    # Use the manager account for password change test (separate from front_desk fixture)
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "dianzhang", "password": "123456"},
    )
    token = resp.json()["access_token"]

    resp = await client.post(
        "/api/auth/change-password",
        json={
            "old_password": "123456",
            "new_password": "newpass456",
            "confirm_password": "newpass456",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Change it back so other tests don't break
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "dianzhang", "password": "newpass456"},
    )
    token2 = resp.json()["access_token"]

    resp = await client.post(
        "/api/auth/change-password",
        json={
            "old_password": "newpass456",
            "new_password": "123456",
            "confirm_password": "123456",
        },
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token(client):
    resp = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "qiantai", "password": "123456"},
    )
    refresh = resp.json()["refresh_token"]

    resp = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
