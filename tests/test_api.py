import pytest


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "business_name": "Test Business",
            "business_email": "test@business.com",
            "business_phone": "+254700000000",
            "business_type": "retail",
            "owner_full_name": "Test Owner",
            "owner_email": "owner@test.com",
            "owner_password": "testpass123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_me(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "owner@test.com"


@pytest.mark.asyncio
async def test_create_product(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Test Product",
            "sku": "TST-001",
            "unit_price": "100.00",
            "cost_price": "60.00",
            "quantity": 50,
            "units": "pcs",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Product"
    assert data["sku"] == "TST-001"


@pytest.mark.asyncio
async def test_list_products(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_adjust_stock_negative_rejected(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    list_resp = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    product_id = list_resp.json()["items"][0]["id"]

    resp = await client.post(
        f"/api/v1/products/{product_id}/adjust",
        json={"quantity_change": -9999, "reason": "adjustment"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_order(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    list_resp = await client.get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    product_id = list_resp.json()["items"][0]["id"]

    resp = await client.post(
        "/api/v1/orders",
        json={
            "channel": "walk_in",
            "items": [{"product_id": product_id, "quantity": 2}],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_confirm_order(client):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@test.com", "password": "testpass123"},
    )
    token = login_resp.json()["access_token"]

    orders_resp = await client.get(
        "/api/v1/orders?status=pending",
        headers={"Authorization": f"Bearer {token}"},
    )
    orders = orders_resp.json().get("items", [])
    if not orders:
        return

    resp = await client.patch(
        f"/api/v1/orders/{orders[0]['id']}/status",
        json={"status": "confirmed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
