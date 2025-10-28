import redis.asyncio as aioredis
from typing import Optional
import os

class RedisClient:
    _client: Optional[aioredis.Redis] = None
    _redis_host: str = os.getenv("REDIS_HOST", "localhost")
    _redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    _redis_password: str = os.getenv("REDIS_PASSWORD", None)
    
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


    