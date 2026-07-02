import random

from locust import FastHttpUser, task, between


class SMARTAAsyncUser(FastHttpUser):
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
            self.headers = {"Authorization": f"Bearer {self.token}"}

            prod_resp = self.client.get("/api/v1/products", headers=self.headers)
            if prod_resp.status_code == 200:
                products = prod_resp.json().get("items", [])
                self.product_ids = [p["id"] for p in products]

            order_resp = self.client.get("/api/v1/orders?status=pending", headers=self.headers)
            if order_resp.status_code == 200:
                orders = order_resp.json().get("items", [])
                self.order_ids = [o["id"] for o in orders]

    @task(4)
    def list_products(self):
        self.client.get("/api/v1/products", headers=self.headers)

    @task(2)
    def confirm_order(self):
        if not self.order_ids:
            return
        order_id = random.choice(self.order_ids)
        self.client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=self.headers,
        )
