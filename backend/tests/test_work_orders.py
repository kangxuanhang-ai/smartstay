import pytest


@pytest.mark.asyncio
async def test_get_all_work_orders(client, biz_token):
    resp = await client.get(
        "/api/work-orders/",
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200
    orders = resp.json()
    assert isinstance(orders, list)


@pytest.mark.asyncio
async def test_create_work_order(client):
    resp = await client.post(
        "/api/work-orders/",
        json={
            "room_id": "3ef02e9d-6979-4b72-89ff-3d283da3a417",
            "type": "repair",
            "content": "马桶堵塞，需要维修",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["type"] == "repair"
    wo_id = data["id"]

    # Test accept (need front_desk token)
    resp2 = await client.post(
        "/api/auth/login/biz",
        json={"id_card": "qiantai", "password": "123456"},
    )
    biz_token = resp2.json()["access_token"]

    resp3 = await client.put(
        f"/api/work-orders/{wo_id}/accept",
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp3.status_code == 200
