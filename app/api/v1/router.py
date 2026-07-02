from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as products_router
from app.api.v1.orders import router as orders_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(products_router)
router.include_router(orders_router)
