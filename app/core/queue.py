# queue to manage background tasks
## can be implemented as Redis queue or SQS queue
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import redis.asyncio as aioredis
from typing import Any
import json



# ========================== Task class ==========================
class QueueTaskPayload(BaseModel):  # similar to dataclass but with pydantic
    task_id: UUID
    task_type: str
    user_id: UUID
    input_image_s3_key: str
    input_image_local_path: str
    parameters: dict | None = None
    created_at: datetime


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
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def enqueue(self, task_payload: QueueTaskPayload) -> bool:
        serialized = task_payload.model_dump_json()  # 已经是 JSON 字符串，不需要 json.dumps
        return await self.redis.lpush(self.QUEUE_NAME, serialized)
    
    async def dequeue(self) -> QueueTaskPayload:
        serialized = await self.redis.rpop(self.QUEUE_NAME)
        if serialized:
            return QueueTaskPayload.model_validate_json(serialized)
        return None