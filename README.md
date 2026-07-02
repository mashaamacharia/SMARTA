# SMARTA — Backend API

**SMARTA** is a production-ready async FastAPI backend for retail/pharmacy/clinic/hotel businesses. It provides auth (JWT), inventory management, order processing with concurrency-safe stock deduction, and a benchmark harness to validate the async architecture decision.

---

## Architecture Decision: Why Async?

The entire production API is built on **asynchronous I/O** (FastAPI + SQLAlchemy 2.0 async + asyncpg). This is the correct choice for SMARTA's workload profile:

| Workload | I/O-bound? | Benefits from async? |
|---|---|---|
| DB queries (PostgreSQL) | Yes | Async pools overlap waits |
| WhatsApp/SMS notifications | Yes | Non-blocking HTTP calls |
| LLM calls (future) | Yes | High-latency, no CPU work |
| Request handling | Mixed | Async FastAPI handles more concurrent connections with fewer OS threads |

A minimal **sync benchmark harness** (2 endpoints: `GET /api/v1/benchmark-sync/products`, `PATCH /api/v1/benchmark-sync/orders/{id}/status`) exists solely to validate this decision with real performance data — it is **not part of the shipped product**.

---

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 15
- Docker & Docker Compose (optional)

### Local Development

```bash
# Clone and enter the project
cd smarta

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker (Full Stack)

```bash
docker-compose up --build
```

This starts:
- **API** on `http://localhost:8000`
- **PostgreSQL 15** on `:5432`
- **pgAdmin** (dev profile) on `http://localhost:5050` — `docker-compose --profile dev up`

Migrations run automatically on container start.

---

## API Endpoints

### Auth (async)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register business + owner |
| POST | `/api/v1/auth/login` | Login → access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate refresh token |
| POST | `/api/v1/auth/logout` | No-op (Redis denylist in Project 2) |
| GET | `/api/v1/auth/me` | Current user profile |

### Products (async)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/products` | Paginated list (search, category, low_stock filters) |
| POST | `/api/v1/products` | Create product |
| GET | `/api/v1/products/{id}` | Get single product |
| PUT | `/api/v1/products/{id}` | Update product |
| DELETE | `/api/v1/products/{id}` | Soft delete |
| POST | `/api/v1/products/{id}/adjust` | Adjust stock with movement log |

### Orders (async)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/orders` | Paginated list (status, date, customer filters) |
| POST | `/api/v1/orders` | Create order (pending) |
| GET | `/api/v1/orders/{id}` | Get order with items |
| PATCH | `/api/v1/orders/{id}/status` | Update status (pending → confirmed → fulfilled) |

### Benchmark (sync — NOT SHIPPED)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/benchmark-sync/products` | List products (sync) |
| PATCH | `/api/v1/benchmark-sync/orders/{id}/status` | Update order status (sync) |

---

## Concurrency Safety: Overselling Prevention

Order confirm uses `SELECT ... FOR UPDATE` row-level locking to prevent overselling under concurrent requests:

```python
# In order_service.py :: confirm_order
for item in order.items:
    product = await db.execute(
        select(Product).where(Product.id == item.product_id).with_for_update()
    )
    if product.quantity < item.quantity:
        raise InsufficientStockError(...)
    product.quantity -= item.quantity
```

This ensures that when two confirm requests arrive simultaneously for the same product:
1. The first request acquires the row lock
2. The second request **waits** for the first to complete
3. If the first consumes the last unit, the second sees `quantity < requested` and returns **409 Conflict**

The same locking strategy is mirrored in the sync benchmark harness.

### Expected Results

| Concurrency Level | Async (req/s) | Sync (req/s) | Oversell Count |
|---|---|---|---|
| 100 users | (measure) | (measure) | 0 |
| 500 users | (measure) | (measure) | 0 |
| 1,000 users | (measure) | (measure) | 0 |

(Insert your Locust results here after running the benchmarks.)

---

## Running Locust Benchmarks

### Prerequisites

Ensure the API is running with seed data:

```bash
# Start the API (local or Docker)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Async Benchmark

```bash
locust -f locust/locustfile_async.py --host http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 60s --headless \
  --html locust/report_async.html
```

### Sync Benchmark

```bash
locust -f locust/locustfile_sync.py --host http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 60s --headless \
  --html locust/report_sync.html
```

Run at 100, 500, and 1,000 concurrent users for each variant.

### Verifying Oversell Count = 0

After each benchmark run:

```sql
SELECT p.name, p.sku, p.quantity,
       SUM(sm.quantity_change) AS total_deducted
FROM products p
JOIN stock_movements sm ON sm.product_id = p.id
WHERE sm.movement_type = 'sale'
GROUP BY p.id, p.name, p.sku, p.quantity
HAVING p.quantity < 0;
```

Any row returned means a race condition allowed overselling. Expected: **0 rows**.

---

## Project Structure

```
smarta/
├── app/
│   ├── main.py                   # FastAPI app entry point
│   ├── core/
│   │   ├── config.py             # pydantic-settings
│   │   ├── security.py           # JWT + bcrypt
│   │   └── database.py           # Async engine + session
│   ├── models/                   # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic request/response
│   ├── api/v1/
│   │   ├── auth.py, products.py, orders.py
│   │   └── benchmark_sync/       # Sync harness (throwaway)
│   └── services/                 # Business logic layer
├── alembic/                      # DB migrations
├── tests/                        # pytest suite
├── locust/                       # Load test scripts
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

## Running Tests

```bash
pytest tests/ -v --asyncio-mode=auto
```

---

## Tenant Isolation

Every product/order/customer query is scoped to the authenticated user's `business_id` via the `get_current_business` dependency. A `business_id` passed in a request body is **never trusted** — the system always reads it from the JWT.

Composite unique constraints enforce data integrity:
- `UNIQUE(business_id, email)` on users — same email OK across businesses, not within one
- `UNIQUE(business_id, sku)` on products — SKU uniqueness per tenant

---

## License

Internal use — SMARTA Project 1
