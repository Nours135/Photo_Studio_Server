from fastapi import APIRouter
from app.router.api.file_upload import router as file_upload_router
from app.router.api.auth import router as auth_router
from app.router.api.tasks import router as tasks_router

router = APIRouter(prefix="/api")

router.include_router(auth_router)
router.include_router(tasks_router)
router.include_router(file_upload_router)
