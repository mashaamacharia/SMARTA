from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.reports import router as reports_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(products_router)
router.include_router(orders_router)
router.include_router(reports_router)
router.include_router(admin_router)
