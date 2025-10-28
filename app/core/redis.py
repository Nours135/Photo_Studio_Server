import redis.asyncio as aioredis
from typing import Optional
import os

class RedisClient:
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        
        self._redis_host = os.getenv("REDIS_HOST", "localhost")
        self._redis_port = int(os.getenv("REDIS_PORT", 6379))
        self._redis_password = os.getenv("REDIS_PASSWORD", None)

    @classmethod
    async def get_client(cls, db: int = 0) -> aioredis.Redis:
        if cls._client is None:
            cls._client = await aioredis.from_url(
                f"redis://{cls._redis_host}:{cls._redis_port}/{db}",
                password=cls._redis_password,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        return cls._client


    