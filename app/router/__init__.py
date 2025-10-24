from fastapi import APIRouter
from app.router.web import router as web_router
from app.router.api import router as api_router

router = APIRouter()

router.include_router(web_router)
router.include_router(api_router)
