import random

from locust import FastHttpUser, task, between


class SMARTASyncUser(FastHttpUser):
    wait_time = between(0.01, 0.05)
    host = "http://localhost:8000"

    token: str = ""
    product_ids: list[str] = []
    order_ids: list[str] = []

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "benchmark@smarta.com", "password": "benchmark"},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]

        prod_resp = self.client.get(
            "/api/v1/benchmark-sync/products",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if prod_resp.status_code == 200:
            self.product_ids = prod_resp.json().get("items", [])

        order_resp = self.client.get(
            "/api/v1/orders?status=pending",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if order_resp.status_code == 200:
            self.order_ids = [o["id"] for o in order_resp.json().get("items", [])]

    @task(4)
    def list_products(self):
        self.client.get(
            "/api/v1/benchmark-sync/products",
            headers={"Authorization": f"Bearer {self.token}"},
        )

    @task(2)
    def confirm_order(self):
        if not self.order_ids:
            return
        order_id = random.choice(self.order_ids)
        self.client.patch(
            f"/api/v1/benchmark-sync/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
