
import json
import os
# load env
from dotenv import load_dotenv
load_dotenv()


# set up api limiters
from fastapi import FastAPI, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
import redis.asyncio as aioredis


# init logger
from app.logger_config import get_logger
logger = get_logger(__name__)


# set up fastapi app
app = FastAPI()


# include routers
from app.router import router as main_router
app.include_router(main_router)


# set up api limiter
@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(os.getenv("REDIS_URL"), encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)

