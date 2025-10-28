# queue client to retirve tasks from queue

from app.core.queue import BaseQueueClient, RedisTaskQueueService, QueueTaskPayload
from app.logger_config import get_logger
from worker.worker_config import get_worker_config

config = get_worker_config()
logger = get_logger(__name__)


def get_queue_client(config) -> BaseQueueClient:
    if config['ENV'] == 'local':
        return RedisTaskQueueService()
    else:
        raise NotImplementedError(f"Queue client for {config['ENV']} is not implemented yet")
        # return SQSQueueClient()


class QueueClient:
    '''
    Queue client for all queue clients
    '''
    def __init__(self):
        config = get_worker_config()
        self.queue_client = get_queue_client(config)

    async def get_task(self) -> QueueTaskPayload:
        return await self.queue_client.dequeue()

