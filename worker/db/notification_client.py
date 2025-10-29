# notification client to notify the task completion for frontend 


import os

from app.core.redis import RedisClient
from app.logger_config import get_logger

logger = get_logger(__name__)

class NotificationClient:
    '''
    Notification client to notify the task completion for frontend by redis pub/sub
    '''
    def __init__(self, timeout: float = 60.0):
        self.redis = None
        self.timeout = timeout

    async def _init_redis(self):
        # not very necessary to use separate db for notification, but just in case
        self.redis = await RedisClient.get_client(db=int(os.getenv("REDIS_QUEUE_DB", 0)))  

    async def notify_task_status(self, task_id: str, message: str):
        '''
        Notify the task status for frontend
        message: JSON string
        Use one api for both task completion and failure
        '''
        if self.redis is None:
            await self._init_redis()
        await self.redis.publish(f"task:{task_id}", message)    