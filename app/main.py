
import json
import os
from dotenv import load_dotenv
import uuid
from fastapi import FastAPI, Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response
from fastapi_limiter import FastAPILimiter
import redis.asyncio as aioredis

from app.monitoring import MetricsMiddleware

load_dotenv()


# init logger
from app.logger_config import get_logger, set_trace_id, clear_trace_id
logger = get_logger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        set_trace_id(trace_id)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = trace_id
            return response
        finally:
            clear_trace_id()


app = FastAPI()
app.add_middleware(TraceIdMiddleware)
app.add_middleware(MetricsMiddleware)


# include routers
from app.router import router as main_router
app.include_router(main_router)


# set up api limiter
@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(os.getenv("REDIS_URL"), encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)

