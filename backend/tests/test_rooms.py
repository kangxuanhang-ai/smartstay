import pytest


@pytest.mark.asyncio
async def test_get_rooms_requires_auth(client):
    resp = await client.get("/api/rooms/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_all_rooms(client, biz_token):
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) >= 1
    for room in rooms:
        assert "room_number" in room
        assert "status" in room
        assert "room_type" in room


@pytest.mark.asyncio
async def test_guest_cannot_access_all_rooms(client, guest_token):
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {guest_token}"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_room_status(client, biz_token):
    resp = await client.get(
        "/api/rooms/", headers={"Authorization": f"Bearer {biz_token}"}
    )
    rooms = resp.json()
    room_id = rooms[0]["id"]

    resp = await client.put(
        f"/api/rooms/{room_id}/status",
        json={"status": "maintenance"},
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200

    resp = await client.put(
        f"/api/rooms/{room_id}/status",
        json={"status": "vacant"},
        headers={"Authorization": f"Bearer {biz_token}"},
    )
    assert resp.status_code == 200
