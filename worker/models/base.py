# provide base inference framework for all tasks
from typing import Any, Dict
import threading
import time
import asyncio

from worker.worker_config import get_worker_config
from worker.db.queue_client import QueueClient
from app.logger_config import get_logger
from app.core.queue import QueueTaskPayload

logger = get_logger(__name__)

class BaseModel:
    '''
    Base model class for all models, define the base interface for all models and some shared functionality
    '''
    def __init__(self, keep_alive_seconds: int = 60 * 60):
        # config
        self.config = get_worker_config()
        self._keep_alive_seconds = keep_alive_seconds  # 1 hour default, config of this model

        # status
        self._running = True
        self._last_used_time = asyncio.get_event_loop().time()

        # model status
        self._is_loaded = False
        self._model = None
        self._model_lock = asyncio.Lock()  # DO need a lock to protect the model from being used and unloaded at the same time

        # stats
        self.stats = {
            'total_tasks_processed': 0,
            'total_successed': 0,
            'total_inference_time': []
        }        

    async def start(self):
        '''
        management method 
        '''
        self._running = True
        self._last_used_time = asyncio.get_event_loop().time()

    
    async def stop(self):
        '''
        management method
        '''
        self._running = False

    async def predict_async(self, task: QueueTaskPayload):
        '''
        Wrapper of inference method for all models
        '''
        async with self._model_lock:
            if not self._is_loaded:
                await self._lazy_load_model()  
            self.stats['total_tasks_processed'] += 1
            start_time = asyncio.get_event_loop().time()
            result = await self._inference(task)  # inference method to be implemented in subclass
            end_time = asyncio.get_event_loop().time()
            self.stats['total_inference_time'].append(end_time - start_time)
            self.stats['total_successed'] += 1
            self._last_used_time = end_time
            return result
            

    async def _inference(self, input: Any) -> Any:
        raise NotImplementedError("Not implemented")

    async def _lazy_load_model(self):   # need IO, so async
        raise NotImplementedError("Not implemented")

    def _unload_model(self):
        raise NotImplementedError("Not implemented")

    async def start_idle_detection(self):
        while self._running:
            try:
                idle_time = asyncio.get_event_loop().time() - self._last_used_time
                async with self._model_lock:  # lock to protect the model from being used and unloaded at the same time
                    if self._is_loaded and self._model is not None:
                        if idle_time > self._keep_alive_seconds:
                            logger.info(f"Unloading idle model")
                            self._unload_model()
        
                await asyncio.sleep(self._keep_alive_seconds - idle_time + 1) 
            except Exception as e:
                logger.error(f"Idle detection error: {e}", exc_info=True)
                await asyncio.sleep(self._keep_alive_seconds - idle_time + 1)
