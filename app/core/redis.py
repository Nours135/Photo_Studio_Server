import redis.asyncio as aioredis
from typing import Optional
import os

class RedisClient:
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        
        self._redis_host = os.getenv("REDIS_HOST", "localhost")
        self._redis_port = int(os.getenv("REDIS_PORT", 6379))
        self._redis_password = os.getenv("REDIS_PASSWORD", None)
    
    async def get_client(self, db: int = 0) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                f"redis://{self._redis_host}:{self._redis_port}/{db}",
                password=self._redis_password,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        return self._client


    