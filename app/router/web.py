from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi_limiter.depends import RateLimiter
from fastapi import Depends
from app.core.dependencies import get_strict_rate_limiter, get_moderate_rate_limiter

import os

router = APIRouter()

templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse, dependencies=[get_moderate_rate_limiter()])
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/login", response_class=HTMLResponse, dependencies=[get_moderate_rate_limiter()])
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse, dependencies=[get_moderate_rate_limiter()])
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/upload", response_class=HTMLResponse, dependencies=[get_moderate_rate_limiter()])
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@router.get("/tasks", response_class=HTMLResponse, dependencies=[get_moderate_rate_limiter()])
async def tasks_page(request: Request):
    return templates.TemplateResponse("tasks.html", {"request": request})
