import pytest


@pytest.mark.asyncio
async def test_checkin_and_checkout(client, biz_token):
    # Get vacant room
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    vacant = next((r for r in resp.json() if r["status"] == "vacant"), None)
    assert vacant is not None, "No vacant room available"

    # Check-in
    resp = await client.post(
        "/api/orders/checkin",
        json={
            "id_card": "429005199001011237",
            "phone": "13811110003",
            "name": "test_checkin",
            "room_id": vacant["id"],
        },
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]

    # Verify room status
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    room = next(r for r in resp.json() if r["id"] == vacant["id"])
    assert room["status"] == "occupied"

    # Checkout
    resp = await client.put(
        f"/api/orders/{order_id}/checkout",
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200

    # Verify room dirty
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    room = next(r for r in resp.json() if r["id"] == vacant["id"])
    assert room["status"] == "dirty"

    # Clean up - set back to vacant
    await client.put(
        f"/api/rooms/{vacant['id']}/status",
        json={"status": "vacant"},
        headers={"Authorization": f"Bearer {biz_token}"},
    )


@pytest.mark.asyncio
async def test_checkin_requires_frontdesk(client, guest_token):
    resp = await client.post(
        "/api/orders/checkin",
        json={
            "id_card": "429005199001011238",
            "phone": "13811110004",
            "name": "test",
            "room_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_checkin_room_not_found(client, biz_token):
    resp = await client.post(
        "/api/orders/checkin",
        json={
            "id_card": "429005199001011239",
            "phone": "13811110005",
            "name": "test",
            "room_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invoice(client, biz_token):
    """Test invoice submission"""
    # First check in a guest to get an order
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    vacant = next((r for r in resp.json() if r["status"] == "vacant"), None)
    assert vacant is not None

    resp = await client.post(
        "/api/orders/checkin",
        json={
            "id_card": "429005199001011240",
            "phone": "13811110006",
            "name": "invoice_test",
            "room_id": vacant["id"],
        },
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]

    # Guest login to submit invoice
    resp = await client.post(
        "/api/auth/login",
        json={"id_card": "429005199001011240", "password": "123456"},
    )
    guest_token = resp.json()["access_token"]

    resp = await client.put(
        f"/api/orders/{order_id}/invoice",
        json={"company_name": "测试公司", "tax_id": "91110000TEST", "email": "test@test.com"},
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert resp.status_code == 200
