# queue to manage background tasks
## can be implemented as Redis queue or SQS queue
from pydantic import BaseModel, Field
from uuid import UUID
import os 
from datetime import datetime
from typing import Any
from app.core.redis import RedisClient
from app.logger_config import get_logger

logger = get_logger(__name__)


# ========================== Task class ==========================
class QueueTaskPayload(BaseModel):  # similar to dataclass but with pydantic
    task_id: UUID
    task_type: str
    user_id: UUID
    input_image_s3_key: str  # All paths can be inferred from this key
    parameters: dict | None = None
    created_at: datetime = Field(default_factory=datetime.now) 


# ========================== Redis-based queue service ==========================
class BaseTaskQueueService:
    '''Task queue service
    FIFO queue for pending tasks
    '''
    
    QUEUE_NAME = "tasks:pending"

    def enqueue(self, task: Any) -> bool:
        raise NotImplementedError("Not implemented")
    
    def dequeue(self) -> Any:
        raise NotImplementedError("Not implemented")


class RedisTaskQueueService(BaseTaskQueueService):
    '''Redis-based queue service for pending tasks'''
    def __init__(self, timeout: float = 60.0):
        self.redis = None
        self.timeout = timeout

    async def _init_redis(self):
        self.redis = await RedisClient.get_client(db=int(os.getenv("REDIS_QUEUE_DB", 0)))  # use db 0 for queue

    async def enqueue(self, task_payload: QueueTaskPayload) -> bool:
        if self.redis is None:
            await self._init_redis()
        serialized = task_payload.model_dump_json()  
        return await self.redis.lpush(self.QUEUE_NAME, serialized)
    
    async def dequeue(self) -> QueueTaskPayload:
        if self.redis is None:
            await self._init_redis()
        result = await self.redis.brpop(self.QUEUE_NAME, timeout=self.timeout)
        if result:
            _, serialized = result  # brpop returns (key, value)
            return QueueTaskPayload.model_validate_json(serialized)
        return None