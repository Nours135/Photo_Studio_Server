
import json
import os
# load env
from dotenv import load_dotenv
load_dotenv()


# set up api limiters
from fastapi import FastAPI, Depends, Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as aioredis


# init logger
from logger_config import get_logger
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





