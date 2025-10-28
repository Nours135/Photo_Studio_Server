from fastapi import APIRouter
from app.router.api.auth import router as auth_router
from app.router.api.tasks import router as tasks_router
from app.router.api.images import router as images_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(tasks_router)
router.include_router(images_router)
